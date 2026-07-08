# ShotFlow —— 从零到 4K 母版的完整教程

[English](./tutorial.md) | 中文（当前）

> 这是一份手把手教程，带你在 ShotFlow 流水线里完成一部 3–5 分钟的 AIGC 短片。我们以示例片《奇点回响》作为贯穿全篇的案例，但每一步都设计成可以替换成你自己的故事。

教程内容来自做《奇点回响》时实际跑通的流程，不是泛泛的"AIGC 视频技巧"——下文每条命令、每个文件路径都指向仓库里真实存在的脚本和工作流。

---

## 1. 引言

### 这份教程能帮你做什么

把一部短片从一行 idea 一路推到 4K 母版、各平台发布包、可复用的 ComfyUI 工作流打包。走完之后你将拿到：

- 一份剧本、世界观、角色圣经，下游的关键帧提示词可以机械式地从这些文档生成。
- 24+ 张通过盲测的角色一致性关键帧。
- ~24 条视频镜头，根据镜头复杂度走本地 Wan2.2 或可灵 API。
- 配音和配乐分轨，按 web/影院响度标准混音。
- 一版 DaVinci 剪辑、青橙调色、Topaz 超分后的 4K 母版。
- 每个发布平台（B 站 / YouTube / 抖音 / 小红书 / 微信视频号 / Reels / 电影节）的交付包，AIGC 标识已就位。

### 适合谁读

已经有故事 idea、想把它做成正片而不是 demo 集锦的人。你得习惯命令行、愿意装 ComfyUI，最好有一张 24 GB 的 NVIDIA 显卡。剪辑师和制片人没有 GPU 也能用 `SIMULATE_MODE` 把整条链路跑一遍熟悉流程，之后再切到 GPU 主机做真实生成。

### 你需要什么

| 项目 | 最低 | 推荐 |
|------|------|------|
| GPU | RTX 3090 24 GB | RTX 4090 24 GB |
| 内存 | 32 GB | 64 GB |
| 存储 | 200 GB SSD | 1 TB NVMe |
| 操作系统 | Ubuntu 22.04 | Ubuntu 22.04 / Windows 11 |
| ComfyUI | 最新版 | 最新版 + ComfyUI Manager |
| DaVinci Resolve | 18（免费版） | 19 |
| Topaz Video AI | Personal | Pro |
| API key | 可灵（PiAPI）用于复杂镜头 | + ElevenLabs + Suno 用于音频 |

只有 CPU？跳过本地 Wan2.2，所有镜头走云端 API（可灵 / Runway）。流水线的 Provider 评分器在 `settings.HAS_GPU=false` 时会自动这么做。

### 流水线一览

每个环节选择的理由见 [`AIGC_Experience_Chain.md`](../AIGC_Experience_Chain.md)。简版：前期锁定角色，Flux.1 Kontext + IPAdapter 锁脸，Wan2.2 出标准镜头，可灵出复杂镜头，DaVinci + ElevenLabs + Suno + Topaz 完成后期。

---

## 2. 前置准备与环境

### 2.1 克隆仓库

```bash
git clone https://github.com/MS33834/ShotFlow.git
cd ShotFlow
```

### 2.2 选一种部署方式

**方式 A —— Docker（最快上手，无 GPU 也能跑通流程）：**

```bash
cp .env.example .env            # 然后编辑 .env，见下文 2.4
docker compose up -d            # postgres + redis + backend + worker + frontend
```

镜像里装好了 Python 依赖和项目脚本。ComfyUI 和模型权重 **不** 在镜像里（授权 + 体积原因）。真实生成请用方式 B。

**方式 B —— 本地源码（真实生成）：**

```bash
cp .env.example .env            # 编辑 .env，见下文 2.4
bash 08_Automation/deploy_comfyui.sh    # 需要 NVIDIA GPU，推荐 RTX 4090 24GB
make setup                      # 安装 Python 依赖（含 black、isort、pytest）
make check                      # 校验项目结构
```

### 2.3 部署 ComfyUI（仅 GPU 主机）

`08_Automation/deploy_comfyui.sh` 会克隆 ComfyUI、装 ComfyUI Manager、拉取项目工作流依赖的自定义节点。模型文件还是要手动放置——精确清单和 HuggingFace 来源见 [`04_SOP/sop_shotflow.md`](../04_SOP/sop_shotflow.md) §1.3：

| 模型 | 放到 |
|------|------|
| FLUX.1-Kontext-dev（FP8 / FP4） | `ComfyUI/models/diffusion_models/` |
| Wan2.2-I2V-A14B FP8 | `ComfyUI/models/diffusion_models/` |
| Wan2.2 VAE | `ComfyUI/models/vae/` |
| umt5_xxl_fp8_e4m3fn_scaled | `ComfyUI/models/text_encoders/` |
| IPAdapter / PuLID 模型包 | 按节点文档 |

启动 ComfyUI，确认它能响应 `.env` 里配置的 URL：

```bash
cd ~/ComfyUI && python main.py --listen --port 8188
curl http://127.0.0.1:8188/system_stats
```

### 2.4 配置 `.env`

