# Final Cut Assembly Guide

> Project: ShotFlow / *Echo of the Singularity* (example)
> Target runtime: ~4 min 10 s
> Target master: 3840×2160 / 24 fps / H.265 / Rec. 709

This guide walks an editor from the pipeline's per-shot outputs (in
`05_Output/EDL/` and the rendered clips) to a locked final master. It assumes
the editor is using DaVinci Resolve 19+ (free version is sufficient) but the
same logic maps to Premiere, Final Cut, or any NLE that reads EDL + a media
bin.

---

## 0. Inputs you need before opening the NLE

| Input | Location | Notes |
|-------|----------|-------|
| Shot clips | `05_Output/Renders/SF_S{scene}_{shot}_*.mp4` | One file per shot, named per the EDL |
| Reference keyframes | `01_Assets/Scenes/SF_S*.png` | For re-takes and poster frames |
| Edit decision list | `05_Output/EDL/shotflow_v01.edl` | Timeline spine |
| Dialogue stems | `01_Assets/Audio/Dialogue/{Role}/` | Per-line WAV files |
| Music stems | `01_Assets/Audio/Music/{Themes,Ambient}/` | Layered BGM |
| SFX stems | `01_Assets/Audio/SFX/{Environment,Mechanical,UI}/` | Spot effects |
| Color LUT | `05_Output/Final/shotflow_grade.cube` | Project look (see `color_grading_notes.md`) |
| Subtitles | `05_Output/Final/subtitles/*.srt` | zh + en closed captions |

If any rendered clip is missing, generate it first via
`08_Automation/storyboard_to_video.py --shot SF_S{scene}_{shot}` (or the
ComfyUI workflow in `03_Workflows/`).

---

## 1. Create the project

1. New Project → `ShotFlow_Master`.
2. Project Settings:
   - Timeline resolution: **3840×2160**
   - Timeline frame rate: **24**
   - Color science: **DaVinci YRGB Color Managed**
   - Color processing mode: **ACEScct**
   - Output color space: **Rec.709 (Scene)** for web; **DCI-P3 D65** for cinema.
3. Save the project into `05_Output/Project/ShotFlow_Master.drp` (git-ignored,
   too large for the repo).

---

## 2. Import media

1. Open the **Media** page.
2. Add the four folders above as media pools, one bin each: `Clips`,
   `Dialogue`, `Music`, `SFX`.
3. Confirm every clip plays. Anything that stutters should be transcoded to
   DNxHR HQX or ProRes 422 HQ via Media Pool → Transcode.

---

## 3. Build the timeline from the EDL

1. **Edit** page → Timeline → Import → Timeline → EDL…
2. Select `05_Output/EDL/shotflow_v01.edl`.
3. In the import dialog:
   - Reel / Tape: ignore
   - **Relink to media pool**: enabled
   - Handle frames: 12 (half a second at 24 fps)
4. The EDL lands on V1 with 24 events. Verify the timeline length matches the
   shot tracker (`examples/echo-of-singularity/shot_tracker.md`): ~4:10.

> The committed EDL is a v01 rough cut. Shot durations in it are 3–5 s each
> and may need lengthening to match the shot tracker's scene-level
> timecodes (e.g. S01_01 is 0:00–0:10 in the tracker but 5 s in the EDL).
> Use the shot tracker as the source of truth and trim/extend accordingly.

---

## 4. Lay audio

Audio goes on six tracks, in this order (top to bottom):

| Track | Type | Content | Source |
|-------|------|---------|--------|
| A1 | Dialogue | Per-line role stems | `01_Assets/Audio/Dialogue/` |
| A2 | Dialogue (alt) | Unused alt takes / breaths | same |
| A3 | Music — Theme | Main theme, in/out | `01_Assets/Audio/Music/Themes/` |
| A4 | Music — Ambient | Scene beds | `01_Assets/Audio/Music/Ambient/` |
| A5 | SFX — Spot | One-shots (beeps, pulses) | `01_Assets/Audio/SFX/Mechanical,UI/` |
| A6 | SFX — Ambience | Looping beds (wind, ship hum) | `01_Assets/Audio/SFX/Environment/` |

Use the **cue sheet** (`01_Assets/Audio/cue_sheet.md`) for exact in/out points.

Mix targets (from `01_Assets/Audio/README.md`):

```
Dialogue  -6 dBFS   high-pass 80 Hz, +2 dB @ 2 kHz
Music    -18 dBFS   side-chain compressed to dialogue
SFX      -20 dBFS   layered, panned to match screen action
Master   -1 dBTP    LUFS -16 (web)  /  LUFS -14 (cinema)
```

---

## 5. Color

1. Drop a Color page node at the start of V1: **LUT** →
   `05_Output/Final/shotflow_grade.cube`.
2. Per-shot balance: lift shadows toward cyan, push highlights toward warm
   orange. Keep skin tones neutral — Ava's amber eyes are the reference.
3. Memory montage (S04_01): bloom + saturation +0.15, grain 35mm.
4. Final (S05_04 → S05_06): gradual warm-up, lift blacks 5%, soften contrast.

All grading decisions are logged in `color_grading_notes.md`.

---

## 6. Titles & subtitles

1. End card (4:08–4:10): "每一个结束，都是另一段回响的开始。"
   Font: Source Han Serif, 60 px, fade-in 12 frames, fade-out 12 frames.
2. Closed captions: import `subtitles/echo_of_singularity.zh.srt` into the
   Subtitle track. Burn-in optional; for platform delivery keep them as a
   soft subtitle track (see `delivery_specs.md`).
3. Credits roll: see `credits.md`.

---

## 7. Export

Export one master per target platform. Use the **Deliver** page with these
presets:

| Preset | Resolution | Codec | Audio | File |
|--------|------------|-------|-------|------|
| Master 4K | 3840×2160 | H.265 CRF 18 | 48 kHz PCM 24-bit | `ShotFlow_4K_Master_v10.mp4` |
| Web 1080p | 1920×1080 | H.264 CRF 20 | 48 kHz AAC 192 kbps | `ShotFlow_1080p_v10.mp4` |
| Vertical | 1080×1920 | H.264 CRF 20 | 48 kHz AAC 128 kbps | `ShotFlow_1080x1920_v10.mp4` |
| Square | 1080×1080 | H.264 CRF 20 | 48 kHz AAC 128 kbps | `ShotFlow_1x1_v10.mp4` |
| Festival | 3840×2160 | ProRes 422 HQ | 48 kHz PCM 16-bit | `ShotFlow_4K_ProRes_v10.mov` |

Verify each export against `delivery_specs.md` §五 before release.

---

## 8. Sanity checks before locking

- [ ] Timeline length matches shot tracker total (±2 s).
- [ ] No black frames, no double audio, no orphaned clips.
- [ ] Every dialogue line is on screen and intelligible.
- [ ] Subtitle spelling: zh and en both proofread.
- [ ] Loudness meter reads -16 LUFS (web) or -14 LUFS (cinema).
- [ ] True peak ≤ -1 dBTP.
- [ ] Color checker clip looks neutral under the LUT.
- [ ] End card stays on screen ≥ 2 s.
- [ ] Project file saved and backed up to two locations.

When all nine pass, bump the version counter in the filenames and run
`08_Automation/sync_repos.sh` to push the new EDL + notes.

---

> This guide is a working example for the *Echo of the Singularity* case
> study. For your own project, copy this file, rename to
> `<your_film>_assembly_guide.md`, and adjust the timecodes, mix targets,
> and export presets to taste.
