# ShotFlow — ComfyUI 工作流节点连接说明

> 本文档为 AIGC 科幻微短剧《奇点回响》(ShotFlow) 的 ComfyUI 工作流详细节点连接指南，供技术总监与 AI 算法工程师在 ComfyUI 中搭建工作流时参考。
>
> 配套文件：
> - `03_Workflows/Flux_Character_Consistency.json` — Flux.1 Kontext [dev] + IPAdapter 角色一致性出图
> - `03_Workflows/Wan22_Dual_Expert_Video.json` — Wan2.2 I2V 14B High/Low Noise 双专家视频生成
> - `03_Workflows/node_dependencies.md` — 节点与模型依赖清单
>
> 约定：本文中"节点 A → 节点 B"表示 A 的输出连接到 B 的输入；表格中"来源"列填写 `<源节点>.<输出名>`，"去向"列填写 `<目标节点>.<输入名>`。

---

## 一、Flux 角色一致性工作流节点连接

### 1.1 工作流概述

| 项目 | 说明 |
|------|------|
| 工作流名称 | Flux_Character_Consistency |
| 核心模型 | FLUX.1-Kontext-dev-fp8.safetensors |
| 一致性方案 | IPAdapter 面部锚点 + 服装/发型关键词固定 |
| 输出分辨率 | 1024×1024 或 1280×720 |
| 采样参数 | steps 24, cfg 4.0, euler, simple, denoise 1.0 |
| 推荐硬件 | RTX 4090 24GB（FP8 精度） |

### 1.2 节点连接总览（数据流）

```
UNETLoader ──┐
DualCLIPLoader ─┬──> CLIPTextEncode(正面) ──┐
                ├──> CLIPTextEncode(负面) ──┤
LoadImage×3 ──┐ │                           │
IPAdapterModelLoader ─┴──> IPAdapterAdvanced ┤
                                           ├──> KSampler ──> VAE Decode ──> SaveImage
EmptyLatentImage ──────────────────────────┘
```

### 1.3 节点详细连接表

#### 节点 1 — UNETLoader（加载 Flux 主模型）

| 字段 | 内容 |
|------|------|
| 节点类型 | `UNETLoader`（Flux 用 UNETLoader；若使用 CheckpointLoaderSimple 则改为对应类型） |
| 关键参数 | `unet_name`: `FLUX.1-Kontext-dev-fp8.safetensors`；`weight_dtype`: `fp8_e4m3fn` |
| 输入连接 | 无（根节点） |
| 输出连接 | `MODEL` → `IPAdapterAdvanced.model`、`KSampler.model` |

> 说明：Flux.1 Kontext 属扩散模型（UNET）而非传统 Checkpoint，故使用 `UNETLoader`。模型存放路径：`ComfyUI/models/diffusion_models/`。

#### 节点 2 — DualCLIPLoader（加载双文本编码器）

| 字段 | 内容 |
|------|------|
| 节点类型 | `DualCLIPLoader` |
| 关键参数 | `clip_name1`: `t5xxl_fp8_e4m3fn.safetensors`；`clip_name2`: `clip_l.safetensors`；`type`: `flux` |
| 输入连接 | 无（根节点） |
| 输出连接 | `CLIP` → `CLIPTextEncode(正面).clip`、`CLIPTextEncode(负面).clip` |

> 说明：Flux 必须同时加载 T5XXL 与 CLIP-L 两个文本编码器，`type` 必须设为 `flux`，否则编码结果维度不匹配。

#### 节点 3 — LoadImage ×3（加载角色参考图）

| 字段 | 内容 |
|------|------|
| 节点类型 | `LoadImage`（共 3 个实例） |
| 关键参数 | `image`: 分别选择 `ava_front.png`、`ava_side.png`、`ava_back.png`（正面/侧面/背面三视图） |
| 输入连接 | 无（根节点） |
| 输出连接 | `IMAGE` → `IPAdapterAdvanced.image`（三张图分别接入，或通过图像批处理节点合并后接入） |

> 说明：参考图需光照均匀、面部清晰、服装锚点完整。建议分辨率不低于 768×1024。