复制 `.env.example`，填你手上有的 key。没有的就留空——对应 service 会自动回落到 `SIMULATE_MODE`。

```ini
# 应用
SIMULATE_MODE=true              # true = 模拟输出，无需 GPU。false = 接真实后端
SECRET_KEY=                     # docker compose 没有这个会拒绝启动。生成: openssl rand -hex 32

# ComfyUI
COMFYUI_URL=http://127.0.0.1:8188
COMFYUI_DIR=${HOME}/ComfyUI

# 云端 API
KLING_API_KEY=                  # 通过 PiAPI: https://api.piapi.ai
KLING_BASE_URL=https://api.piapi.ai
ELEVENLABS_API_KEY=
SUNO_API_KEY=
SUNO_BASE_URL=https://api.sunoaiapi.com
```

### 2.5 关于 `SIMULATE_MODE`

`SIMULATE_MODE=true` 是项目里"无 GPU 也能学"的开关。打开之后：

- `backend/app/services/` 里所有生成 service 都返回模拟输出，不真正调用 ComfyUI / 可灵 / ElevenLabs / Suno。
- 流水线骨架、队列、SSE 事件、CSV 日志全部照常工作——你可以不花一分钱 API 费用把整部片子的流程跑一遍。

切到 GPU 主机、配上真实 key 时再设为 `false`。配套的 `settings.HAS_GPU`（默认 `true`）会喂给 Provider 评分器——见第 5 步。

### 2.6 自检

```bash
python 08_Automation/preflight_check.py --dry-run    # 结构 + key 存在性，无需 GPU
make check                                           # 仓库结构
```

如果 `preflight_check.py` 报 GPU 不可用，但你确实有 GPU，多半是 PyTorch 装成了 CPU 版。从 https://pytorch.org 重装 CUDA 版即可。

---

## 3. 第 1 步：剧本与世界观

这一步的目标是产出一组纯文本文档，让下游的提示词可以机械式地从中生成——避免导演和提示词工程师在同一步里互相即兴。

### 3.1 用 LLM 起草圣经

我们用 DeepSeek 或 Claude。给一个紧凑的 brief（类型、片长、基调），一次性让它输出：

1. **世界观设定** —— 时代、地点、单一核心科幻前提、视觉风格关键词（色彩、光影、质感）。
2. **角色圣经** —— 每个角色：姓名、年龄、身份、性格关键词，以及一份固定的**外在锚点**清单（脸、发型、瞳色、疤、服装、道具）。锚点是下一步能成立的前提。
3. **分场景剧本** —— 每个镜头：镜头号、时长、景别、运镜、生成方式提示、情绪 beat、对白（如果有）。
4. **提示词锚点** —— 每个角色一段"每镜必含"文本，加一段负向提示词。

范例见 [`02_Scripts/script_and_worldbuilding.md`](../02_Scripts/script_and_worldbuilding.md)。先读它的结构，再替换内容。注意 Ava 的锚点是一段可以直接复制的文本块：

```
Ava, 28-year-old woman, short dark hair, amber eyes, light scar under right eye,
cybernetic neural interface glowing on back of neck, dark gray patched windbreaker,
black turtleneck, dark cargo pants, scuffed military boots, glowing bracelet on left wrist,
weathered data terminal at waist
```

### 3.2 分镜表和关键帧提示词

在剧本基础上再产出两份文档：

- **详细分镜表** —— 见 [`02_Scripts/detailed_storyboard.md`](../02_Scripts/detailed_storyboard.md)。每个镜头一行，含镜头号、场景、景别、时长、生成方式、提示词摘要。范例有 5 个场景共 24 个镜头。
- **关键帧提示词汇总表** —— 见 [`02_Scripts/keyframe_prompts.md`](../02_Scripts/keyframe_prompts.md)。每个关键帧一行，含完整正向提示词、负向提示词、分辨率、生成方式。《奇点回响》共 29 张关键帧（24 个镜头 + 5 张为可灵准备的首尾帧拆分）。

### 3.3 单独锁定角色圣经

角色圣经单独成文，位于 `examples/echo-of-singularity/character_bible_ava.md`（模板在 `02_Scripts/character_bible_template.md`）。第 2 步的盲测就是以这份文档为评分基准——两张关键帧与圣经冲突时，以圣经为准。

### 3.4 本步产出物

| 文件 | 位置 | 给谁用 |
|------|------|--------|
| 剧本 + 世界观 | `02_Scripts/script_and_worldbuilding.md` | 导演、提示词工程师 |
| 详细分镜表 | `02_Scripts/detailed_storyboard.md` | 第 3 步 |
| 关键帧提示词 | `02_Scripts/keyframe_prompts.md` | 第 2 步 |
| 角色圣经 | `examples/echo-of-singularity/character_bible_ava.md` | 第 2 步盲测 |

导演没确认镜头数和角色锚点之前不要进入下一步。第 2 步之后改锚点等于全部关键帧重出。

---

## 4. 第 2 步：角色一致性关键帧

这一步决定片子成败。如果脸在第 3 镜和第 15 镜之间漂走，再怎么调色都救不回来。我们用 Flux.1 Kontext + IPAdapter 加一道盲测闸门来锁。

### 4.1 工作流

