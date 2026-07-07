# ShotFlow — From Zero to a 4K Master

English (current) | [中文](./tutorial.zh.md)

> A hands-on, end-to-end tutorial for making a 3–5 minute AIGC short film with the ShotFlow pipeline. The example film *Echo of the Singularity* runs as the through-line, but every step is meant to be swapped for your own story.

This is the same workflow that produced *Echo of the Singularity*. It is not a generic "AIGC video tips" guide — every command and file path below points at real scripts and workflows in this repo.

---

## 1. Introduction

### What this tutorial helps you do

Walk a single short film from a one-line idea all the way to a 4K master, a per-platform release package, and a ComfyUI workflow bundle you can re-run on the next project. By the end you will have:

- A script, world bible, and character bible that keyframe prompts can be generated from mechanically.
- 24+ on-model keyframes that pass a blind consistency test.
- ~24 video shots, generated locally on Wan2.2 or via the Kling API depending on shot complexity.
- Dialogue and score stems, mixed to web/cinema loudness targets.
- A DaVinci-cut, teal-and-orange graded, Topaz-upscaled 4K master.
- A delivery package per platform (Bilibili / YouTube / Douyin / Xiaohongshu / WeChat / Reels / festival), with AIGC disclosure baked in.

### Who this is for

People who already have a story idea and want to ship it as a film, not a demo reel. You should be comfortable on the command line, be willing to install ComfyUI, and ideally have access to a 24 GB NVIDIA GPU. Editors and producers without a GPU can still run the whole chain in `SIMULATE_MODE` to learn the pipeline, then move to a GPU host for real generation.

### What you need

| Item | Minimum | Recommended |
|------|---------|-------------|
| GPU | RTX 3090 24 GB | RTX 4090 24 GB |
| RAM | 32 GB | 64 GB |
| Storage | 200 GB SSD | 1 TB NVMe |
| OS | Ubuntu 22.04 | Ubuntu 22.04 / Windows 11 |
| ComfyUI | Latest | Latest, with ComfyUI Manager |
| DaVinci Resolve | 18 (free) | 19 |
| Topaz Video AI | Personal | Pro |
| API keys | Kling (PiAPI) for complex shots | + ElevenLabs + Suno for audio |

CPU-only? Skip local Wan2.2 and route every shot through cloud APIs (Kling / Runway). The pipeline's provider scorer handles this automatically when `settings.HAS_GPU=false`.

### The pipeline at a glance

See [`AIGC_Experience_Chain.md`](../AIGC_Experience_Chain.md) for the reasoning behind every choice. The short version: pre-production locks the character, Flux.1 Kontext + IPAdapter locks the face, Wan2.2 handles standard shots, Kling handles complex shots, DaVinci + ElevenLabs + Suno + Topaz finish the film.

---

## 2. Prerequisites & Setup

### 2.1 Clone the repo

```bash
git clone https://github.com/MS33834/ShotFlow.git
cd ShotFlow
```

### 2.2 Pick a deployment mode

**Option A — Docker (fastest look, no GPU needed to learn the shape):**

```bash
cp .env.example .env            # then edit .env — see 2.4 below
docker compose up -d            # postgres + redis + backend + worker + frontend
```

The image ships Python deps and project scripts. ComfyUI and model weights are **not** bundled (licensing + size). Use Option B on the GPU host.

**Option B — Local source (real generation):**

```bash
cp .env.example .env            # edit .env — see 2.4
bash 08_Automation/deploy_comfyui.sh    # needs NVIDIA GPU, RTX 4090 24GB recommended
make setup                      # install Python deps (black, isort, pytest included)
make check                      # verify project structure
```

### 2.3 Deploy ComfyUI (GPU host only)

`08_Automation/deploy_comfyui.sh` clones ComfyUI, installs ComfyUI Manager, and pulls the custom nodes the project workflows depend on. The model files you still need to place by hand — see [`04_SOP/sop_shotflow.md`](../04_SOP/sop_shotflow.md) §1.3 for the exact list and HuggingFace sources:

| Model | Drop into |
|-------|-----------|
| FLUX.1-Kontext-dev (FP8 / FP4) | `ComfyUI/models/diffusion_models/` |
| Wan2.2-I2V-A14B FP8 | `ComfyUI/models/diffusion_models/` |
| Wan2.2 VAE | `ComfyUI/models/vae/` |
| umt5_xxl_fp8_e4m3fn_scaled | `ComfyUI/models/text_encoders/` |
| IPAdapter / PuLID model packs | per node docs |

Start ComfyUI and confirm it answers on the URL you set in `.env`:

```bash
cd ~/ComfyUI && python main.py --listen --port 8188
curl http://127.0.0.1:8188/system_stats
```

### 2.4 Configure `.env`

Copy `.env.example` and fill the keys you actually have. Everything you do not have stays blank — the matching service falls back to `SIMULATE_MODE`.