#### 节点 4 — IPAdapterModelLoader（加载 IPAdapter 模型）

| 字段 | 内容 |
|------|------|
| 节点类型 | `IPAdapterModelLoader` |
| 关键参数 | `ipadapter_file`: `ip-adapter-faceid-plusv2_sd15.bin`（或 Flux 专用 IPAdapter 权重） |
| 输入连接 | 无（根节点） |
| 输出连接 | `IPADAPTER` → `IPAdapterAdvanced.ipadapter` |

#### 节点 5 — IPAdapterAdvanced（应用面部一致性约束）

| 字段 | 内容 |
|------|------|
| 节点类型 | `IPAdapterAdvanced` |
| 关键参数 | `weight`: `0.7`（范围 0.7–0.8）；`weight_type`: `linear`；`start_at`: `0.0`；`end_at`: `1.0`；`unfold_batch`: `true` |
| 输入连接 | `model` ← `UNETLoader.MODEL`；`ipadapter` ← `IPAdapterModelLoader.IPADAPTER`；`image` ← `LoadImage.IMAGE`（三视图） |
| 输出连接 | `MODEL` → `KSampler.model` |

> 说明：`weight` 0.7–0.8 为本项目调优区间（见 `06_Research/parameter_tuning.md`）。过低一致性不足，过高易出现参考图痕迹/过拟合。

#### 节点 6 — CLIPTextEncode（正面提示词）

| 字段 | 内容 |
|------|------|
| 节点类型 | `CLIPTextEncode` |
| 关键参数 | `text`: 角色锚点 + 场景描述（模板见下） |
| 输入连接 | `clip` ← `DualCLIPLoader.CLIP` |
| 输出连接 | `CONDITIONING` → `KSampler.positive` |

正面提示词模板：
```
Ava, a 28-year-old woman with short dark hair, amber eyes, light scar under right eye,
cybernetic neural interface glowing on the back of her neck, wearing dark gray windbreaker
with patched right shoulder, black turtleneck, dark cargo pants, scuffed military boots,
left wrist glowing bracelet, weathered data terminal at waist, {scene_description},
cinematic sci-fi lighting, film grain, teal and orange color grade
```

#### 节点 7 — CLIPTextEncode（负面提示词）

| 字段 | 内容 |
|------|------|
| 节点类型 | `CLIPTextEncode` |
| 关键参数 | `text`: 负面提示词 |
| 输入连接 | `clip` ← `DualCLIPLoader.CLIP` |
| 输出连接 | `CONDITIONING` → `KSampler.negative` |

负面提示词模板：
```
bad anatomy, deformed face, extra limbs, blurry, low quality, inconsistent character,
different person, mutated hands
```

#### 节点 8 — EmptyLatentImage（空 Latent 画布）

| 字段 | 内容 |
|------|------|
| 节点类型 | `EmptyLatentImage`（或 `LatentFromBatch` 复用批次） |
| 关键参数 | `width`: `1024`、`height`: `1024`（或 `1280`×`720`）；`batch_size`: `4` |
| 输入连接 | 无（根节点） |
| 输出连接 | `LATENT` → `KSampler.latent_image` |

> 说明：横屏镜头使用 1280×720，方图/角色立绘使用 1024×1024。

#### 节点 9 — KSampler（采样生成）

| 字段 | 内容 |
|------|------|
| 节点类型 | `KSampler` |
| 关键参数 | `seed`: `-1`；`steps`: `24`；`cfg`: `4.0`；`sampler_name`: `euler`；`scheduler`: `simple`；`denoise`: `1.0` |
| 输入连接 | `model` ← `IPAdapterAdvanced.MODEL`；`positive` ← `CLIPTextEncode(正面).CONDITIONING`；`negative` ← `CLIPTextEncode(负面).CONDITIONING`；`latent_image` ← `EmptyLatentImage.LATENT` |
| 输出连接 | `LATENT` → `VAEDecode.samples` |