在 ComfyUI 里打开 [`03_Workflows/Flux_Character_Consistency.json`](../03_Workflows/Flux_Character_Consistency.json)（界面版）。脚本调用的 API 版是 [`03_Workflows/api/Flux_Character_Consistency_api.json`](../03_Workflows/api/Flux_Character_Consistency_api.json)。节点连线和依赖见 [`03_Workflows/comfyui_node_connections.md`](../03_Workflows/comfyui_node_connections.md) 和 [`03_Workflows/node_dependencies.md`](../03_Workflows/node_dependencies.md)。

用大白话讲流程：

1. 把角色的三张参考图——正面、侧面、背面——载入 IPAdapter。这是你的**锚点参考**，镜头之间不变。
2. 正向提示词始终以第 1 步的角色锚点块开头，再追加当镜的场景 beat。
3. 负向提示词始终包含 `inconsistent hairstyle, wrong clothing, different person, extra fingers, mutated hands, deformed face`。
4. 采样：1024×1024 或 1280×720，20–30 steps，CFG 3.5–4.5，FP8 精度。

### 4.2 先出三视图参考

碰分镜之前，先出 Ava 的三视图参考集，存到 `01_Assets/Characters/Ava/`：

- `Ava_front.png`
- `Ava_side.png`
- `Ava_back.png`

这三张就是后续每张关键帧 IPAdapter 绑定的对象。重抽直到你能把这三张图给一个没看过角色的同事看，让他描述出同一个人。

### 4.3 批量生成 29 张关键帧

用脚本——别在 ComfyUI 里一条提示词一条提示词地点，你会丢种子和参数。

```bash
# 预览要生成什么，不调 GPU
python 08_Automation/batch_keyframe_gen.py --dry-run

# 真正生成
python 08_Automation/batch_keyframe_gen.py
```

脚本读关键帧提示词表，调 API 工作流，每张关键帧写一张 PNG 到 `01_Assets/Scenes/SF_{shot_id}_v01.png`。每次生成的种子、步数、CFG、提示词都会追加到 `06_Research/video_gen_log.csv`——这就是你的可复现台账。

### 4.4 盲测闸门

任何一张关键帧进入视频生产之前，先跑 [`06_Research/qa_and_blind_test.md`](../06_Research/qa_and_blind_test.md) 描述的盲测：

1. 把 29 张关键帧丢进一个文件夹，文件名打乱。
2. 交给一个没看过分镜的人。
3. 问："这个文件夹里有几个不同的人？"
4. 通过 = 答案是"一个"。其他答案 = 重抽有问题的关键帧，把 IPAdapter 权重往 0.8–1.0 调，或者补锚点关键词。

这道闸门没得商量。重抽一张关键帧比重抽一条 5 秒视频便宜得多。

### 4.5 本步产出物

- `01_Assets/Characters/Ava/{front,side,back}.png` —— 锁定的参考集
- `01_Assets/Scenes/SF_S{scene}_{shot}_v01.png` —— 29 张关键帧
- `06_Research/video_gen_log.csv` —— 每张关键帧的参数和种子
- 一份签字确认的盲测结果

镜头进展表 [`examples/echo-of-singularity/shot_tracker.md`](../examples/echo-of-singularity/shot_tracker.md) 用来记录哪些关键帧过了、哪些要重抽。

---

## 5. 第 3 步：分镜转视频

分镜表每行现在都有关键帧了。这一步把 29 张静帧变成 ~24 条运动镜头，按镜头复杂度选生成器。

### 5.1 标准镜头 —— Wan2.2 I2V 14B

标准镜头是对白、特写、缓推——运动幅度可控的镜头。这些走本地 Wan2.2 I2V 双专家工作流：[`03_Workflows/Wan22_Dual_Expert_Video.json`](../03_Workflows/Wan22_Dual_Expert_Video.json)（界面版）和 [`03_Workflows/api/Wan22_Dual_Expert_Video_api.json`](../03_Workflows/api/Wan22_Dual_Expert_Video_api.json)（API 版）。

为什么用两个专家？**High-Noise 专家**驱动大幅运动，**Low-Noise 专家**修复崩坏帧。标准节奏是先用 High-Noise 跑出运动，再对扭曲或闪烁的镜头跑 Low-Noise 修复。理由见 [`AIGC_Experience_Chain.md`](../AIGC_Experience_Chain.md) §Stage 2。

真正要调的参数（默认值都合理，镜头崩了再调）：

- `frames`: 81（24 fps 下约 3.4 秒）。5 秒镜头用 121。
- `cfg`: 0.5–1.0。低 = 运动更大，高 = 更贴合关键帧。
- `steps`: 30。
- `negative_prompt`: 始终包含 `flickering, distorted motion, inconsistent character, mutated hands`。

### 5.2 复杂镜头 —— 可灵 2.5 Turbo 首尾帧

《奇点回响》有 5 个镜头涉及本地模型搞不定的运镜——核心 chamber 环绕 Ava（`S03_04`）、舱门打开（`S02_05`）、结尾拉远（`S05_04`）。这些走可灵，用**首帧 + 尾帧**约束：给两张关键帧，它生成中间的运动。