```ini
# Application
SIMULATE_MODE=true              # true = mock output, no GPU needed. false = hit real backends.
SECRET_KEY=                     # docker compose refuses to start without this. Generate with: openssl rand -hex 32

# ComfyUI
COMFYUI_URL=http://127.0.0.1:8188
COMFYUI_DIR=${HOME}/ComfyUI

# Cloud APIs
KLING_API_KEY=                  # via PiAPI: https://api.piapi.ai
KLING_BASE_URL=https://api.piapi.ai
ELEVENLABS_API_KEY=
SUNO_API_KEY=
SUNO_BASE_URL=https://api.sunoaiapi.com
```

### 2.5 About `SIMULATE_MODE`

`SIMULATE_MODE=true` is the project's "learn without a GPU" switch. When it is on:

- Every generation service in `backend/app/services/` returns mock output instead of calling ComfyUI / Kling / ElevenLabs / Suno.
- The pipeline shape, queue, SSE events, and CSV logs all still work — you can rehearse the whole film without spending API credits.

Flip to `false` on a GPU host with real API keys to actually generate. The companion setting `settings.HAS_GPU` (default `true`) feeds the provider scorer — see Step 3.

### 2.6 Sanity check

```bash
python 08_Automation/preflight_check.py --dry-run    # structure + key presence, no GPU needed
make check                                           # repo structure
```

If `preflight_check.py` reports GPU unavailable and you do have a GPU, reinstall the CUDA build of PyTorch from https://pytorch.org — the CPU wheel gets pulled in by mistake fairly often.

---

## 3. Step 1: Script & World-building

The goal of this step is to produce a set of plain-text documents that downstream prompts can be generated from mechanically — so the director and the prompt engineer are not improvising in the same step.

### 3.1 Use an LLM to draft the bible

We use DeepSeek or Claude. Feed them a tight brief (genre, runtime, tone) and ask for, in one pass:

1. **World setting** — era, place, the single core sci-fi premise, visual style keywords (color palette, light, texture).
2. **Character bible** — for each character: name, age, role, personality keywords, and a fixed list of **external anchors** (face, hair, eyes, scars, clothing, props). Anchors are what makes the next step possible.
3. **Scene-by-scene script** — for each shot: shot ID, duration, framing, camera move, generation method hint, emotion beat, dialogue if any.
4. **Prompt anchors** — one block of "every-shot-must-include" text per character, plus a negative-prompt block.

The worked example is [`02_Scripts/script_and_worldbuilding.md`](../02_Scripts/script_and_worldbuilding.md). Read its structure, then replace the content. Note how Ava's anchors are a single copy-pasteable block:

```
Ava, 28-year-old woman, short dark hair, amber eyes, light scar under right eye,
cybernetic neural interface glowing on back of neck, dark gray patched windbreaker,
black turtleneck, dark cargo pants, scuffed military boots, glowing bracelet on left wrist,
weathered data terminal at waist
```

### 3.2 Storyboard and keyframe prompts

From the script, produce two more documents:

- A **detailed storyboard** — see [`02_Scripts/detailed_storyboard.md`](../02_Scripts/detailed_storyboard.md). One row per shot with shot ID, scene, framing, duration, generation method, and prompt summary. The example has 24 shots across 5 scenes.
- A **keyframe prompts table** — see [`02_Scripts/keyframe_prompts.md`](../02_Scripts/keyframe_prompts.md). One row per keyframe with full positive prompt, negative prompt, resolution, and generation method. *Echo of the Singularity* has 29 keyframes (24 shots + 5 first/last-frame splits for Kling).

### 3.3 Lock the character bible separately

The character bible also gets its own file under `examples/echo-of-singularity/character_bible_ava.md` (template at `02_Scripts/character_bible_template.md`). This is the document the blind test in Step 2 is graded against — if two keyframes disagree with the bible, the bible wins.

### 3.4 Deliverables from this step

| File | Where | Used by |
|------|-------|---------|
| Script + world bible | `02_Scripts/script_and_worldbuilding.md` | Director, prompter |
| Detailed storyboard | `02_Scripts/detailed_storyboard.md` | Step 3 |
| Keyframe prompts | `02_Scripts/keyframe_prompts.md` | Step 2 |
| Character bible | `examples/echo-of-singularity/character_bible_ava.md` | Step 2 blind test |

Do not move on until the director has signed off on the shot count and the character anchors. Changing the anchors after Step 2 means regenerating every keyframe.

---

## 4. Step 2: Character Consistency Keyframes

This is the step where the film lives or dies. If the face drifts between shot 3 and shot 15, no amount of grading fixes it. We lock it with Flux.1 Kontext + IPAdapter and a blind test gate.

### 4.1 The workflow