> 说明：Flux Kontext 推荐 `euler` + `simple` 调度器组合；`denoise 1.0` 表示完全重绘（非图生图局部重绘场景）。

#### 节点 10 — VAEDecode（解码 Latent）

| 字段 | 内容 |
|------|------|
| 节点类型 | `VAEDecode` |
| 关键参数 | 无特殊参数（Flux 内置 VAE 随模型加载，无需单独 VAELoader） |
| 输入连接 | `samples` ← `KSampler.LATENT`；`vae` ← Flux 模型自带 VAE（通过 `UNETLoader` 后由 `VAELoader` 加载 `ae.safetensors`，或使用 `LoadVAE` 显式加载） |
| 输出连接 | `IMAGE` → `SaveImage.images` |

> 说明：Flux 的 VAE 权重文件通常为 `ae.safetensors`，存放于 `ComfyUI/models/vae/`。若工作流未自动注入 VAE，需增加 `VAELoader` 节点并将其 `VAE` 输出连接到 `VAEDecode.vae`。

#### 节点 11 — SaveImage（保存结果）

| 字段 | 内容 |
|------|------|
| 节点类型 | `SaveImage` |
| 关键参数 | `filename_prefix`: `SF_Ava_` |
| 输入连接 | `images` ← `VAEDecode.IMAGE` |
| 输出连接 | 无（终端节点） |

### 1.4 节点连接速查表

| 序号 | 节点类型 | 关键参数 | 输入来源 | 输出去向 |
|------|----------|----------|----------|----------|
| 1 | UNETLoader | `FLUX.1-Kontext-dev-fp8.safetensors`, fp8 | — | IPAdapterAdvanced.model, KSampler.model |
| 2 | DualCLIPLoader | t5xxl_fp8 + clip_l, type=flux | — | CLIPTextEncode(正/负).clip |
| 3 | LoadImage ×3 | 正面/侧面/背面三视图 | — | IPAdapterAdvanced.image |
| 4 | IPAdapterModelLoader | ip-adapter-faceid-plusv2 | — | IPAdapterAdvanced.ipadapter |
| 5 | IPAdapterAdvanced | weight 0.7–0.8 | UNETLoader.MODEL, IPAdapterModelLoader.IPADAPTER, LoadImage.IMAGE | KSampler.model |
| 6 | CLIPTextEncode(正面) | 角色锚点+场景 | DualCLIPLoader.CLIP | KSampler.positive |
| 7 | CLIPTextEncode(负面) | 负面提示词 | DualCLIPLoader.CLIP | KSampler.negative |
| 8 | EmptyLatentImage | 1024×1024 或 1280×720 | — | KSampler.latent_image |
| 9 | KSampler | steps24/cfg4.0/euler/simple/denoise1.0 | IPAdapterAdvanced.MODEL, CLIPTextEncode×2.CONDITIONING, EmptyLatentImage.LATENT | VAEDecode.samples |
| 10 | VAEDecode | — | KSampler.LATENT, VAELoader.VAE | SaveImage.images |
| 11 | SaveImage | prefix=SF_Ava_ | VAEDecode.IMAGE | — |

---

## 二、Wan2.2 双专家视频生成工作流节点连接

### 2.1 工作流概述

| 项目 | 说明 |
|------|------|
| 工作流名称 | Wan22_Dual_Expert_Video |
| 核心模型 | wan2.2_i2v_high_noise_14B_fp8 + wan2.2_i2v_low_noise_14B_fp8（双专家切换） |
| VAE | wan2.2_vae.safetensors |
| 文本编码器 | umt5_xxl_fp8_e4m3fn_scaled.safetensors |
| 输出规格 | 720p，120 帧，24fps（约 5 秒） |
| 采样参数 | steps 30, cfg 0.5, denoise 0.7 |
| 推荐硬件 | RTX 4090 24GB（FP8 + offload） |

### 2.2 节点连接总览（数据流）

```
UNETLoader(High) ──┐
UNETLoader(Low) ───┤   (二选一/切换)
VAELoader ─────────┼──> WanImageToVideo/WanVideoSampler ──> VAE Decode(Video) ──> VideoCombine
CLIPLoader ──> CLIPTextEncode ───────────────────────────┘
LoadImage(首帧) ─────────────────────────────────────────┘
```