通过脚本调用：

```bash
python 08_Automation/kling_video_api.py --dry-run    # 预览
python 08_Automation/kling_video_api.py              # 真正调用
```

可灵参数：`duration: 5`、`aspect_ratio: "16:9"`、`mode: "pro"`、`version: "2.5-turbo"`。先确认 `.env` 里 `KLING_API_KEY` 已配置——调用慢或失败见 [`TROUBLESHOOTING.md`](../TROUBLESHOOTING.md)。

### 5.3 一条命令跑完整张分镜表

```bash
python 08_Automation/storyboard_to_video.py --dry-run    # 预览镜头列表和 provider 选择
python 08_Automation/storyboard_to_video.py              # 真正生成
```

脚本读分镜表，按 `gen_method` 列给每个镜头选 Wan2.2 或可灵，把片段写到 `05_Output/Rough_Cuts/SF_{shot_id}_{tool}_v01.mp4`。命名遵循 [`04_SOP/sop_shotflow.md`](../04_SOP/sop_shotflow.md) §6.1：`SCENE_SHOT_TAKE_TOOL_vNN.mp4`。

### 5.4 Provider 自动选择与回退

走 Web 平台的渲染队列（第 9 步）而不是 CLI 时，后端 `render_tasks._dispatch` 会替你选 provider。如果你没固定 `extra.provider`，它会用镜头的 `complexity` 和 `settings.HAS_GPU` 调 `provider_scorer.recommend_provider`，并把所选 provider 写回 `extra._provider_source="auto"` 供事后追溯。评分维度（质量 / 速度 / 成本 / 能力）和权重见 [`backend/app/services/provider_scorer.py`](../backend/app/services/provider_scorer.py)。

简言之：标准镜头 + GPU = 本地 Wan2.2。标准镜头 + 无 GPU = 走云端。复杂镜头 = 一律可灵，因为 Wan2.2 做不好首尾帧约束。

### 5.5 每条镜头都要质检

```bash
python 08_Automation/video_quality_check.py
```

按镜头表检查分辨率、帧率、闪烁、锐度。闪烁是最常见的失败——修法是 Low-Noise 专家再来一遍，再不行就用第 7 步的 Topaz 时域降噪。

### 5.6 本步产出物

- `05_Output/Rough_Cuts/SF_S{scene}_{shot}_{tool}_v01.mp4` —— ~24 条片段
- `06_Research/video_gen_log.csv` —— 每条片段的参数、种子、provider、重试次数
- 一份状态已更新为"已渲染"或"重抽"的镜头表

---

## 6. 第 4 步：音频制作

画面差不多锁了。现在铺声音。音频分三条轨：对白（ElevenLabs）、配乐（Suno）、音效（素材库 + 生成）。

### 6.1 声音圣经 —— 出第一句对白前先锁声线

每个角色在声音圣经里都有一条记录，固定 TTS 引擎、voice ID 和各维度参数（stability、similarity、style、speaker boost）。范例见 [`01_Assets/Audio/voice_bibles.md`](../01_Assets/Audio/voice_bibles.md)。Ava 的配置：

| 维度 | 设定 |
|------|------|
| ElevenLabs Voice | `Rachel` |
| Stability | 40% |
| Similarity | 75% |
| Style | 0.25 |
| Speaker Boost | 开启 |
| 模型 | `eleven_multilingual_v2` |
| 后处理 | 高通 80 Hz / 去齿音 / 轻混响（RT60 0.4 s） |

锁定之后，**所有**该角色的对白都用同一组参数。要改就必须 bump 版本号、把该角色全部对白重生成——不然镜头之间声线漂移，剪辑就崩了。校准样音：`01_Assets/Audio/Dialogue/Ava/_reference_v1.wav`。

### 6.2 生成对白

```bash
python 08_Automation/elevenlabs_tts_api.py --dry-run    # 预览
python 08_Automation/elevenlabs_tts_api.py              # 真正生成
```

输出：`01_Assets/Audio/Dialogue/{Role}/{Role}_{ShotID}_v1.wav`。每条都要人工审听——字音（中文多音字、专有名词"奇点"读 qí diǎn）、情绪是否匹配圣经的情绪分段、有没有喷麦和齿音爆点。

### 6.3 生成配乐

```bash
python 08_Automation/suno_music_api.py --dry-run
python 08_Automation/suno_music_api.py
```

《奇点回响》我们用 `sci-fi, cinematic, ambient, electronic` 加每场景的情绪标签（tense / hopeful / mysterious），每个 cue 出 3–5 条候选，凭耳朵挑。输出：`01_Assets/Audio/Music/{Theme}_v1.mp3`。配乐要进成片就用 Suno Pro 或 Premier 计划——免费版仅限非商用（见 [`06_Research/licensing_compliance.md`](../06_Research/licensing_compliance.md) §2.6）。

### 6.4 cue sheet —— 每个音频事件都带时间码

[`01_Assets/Audio/cue_sheet.md`](../01_Assets/Audio/cue_sheet.md) 是混音的主轴。它列出 4:10 全片：

