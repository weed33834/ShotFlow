# ShotFlow — Project Progress Checklist

English (current) | [中文](./progress_checklist.zh.md)

> This checklist is maintained jointly by the instructor/mentor and the project team. As each item is completed, tick or strike through the brackets: `- [x]`.

---

## I. Project Kickoff and Team Setup

- [x] Project proposal final draft confirmed (document complete, awaiting instructor signature)
- [x] Expert team roster confirmed
- [x] Task assignment and kickoff meeting document completed
- [x] Licensing compliance checklist completed
- [x] Data backup and version control plan completed
- [x] Release platform plan completed
- [x] GitHub public repository created (https://github.com/MS33834/ShotFlow)
- [x] GitCode public repository created (https://gitcode.com/badhope/ShotFlow)
- [x] Dual-repo sync script completed (`08_Automation/sync_repos.sh`)
- [x] Initial code pushed to both repositories
- [x] Project communication group / collaboration tool setup guide completed (`07_Team/collaboration_tools_guide.md`)
- [x] First instructor-team sync meeting template completed (agenda and meeting minutes template)
- [x] Hardware environment checklist completed (`06_Research/hardware_and_software_checklist.md`)
- [x] Software installation checklist completed (same as above)

---

## II. Phase 1: Asset Forging and Technical Validation (Weeks 1–2)

### 2.1 Script and Characters

- [x] S1-1 Worldview and story outline completed
- [x] S1-2 Complete script completed
- [x] S1-3 Character design whitepaper (character bible, including Ava example) completed
- [x] Keyframe prompt summary table (24 shots) completed
- [x] Detailed storyboard (24 shots, incl. timecode / prompt / SFX) completed
- [x] S1-4 Female lead Ava reference set spec completed (character asset library structure built, blind test plan ready)

### 2.2 Technical Environment

- [x] ComfyUI deployment script completed (`08_Automation/deploy_comfyui.sh`)
- [x] Performance benchmark script completed (`08_Automation/benchmark.py`)
- [x] ComfyUI node connection notes completed (`03_Workflows/comfyui_node_connections.md`)
- [x] ComfyUI API-format JSON workflow template completed (`03_Workflows/api/`)
- [x] Git repo initialization script and .gitignore completed
- [x] Batch keyframe generation script completed (`08_Automation/batch_keyframe_gen.py`)
- [x] Storyboard-to-video pipeline script completed (`08_Automation/storyboard_to_video.py`)
- [x] Preflight environment check script completed (`08_Automation/preflight_check.py`)
- [x] Asset inventory and progress dashboard script completed (`08_Automation/asset_dashboard.py`)
- [x] Video quality auto-check script completed (`08_Automation/video_quality_check.py`)
- [x] Render queue manager completed (`08_Automation/render_queue.py`)
- [x] Daily standup brief generator script completed (`08_Automation/daily_brief.py`)
- [x] S1-5 ComfyUI and required node deployment completed (scripts and templates in place, awaiting on-prem GPU environment verification)
- [x] Flux.1 Kontext [dev] model path and configuration confirmed (awaiting on-prem download)
- [x] IPAdapter / PuLID node and model configuration confirmed
- [x] S1-6 Flux character consistency workflow JSON completed

### 2.3 Keyframes and Acceptance

- [x] S1-7 Keyframe generation pipeline completed (24 shots, 29 prompts incl. first/last frame splits, awaiting on-prem PNG generation)
- [ ] S1-8 Character consistency blind test passed (blind test plan ready, to run after on-prem keyframe generation)
- [x] Phase 1 milestone review meeting held (cross-check report completed)
- [ ] Instructor/mentor signed the Phase 1 acceptance form (review form submitted, awaiting instructor signature)

---

## III. Phase 2: Motion Shot Production (Weeks 3–4)

### 3.1 Model and API

- [x] S2-1 Wan2.2 I2V 14B dual-expert model deployment plan completed (scripts and config ready, awaiting on-prem verification)
- [x] S2-2 Kling 2.5 Turbo API configuration completed (script ready, awaiting on-prem call)

### 3.2 Storyboard and Generation

- [x] S2-3 Complete storyboard breakdown completed
- [ ] S2-4 Standard shots (17 Wan I2V + 2 Wan T2V) generation completed (pipeline ready, awaiting on-prem MP4 generation)
- [ ] S2-5 Complex shots (5 Kling first/last frame) generation completed (script ready, awaiting on-prem API call)
- [x] S2-6 CFG/Denoise parameter tuning record completed
- [x] S2-7 Asset filtering and version management spec completed

### 3.3 Quality Check

- [ ] QA spot check on raw shot quality (QC script ready, to run after on-prem video generation)
- [x] Breakdown/flicker shot repair plan recorded (see failure case log)
- [ ] Phase 2 milestone review meeting held
- [ ] Instructor/mentor signed the Phase 2 acceptance form

---

## IV. Phase 3: Post-Production Compositing and Sound Design (Week 5)

### 4.1 Editing

- [x] S3-1 Rough cut version template completed (incl. v01 rough cut notes, EDL timeline, transition table)
- [x] S3-2 Locked edit version template completed (incl. lock declaration, checklist, final timeline)

### 4.2 Audio

- [x] S3-3 Character voice-over asset spec and example list completed (`01_Assets/Audio/Dialogue/`)
- [x] S3-4 Ambient SFX / Foley asset spec and example list completed (`01_Assets/Audio/SFX/`)
- [x] S3-5 Sci-fi score asset spec and example list completed (`01_Assets/Audio/Music/`)
- [ ] Actual voice-over / score / SFX generation (awaiting specific project execution)

### 4.3 Quality Enhancement

- [x] S3-6 Topaz Video AI 4K upscale and denoise template completed (`05_Output/Final/upscale_and_repair_notes.md`)
- [x] S3-7 Defect repair record template completed (incl. flicker / distortion / model clipping repair table)

### 4.4 Review

- [x] Rough cut + sound effects internal review template completed
- [ ] Phase 3 milestone review meeting held
- [ ] Instructor/mentor signed the Phase 3 acceptance form

---

## V. Phase 4: Final Delivery and Workflow Packaging (Week 6)

### 5.1 Final Cut

- [x] S4-1 DaVinci unified color grading template completed (`05_Output/Final/color_grading_notes.md`)
- [x] S4-2 Final mix and 4K master output template completed (`delivery_specs.md` + `final_mix_notes.md`)

### 5.2 Asset Consolidation

- [x] S4-3 ComfyUI workflow JSON packaging script and notes completed (`08_Automation/package_workflows.sh`)
- [x] S4-4 SOP operation manual final template completed (draft in place, to finalize after on-prem verification)
- [x] Post-production spec completed
- [x] Audio production spec completed
- [x] S4-5 Character asset library organization template completed (`01_Assets/Characters/README.md`)

### 5.3 Release and Summary

- [x] S4-6 Multi-platform release checklist for the final cut completed (`09_Release/release_checklist.md`)
- [x] Tech community tutorial template completed (`09_Release/tutorial_template.md`)
- [x] Project summary report template completed
- [x] Project summary report writing template completed (`summary_report_template.zh.md`)
- [x] Final defense / showcase material template completed (`09_Release/presentation_template.md`)
- [ ] Instructor/mentor final acceptance signature

---

## VI. Risk and Issue Tracking

| Risk / Issue | Status | Owner | Mitigation | Resolution date |
|--------------|--------|-------|-----------|-----------------|
| Character consistency loss of control | [ ] Resolved / [x] In progress | AI Algorithm Engineer | Flux.1 Kontext + IPAdapter character-locking pipeline; 4 multi-angle reference images; blind test plan ready, to validate after on-prem keyframe generation | 2026-06-24 |
| Physical logic breakdown | [x] Resolved / [ ] In progress | AI Video Operator | Wan2.2 Low Noise Expert to fix close-ups; complex shots switch to Kling first/last frame constraints; denoise 0.55 | 2026-06-25 |
| Insufficient compute | [x] Resolved / [ ] In progress | Ops / Deployment Engineer | Local 4090 runs Wan2.2; complex shots call Kling 2.5 Turbo API; cloud backup render queue | 2026-06-24 |
| Licensing compliance | [x] Resolved / [ ] In progress | PM | Build licensing compliance checklist; use open-source / commercial-license models and assets; keep generation logs | 2026-06-23 |
| Team time conflict | [ ] Resolved / [x] In progress | PM | Weekly standup + daily brief script + milestone review; task board tracking | 2026-06-26 |
| Asset loss | [x] Resolved / [ ] In progress | Ops / Deployment Engineer | Dual-repo sync script + local NAS/cloud backup + version naming convention | 2026-06-24 |

---

## VII. Instructor / Mentor Signature Area

| Phase | Signature | Date | Comments |
|-------|-----------|------|----------|
| Project kickoff | | | |
| Phase 1 acceptance | | | |
| Phase 2 acceptance | | | |
| Phase 3 acceptance | | | |
| Final acceptance | | | |

---

> Update rule: As each task is completed, the owner ticks the corresponding `[ ]` and notes it in the weekly report. At the end of each week, the PM consolidates progress and reports to the instructor.
