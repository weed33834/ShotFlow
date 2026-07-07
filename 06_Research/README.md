# 06_Research — Research and reference

Technical research, tuning notes, and reference data accumulated during the example
film's production. These docs capture the "why" behind parameter and tool choices.

## Files

- [`tech_stack_and_budget.md`](./tech_stack_and_budget.md) — full tech stack breakdown
  and 6-week budget estimate (local GPU vs cloud API).
- [`hardware_and_software_checklist.md`](./hardware_and_software_checklist.md) —
  deployment checklist for GPU, drivers, ComfyUI, models.
- [`parameter_tuning.md`](./parameter_tuning.md) — CFG scale, denoise, and seed tuning
  notes per shot type.
- [`failure_cases.md`](./failure_cases.md) — logged failure cases and root causes
  (flicker, face drift, physics breaks).
- [`qa_and_blind_test.md`](./qa_and_blind_test.md) — QA strategy, character-consistency
  blind test protocol, scoring rubric.
- [`phase1_cross_check.md`](./phase1_cross_check.md) — phase 1 cross-check sign-off.
- [`backup_and_versioning.md`](./backup_and_versioning.md) — backup strategy, NAS/cloud,
  Git LFS for large files.
- [`licensing_compliance.md`](./licensing_compliance.md) — model and service licensing
  notes (Flux non-commercial, Suno/ElevenLabs commercial plans).
- [`release_platforms.md`](./release_platforms.md) — target release platforms and
  format requirements.
- [`render_queue.json`](./render_queue.json) — historical JSON render queue (pre-backend,
  kept for migration reference).
- [`video_gen_log.csv`](./video_gen_log.csv) — per-clip generation log (seed, model,
  duration, status).

## Usage

Start with `tech_stack_and_budget.md` for the big picture, then `parameter_tuning.md`
and `failure_cases.md` for the practical tuning knowledge.