- **A1 对白** —— 10 个 cue，含入/出点时间码、角色、文件路径
- **A3/A4 配乐** —— 7 个 cue，主题 + 氛围分层，含侧链避让规则
- **A5/A6 音效** —— 10 个 cue，点状 + 环境床

混音响度目标钉在 cue sheet 末尾：

```
对白 A1     -6 dBFS    HPF 80 Hz, +2 dB @ 2 kHz
配乐 A3/A4 -18 dBFS    侧链压缩避让 A1
点状 A5    -20 dBFS    分层分组，按画面位置 pan
环境 A6    -24 dBFS    持续低垫，不抢戏

总线         -1 dBTP    LUFS -16 (web)  /  LUFS -14 (cinema)
```

### 6.5 走 Web 平台的路径（备选）

如果你从 Web 平台而不是 CLI 跑音频，同样的 TTS 和配乐脚本被 `backend/app/services/audio_service.py`（`run_tts_task`、`run_music_task`）封装。它 shell out 调的是同一份 `08_Automation` 脚本——同样的输出、同样的命名，只是改走队列提交。`SIMULATE_MODE` 下返回模拟路径，方便排练。

### 6.6 本步产出物

- `01_Assets/Audio/Dialogue/{Role}/` —— 每条对白 WAV 分轨
- `01_Assets/Audio/Music/{Themes,Ambient}/` —— 配乐分轨
- `01_Assets/Audio/SFX/{Environment,Mechanical,UI}/` —— 音效分轨（来源和授权链见 [`01_Assets/Audio/sfx_list.md`](../01_Assets/Audio/sfx_list.md)）
- `01_Assets/Audio/cue_sheet.md` —— 锁定的混音主轴

---

## 7. 第 5 步：后期

所有东西在 DaVinci Resolve 里汇合。完整的剪辑走查见 [`05_Output/Final/assembly_guide.md`](../05_Output/Final/assembly_guide.md)；本节是简版。

### 7.1 输入物

| 输入 | 位置 |
|------|------|
| 渲染好的镜头片段 | `05_Output/Renders/SF_S{scene}_{shot}_*.mp4` |
| 参考关键帧 | `01_Assets/Scenes/SF_S*.png` |
| EDL | [`05_Output/EDL/shotflow_v01.edl`](../05_Output/EDL/shotflow_v01.edl) |
| 对白 / 配乐 / 音效分轨 | `01_Assets/Audio/{Dialogue,Music,SFX}/` |
| 调色 LUT | `05_Output/Final/shotflow_grade.cube` |
| 字幕 | `05_Output/Final/subtitles/*.srt` |

### 7.2 工程设置

- 时间线：3840×2160，24 fps
- 色彩科学：DaVinci YRGB Color Managed，ACEScct
- 输出：网络用 Rec.709 (Scene)；影院用 DCI-P3 D65

### 7.3 从 EDL 建时间线

Edit 页 → Timeline → Import → EDL → 选 [`05_Output/EDL/shotflow_v01.edl`](../05_Output/EDL/shotflow_v01.edl)。打开"Relink to media pool"，handle frames 设 12。EDL 落到 V1，24 个事件。总时长跟 [`examples/echo-of-singularity/shot_tracker.md`](../examples/echo-of-singularity/shot_tracker.md) 对一下——应该是 ~4:10。

> 提交进仓库的 EDL 是 v01 粗剪版，每镜 3–5 秒。以镜头表的场景级时间码为准去 trim/extend。

### 7.4 在六条轨上铺音频

A1 对白、A2 备用条、A3 主题配乐、A4 氛围配乐、A5 点状音效、A6 环境床。入/出点从 [`01_Assets/Audio/cue_sheet.md`](../01_Assets/Audio/cue_sheet.md) 取。A3/A4 侧链压缩避让 A1。按 §6.4 的响度目标混。详细混音规则见 [`05_Output/Final/final_mix_notes.md`](../05_Output/Final/final_mix_notes.md)。

### 7.5 调色 —— 青橙

1. 在 V1 起点放一个 LUT 节点，载入 `05_Output/Final/shotflow_grade.cube`。
2. 每镜：暗部往青色提，高光往暖橙推。肤色保持中性——Ava 的琥珀色眼睛是参考。
3. 记忆蒙太奇（`S04_01`）：bloom + 饱和度 +0.15，35 mm 颗粒。
4. 结尾（`S05_04` → `S05_06`）：渐暖，黑场抬 5%，对比度收一点。

每条调色决策都记录在 [`05_Output/Final/color_grading_notes.md`](../05_Output/Final/color_grading_notes.md) 里，含每场景的节点图。

### 7.6 Topaz 4K 超分与修复

如果某些渲染片段没到 4K，或 Low-Noise 专家修不掉闪烁，在最终 mixdown **之前** 跑 Topaz Video AI。模型选择和每镜修复日志见 [`05_Output/Final/upscale_and_repair_notes.md`](../05_Output/Final/upscale_and_repair_notes.md)：

- 超分 2× / 4×：Proteus（通用）或 Iris（人脸）
- 降噪：Nyx
- 稳定：只在镜头真的需要时用——滥用会把手持感杀掉

输出到 `05_Output/Rough_Cuts/enhanced/`，在 DaVinci 里重新 link。