### 2.3 节点详细连接表

#### 节点 1 — UNETLoader（High Noise 专家）

| 字段 | 内容 |
|------|------|
| 节点类型 | `UNETLoader` |
| 关键参数 | `unet_name`: `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors`；`weight_dtype`: `fp8_e4m3fn` |
| 输入连接 | 无（根节点） |
| 输出连接 | `MODEL` → `WanVideoSampler.model`（默认启用） |

> 说明：High Noise 专家负责大幅运动与整体构图，为首选生成模型。

#### 节点 2 — UNETLoader（Low Noise 专家，备用切换）

| 字段 | 内容 |
|------|------|
| 节点类型 | `UNETLoader` |
| 关键参数 | `unet_name`: `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors`；`weight_dtype`: `fp8_e4m3fn` |
| 输入连接 | 无（根节点） |
| 输出连接 | `MODEL` → `WanVideoSampler.model`（修复阶段切换接入） |

> 说明：Low Noise 专家负责细节修复与稳定性提升。两个 UNETLoader 同时存在于工作流中，通过切换 `WanVideoSampler.model` 的输入来源实现专家切换，无需删除节点。

#### 节点 3 — VAELoader（加载 Wan2.2 VAE）

| 字段 | 内容 |
|------|------|
| 节点类型 | `VAELoader` |
| 关键参数 | `vae_name`: `wan2.2_vae.safetensors` |
| 输入连接 | 无（根节点） |
| 输出连接 | `VAE` → `WanImageToVideo.vae`（或 `WanVideoSampler.vae`）、`VAEDecode(Video).vae` |

#### 节点 4 — CLIPLoader（加载 UMT5 文本编码器）

| 字段 | 内容 |
|------|------|
| 节点类型 | `CLIPLoader` |
| 关键参数 | `clip_name`: `umt5_xxl_fp8_e4m3fn_scaled.safetensors`；`type`: `wan` |
| 输入连接 | 无（根节点） |
| 输出连接 | `CLIP` → `CLIPTextEncode.clip` |

> 说明：Wan2.2 使用 UMT5-XXL 单文本编码器（非双编码器），`type` 必须设为 `wan`。`_scaled` 后缀版本已对视频任务做缩放预处理，不可用普通 umt5 替代。

#### 节点 5 — LoadImage（加载首帧关键帧）

| 字段 | 内容 |
|------|------|
| 节点类型 | `LoadImage` |
| 关键参数 | `image`: 选择由 Flux 工作流生成的关键帧（如 `SF_Ava_S01_03.png`） |
| 输入连接 | 无（根节点） |
| 输出连接 | `IMAGE` → `WanImageToVideo.image`（或 `WanVideoSampler.image`） |

> 说明：首帧质量直接决定视频质量，建议使用 Flux 一致性出图筛选后的最优关键帧。

#### 节点 6 — CLIPTextEncode（视频运动提示词）

| 字段 | 内容 |
|------|------|
| 节点类型 | `CLIPTextEncode` |
| 关键参数 | `text`: 视频运动提示词 |
| 输入连接 | `clip` ← `CLIPLoader.CLIP` |
| 输出连接 | `CONDITIONING` → `WanVideoSampler.positive`（Wan2.2 I2V 通常无需负面条件） |

视频运动提示词模板：
```
Ava walking cautiously through ruined futuristic corridor, amber eyes scanning environment,
subtle head movement, dust particles floating in cinematic sci-fi lighting,
teal and orange color grade, 24fps, smooth camera follow
```

#### 节点 7 — WanImageToVideo / WanVideoSampler（视频采样）