Open [`03_Workflows/Flux_Character_Consistency.json`](../03_Workflows/Flux_Character_Consistency.json) in ComfyUI (the interface version). The API version used by scripts is [`03_Workflows/api/Flux_Character_Consistency_api.json`](../03_Workflows/api/Flux_Character_Consistency_api.json). Node wiring and dependencies are documented in [`03_Workflows/comfyui_node_connections.md`](../03_Workflows/comfyui_node_connections.md) and [`03_Workflows/node_dependencies.md`](../03_Workflows/node_dependencies.md).

Workflow in plain English:

1. Load three reference images of the character — front, side, back — into IPAdapter. These are your **anchor references**; they do not change between shots.
2. The positive prompt always starts with the character anchor block from Step 1, then adds the scene-specific beat.
3. Negative prompt always includes `inconsistent hairstyle, wrong clothing, different person, extra fingers, mutated hands, deformed face`.
4. Sample at 1024×1024 or 1280×720, 20–30 steps, CFG 3.5–4.5, FP8 precision.

### 4.2 Generate the reference angles first

Before touching the storyboard, generate Ava's three-view reference set and save to `01_Assets/Characters/Ava/`:

- `Ava_front.png`
- `Ava_side.png`
- `Ava_back.png`

These three are what IPAdapter binds to for every subsequent keyframe. Reroll until you can hand them to a teammate who has never seen the character and have them describe the same person.

### 4.3 Batch-generate the 29 keyframes

Use the script — do not click through ComfyUI one prompt at a time, you will lose track of seeds and parameters.

```bash
# Preview what will be generated — no GPU calls
python 08_Automation/batch_keyframe_gen.py --dry-run

# Actually generate
python 08_Automation/batch_keyframe_gen.py
```

The script reads the keyframe prompts table, calls the API workflow, and writes one PNG per keyframe to `01_Assets/Scenes/SF_{shot_id}_v01.png`. Every generation's seed, steps, CFG, and prompt are appended to `06_Research/video_gen_log.csv` — that is your reproducibility ledger.

### 4.4 The blind test gate

Before any keyframe goes into video production, run the blind test described in [`06_Research/qa_and_blind_test.md`](../06_Research/qa_and_blind_test.md):

1. Dump all 29 keyframes into a folder, filenames shuffled.
2. Hand them to someone who has not seen the storyboard.
3. Ask: "how many different people are in this folder?"
4. Pass = the answer is "one". Anything else = reroll the offending keyframes, raise IPAdapter weight toward 0.8–1.0, or add anchor keywords.

This gate is non-negotiable. It is much cheaper to reroll a keyframe than to reroll a 5-second video clip.

### 4.5 Deliverables from this step

- `01_Assets/Characters/Ava/{front,side,back}.png` — locked reference set
- `01_Assets/Scenes/SF_S{scene}_{shot}_v01.png` — 29 keyframes
- `06_Research/video_gen_log.csv` — parameters and seeds for every keyframe
- A signed-off blind test result

The shot tracker at [`examples/echo-of-singularity/shot_tracker.md`](../examples/echo-of-singularity/shot_tracker.md) is where you record which keyframes passed and which need another pass.

---

## 5. Step 3: Storyboard to Video

Each storyboard row now has a keyframe. The job is to turn 29 stills into ~24 motion clips, picking the right generator per shot.

### 5.1 Standard shots — Wan2.2 I2V 14B

Standard shots are dialogue, close-ups, slow pushes — anything where the motion is contained. These go through the local Wan2.2 I2V dual-expert workflow: [`03_Workflows/Wan22_Dual_Expert_Video.json`](../03_Workflows/Wan22_Dual_Expert_Video.json) (interface) and [`03_Workflows/api/Wan22_Dual_Expert_Video_api.json`](../03_Workflows/api/Wan22_Dual_Expert_Video_api.json) (API).

Why two experts? The **High-Noise expert** drives large motion; the **Low-Noise expert** repairs broken frames. The standard pattern is: generate the High-Noise pass first to get the motion, then run the Low-Noise pass on any shot that came out warped or flickery. See [`AIGC_Experience_Chain.md`](../AIGC_Experience_Chain.md) §Stage 2 for the rationale.

Parameters that actually matter (defaults are sane; tune only when a shot breaks):

- `frames`: 81 (= ~3.4 s at 24 fps). For 5 s shots, 121.
- `cfg`: 0.5–1.0. Lower = more motion, higher = more adherence to the keyframe.
- `steps`: 30.
- `negative_prompt`: always include `flickering, distorted motion, inconsistent character, mutated hands`.

### 5.2 Complex shots — Kling 2.5 Turbo keyframe-to-keyframe

Five shots in *Echo of the Singularity* involve camera moves the local model cannot keep coherent — the orbit around Ava at the core (`S03_04`), the hatch opening (`S02_05`), the pull-back at the end (`S05_04`). These go to Kling with **first-frame + last-frame** constraint: you give it two keyframes and it generates the motion between them.

