# Echo of the Singularity — Example Case Study

English | [中文](./README.zh.md)

> A complete AIGC short-film workflow, demonstrated through the 3–5 minute sci-fi micro-short *Echo of the Singularity*.

This directory contains the full plan and production records for the example project used throughout ShotFlow. It is meant to show how the generic workflow templates in the repository map to a real (albeit fictional) production.

---

## What is included

| Document | Purpose |
|----------|---------|
| [`production_plan.md`](./production_plan.md) | Schedule, milestones, deliverables, and risk plan for the example. |
| [`production_log.md`](./production_log.md) | Day-by-day production notes, decisions, and blockers. |
| [`character_bible_ava.md`](./character_bible_ava.md) | Locked character reference for Ava, the protagonist. |
| [`shot_tracker.md`](./shot_tracker.md) | 24-shot progress table: status, generator, seed, reviewer. |

The actual script, storyboard, and keyframe prompts live in:

- [`../../02_Scripts/script_and_worldbuilding.md`](../../02_Scripts/script_and_worldbuilding.md)
- [`../../02_Scripts/detailed_storyboard.md`](../../02_Scripts/detailed_storyboard.md)
- [`../../02_Scripts/keyframe_prompts.md`](../../02_Scripts/keyframe_prompts.md)

---

## Quick facts

- **Project code**: ShotFlow
- **Chinese title**: 奇点回响
- **Genre**: Sci-fi / mystery / poetic
- **Runtime**: ~4 minutes 10 seconds
- **Shots**: 24 across 5 scenes
- **Keyframes**: 29 reference frames
- **Lead character**: Ava, 28, former interstellar archaeologist
- **Core technical challenge**: character consistency across shots
- **Primary tool stack**: Flux.1 Kontext + IPAdapter, Wan2.2 I2V, Kling 2.5 Turbo

---

## Why this example matters

Most AIGC video demos stop at a few cool clips. This case study shows the paperwork around the clips: how the script becomes a shot list, how the shot list becomes reference frames, how reference frames become videos, and how everything is tracked so the project does not fall apart in week three.

If you want to use ShotFlow for your own film, replace the content of these files with your own story and keep the structure.

---

## Reading order

1. `production_plan.md` — what we planned to do and when
2. `character_bible_ava.md` — who the lead character is and why she looks the same in every shot
3. [`../../02_Scripts/detailed_storyboard.md`](../../02_Scripts/detailed_storyboard.md) — the 24-shot breakdown
4. `shot_tracker.md` — which shots are done and which need another pass
5. `production_log.md` — what actually happened during production
6. [`../../AIGC_Experience_Chain.md`](../../AIGC_Experience_Chain.md) — how this example fits into the bigger workflow

---

> Maintained by the ShotFlow team. Last updated 2026-06-25.
