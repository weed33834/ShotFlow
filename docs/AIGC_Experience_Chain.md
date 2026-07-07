# ShotFlow — The AIGC Production Chain

> This doc explains the full AIGC video production chain covered by ShotFlow, and the concrete problem each stage solves.

English | [中文](./AIGC_Experience_Chain.zh.md)

---

## Why we built this

AIGC video looks fast in demos, but once you stretch to a 3–5 minute finished piece, the pain points pile up:

- The same face looks like a different person in shot 3 and shot 15.
- A generated shot has six fingers, and you only notice it in post.
- Prompts drift away from the storyboard, so you end up missing coverage.
- Generation parameters are scattered across ComfyUI nodes; move to another machine and you start over.
- Team members work in silos and the assets never line up.

ShotFlow ties these problems into one executable, reproducible, collaborative pipeline. We use a sci-fi short, *Echo of the Singularity*, as a worked example. Every step from script to 4K master is written down as docs, scripts, and workflows so we can reuse it ourselves and others can adapt it.

---

## Full Pipeline

```mermaid
flowchart TB
    subgraph Pre["Pre-production"]
        A[Planning & Task Breakdown]
        B[Script & World-building]
        C[Character Bible + Storyboard]
    end

    subgraph Asset["Asset Layer"]
        D[Flux.1 Kontext + IPAdapter]
        E[29 Keyframes]
    end

    subgraph Motion["Motion Layer"]
        F[Wan2.2 I2V 14B]
        G[Kling 2.5 Turbo]
        H[19 Standard Shots]
        I[5 Complex Shots]
    end

    subgraph Post["Post-production"]
        J[DaVinci Edit & Grade]
        K[ElevenLabs Voice]
        L[Suno Music]
        M[Topaz 4K Upscale]
    end

    subgraph Release["Release"]
        N[4K Master]
        O[ComfyUI Workflow Package]
        P[Multi-platform Release]
    end

    A --> D
    B --> D
    C --> E
    D --> E
    E --> F
    E --> G
    F --> H
    G --> I
    H --> J
    I --> J
    J --> M
    K --> J
    L --> J
    M --> N
    N --> O
    O --> P
```

---

## What each stage solves

### Stage 1: Asset Casting & Tech Validation

**Problem**: character inconsistency across shots.

**Our approach**:

- Lock appearance, clothing, and expression anchors in a character bible.
- Bind multi-angle reference images to the Flux workflow with IPAdapter.
- Run blind tests and reroll shots that do not pass.

**Key files**:

- [`02_Scripts/script_and_worldbuilding.md`](./02_Scripts/script_and_worldbuilding.md)
- [`02_Scripts/keyframe_prompts.md`](./02_Scripts/keyframe_prompts.md)
- [`03_Workflows/Flux_Character_Consistency.json`](./03_Workflows/Flux_Character_Consistency.json)
- [`06_Research/qa_and_blind_test.md`](./06_Research/qa_and_blind_test.md)

---

### Stage 2: Motion Production

**Problem**: flickering, broken, or narratively wrong video.

**Our approach**:

- Standard shots go through local Wan2.2 I2V: low cost, high control.
- Complex shots go through Kling 2.5 Turbo keyframe-to-keyframe for continuity.
- Wan2.2 uses a High-Noise expert for large motion and a Low-Noise expert to repair broken frames.
- All parameters are logged to CSV for reproducibility and batch reruns.

**Key files**:

- [`03_Workflows/Wan22_Dual_Expert_Video.json`](./03_Workflows/Wan22_Dual_Expert_Video.json)
- [`08_Automation/storyboard_to_video.py`](./08_Automation/storyboard_to_video.py)
- [`08_Automation/kling_video_api.py`](./08_Automation/kling_video_api.py)
- [`08_Automation/video_quality_check.py`](./08_Automation/video_quality_check.py)

---

### Stage 3: Post-production & Sound

**Problem**: AI footage looks like disconnected clips instead of a film.

**Our approach**:

- Rough cut to lock pacing, then picture lock before moving on.
- ElevenLabs for character voice, Suno for atmosphere score.
- DaVinci Resolve for a Teal & Orange sci-fi grade.
- Topaz for 4K upscale and temporal denoise.

**Key files**:

- [`04_SOP/postproduction.md`](./04_SOP/postproduction.md)
- [`04_SOP/audio_production.md`](./04_SOP/audio_production.md)
- [`08_Automation/elevenlabs_tts_api.py`](./08_Automation/elevenlabs_tts_api.py)
- [`08_Automation/suno_music_api.py`](./08_Automation/suno_music_api.py)

---

### Stage 4: Release & Workflow Packaging

**Problem**: once finished, the knowledge is lost and the next project starts from zero.

**Our approach**:

- Package ComfyUI workflow JSON.
- Archive SOPs in the repo.
- Use a release checklist so deliverables are not missed.
- Publish tutorials and showcase decks.

**Key files**:

- [`08_Automation/package_workflows.sh`](./08_Automation/package_workflows.sh)
- [`09_Release/release_checklist.md`](./09_Release/release_checklist.md)
- [`09_Release/tutorial_template.md`](./09_Release/tutorial_template.md)
- [`09_Release/presentation_template.md`](./09_Release/presentation_template.md)

---

## Engineering

Beyond creativity, we script the repetitive parts:

| Capability | File |
|------------|------|
| One-click ComfyUI deploy | [`08_Automation/deploy_comfyui.sh`](./08_Automation/deploy_comfyui.sh) |
| Environment preflight | [`08_Automation/preflight_check.py`](./08_Automation/preflight_check.py) |
| Performance benchmark | [`08_Automation/benchmark.py`](./08_Automation/benchmark.py) |
| Batch keyframe generation | [`08_Automation/batch_keyframe_gen.py`](./08_Automation/batch_keyframe_gen.py) |
| Batch video generation | [`08_Automation/storyboard_to_video.py`](./08_Automation/storyboard_to_video.py) |
| Render queue manager (deprecated) | [`08_Automation/render_queue.py`](./08_Automation/render_queue.py) — superseded by [`backend/app/services/queue_service.py`](./backend/app/services/queue_service.py) |
| Asset dashboard | [`08_Automation/asset_dashboard.py`](./08_Automation/asset_dashboard.py) |
| Daily brief generator | [`08_Automation/daily_brief.py`](./08_Automation/daily_brief.py) |
| Dual-repo sync | [`08_Automation/sync_repos.sh`](./08_Automation/sync_repos.sh) |

---

## Current State

| Asset Type | Status | Note |
|------------|--------|------|
| Plans / Docs / SOPs | Complete | Ready to use |
| ComfyUI workflow JSON | Complete | Flux + Wan2.2 workflows |
| Automation scripts | Complete | 16 scripts covering main stages |
| Script / Storyboard / Prompts | Complete | 24 shots + 29 keyframe prompts |
| Character reference PNGs | Placeholder | Scripts ready; generate on GPU machine |
| Keyframe PNGs | Placeholder | Same as above |
| Video MP4s | Placeholder | Same as above |
| Audio assets | Placeholder | Same as above |
| Final master | Placeholder | Same as above |

> The core value of this repo is the **process, code, and documentation**. Actual PNG/MP4 files are one script run away and do not affect the usefulness of the workflow.

---

## Suggested Reading Order

1. [`README.md`](./README.md) — project overview
2. [`project_proposal.zh.md`](./07_Team/templates/project_proposal.zh.md) — full plan and technical architecture
3. [`AIGC_Experience_Chain.md`](./AIGC_Experience_Chain.md) — this doc
4. [`04_SOP/sop_shotflow.md`](./04_SOP/sop_shotflow.md) — full operation manual
5. [`08_Automation/README.md`](./08_Automation/README.md) — automation scripts
6. [`07_Team/expert_team.md`](./07_Team/expert_team.md) — team roles
7. [`09_Release/presentation_template.md`](./09_Release/presentation_template.md) — showcase template

---

> Maintained by the ShotFlow team. Updated as the workflow evolves.
