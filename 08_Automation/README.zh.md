# ShotFlow — 自动化脚本说明

[English](./README.md) | 中文（当前）

本目录存放项目中所有自动化脚本，涵盖环境部署、批量生成、API 调用、质量检测与项目管理。

> 所有脚本均使用 `PROJECT_ROOT = Path(__file__).resolve().parent.parent` 定位项目根目录，可从任意目录运行。大部分脚本支持 `--help` / `--dry-run` 参数，建议首次运行时先用 `--help` 查看用法。

## 文件清单

### 环境与部署

| 文件 | 用途 |
|------|------|
| `deploy_comfyui.sh` | 部署 ComfyUI 环境与必要节点 |
| `init_git.sh` | 初始化 Git 仓库与 .gitignore |
| `preflight_check.py` | 预飞行环境检查（GPU/内存/磁盘/模型/API 密钥） |
| `project_health_check.py` | 项目结构完整性检查（被 CI 与测试调用） |
| `benchmark.py` | ComfyUI 性能基准测试（Flux/Wan2.2） |
| `requirements.txt` | 运行时 Python 依赖清单 |
| `requirements-dev.txt` | 开发依赖（black/isort/pytest） |

### 批量生成

| 文件 | 用途 |
|------|------|
| `batch_keyframe_gen.py` | 通过 ComfyUI API 批量生成关键帧 |
| `storyboard_to_video.py` | 分镜到视频流水线（Wan2.2 I2V/T2V） |
| `kling_video_api.py` | 可灵 2.5 Turbo 图生视频（含首尾帧） |
| `elevenlabs_tts_api.py` | ElevenLabs 文本转语音，生成角色对白 |
| `suno_music_api.py` | Suno AI 科幻氛围配乐生成 |
| `render_queue.py` | 已弃用 — 渲染队列管理器（已被后端 `queue_service.py` 取代，保留作离线回退） |

### 质量与管理

| 文件 | 用途 |
|------|------|
| `video_quality_check.py` | 视频质量自动检测（分辨率/帧率/闪烁/锐度） |
| `asset_dashboard.py` | 资产盘点与进度看板 |
| `daily_brief.py` | 每日站会简报生成 |

### 仓库同步

| 文件 | 用途 |
|------|------|
| `sync_repos.sh` | GitHub/GitCode 双仓库同步推送 |
| `package_workflows.sh` | ComfyUI 工作流 JSON 打包发布 |

## 快速开始

下列命令均在**仓库根目录**（包含 `README.md` 与 `08_Automation/` 的目录）下执行。

1. 安装依赖：

```bash
pip install -r 08_Automation/requirements-dev.txt
# PyTorch 请按 CUDA 版本单独安装: https://pytorch.org
```

2. 配置环境变量（复制 .env.example 并编辑）：

```bash
cp .env.example .env
# 编辑 .env，填入 KLING_API_KEY、ELEVENLABS_API_KEY、SUNO_API_KEY 等
```

3. 预飞行检查：

```bash
python 08_Automation/preflight_check.py         # 完整检查（需要 GPU/模型）
python 08_Automation/preflight_check.py --dry-run  # 只检查结构与密钥
```

4. 批量生成（首次运行建议先加 `--help` / `--dry-run`）：

```bash
python 08_Automation/batch_keyframe_gen.py --dry-run     # 预览关键帧列表
python 08_Automation/batch_keyframe_gen.py               # 实际生成关键帧

python 08_Automation/storyboard_to_video.py --dry-run    # 预览视频镜头列表
python 08_Automation/storyboard_to_video.py              # 实际生成视频

python 08_Automation/kling_video_api.py --dry-run        # 检查参数
python 08_Automation/kling_video_api.py                  # 生成复杂镜头

python 08_Automation/elevenlabs_tts_api.py --dry-run     # 检查参数
python 08_Automation/elevenlabs_tts_api.py               # 生成全部配音

python 08_Automation/suno_music_api.py --dry-run         # 检查参数
python 08_Automation/suno_music_api.py                   # 生成配乐
```

5. 质量与管理：

```bash
python 08_Automation/video_quality_check.py        # 视频质检
python 08_Automation/asset_dashboard.py --dry-run  # 预览资产看板
python 08_Automation/asset_dashboard.py            # 写入 06_Research/asset_dashboard.md
python 08_Automation/daily_brief.py --dry-run      # 预览站会简报
python 08_Automation/daily_brief.py                # 写入 07_Team/daily_briefs/YYYY-MM-DD.md
```

## 输出规范

- 关键帧：`01_Assets/Scenes/SF_{镜头号}_v01.png`
- 视频：`05_Output/Rough_Cuts/SF_{镜头号}_{工具}_v01.mp4`
- 配音：`01_Assets/Audio/Dialogue/{角色}_{序号}.wav`
- 配乐：`01_Assets/Audio/Music/{曲名}_v1.mp3`
- 日志：`06_Research/video_gen_log.csv`
- 报告：`06_Research/*.md`