Call it through the script:

```bash
python 08_Automation/kling_video_api.py --dry-run    # preview
python 08_Automation/kling_video_api.py              # real call
```

Kling parameters we use: `duration: 5`, `aspect_ratio: "16:9"`, `mode: "pro"`, `version: "2.5-turbo"`. Confirm `KLING_API_KEY` is set in `.env` first — see [`TROUBLESHOOTING.md`](../TROUBLESHOOTING.md) if calls come back slow or failing.

### 5.3 Run the whole storyboard in one command

```bash
python 08_Automation/storyboard_to_video.py --dry-run    # preview shot list and provider picks
python 08_Automation/storyboard_to_video.py              # generate
```

The script reads the storyboard, picks Wan2.2 or Kling per shot based on the `gen_method` column, and writes clips to `05_Output/Rough_Cuts/SF_{shot_id}_{tool}_v01.mp4`. Naming follows [`04_SOP/sop_shotflow.md`](../04_SOP/sop_shotflow.md) §6.1: `SCENE_SHOT_TAKE_TOOL_vNN.mp4`.

### 5.4 Provider auto-selection and fallback

When you run via the Web platform's render queue (Step 9) instead of the CLI, the backend's `render_tasks._dispatch` does provider selection for you. If you do not pin `extra.provider`, it calls `provider_scorer.recommend_provider` with the shot's `complexity` and `settings.HAS_GPU` and writes the chosen provider back as `extra._provider_source="auto"` so you can audit the decision later. See [`backend/app/services/provider_scorer.py`](../backend/app/services/provider_scorer.py) for the scoring dimensions (quality / speed / cost / capability) and weights.

In short: standard shot + GPU = local Wan2.2. Standard shot + no GPU = cloud. Complex shot = Kling regardless, because Wan2.2 cannot do first/last-frame constraint well.

### 5.5 QA every clip

```bash
python 08_Automation/video_quality_check.py
```

Checks resolution, frame rate, flicker, and sharpness against the shot tracker. Flicker is the most common failure — the fix is the Low-Noise expert pass or, failing that, Topaz temporal denoise in Step 5.

### 5.6 Deliverables from this step

- `05_Output/Rough_Cuts/SF_S{scene}_{shot}_{tool}_v01.mp4` — ~24 clips
- `06_Research/video_gen_log.csv` — every clip's parameters, seed, provider, retry count
- A shot tracker with status updated to "rendered" or "reroll"

---

## 6. Step 4: Audio Production

Picture is locked-ish. Now lay the sound. Audio is split into three tracks: dialogue (ElevenLabs), music (Suno), SFX (library + generation).

### 6.1 Voice bibles — lock the voice before generating a single line

Each character gets a voice bible entry that pins the TTS engine, voice ID, and per-dimension parameters (stability, similarity, style, speaker boost). The example is [`01_Assets/Audio/voice_bibles.md`](../01_Assets/Audio/voice_bibles.md). Ava's entry:

| Dimension | Setting |
|-----------|---------|
| ElevenLabs Voice | `Rachel` |
| Stability | 40% |
| Similarity | 75% |
| Style | 0.25 |
| Speaker Boost | on |
| Model | `eleven_multilingual_v2` |
| Post-processing | HPF 80 Hz, de-ess, light reverb RT60 0.4 s |

Once locked, **every** line for that character uses the same parameters. If you change them, you must bump the version number and regenerate the whole character — otherwise the voice drifts between shots and the edit falls apart. Calibration sample: `01_Assets/Audio/Dialogue/Ava/_reference_v1.wav`.

### 6.2 Generate dialogue

```bash
python 08_Automation/elevenlabs_tts_api.py --dry-run    # preview
python 08_Automation/elevenlabs_tts_api.py              # generate
```

Output: `01_Assets/Audio/Dialogue/{Role}/{Role}_{ShotID}_v1.wav`. Every line gets a manual listen — check character pronunciation, emotion match against the bible's emotion segments, and that there are no plosives or sibilance spikes.

### 6.3 Generate the score

```bash
python 08_Automation/suno_music_api.py --dry-run
python 08_Automation/suno_music_api.py
```

For *Echo of the Singularity* we asked for `sci-fi, cinematic, ambient, electronic` with per-scene mood tags (tense / hopeful / mysterious), generated 3–5 candidates per cue, and picked by ear. Output: `01_Assets/Audio/Music/{Theme}_v1.mp3`. Use a Pro or Premier Suno plan if the music goes into the final master — the free tier is non-commercial only (see [`06_Research/licensing_compliance.md`](../06_Research/licensing_compliance.md) §2.6).

### 6.4 The cue sheet — every audio event with timecodes

[`01_Assets/Audio/cue_sheet.md`](../01_Assets/Audio/cue_sheet.md) is the spine of the mix. It lists, for the full 4:10 runtime:

- **A1 dialogue** — 10 cues with in/out timecodes, role, file path
- **A3/A4 music** — 7 cues, theme + ambient layers, with side-chain ducking rules
- **A5/A6 SFX** — 10 cues, spot + ambience beds

Mix targets are pinned at the bottom of the cue sheet:

```
Dialogue  -6 dBFS   HPF 80 Hz, +2 dB @ 2 kHz
Music    -18 dBFS   side-chain compressed to dialogue
SFX      -20 dBFS   layered, panned to match screen action
Master   -1 dBTP    LUFS -16 (web)  /  LUFS -14 (cinema)
```

### 6.5 Web platform path (alternative)

If you are driving audio from the Web platform instead of the CLI, the same TTS and music scripts are wrapped by `backend/app/services/audio_service.py` (`run_tts_task`, `run_music_task`). It shells out to the same `08_Automation` scripts — same outputs, same naming, just submitted through the queue. In `SIMULATE_MODE` it returns mock paths so you can rehearse.

### 6.6 Deliverables from this step

- `01_Assets/Audio/Dialogue/{Role}/` — per-line WAV stems
- `01_Assets/Audio/Music/{Themes,Ambient}/` — music stems
- `01_Assets/Audio/SFX/{Environment,Mechanical,UI}/` — SFX stems (see [`01_Assets/Audio/sfx_list.md`](../01_Assets/Audio/sfx_list.md) for sources and license chain)
- `01_Assets/Audio/cue_sheet.md` — locked mix spine

---

## 7. Step 5: Post-production

Everything converges in DaVinci Resolve. The full editor walkthrough is [`05_Output/Final/assembly_guide.md`](../05_Output/Final/assembly_guide.md); this section is the executive summary.

### 7.1 Inputs

| Input | Location |
|-------|----------|
| Rendered shot clips | `05_Output/Renders/SF_S{scene}_{shot}_*.mp4` |
| Reference keyframes | `01_Assets/Scenes/SF_S*.png` |
| Edit decision list | [`05_Output/EDL/shotflow_v01.edl`](../05_Output/EDL/shotflow_v01.edl) |
| Dialogue / Music / SFX stems | `01_Assets/Audio/{Dialogue,Music,SFX}/` |
| Color LUT | `05_Output/Final/shotflow_grade.cube` |
| Subtitles | `05_Output/Final/subtitles/*.srt` |

### 7.2 Project settings

- Timeline: 3840×2160, 24 fps
- Color science: DaVinci YRGB Color Managed, ACEScct
- Output: Rec.709 (Scene) for web; DCI-P3 D65 for cinema

### 7.3 Build the timeline from the EDL

Edit page → Timeline → Import → EDL → select [`05_Output/EDL/shotflow_v01.edl`](../05_Output/EDL/shotflow_v01.edl). Enable "Relink to media pool", set handle frames to 12. The EDL lands on V1 with 24 events. Cross-check the total length against [`examples/echo-of-singularity/shot_tracker.md`](../examples/echo-of-singularity/shot_tracker.md) — should be ~4:10.

> The committed EDL is a v01 rough cut with 3–5 s per shot. Use the shot tracker's scene-level timecodes as the source of truth and trim/extend to match.

### 7.4 Lay audio on six tracks

A1 dialogue, A2 alt takes, A3 theme music, A4 ambient music, A5 spot SFX, A6 ambience bed. Pull in/out points from [`01_Assets/Audio/cue_sheet.md`](../01_Assets/Audio/cue_sheet.md). Side-chain A3/A4 to A1. Mix to the loudness targets in §6.4. Detailed mix rules are in [`05_Output/Final/final_mix_notes.md`](../05_Output/Final/final_mix_notes.md).

### 7.5 Color — the teal-and-orange grade

1. Drop a LUT node at the start of V1 loading `05_Output/Final/shotflow_grade.cube`.
2. Per shot: lift shadows toward cyan, push highlights toward warm orange. Keep skin neutral — Ava's amber eyes are the reference.
3. Memory montage (`S04_01`): bloom + saturation +0.15, 35 mm grain.
4. Ending (`S05_04` → `S05_06`): gradual warm-up, lift blacks 5%, soften contrast.

Every grading decision is logged in [`05_Output/Final/color_grading_notes.md`](../05_Output/Final/color_grading_notes.md) with per-scene node graphs.

### 7.6 Topaz 4K upscale and repair

Run Topaz Video AI on the rendered clips **before** the final mixdown if any came in below 4K or had flicker the Low-Noise expert could not fix. Model choices and the per-shot repair log are in [`05_Output/Final/upscale_and_repair_notes.md`](../05_Output/Final/upscale_and_repair_notes.md):

- Upscale 2× / 4×: Proteus (general) or Iris (faces)
- Denoise: Nyx
- Stabilization: only when a shot actually needs it — over-using it kills hand-held energy

