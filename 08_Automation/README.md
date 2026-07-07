# ShotFlow — Automation Scripts

English (current) | [中文](./README.zh.md)

This directory holds all automation scripts for the project: environment deployment, batch generation, API calls, quality checks, and project management.

> All scripts locate the project root via `PROJECT_ROOT = Path(__file__).resolve().parent.parent`, so they can be run from any directory. Most scripts support `--help` / `--dry-run`; run with `--help` first to see the usage.

## File index

### Environment & deployment

| File | Purpose |
|------|---------|
| `deploy_comfyui.sh` | Deploy the ComfyUI environment and required nodes |
| `init_git.sh` | Initialize the Git repo and `.gitignore` |
| `preflight_check.py` | Pre-flight environment check (GPU / memory / disk / models / API keys) |
| `project_health_check.py` | Project structure integrity check (called by CI and tests) |
| `benchmark.py` | ComfyUI performance benchmark (Flux / Wan2.2) |
| `requirements.txt` | Runtime Python dependencies |
| `requirements-dev.txt` | Dev dependencies (black / isort / pytest) |

### Batch generation

| File | Purpose |
|------|---------|
| `batch_keyframe_gen.py` | Batch-generate keyframes via the ComfyUI API |
| `storyboard_to_video.py` | Storyboard-to-video pipeline (Wan2.2 I2V / T2V) |
| `kling_video_api.py` | Kling 2.5 Turbo image-to-video (with first/last frame) |
| `elevenlabs_tts_api.py` | ElevenLabs text-to-speech for character dialogue |
| `suno_music_api.py` | Suno AI sci-fi ambient music generation |
| `render_queue.py` | Deprecated — render queue manager (superseded by the backend `queue_service.py`; kept as an offline fallback) |

### Quality & management

| File | Purpose |
|------|---------|
| `video_quality_check.py` | Automated video quality check (resolution / fps / flicker / sharpness) |
| `asset_dashboard.py` | Asset inventory and progress dashboard |
| `daily_brief.py` | Daily standup brief generator |

### Repo sync

| File | Purpose |
|------|---------|
| `sync_repos.sh` | Push to both GitHub and GitCode mirrors |
| `package_workflows.sh` | Package ComfyUI workflow JSONs for release |

## Quick start

All commands below run from the **repository root** (the directory containing `README.md` and `08_Automation/`).

1. Install dependencies:

```bash
pip install -r 08_Automation/requirements-dev.txt
# Install PyTorch separately per your CUDA version: https://pytorch.org
```

2. Configure environment variables (copy `.env.example` and edit):

```bash
cp .env.example .env
# Edit .env: fill in KLING_API_KEY, ELEVENLABS_API_KEY, SUNO_API_KEY, etc.
```

3. Pre-flight check:

```bash
python 08_Automation/preflight_check.py         # full check (needs GPU / models)
python 08_Automation/preflight_check.py --dry-run  # structure + keys only
```

4. Batch generation (run with `--help` / `--dry-run` first):

```bash
python 08_Automation/batch_keyframe_gen.py --dry-run     # preview keyframe list
python 08_Automation/batch_keyframe_gen.py               # actually generate keyframes

python 08_Automation/storyboard_to_video.py --dry-run    # preview shot list
python 08_Automation/storyboard_to_video.py              # actually generate videos

python 08_Automation/kling_video_api.py --dry-run        # check params
python 08_Automation/kling_video_api.py                  # generate complex shots

python 08_Automation/elevenlabs_tts_api.py --dry-run     # check params
python 08_Automation/elevenlabs_tts_api.py               # generate all dialogue

python 08_Automation/suno_music_api.py --dry-run         # check params
python 08_Automation/suno_music_api.py                   # generate music
```

5. Quality & management:

```bash
python 08_Automation/video_quality_check.py        # video QA
python 08_Automation/asset_dashboard.py --dry-run  # preview asset dashboard
python 08_Automation/asset_dashboard.py            # write 06_Research/asset_dashboard.md
python 08_Automation/daily_brief.py --dry-run      # preview standup brief
python 08_Automation/daily_brief.py                # write 07_Team/daily_briefs/YYYY-MM-DD.md
```

## Output conventions

- Keyframes: `01_Assets/Scenes/SF_{shot_id}_v01.png`
- Videos: `05_Output/Rough_Cuts/SF_{shot_id}_{tool}_v01.mp4`
- Dialogue: `01_Assets/Audio/Dialogue/{character}_{n}.wav`
- Music: `01_Assets/Audio/Music/{track}_v1.mp3`
- Logs: `06_Research/video_gen_log.csv`
- Reports: `06_Research/*.md`