| 字段 | 内容 |
|------|------|
| 节点类型 | `WanImageToVideo`（图像到视频封装）或 `WanVideoSampler`（原生采样器） |
| 关键参数 | `seed`: `-1`；`steps`: `30`；`cfg`: `0.5`；`denoise`: `0.7`；`frames`: `120`；`fps`: `24`；`resolution`: `720p` |
| 输入连接 | `model` ← `UNETLoader(High/Low).MODEL`；`vae` ← `VAELoader.VAE`；`positive` ← `CLIPTextEncode.CONDITIONING`；`image` ← `LoadImage.IMAGE` |
| 输出连接 | `LATENT`（或 `IMAGE` 批次） → `VAEDecode(Video).samples` |

> 说明：
> - `cfg` 建议 0.5–1.0，过高会导致画面僵硬。
> - `denoise` 建议 0.6–0.8，过高会偏离首帧。
> - `frames 120` + `fps 24` ≈ 5 秒视频。
> - Wan2.2 I2V 通常不使用负面提示词，仅接入正面条件。

#### 节点 8 — VAEDecode（视频 Latent 解码）

| 字段 | 内容 |
|------|------|
| 节点类型 | `VAEDecode`（视频批次解码）或 `WanVideoDecode`（Wan 专用解码节点） |
| 关键参数 | 无特殊参数；若使用 `WanVideoDecode` 需启用视频模式 |
| 输入连接 | `samples` ← `WanVideoSampler.LATENT`；`vae` ← `VAELoader.VAE` |
| 输出连接 | `IMAGE`（帧批次） → `VideoCombine.images` |

> 说明：视频 VAE 解码显存占用较大，建议启用 offload 或分块解码（tile decode）以避免 OOM。

#### 节点 9 — VideoCombine / SaveAnimatedWEBP / SaveVideo（保存视频）

| 字段 | 内容 |
|------|------|
| 节点类型 | `VideoCombine`（来自 ComfyUI-VideoHelperSuite）或 `SaveAnimatedWEBP` / `SaveVideo` |
| 关键参数 | `filename_prefix`: `SF_Shot_`；`fps`: `24`；`format`: `video/h264-mp4`（或 `webp`/`gif`）；`save_metadata`: `true` |
| 输入连接 | `images` ← `VAEDecode(Video).IMAGE` |
| 输出连接 | 无（终端节点） |

> 说明：推荐使用 `VideoCombine` 输出 MP4（H.264），便于后期剪辑软件直接导入。WEBP/GIF 适用于预览与团队评审。

### 2.4 节点连接速查表

| 序号 | 节点类型 | 关键参数 | 输入来源 | 输出去向 |
|------|----------|----------|----------|----------|
| 1 | UNETLoader(High) | wan2.2_i2v_high_noise_14B_fp8 | — | WanVideoSampler.model |
| 2 | UNETLoader(Low) | wan2.2_i2v_low_noise_14B_fp8 | — | WanVideoSampler.model（切换） |
| 3 | VAELoader | wan2.2_vae | — | WanVideoSampler.vae, VAEDecode(Video).vae |
| 4 | CLIPLoader | umt5_xxl_fp8_scaled, type=wan | — | CLIPTextEncode.clip |
| 5 | LoadImage | 首帧关键帧 | — | WanVideoSampler.image |
| 6 | CLIPTextEncode | 视频运动提示词 | CLIPLoader.CLIP | WanVideoSampler.positive |
| 7 | WanVideoSampler | steps30/cfg0.5/denoise0.7/frames120/fps24 | UNETLoader.MODEL, VAELoader.VAE, CLIPTextEncode.CONDITIONING, LoadImage.IMAGE | VAEDecode(Video).samples |
| 8 | VAEDecode(Video) | — | WanVideoSampler.LATENT, VAELoader.VAE | VideoCombine.images |
| 9 | VideoCombine | prefix=SF_Shot_, fps24, mp4 | VAEDecode(Video).IMAGE | — |

---

## 三、双专家策略执行步骤

Wan2.2 I2V 14B 提供 High Noise 与 Low Noise 两个专家模型，分别擅长大幅运动生成与细节稳定修复。本项目采用"先整体后细节"的串行策略，具体执行步骤如下：

### 步骤 1 — High Noise 模型生成完整视频