Output to `05_Output/Rough_Cuts/enhanced/` and relink in DaVinci.

### 7.7 Export

From the Deliver page, export one master per target — see the table in [`05_Output/Final/assembly_guide.md`](../05_Output/Final/assembly_guide.md) §7. The four you will actually use:

| Preset | Resolution | Codec | File |
|--------|------------|-------|------|
| Master 4K | 3840×2160 | H.265 CRF 18 | `ShotFlow_4K_Master_v10.mp4` |
| Web 1080p | 1920×1080 | H.264 CRF 20 | `ShotFlow_1080p_v10.mp4` |
| Vertical | 1080×1920 | H.264 CRF 20 | `ShotFlow_1080x1920_v10.mp4` |
| Festival | 3840×2160 | ProRes 422 HQ | `ShotFlow_4K_ProRes_v10.mov` |

### 7.8 Lock checklist

Before bumping the version counter, run the eight checks in [`05_Output/Final/assembly_guide.md`](../05_Output/Final/assembly_guide.md) §8 — timeline length, no black frames, dialogue intelligible, subtitle proofread, loudness at -16 LUFS web / -14 LUFS cinema, true peak ≤ -1 dBTP, color checker neutral, end card held ≥ 2 s.

### 7.9 Deliverables from this step

- `05_Output/Final/ShotFlow_4K_Master_v10.mp4` — locked master
- `05_Output/Final/ShotFlow_4K_ProRes_v10.mov` — festival master
- `05_Output/Final/asset_manifest.md` — full asset inventory with checksum template
- `05_Output/Final/subtitles/` — `.srt` (zh + en) and styled `.ass` for festival burn-in
- `05_Output/Final/credits.md` — cast, voice, music, tools, license roll

---

## 8. Step 6: Delivery & Release

The film is locked. Now you turn it into a per-platform release package and ship it without tripping over AIGC disclosure rules.

### 8.1 Platform specs

[`05_Output/Final/delivery_specs.md`](../05_Output/Final/delivery_specs.md) is the master spec sheet. The short version:

| Platform | Resolution | Codec | Audio | AIGC disclosure |
|----------|-----------|-------|-------|-----------------|
| Bilibili / YouTube | 1920×1080 | H.264 | AAC 128 kbps | Bilibili: tick "AIGC 创作"; YouTube: first line of description |
| Douyin / Xiaohongshu / Reels | 1080×1920 | H.264 | AAC 128 kbps | Tick "AIGC 创作" / first line of description |
| WeChat Channels | 1080×1080 or 1080×1920 | H.264 | AAC 128 kbps | Tick AIGC |
| Festival / awards | 4K ProRes 422 HQ | ProRes | PCM 16-bit | Per《生成式人工智能服务管理暂行办法》, prominent marking |

### 8.2 Build a distribution kit per platform

[`09_Release/distribution_kit.md`](../09_Release/distribution_kit.md) defines the exact contents of each platform's release folder. The Bilibili kit, for example:

```
release_bilibili/
├── ShotFlow_1080p_v10.mp4
├── ShotFlow_1080x1920_v10.mp4
├── cover_landscape_1146x717.jpg
├── cover_portrait_1080x1920.jpg
├── echo_of_singularity.zh.srt
├── title.txt
├── description.txt
├── tags.txt
└── LICENSE.txt
```

The vertical platforms (Douyin, Xiaohongshu, WeChat, Reels) share one vertical物料 set; only title/description/tags differ. See [`09_Release/distribution_kit.md`](../09_Release/distribution_kit.md) §4 for the vertical cut rules — main shot retained but reframed to medium close-up, subtitles +50% font, runtime compressed to 60–90 s by cutting the climax (S03_04 + S05_04 + S05_06), 5 s end card with title and repo URL.

Cover and poster specs are in [`09_Release/poster_spec.md`](../09_Release/poster_spec.md) — sizes, fonts, Flux.1 prompts for the cover image.

### 8.3 AIGC disclosure and licensing

Two things you cannot skip:

1. **AIGC disclosure.** Every platform the film ships on requires AIGC marking. Tick the platform box where there is one; otherwise put "AI-generated short film" as the first line of the description. For festival submissions, follow《生成式人工智能服务管理暂行办法》— prominent marking, and most festivals put AIGC work in a separate category.
2. **License audit.** Before any commercial release (paid streaming, ad-share, brand work, paid competition), run through [`06_Research/licensing_compliance.md`](../06_Research/licensing_compliance.md). The repo itself is MIT-licensed; several components are also NC by default (Flux.1 Kontext [dev], Suno free tier, ElevenLabs free tier). The compliance doc lists every component, its license, the commercial boundary, and the cost to upgrade. The short version: Flux commercial license is the expensive one; the SaaS subscriptions (ElevenLabs Creator, Suno Pro, Topaz Pro) are cheap and unlock commercial rights.

### 8.4 Final pre-release checks