### 7.7 输出

从 Deliver 页按目标各导一版母版——见 [`05_Output/Final/assembly_guide.md`](../05_Output/Final/assembly_guide.md) §7 的表。实际会用的四版：

| 预设 | 分辨率 | 编码 | 文件 |
|------|--------|------|------|
| Master 4K | 3840×2160 | H.265 CRF 18 | `ShotFlow_4K_Master_v10.mp4` |
| Web 1080p | 1920×1080 | H.264 CRF 20 | `ShotFlow_1080p_v10.mp4` |
| Vertical | 1080×1920 | H.264 CRF 20 | `ShotFlow_1080x1920_v10.mp4` |
| Festival | 3840×2160 | ProRes 422 HQ | `ShotFlow_4K_ProRes_v10.mov` |

### 7.8 锁版检查

bump 版本号之前，跑 [`05_Output/Final/assembly_guide.md`](../05_Output/Final/assembly_guide.md) §8 的八项检查——时间线长度、无黑场、对白清晰、字幕校对、响度 -16 LUFS（web）/ -14 LUFS（影院）、true peak ≤ -1 dBTP、色卡中性、片尾停留 ≥ 2 秒。

### 7.9 本步产出物

- `05_Output/Final/ShotFlow_4K_Master_v10.mp4` —— 锁定的母版
- `05_Output/Final/ShotFlow_4K_ProRes_v10.mov` —— 电影节母版
- `05_Output/Final/asset_manifest.md` —— 完整资产清单 + 校验和模板
- `05_Output/Final/subtitles/` —— `.srt`（zh + en）和电影节烧录用 `.ass`
- `05_Output/Final/credits.md` —— 演员、配音、音乐、工具、授权字幕

---

## 8. 第 6 步：交付与发布

片子锁了。接下来把它打包成各平台发布包，并在不踩 AIGC 标识合规坑的前提下发出去。

### 8.1 平台规格

[`05_Output/Final/delivery_specs.md`](../05_Output/Final/delivery_specs.md) 是主规格书。简版：

| 平台 | 分辨率 | 编码 | 音频 | AIGC 标识 |
|------|--------|------|------|-----------|
| B 站 / YouTube | 1920×1080 | H.264 | AAC 128 kbps | B 站勾"AIGC 创作"；YouTube 描述首行注明 |
| 抖音 / 小红书 / Reels | 1080×1920 | H.264 | AAC 128 kbps | 勾"AIGC 创作" / 描述首行注明 |
| 微信视频号 | 1080×1080 或 1080×1920 | H.264 | AAC 128 kbps | 勾 AIGC |
| 电影节 / 投奖 | 4K ProRes 422 HQ | ProRes | PCM 16-bit | 按《生成式人工智能服务管理暂行办法》显著标识 |

### 8.2 每个平台打一个发布包

[`09_Release/distribution_kit.md`](../09_Release/distribution_kit.md) 定义了每个平台发布文件夹的精确内容。B 站包例如：

```
release_bilibili/
├── ShotFlow_1080p_v10.mp4
├── ShotFlow_1080x1920_v10.mp4
├── cover_landscape_1146x717.jpg
├── cover_portrait_1080x1920.jpg
├── echo_of_singularity.zh.srt
├── title.txt
├── description.txt
├── tags.txt
└── LICENSE.txt
```

竖屏平台（抖音、小红书、微信、Reels）共用一组竖版物料，只有标题/简介/标签按平台调。竖版剪辑规则见 [`09_Release/distribution_kit.md`](../09_Release/distribution_kit.md) §4——主镜头保留但景别改为中近景，字幕字号 +50%，时长压缩到 60–90 秒（剪高潮段：S03_04 + S05_04 + S05_06），片尾 5 秒固定标题 + 仓库链接。

封面和海报规格见 [`09_Release/poster_spec.md`](../09_Release/poster_spec.md)——尺寸、字体、封面图的 Flux.1 提示词。

### 8.3 AIGC 标识与授权

两件事不能省：

1. **AIGC 标识。** 影片发布的每个平台都要求 AIGC 标注。有勾选项的平台就勾；没有就把 "AI-generated short film"（或中文 "本片为 AIGC 生成内容"）放在描述首行。电影节投奖按《生成式人工智能服务管理暂行办法》显著标识——多数电影节把 AIGC 作品单独分类评审。
2. **授权审计。** 任何商用发布（付费点播、广告分成、品牌合作、付费参赛）之前，过一遍 [`06_Research/licensing_compliance.md`](../06_Research/licensing_compliance.md)。仓库本身采用 CNCL（自定义非商业许可证）；几个组件默认也是 NC（Flux.1 Kontext [dev]、Suno 免费版、ElevenLabs 免费版）。合规文档列了每个组件的许可、商用边界、升级费用。简版：Flux 商用授权是贵的那个；SaaS 订阅（ElevenLabs Creator、Suno Pro、Topaz Pro）便宜，订阅后即解锁商用权。

### 8.4 发布前最终检查

每个平台发布前过 [`09_Release/release_checklist.md`](../09_Release/release_checklist.md)。重点：

