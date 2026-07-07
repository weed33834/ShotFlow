# Echo of the Singularity — Production Plan

> Project: ShotFlow  
> Example: Echo of the Singularity (奇点回响)  
> Planned duration: 6 weeks  
> Target output: 3–5 minute sci-fi micro-short, 4K master

---

## 1. Scope

### Included
- Script, world-building, character bible
- 24-shot storyboard with reference-frame prompts
- Character consistency pipeline (Flux.1 Kontext + IPAdapter)
- Standard-shot generation (Wan2.2 I2V 14B)
- Complex/transition-shot generation (Kling 2.5 Turbo)
- Dialogue (ElevenLabs), music (Suno), sound design
- Edit, color grade, 4K upscale, delivery

### Not included
- Live-action filming
- Traditional 3D CG pipeline
- Commercial distribution or rights trading

---

## 2. Milestones

| Week | Milestone | Deliverables |
|------|-----------|--------------|
| 1 | Pre-production lock | Final script, character bible, 24-shot storyboard |
| 2 | Asset铸造 | Ava reference set (front/side/back/expressions/turnaround), 29 keyframes |
| 3 | Video pass 1 | 19 standard shots (Wan2.2), first QA pass |
| 4 | Video pass 2 | 5 complex shots (Kling), retakes, second QA pass |
| 5 | Post-production | Dialogue, music, edit, color grade, sound mix |
| 6 | Delivery | 4K master, packaged ComfyUI workflows, release docs |

---

## 3. Team roles

See [`../../07_Team/expert_team.md`](../../07_Team/expert_team.md) for the full team roster. For this example the responsibilities map as follows:

| Role | Focus on this example |
|------|------------------------|
| Director / Writer | Script, tone, shot intent |
| AI Art Director | Ava reference set, keyframe quality |
| AI Algorithm Engineer | Flux + Wan workflow tuning |
| Post Director | Edit, color, sound mix |
| QA Lead | Per-shot review, consistency checks |
| DevOps | Render queue, sync, backup |

---

## 4. Technical approach

### Character consistency
- Build Ava reference set from locked prompts.
- Use IPAdapter in every Flux generation node.
- Run blind-test review: 5 reviewers, >95% recognition threshold.

### Shot generation
- Standard shots: Wan2.2 I2V 14B, 720P first, upscale later.
- Complex camera moves and transitions: Kling 2.5 Turbo with start/end frames.
- Save seed, cfg, sampler, and prompt version per shot.

### Post
- Rough cut in DaVinci Resolve.
- Teal & orange sci-fi color grade.
- ElevenLabs for the Core (neutral, slightly reverbed), female lead voice for Ava.
- Suno for scene BGM, then mixed with sound effects.
- Topaz Video AI for final 4K upscale and denoise.

---

## 5. Risk plan

| Risk | Mitigation |
|------|------------|
| Ava face drifts between shots | Reference set + IPAdapter + per-shot QA |
| Wan2.2 produces flicker | Dual-expert workflow, Low Noise repair pass |
| Kling API quota exhausted | Render queue with fallback seeds, local Wan for backups |
| Hand / anatomy errors | Extra negative prompts, manual masking on critical close-ups |
| Long render times | Night batch queue, progress tracker, daily standup |

---

## 6. Deliverables

- `01_Assets/Characters/Ava/` — reference image set
- `01_Assets/Scenes/` — 29 keyframes
- `05_Output/Rough_Cuts/` — v01 rough cut, locked cut notes
- `05_Output/Final/` — 4K master, color notes, mix notes
- `03_Workflows/` — packaged Flux + Wan2.2 JSON
- `09_Release/` — tutorial, presentation, release checklist

---

> This plan is a worked example. Replace dates, names, and content for your own production.