Run through [`09_Release/release_checklist.md`](../09_Release/release_checklist.md) per platform. Highlights:

- [ ] Master passes [`08_Automation/video_quality_check.py`](../08_Automation/video_quality_check.py)
- [ ] Subtitles proofread (zh + en)
- [ ] Title / description have no platform-violating words
- [ ] AIGC box ticked / disclosure line present
- [ ] Cover dimensions match platform spec
- [ ] Open-source repo link in description
- [ ] MIT license statement in description
- [ ] `LICENSE.txt` shipped with the package

### 8.5 Deliverables from this step

- `09_Release/release_{bilibili,youtube,vertical,festival}/` — per-platform packages
- Posted film on each platform
- Archived license receipts and API bills under `06_Research/licenses/` (per the appendix of [`06_Research/licensing_compliance.md`](../06_Research/licensing_compliance.md))

---

## 9. Using the Web Platform

The CLI gets one person through the pipeline. The Web platform lets a small team drive it from a browser — same generation logic, the backend wraps the `08_Automation` scripts instead of rewriting them.

### 9.1 Start the full stack

```bash
cp .env.example .env            # set SECRET_KEY (openssl rand -hex 32) and API keys
docker compose up -d            # postgres + redis + backend + worker + frontend
```

Verify:

```bash
curl http://localhost:8000/api/v1/health     # DB + Redis
open http://localhost:8000/docs              # Swagger
open http://localhost                        # Frontend admin UI
```

`SIMULATE_MODE=true` is the default in `docker-compose.yml`. Every service returns mock output, so the whole chain runs without a GPU. Flip to `false` on a GPU host to hit real ComfyUI / Kling / ElevenLabs / Suno.

### 9.2 Backend API surface

| Route | Purpose |
|-------|---------|
| `/api/v1/projects` | Project CRUD |
| `/api/v1/shots` | Shot & storyboard management |
| `/api/v1/keyframes` | Keyframe management |
| `/api/v1/videos` | Video clip management |
| `/api/v1/audio` | Dialogue & voiceover |
| `/api/v1/queue` | Render queue: submit / query / retry / cancel |
| `/api/v1/queue/stream/events` | SSE real-time queue status |
| `/api/v1/workflows` | ComfyUI workflow management |
| `/api/v1/qa` | QA reports |
| `/api/v1/daily-briefs` | Daily stand-up briefs |
| `/api/v1/health` | Health check (DB + Redis) |

### 9.3 Frontend admin console

React 18 + TypeScript + Vite + Ant Design Pro. Routes:

| Route | Purpose |
|-------|---------|
| `/login` | Login (JWT) |
| `/dashboard` | Overview: health + queue stats + projects |
| `/projects` | Project CRUD |
| `/shots` | Shot management (filter by project) |
| `/keyframes` | Keyframe management (submit generation) |
| `/queue` | Render queue with SSE + submit / retry / cancel |
| `/workflows` | ComfyUI workflow management |
| `/workflow-configs` | YAML config + provider scoring |
| `/assets` | Asset gallery (scans disk by type) |
| `/audio` | Dialogue & voiceover |
| `/qa` | QA reports |
| `/case-studies` | Case study showcase |

The SSE push is a `useQueueStream` hook with exponential-backoff reconnect; the Nginx multi-stage build disables SSE proxy buffering so events stream cleanly.

### 9.4 SSE real-time queue

Submit a render task to `/api/v1/queue`, then subscribe to `/api/v1/queue/stream/events` to watch it move through `pending → running → done` (or `failed`). The Celery worker (container `shotflow-worker`) also runs `--beat`, which every 60 seconds calls `queue.recover` to revive any task left in `running` by a crash. So a worker restart does not lose work.

### 9.5 YAML workflow parameterization (`/workflow-configs`)

The ComfyUI workflows are parameterized through [`03_Workflows/workflows.yaml`](../03_Workflows/workflows.yaml). Each entry declares a workflow name, task type, the API JSON file to load, and a list of parameters — each parameter knows its `node_class`, `node_input`, and optional `node_index`, so the backend can inject it into the right node without anyone editing JSON by hand.

The frontend page `/workflow-configs` exposes this: list configs, fetch one to see its default parameters, then POST to `/api/v1/workflows/configs/{name}/inject` with your chosen params. The backend validates them (returns 422 on bad types or out-of-range values) and returns the fully-injected workflow JSON ready to submit to ComfyUI.

API endpoints (see [`backend/app/api/v1/workflow_configs.py`](../backend/app/api/v1/workflow_configs.py)):

- `GET /api/v1/workflows/configs` — list all parameterized workflows
- `GET /api/v1/workflows/configs/{name}` — get one workflow + its default params
- `POST /api/v1/workflows/configs/{name}/inject` — validate and inject params, return ready-to-submit workflow
- `GET /api/v1/workflows/provider/recommend?complexity=standard&gen_method=wan_i2v&has_gpu=true` — get the recommended provider for a shot

