# 02_Scripts — Script, storyboard, prompts

Pre-production documents: script, world-building, character bible, storyboard, and the
keyframe prompts that feed the Flux.1 Kontext generation workflow.

## Files

- [`script_and_worldbuilding.md`](./script_and_worldbuilding.md) — script, world bible,
  and tone notes for the example film.
- [`detailed_storyboard.md`](./detailed_storyboard.md) — 24-shot storyboard with framing,
  action, and dialogue per shot.
- [`keyframe_prompts.md`](./keyframe_prompts.md) — 29 keyframe prompts (24 shots + 5
  keyframe-to-keyframe endpoints), one block per shot with seed and parameters.
- [`character_bible_template.md`](./character_bible_template.md) — blank template for a
  character bible (appearance, costume anchors, voice, personality).
- [`storyboard_template.md`](./storyboard_template.md) — blank storyboard table template.

## How it fits

`keyframe_prompts.md` is the input to [`batch_keyframe_gen.py`](../08_Automation/batch_keyframe_gen.py).
`detailed_storyboard.md` drives [`storyboard_to_video.py`](../08_Automation/storyboard_to_video.py).
The example content uses the *Echo of the Singularity* case study — replace it with your
own story for a new project.
