# ShotFlow — 技术栈调研与预算估算

> 调研日期：2026-06-23（基于当前公开信息，价格可能波动，请以实际下单为准）

## 一、核心技术组件现状

### 1.1 Flux.1 Kontext [dev] — 角色一致性出图

| 项目 | 详情 |
|------|------|
| 发布时间 | 2025 年 6 月 26 日 |
| 参数规模 | 12B |
| 授权 | FLUX.1 Non-Commercial License（可购买商业授权） |
| ComfyUI 支持 | Day-0 原生支持，可通过 `Workflow → Browse Templates → Flux` 加载 |
| 显存需求（NVIDIA 优化版） | FP8 约 12 GB（Ada/RTX 40 系）；FP4 约 7 GB（Blackwell/RTX 50 系） |
| 优化框架 | NVIDIA TensorRT，BF16/FP8/FP4 多精度可选 |
| 关键能力 | 角色一致性、局部编辑、风格参考、多轮迭代编辑 |
| 参考 | [Black Forest Labs 官方公告](https://bfl.ai/blog/flux-1-kontext-dev)、[NVIDIA 中文博客](https://blogs.nvidia.cn/blog/rtx-ai-garage-flux-kontext-nim-tensorrt/)、[ComfyUI Day-0 支持](https://blog.comfy.org/p/flux1-kontext-dev-day-0-support) |

**项目适配建议**：
- 本地 RTX 4090（24 GB）使用 FP8 精度可流畅运行。
- 若升级到 RTX 5090，可使用 FP4 获得更低显存占用与更快推理。
- 角色一致性建议结合 IPAdapter / PuLID 做面部锚点，再用 Kontext 做场景/服装迁移。

### 1.2 Wan2.2 — 图生视频双专家模型

| 项目 | 详情 |
|------|------|
| 发布方 | 阿里巴巴 Wan-AI |
| 主要可用模型 | T2V A14B、I2V A14B、TI2V 5B、S2V 14B、Animate 14B |
| 推荐本项目使用 | **I2V A14B**（图生视频，支持 480P/720P） |
| 原生 FP16 显存 | 约 60 GB VRAM |
| 量化后显存 | FP8 版本可在 RTX 4090（24 GB）上通过 offload 运行；5B TI2V 更轻量 |
| 双专家机制 | High Noise / Low Noise 双模型分别负责大幅运动与细节修复 |
| ComfyUI 资源 | [Comfy-Org 官方 Repackaged 模型](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged)、[Wan-AI HuggingFace](https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B) |
| 参考 | [apatero ComfyUI 完整指南](https://apatero.com/zh/blog/wan-2-2-comfyui-complete-guide-ai-video-generation-2025)、[StableDiffusionTutorials 安装教程](https://www.stablediffusiontutorials.com/2025/08/wan-2.2-video-generation.html) |

**项目适配建议**：
- 标准镜头（对话、微表情）使用 Wan2.2 I2V 14B FP8，本地 RTX 4090 生成。
- 复杂镜头（奔跑、转场）使用可灵 2.5 Turbo 首尾帧约束作为补充。
- 若本地显存吃紧，可改用 Wan2.2 TI2V 5B 或云端算力。

### 1.3 可灵 2.5 Turbo — 云端复杂镜头

| 项目 | 详情 |
|------|------|
| 能力 | 文生视频 / 图生视频 / 首尾帧约束 / 运动控制 |
| 分辨率 | 最高 1080p 以上 |
| 提示词长度 | 约 2500 字符 |
| 官方 API | 快手可灵官方 API（需申请） |
| 第三方聚合价（供参考） | PiAPI: $0.28/5s、$0.56/10s；Runware: $0.21/5s（720p）；CometAPI: ~$1.00/5s |
| 参考 | [PiAPI Kling Turbo 文档](https://app.piapi.ai/docs/kling-api/kling-turbo-api)、[Runware KlingAI 2.5 Turbo](https://runware.ai/docs/models/klingai-2-5-turbo-standard) |

**项目适配建议**：
- 复杂镜头与转场优先用可灵首尾帧功能，降低运动崩坏概率。
- 预算按 5 个复杂镜头、每个 5 秒估算，约 $4–20。

## 二、音效 / 配乐 / 配音成本

### 2.1 ElevenLabs — 角色配音

| 方案 | 价格 | 容量 |
|------|------|------|
| Free | $0/月 | 10k credits/月（约 10 分钟高质量 TTS） |
| Starter | ~$5/月 | 30k credits/月（约 30 分钟） |
| Creator | $22/月 | 100k credits/月（约 100 分钟） |
| Pro | $99/月 | 500k credits/月（约 500 分钟） |
| API 按量 | $0.1/1K chars（Multilingual v2/v3）；$0.05/1K chars（Flash/Turbo） | 按字符计费 |
| 参考 | [ElevenLabs Pricing](https://elevenlabs.io/pricing/api) | |

**项目适配建议**：
- 3-5 分钟短片对白约 500-1500 字符，Creator 计划足够覆盖。
- 如需多角色、多语言或情绪微调，建议 Pro 计划。

### 2.2 Suno / Udio — 科幻配乐

| 平台 | 方案 | 价格 | 容量 |
|------|------|------|------|
| Suno | Basic（免费） | $0 | 50 credits/日，非商用 |
| Suno | Pro | $10/月 | 2,500 credits/月（约 500 首） |
| Suno | Premier | $30/月 | 10,000 credits/月 |
| Udio | Standard | $10/月 | 1,200 credits/月（约 2,400 首） |
| Udio | Pro | $30/月 | 6,000 credits/月 |
| 参考 | [Suno Pricing](https://artificial-intelligence-wiki.com/generative-ai/ai-music-generation/suno-ai-pricing-plans/)、[Udio vs Suno 对比](https://artificial-intelligence-wiki.com/generative-ai/ai-music-generation/udio-vs-suno-comparison/) | |

**项目适配建议**：
- 科幻氛围背景音乐建议使用 Suno Pro 或 Udio Standard。
- 如需更高音质与 stem 导出，优先 Udio Pro。

## 三、画质增强 — Topaz Video AI

| 方案 | 价格 | 说明 |
|------|------|------|
| Topaz Video（Personal） | $299/年 | 无限本地渲染，25 个/月云端视频 credits，有限商业使用 |
| Topaz Video Pro | $699/年 | 含本地 Starlight 模型、100 个/月云端 credits、完整商业授权 |
| Topaz Studio | $399/年 | 包含 Video + Photo + Gigapixel 等全套工具，300 个/月云端视频 credits |
| 参考 | [Topaz Video AI](https://www.topazlabs.com/topaz-video-ai)、[Topaz Video Pro](https://www.topazlabs.com/video-pro) | |

**项目适配建议**：
- 项目周期 6 周，选择 **Topaz Video Personal（$299/年）** 即可满足 4K 超分与降噪需求。
- 若团队已有摄影师或需批量处理大量素材，考虑 Topaz Studio。

## 四、算力成本估算

### 4.1 本地硬件（一次性 / 折旧）

| 硬件 | 规格 | 估算价格 |
|------|------|----------|
| GPU | NVIDIA RTX 4090 24GB | ¥12,000–16,000 |
| 内存 | 64GB DDR4/DDR5 | ¥1,000–2,000 |
| 存储 | 2TB NVMe SSD | ¥800–1,200 |
| 电源/散热/主板升级 | 适配 4090 | ¥2,000–4,000 |
| **合计** | | **约 ¥16,000–23,000** |

### 4.2 云端弹性算力（按需）

| 平台 | RTX 4090 单价 | 6 周按 200 小时估算 |
|------|---------------|---------------------|
| RunPod Secure Cloud | $0.69/hr | ~$138 |
| RunPod Community Cloud | $0.34/hr | ~$68 |
| Vast.ai（平均） | $0.28–0.37/hr | ~$56–74 |
| SaladCloud（Batch Priority） | $0.16/hr | ~$32 |
| 国内 AutoDL（3090 参考） | ~¥1.58/hr（3090） | 4090 约 ¥2.5–3.5/hr |

**项目适配建议**：
- 若团队已有 RTX 4090，本地为主，云端为辅。
- 若需临时扩容或多人协作，优先 Vast.ai / RunPod Community Cloud。
- 云端主要用于复杂镜头补算、模型下载调试或并行生成。

## 五、6 周项目总预算估算（人民币）

| 类别 | 项目 | 预估费用 |
|------|------|----------|
| **硬件** | RTX 4090 工作站（一次性/折旧） | ¥16,000–23,000 |
| **软件订阅** | Topaz Video AI（1 年） | ¥2,100（约 $299） |
| | ElevenLabs Creator（1 个月） | ¥160（约 $22） |
| | Suno Pro / Udio Standard（1 个月） | ¥75（约 $10） |
| | 剪映专业版 / 达芬奇（免费或 Resolve Studio 一次性） | ¥0–2,600 |
| **云端 API** | 可灵 2.5 Turbo（5 个复杂镜头） | ¥30–150 |
| | 云端 GPU 弹性扩容（可选 200hr） | ¥200–1,000 |
| **模型/资产** | Civitai/HuggingFace LoRA、风格模型（可选） | ¥0–500 |
| **人力** | 9 人核心团队 × 6 周（按市场 freelance/兼职估算） | ¥30,000–80,000 |
| **不可预见** | 迭代、补拍、修复预留 10% | ¥5,000–12,000 |
| **总计** | | **约 ¥54,000–122,000** |

> 注：以上为中小团队/freelance 估算。若按正式公司全职人员、更高制作标准或商业授权，预算需上浮。

## 六、关键风险与技术建议

1. **显存不足**：Wan2.2 14B 原生需 60GB，务必使用 FP8/GGUF 量化或云端算力。
2. **授权合规**：Flux.1 Kontext [dev] 默认非商业授权，若用于商业发布需购买 BFL 商业授权。
3. **API 价格波动**：可灵官方 API 与第三方聚合价差异大，建议优先申请官方 API。
4. **模型迭代快**：2025 年下半年 Flux/Wan/可灵均有更新，项目启动前需再次确认最新版本与节点兼容性。