1. 在工作流中将 `WanVideoSampler.model` 的输入切换为 `UNETLoader(High).MODEL`。
2. 设置参数：`steps 30`、`cfg 0.5`、`denoise 0.7`、`frames 120`、`fps 24`、`resolution 720p`。
3. 加载 Flux 生成的关键帧作为首帧。
4. 运行工作流，生成完整 5 秒视频片段。
5. 保存至 `05_Output/Rough_Cuts/`，命名格式 `SCENE_SHOT_TAKE_WanHN_vNN.mp4`（如 `S01_03_T01_WanHN_v01.mp4`）。

**目标**：获取整体构图、运动幅度与镜头节奏。High Noise 专家擅长生成大幅运动，但细节可能存在闪烁/崩坏。

### 步骤 2 — 检查问题帧

1. 在剪映/达芬奇中逐帧回放生成的视频。
2. 重点检查以下问题：
   - 面部变形/变脸（角色一致性丢失）
   - 手指/物体结构崩坏
   - 画面闪烁/抖动
   - 运动不自然/穿模
   - 偏离首帧构图
3. 记录问题帧的时间码区间（如 `00:02–00:03 面部变形`）。
4. 评估问题严重程度：若仅局部细节问题 → 进入步骤 3；若整体运动崩坏 → 调整提示词/降低 denoise 后回到步骤 1 重新生成。

### 步骤 3 — 切换 Low Noise 模型，对问题片段重新生成

1. 在工作流中将 `WanVideoSampler.model` 的输入切换为 `UNETLoader(Low).MODEL`。
2. 调整参数：
   - `denoise`: 降至 `0.5–0.6`（保留首帧构图，仅修复细节）
   - `steps`: 可提升至 `40`（增强细节）
   - `cfg`: 保持 `0.5` 或略降至 `0.5`
3. 若仅修复特定区间，可截取问题帧前后的关键帧作为新的首帧/尾帧输入。
4. 运行生成，输出修复版本，命名 `SCENE_SHOT_TAKE_WanLN_vNN.mp4`。
5. 将修复片段与原片段在剪辑软件中拼接替换。

**目标**：Low Noise 专家在低 denoise 下能稳定细节、消除闪烁，同时保留 High Noise 版本的整体运动。

### 步骤 4 — 必要时使用帧插值

1. 若生成视频帧率不足或运动卡顿，使用帧插值提升流畅度。
2. 推荐工具：
   - **RIFE**（ComfyUI 内 `RIFE VFI` 节点，来自 ComfyUI-VideoHelperSuite）
   - **FILM**（Google 大运动插值）
   - **Topaz Video AI**（Frame Interpolation 模式，后期阶段统一处理）
3. 插值倍率：24fps → 48fps（2x）或 60fps（2.5x），按发布平台要求选择。
4. 插值后再次检查是否存在伪影，必要时回到步骤 3 修复。

### 双专家策略决策流程图

```
[High Noise 生成] → [逐帧检查]
                          │
                ┌─────────┴─────────┐
                │                   │
          整体运动崩坏           局部细节问题
                │                   │
        调整提示词/denoise     [Low Noise 修复]
        重新 High Noise            │
                          ┌────────┴────────┐
                          │                 │
                     修复成功           仍有卡顿
                          │                 │
                       输出片段        [帧插值 RIFE/FILM]
                                            │
                                         输出片段
```

---

## 四、常见节点错误与排查

### 4.1 模型路径错误

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| UNETLoader/VAELoader 下拉列表无目标模型 | 模型未放入正确目录 | 按下表路径放置模型，重启 ComfyUI |
| `FileNotFoundError` 或 `KeyError: 'xxx.safetensors'` | 文件名拼写错误或扩展名不符 | 核对文件名与工作流中 `unet_name`/`vae_name` 完全一致 |
| DualCLIPLoader 报错 `type` 不支持 | ComfyUI 版本过旧 | 升级 ComfyUI 至最新版（≥0.3.46） |

模型存放路径对照表：

