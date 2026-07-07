# 05_Output — Deliverables

Final and intermediate output of the pipeline. Structure mirrors a typical film
delivery: rough cuts iteratively refined into a final master.

## Layout

- [`Rough_Cuts/`](./Rough_Cuts/) — work-in-progress cuts with notes per version
  (`v01_rough_cut_notes.md`, `locked_cut_notes.md`).
- [`Final/`](./Final/) — final master and delivery package:
  - **Specs & records**: [`delivery_specs.md`](./Final/delivery_specs.md),
    [`color_grading_notes.md`](./Final/color_grading_notes.md),
    [`final_mix_notes.md`](./Final/final_mix_notes.md),
    [`upscale_and_repair_notes.md`](./Final/upscale_and_repair_notes.md).
  - **Assembly & inventory**: [`assembly_guide.md`](./Final/assembly_guide.md)
    (how to build the locked master from EDL + assets),
    [`asset_manifest.md`](./Final/asset_manifest.md) (complete asset list +
    checksum template), [`credits.md`](./Final/credits.md) (cast / crew / tools
    / license roll).
  - **Subtitles**: [`subtitles/`](./Final/subtitles/) — zh + en `.srt` and a
    styled zh `.ass` for festival burn-in.
  - **Master files** (not committed): 4K / 1080p / vertical / square / ProRes
    masters, plus the DaVinci project file.
- [`EDL/`](./EDL/) — edit decision lists and timeline exports.

## Status

The example film's rendered outputs are not committed (size + licensing). The
notes, specs, EDL, subtitles, and assembly guide are the reference; populate
the actual media by running the pipeline end-to-end, then follow
[`assembly_guide.md`](./Final/assembly_guide.md) to lock the master.