### 9.6 Provider scoring (`/provider/recommend`)

The `/workflow-configs` page also exposes the provider scorer. Query it with `complexity` (`standard` / `complex`), `gen_method`, and `has_gpu` to see which provider the backend would pick and why. Scoring dimensions are quality, speed, cost, and capability, weighted "quality-first + cost-sensitive" (see [`backend/app/services/provider_scorer.py`](../backend/app/services/provider_scorer.py)). This is the same call `render_tasks._dispatch` makes internally when `extra.provider` is unset.

### 9.7 When to use the Web platform vs the CLI

- **CLI** — solo work, scripting, batch rerenders, CI. Faster to iterate on a single shot.
- **Web platform** — team collaboration, queue visibility, non-engineers driving generation, reproducibility audit through the queue's history.

Both write to the same folders and the same `06_Research/video_gen_log.csv`. Switching between them mid-project is safe.

---

## 10. Troubleshooting

The full FAQ is [`TROUBLESHOOTING.md`](../TROUBLESHOOTING.md). The issues that come up most often:

**`deploy_comfyui.sh` fails.** Usually no NVIDIA driver, wrong Python version, or network. Verify with `nvidia-smi` and `python3 --version`; use a HuggingFace mirror or pre-download models if the network is the blocker.

**`preflight_check.py` reports GPU unavailable.** Either no CUDA on the machine, or PyTorch got installed as the CPU wheel. Reinstall the CUDA build from https://pytorch.org. If you genuinely have no GPU, switch to cloud API mode and run only scripts + post-production.

**Character looks like a different person across shots.** The classic AIGC video failure. Fixes, in order: confirm the character bible pins every anchor; confirm IPAdapter references cover front/side/back; raise IPAdapter weight to 0.8–1.0; add `inconsistent hairstyle, wrong clothing` to the negative prompt; reroll the failing shots and rerun the blind test.

**Keyframes show extra fingers or deformed faces.** Add `extra fingers, mutated hands, deformed face` to the negative prompt; lower CFG or increase steps; use ADetailer or a similar node for local repair.

**Severe video flickering.** Confirm the keyframe and the video prompt agree; run the Wan2.2 Low-Noise expert pass to repair broken frames; lower the motion-amplitude prompt wording; apply temporal denoise in Topaz or FFmpeg as a last resort.

**Kling API call fails or is slow.** Confirm `KLING_API_KEY` is set in `.env`; check the API quota; review the official Kling docs to confirm the API version and parameter format. Off-peak generation or webhook callbacks help with slowness.

**ElevenLabs voiceover emotion is off.** Switch the voice ID closer to the character setting; adjust stability and similarity; add emotion tags like `[whisper]`, `[angry]` to the lines.

**Suno music does not match the style.** Be explicit about style, mood, and instruments in the prompt; use the reference-audio feature; generate several tracks and pick.

**`sync_repos.sh` push fails.** Confirm the remote URLs in `.git/config` do not contain a hardcoded token — use SSH or a credential manager. For GitCode keep `https://gitcode.com/badhope/ShotFlow.git` and let the credential manager supply the token.

**Accidentally committed an API key.** Revoke the key immediately; clean history with `git filter-repo` or BFG; regenerate the key and write it into `.env`.

If none of the above solves it, open an Issue with environment, reproduction, and logs.

---

## 11. Next Steps

You have shipped one film. The next moves:

### Customize the workflow

- Edit [`03_Workflows/workflows.yaml`](../03_Workflows/workflows.yaml) to expose new parameters (resolution, sampler, scheduler) to the `/workflow-configs` page without touching JSON.
- Drop a new ComfyUI workflow JSON into `03_Workflows/api/`, add an entry to `workflows.yaml`, and the Web platform picks it up automatically.
- Swap models — HunyuanVideo, LTX-Video, CogVideoX are wired into the provider scorer's `_PROVIDERS` dict in `backend/app/services/provider_scorer.py`; add a new entry there to plug in another backend.

### Contribute back

The repo is MIT-licensed, and pull requests are welcome. See [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the full rules; the highlights:

- Fork, branch off `main`, keep the existing directory layout and naming style.
- New scripts must pass `preflight_check.py`'s basic checks.
- Python: 4-space indent, PEP 8. Shell: start with `set -euo pipefail`. Docs: clean Markdown heading hierarchy.
- **Mandatory**: before every push, run the remote-state checklist in [`CONTRIBUTING.md`](../CONTRIBUTING.md) — PRs to review, open issues, stale branches, CI green, GitHub/GitCode mirror parity, local tests green, sensitive-file scan clean. Never push on a red build.
- Never write tokens into `.git/config` or scripts. Use a credential manager.

---

> This tutorial is a working document; if a step does not match what the scripts actually do, open an Issue or PR.