- [ ] 母版通过 [`08_Automation/video_quality_check.py`](../08_Automation/video_quality_check.py)
- [ ] 字幕无错别字（zh + en 都已校对）
- [ ] 标题 / 简介无违规词
- [ ] 已勾选 AIGC 标识 / 已加标注行
- [ ] 封面尺寸符合平台规格
- [ ] 简介里已加开源仓库链接
- [ ] 简介里已加 CNCL 许可证声明
- [ ] `LICENSE.txt` 随包附送

### 8.5 本步产出物

- `09_Release/release_{bilibili,youtube,vertical,festival}/` —— 各平台发布包
- 各平台上线的正片
- 归档好的授权凭证和 API 账单（按 [`06_Research/licensing_compliance.md`](../06_Research/licensing_compliance.md) 附录的目录结构放到 `06_Research/licenses/`）

---

## 9. 使用 Web 平台

CLI 让一个人能跑通流水线。Web 平台让一个小团队从浏览器驱动它——同样的生成逻辑，后端是封装 `08_Automation` 脚本，而不是重写。

### 9.1 起全栈

```bash
cp .env.example .env            # 设置 SECRET_KEY（openssl rand -hex 32）和 API key
docker compose up -d            # postgres + redis + backend + worker + frontend
```

验证：

```bash
curl http://localhost:8000/api/v1/health     # DB + Redis
open http://localhost:8000/docs              # Swagger
open http://localhost                        # 前端管理后台
```

`docker-compose.yml` 里默认 `SIMULATE_MODE=true`。所有 service 返回模拟输出，全链路无 GPU 也能跑。在 GPU 主机上切到 `false` 才真正调 ComfyUI / 可灵 / ElevenLabs / Suno。

### 9.2 后端 API 一览

| 路由 | 用途 |
|------|------|
| `/api/v1/projects` | 项目 CRUD |
| `/api/v1/shots` | 镜头与分镜管理 |
| `/api/v1/keyframes` | 关键帧管理 |
| `/api/v1/videos` | 视频片段管理 |
| `/api/v1/audio` | 对白与配音 |
| `/api/v1/queue` | 渲染队列：提交 / 查询 / 重试 / 取消 |
| `/api/v1/queue/stream/events` | SSE 实时队列状态 |
| `/api/v1/workflows` | ComfyUI 工作流管理 |
| `/api/v1/qa` | QA 报告 |
| `/api/v1/daily-briefs` | 每日站会简报 |
| `/api/v1/health` | 健康检查（DB + Redis） |

### 9.3 前端管理后台

React 18 + TypeScript + Vite + Ant Design Pro。路由：

| 路由 | 用途 |
|------|------|
| `/login` | 登录（JWT） |
| `/dashboard` | 总览：健康 + 队列统计 + 项目 |
| `/projects` | 项目 CRUD |
| `/shots` | 镜头管理（按项目筛选） |
| `/keyframes` | 关键帧管理（提交生成） |
| `/queue` | 渲染队列，SSE + 提交 / 重试 / 取消 |
| `/workflows` | ComfyUI 工作流管理 |
| `/workflow-configs` | YAML 配置 + Provider 评分 |
| `/assets` | 资产画廊（按类型扫描磁盘） |
| `/audio` | 对白与配音 |
| `/qa` | QA 报告 |
| `/case-studies` | 案例展示 |

SSE 推送用 `useQueueStream` hook，带指数退避重连；Nginx 多阶段构建里关掉了 SSE 代理缓冲，事件能干净地流过来。

### 9.4 SSE 实时队列

向 `/api/v1/queue` 提交渲染任务，然后订阅 `/api/v1/queue/stream/events` 看它走 `pending → running → done`（或 `failed`）。Celery worker（容器 `shotflow-worker`）同时跑 `--beat`，每 60 秒调一次 `queue.recover`，把崩溃遗留的 `running` 任务恢复回来。所以 worker 重启不会丢活。

### 9.5 YAML 工作流参数化（`/workflow-configs`）

ComfyUI 工作流通过 [`03_Workflows/workflows.yaml`](../03_Workflows/workflows.yaml) 参数化。每个条目声明工作流名、任务类型、要加载的 API JSON 文件，以及一份参数列表——每个参数都知道自己的 `node_class`、`node_input` 和可选的 `node_index`，所以后端能把参数注入到正确的节点，没人需要手改 JSON。

前端 `/workflow-configs` 页暴露这个能力：列出配置、取一个看默认参数、然后 POST 到 `/api/v1/workflows/configs/{name}/inject` 提交你选的参数。后端会校验（类型不对或越界返回 422），返回注入完成的完整工作流 JSON，可以直接提交给 ComfyUI。

API 端点（见 [`backend/app/api/v1/workflow_configs.py`](../backend/app/api/v1/workflow_configs.py)）：

- `GET /api/v1/workflows/configs` —— 列出所有参数化工作流
- `GET /api/v1/workflows/configs/{name}` —— 取一个工作流 + 默认参数
- `POST /api/v1/workflows/configs/{name}/inject` —— 校验并注入参数，返回可提交的工作流
- `GET /api/v1/workflows/provider/recommend?complexity=standard&gen_method=wan_i2v&has_gpu=true` —— 取一个镜头的推荐 provider

