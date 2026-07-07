# 01_Assets — Production assets

Characters, scenes, and audio assets for the example film. Asset generation is logged
per file so each artifact is traceable to its prompt, seed, and parameters.

## Layout

- [`Characters/`](./Characters/) — character reference libraries (e.g. Ava). Each
  character has an `.asset_generation_log.json` recording seeds and prompts.
- [`Scenes/`](./Scenes/) — scene keyframes, with a `keyframe_generation_log.csv`
  tracking each keyframe's source prompt and generation status.
- [`Audio/`](./Audio/) — dialogue, music, and SFX subdirectories, each with its own
  README covering format and mix standards.

## Status

The example film's assets are **placeholders / pending generation** — the repo ships
the prompts, logs, and structure, not the rendered PNGs/MP4s (size + licensing). Run
the generation scripts in [`08_Automation/`](../08_Automation/) to populate them.

See [`Characters/Ava/README.md`](./Characters/Ava/README.md) for an example of how a
character asset directory is organized.