| 模型类型 | 存放路径 |
|----------|----------|
| Flux / Wan 扩散模型 | `ComfyUI/models/diffusion_models/` |
| VAE | `ComfyUI/models/vae/` |
| 文本编码器（T5/CLIP/UMT5） | `ComfyUI/models/text_encoders/` |
| IPAdapter 权重 | `ComfyUI/models/ipadapter/` |

### 4.2 显存不足（OOM）

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| `CUDA out of memory` | Wan2.2 14B 未量化 / 分辨率过高 / batch 过大 | ① 使用 FP8 量化模型；② 分辨率降至 480P；③ 启用 model offload / cpu offload；④ `batch_size` 设为 1 |
| Flux 生成时 OOM | 未使用 FP8 / 参考图过大 | ① 切换 FP8 权重；② 参考图压缩至 1024px 以内；③ 关闭其他 GPU 进程 |
| VAE 解码视频时 OOM | 视频 VAE 解码显存峰值高 | ① 启用 tile decode（分块解码）；② 启用 vae offload；③ 减少单次解码帧数，分段解码后拼接 |
| 间歇性 OOM（时好时坏） | 显存碎片化 | 重启 ComfyUI；设置 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` |

### 4.3 节点缺失（红色节点 / "Missing Node"）

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| 节点显示红色，标题为 `Missing Node: xxx` | 对应自定义节点未安装 | 通过 ComfyUI-Manager → Install Custom Nodes 搜索安装，重启 ComfyUI |
| `IPAdapterAdvanced` 缺失 | 未安装 ComfyUI-IPAdapter-Plus | 安装 `ComfyUI-IPAdapter-Plus` |
| `WanVideoSampler` / `WanImageToVideo` 缺失 | 未安装 Wan 视频节点包 | 安装 `ComfyUI-WanVideoWrapper` 或升级 ComfyUI 至含原生 Wan 节点的版本 |
| `VideoCombine` 缺失 | 未安装 ComfyUI-VideoHelperSuite | 安装 `ComfyUI-VideoHelperSuite` |
| 安装后仍缺失 | 未重启 / Python 依赖未装 | 重启 ComfyUI；进入插件目录执行 `pip install -r requirements.txt` |

### 4.4 连接类型不匹配

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| 连线显示红色，无法连接 | 输出类型与输入类型不一致（如 `MODEL` 接到 `CLIP` 输入） | 核对节点输入/输出类型，参考本文第一、二章连接表 |
| DualCLIPLoader 输出无法接入 CLIPTextEncode | `type` 参数设错（如设为 `sd` 而非 `flux`/`wan`） | 将 `type` 设为对应模型类型 |
| IPAdapter 输出 MODEL 无法接入 KSampler | 使用了错误的 IPAdapter 节点变体 | 确认使用 `IPAdapterAdvanced`（输出 MODEL）而非 `IPAdapter`（仅应用，不改 model） |
| Wan 采样器输出无法接入普通 VAEDecode | 视频批次维度与图像不同 | 使用 `WanVideoDecode` 或支持批次的 VAEDecode 节点 |
| LoadImage 输出 IMAGE 无法接入 IPAdapter | 图像通道/格式不符 | 中间插入 `ImageScale` / `ConvertImage` 节点规范化 |

### 4.5 生成结果异常

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| Flux 出图角色不一致 | 参考图质量差 / 提示词未固定锚点 | 增加多角度参考图，强制服装/发型关键词；提升 IPAdapter weight 至 0.8 |
| Wan2.2 视频闪烁严重 | Denoise 过高 / 模型不匹配 | 降低 Denoise 至 0.6，切换 Low Noise Expert |
| 视频手指/物体崩坏 | 长镜头运动幅度过大 | 切分镜头缩短时长，或改用可灵首尾帧约束 |
| 视频偏离首帧 | Denoise 过高 | 降低 Denoise 至 0.5–0.6 |
| 画面僵硬不自然 | CFG 过高 | Wan2.2 将 CFG 降至 0.5–1.0 |

---

## 五、ComfyUI-Manager 推荐安装的自定义节点

通过 ComfyUI 右下角 **Manager → Install Custom Nodes** 搜索安装以下节点包，安装完成后重启 ComfyUI 生效。

### 5.1 必装节点包

| 节点包（仓库） | 用途 | 用于工作流 | 安装优先级 |
|----------------|------|------------|------------|
| **ComfyUI-Manager** | 节点管理器，安装/更新/删除自定义节点 | 全局 | 必装 |
| **ComfyUI-IPAdapter-Plus** | IPAdapter 面部/风格一致性，提供 `IPAdapterModelLoader`、`IPAdapterAdvanced` | Flux 角色一致性 | 必装 |
| **ComfyUI-WanVideoWrapper** | Wan2.2 视频模型加载与采样封装节点 | Wan2.2 视频生成 | 必装（若 ComfyUI 版本无原生 Wan 节点） |
| **ComfyUI-VideoHelperSuite** | 视频加载/保存/帧合并/帧插值，提供 `VideoCombine`、`LoadVideo`、`RIFE VFI` | Wan2.2 视频生成 | 必装 |

### 5.2 推荐节点包

| 节点包（仓库） | 用途 | 用于工作流 | 安装优先级 |
|----------------|------|------------|------------|
| **ComfyUI_PuLID_Flux** | Flux 面部 ID 一致性（IPAdapter 的补充/替代方案） | Flux 角色一致性 | 推荐（可选） |
| **ComfyUI-Impact-Pack** | 检测器、分割、批处理增强，辅助角色面部区域处理 | Flux 角色一致性 | 推荐 |
| **ComfyUI-segment-anything** | 自动分割抠图，用于参考图预处理 | Flux 角色一致性 | 可选 |
| **ComfyUI-RIFE** | RIFE 帧插值（若 VideoHelperSuite 内置 RIFE 不可用） | Wan2.2 视频后处理 | 可选 |
| **ComfyUI_essentials** | 通用图像/数值/字符串工具节点 | 全局辅助 | 可选 |
| **rgthree-comfy** | Mute/Bypass 批量开关、上下文节点，便于双专家切换 | Wan2.2 双专家切换 | 推荐 |

### 5.3 安装后验证清单

- [ ] ComfyUI-Manager 入口出现在右下角菜单
- [ ] `IPAdapterAdvanced` 节点可在 Add Node 中搜索到
- [ ] `WanVideoSampler` / `WanImageToVideo` 节点可搜索到
- [ ] `VideoCombine` 节点可搜索到
- [ ] 各插件目录下 `requirements.txt` 依赖已安装（`pip install -r requirements.txt`）
- [ ] 重启 ComfyUI 后无红色 Missing Node 提示

### 5.4 模型下载地址

| 模型 | 来源 |
|------|------|
| FLUX.1-Kontext-dev | https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev |
| Wan2.2 ComfyUI Repackaged（含 FP8/VAE/UMT5） | https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged |
| Wan-AI Wan2.2-I2V-A14B 原始权重 | https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B |

---

## 附录：参数预设速查

### Flux 角色一致性（参考 `06_Research/parameter_tuning.md`）

| 参数 | 推荐值 | 调优区间 |
|------|--------|----------|
| Steps | 24 | 20–30 |
| CFG | 4.0 | 3.5–4.5 |
| Sampler | euler | — |
| Scheduler | simple | — |
| Denoise | 1.0 | 1.0（全重绘） |
| IPAdapter Weight | 0.7 | 0.6–0.8 |
| 参考图数 | 3 | 2–3 |
| 分辨率 | 1024×1024 / 1280×720 | — |

### Wan2.2 I2V 视频生成

| 参数 | 推荐值 | 调优区间 |
|------|--------|----------|
| Steps | 30 | 30–40 |
| CFG | 0.5 | 0.5–1.0 |
| Denoise | 0.7 | 0.5–0.8 |
| Frames | 120 | — |
| FPS | 24 | — |
| 分辨率 | 720p | 480p–720p |
| 双专家策略 | High Noise 生成 → Low Noise 修复 | — |

---

> 本文档随工作流实际搭建与调优持续更新。重大节点/参数变更请在 `06_Research/parameter_tuning.md` 同步登记。
