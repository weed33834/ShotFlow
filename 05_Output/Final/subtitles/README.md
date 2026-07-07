# Subtitles

Closed-caption files for the example film *Echo of the Singularity*.

## Files

| File | Language | Format | Use |
|------|----------|--------|-----|
| [`echo_of_singularity.zh.srt`](./echo_of_singularity.zh.srt) | Chinese (Simplified) | SRT | Soft subs on Bilibili / YouTube / video platforms |
| [`echo_of_singularity.en.srt`](./echo_of_singularity.en.srt) | English | SRT | Soft subs for international platforms |
| [`echo_of_singularity.zh.ass`](./echo_of_singularity.zh.ass) | Chinese (Simplified) | ASS | Burn-in styled subs for festival / cinema masters |

## Timecode reference

Timecodes follow the **shot tracker**
([`examples/echo-of-singularity/shot_tracker.md`](../../../examples/echo-of-singularity/shot_tracker.md)),
which uses scene-level durations (total runtime ~4:10). The committed EDL
uses 5-second-per-shot rough durations and will diverge — re-time the
subtitles if you assemble from the v01 EDL instead.

## Style notes (ASS)

- Font: **Source Han Serif SC** (思源宋体). Ships with most Linux distros;
  on Windows use **SimSun** as a fallback, on macOS use **Songti SC**.
- Ava (white) / Core (warm orange `#FFE0B0`) / Narrator (grey) get distinct
  styles so the audience can tell who is speaking without name labels.
- Bottom-center alignment, 52 px size at 1080p (scales with PlayResX/Y).
- 2 px outline + 1 px drop shadow for readability over busy backgrounds.

## Editing

- SRT: use **Subtitle Edit** (cross-platform) or Aegisub.
- ASS: use **Aegisub**. Open the file, adjust via the Styles Manager.

To convert ASS → SRT (drops styling):

```bash
ffmpeg -i echo_of_singularity.zh.ass echo_of_singularity.zh.from_ass.srt
```

## Burn-in (DaVinci Resolve)

1. Drop the SRT or ASS onto a Subtitle track above V1.
2. Right-click → **Burn In** (for festival master).
3. For web delivery, leave as soft subs so viewers can toggle them.

## Validation

Each SRT must pass:

- All cue indices sequential starting at 1.
- All timecodes in `HH:MM:SS,mmm --> HH:MM:SS,mmm` format, ascending.
- No cue overlaps the next.
- UTF-8 encoded with no BOM.

Quick check:

```bash
python 08_Automation/subtitle_lint.py 05_Output/Final/subtitles/*.srt
```

(The lint script is a stub — implement if needed. Until then, a manual
review pass is sufficient for this example film's 11 cues.)

## Translation policy

The English subtitles are not a literal translation of the Chinese. They
prioritize natural English rhythm and line length over word-for-word
equivalence. If you fork this repo and re-shoot with your own dialogue,
re-translate rather than reusing these lines.

## License

Subtitle files are part of the repository and fall under the same
[MIT](../../../LICENSE) license. You may use, modify, and
re-translate them freely, including for commercial purposes.