### 9.6 Provider 评分（`/provider/recommend`）

`/workflow-configs` 页同时暴露 Provider 评分器。用 `complexity`（`standard` / `complex`）、`gen_method`、`has_gpu` 查询，看后端会选哪个 provider 以及为什么。评分维度是质量、速度、成本、能力，权重偏"质量优先 + 成本敏感"（见 [`backend/app/services/provider_scorer.py`](../backend/app/services/provider_scorer.py)）。这就是 `render_tasks._dispatch` 在 `extra.provider` 未指定时内部调的同一个接口。

### 9.7 什么时候用 Web 平台，什么时候用 CLI

- **CLI** —— 单人作业、脚本化、批量重渲染、CI。单镜迭代更快。
- **Web 平台** —— 团队协作、队列可见性、非工程师驱动生成、通过队列历史做可复现审计。

两边写的是同一批文件夹、同一份 `06_Research/video_gen_log.csv`。项目中途切换是安全的。

---

## 10. 故障排查

完整 FAQ 见 [`TROUBLESHOOTING.md`](../TROUBLESHOOTING.md)。最常见的几个：

**`deploy_comfyui.sh` 跑不起来。** 通常是没装 NVIDIA 驱动、Python 版本不对、或网络问题。用 `nvidia-smi` 和 `python3 --version` 核对；网络问题就用 HuggingFace 镜像或预下载模型。

**`preflight_check.py` 报 GPU 不可用。** 要么机器没 CUDA，要么 PyTorch 装成了 CPU 版。从 https://pytorch.org 重装 CUDA 版。如果真没 GPU，切到云端 API 模式，只跑脚本和后期。

**角色在镜头之间像不同的人。** AIGC 视频的经典翻车。按顺序排查：确认角色圣经锁了所有锚点；确认 IPAdapter 参考图覆盖正/侧/背；把 IPAdapter 权重往 0.8–1.0 调；负向提示词加 `inconsistent hairstyle, wrong clothing`；重抽问题镜头，重跑盲测。

**关键帧出现多指或脸崩。** 负向提示词加 `extra fingers, mutated hands, deformed face`；降 CFG 或加步数；用 ADetailer 或类似节点做局部修复。

**视频闪烁严重。** 确认关键帧和视频提示词一致；用 Wan2.2 Low-Noise 专家修崩坏帧；降低提示词里的运动幅度描述；最后兜底用 Topaz 或 FFmpeg 做时域降噪。

**可灵 API 调用失败或慢。** 确认 `.env` 里 `KLING_API_KEY` 已配置；查 API 配额；查可灵官方文档确认 API 版本和参数格式。慢可以错峰生成或开 webhook 回调。

**ElevenLabs 配音情绪不对。** 换更贴近角色设定的 voice ID；调 stability 和 similarity；给台词加情绪标签，如 `[whisper]`、`[angry]`。

**Suno 配乐风格不对。** 提示词里明确风格、情绪、乐器；用参考音频功能；多出几条凭耳朵挑。

**`sync_repos.sh` 推送失败。** 确认 `.git/config` 里的 remote URL 没有硬编码 token——用 SSH 或 credential manager。GitCode 保持 `https://gitcode.com/badhope/ShotFlow.git`，让 credential manager 提供 token。

**不小心把 API key 提交进仓库了。** 立即吊销 key；用 `git filter-repo` 或 BFG 清历史；重新生成 key 写进 `.env`。

以上都没解决就开 Issue，附上环境、复现步骤、日志。

---

## 11. 下一步

一部片子发完了。接下来：

### 自定义工作流

- 编辑 [`03_Workflows/workflows.yaml`](../03_Workflows/workflows.yaml) 给 `/workflow-configs` 页暴露新参数（分辨率、采样器、调度器），不用动 JSON。
- 把新的 ComfyUI 工作流 JSON 丢进 `03_Workflows/api/`，在 `workflows.yaml` 里加一条，Web 平台会自动识别。
- 换模型——HunyuanVideo、LTX-Video、CogVideoX 已经接进 Provider 评分器的 `_PROVIDERS` 字典（`backend/app/services/provider_scorer.py`），新模型加一条就行。

### 贡献回社区

仓库采用 CNCL（自定义非商业许可证），欢迎 PR。完整规则见 [`CONTRIBUTING.md`](../CONTRIBUTING.md)；要点：

- Fork，从 `main` 切分支，保持现有目录结构和命名风格。
- 新脚本必须过 `preflight_check.py` 的基础检查。
- Python：4 空格缩进，PEP 8。Shell：以 `set -euo pipefail` 开头。文档：干净的 Markdown 标题层级。
- **强制**：每次 push 之前，跑 [`CONTRIBUTING.md`](../CONTRIBUTING.md) 里的远端状态检查清单——待评审的 PR、未关闭的 Issue、过期分支、CI 绿、GitHub/GitCode 镜像一致、本地测试绿、敏感文件扫描干净。绝不在红构建上推。
- 永远不要把 token 写进 `.git/config` 或脚本。用 credential manager。

---

> 本教程是活文档，如果某一步和脚本实际行为不一致，欢迎开 Issue 或 PR。
