# ShotFlow — SOP 操作手册（初稿）

> 本手册覆盖 AIGC 微短剧从角色出图到最终成片的完整工业化流程。  
> 以 ShotFlow /《奇点回响》为例演示，所有角色、剧情、参数可按实际项目替换。

## 目录

1. [前置准备](#1-前置准备)
2. [第一阶段：角色资产与关键帧生产](#2-第一阶段角色资产与关键帧生产)
3. [第二阶段：视频生成](#3-第二阶段视频生成)
4. [第三阶段：后期与音效](#4-第三阶段后期与音效)
5. [第四阶段：成片输出与资产归档](#5-第四阶段成片输出与资产归档)
6. [命名规范](#6-命名规范)
7. [常见问题排查](#7-常见问题排查)

---

## 1. 前置准备

### 1.1 硬件与环境检查

- GPU：NVIDIA RTX 4090 24GB 或以上
- 显存：≥24GB（Wan2.2 14B FP8 最低要求）
- 内存：≥64GB
- 存储：≥2TB NVMe SSD
- 系统：Windows 11 / Ubuntu 22.04 LTS

### 1.2 软件安装清单

| 软件 | 版本/来源 | 用途 |
|------|----------|------|
| ComfyUI | 最新版 | 图像与视频生成工作流 |
| Python | 3.12 | 运行环境 |
| CUDA | 12.x | GPU 加速 |
| 剪映专业版 | 最新版 | 粗剪 |
| DaVinci Resolve | 18/19 | 调色与精剪 |
| Topaz Video AI | 最新订阅版 | 超分与降噪 |
| After Effects | 2024/2025 | 逐帧修复 |
| ElevenLabs | 网页/API | 配音 |
| Suno / Udio | 网页/API | 配乐 |

### 1.3 模型下载清单

| 模型 | 存放路径 | 来源 |
|------|----------|------|
| FLUX.1-Kontext-dev / FP8 / FP4 | `ComfyUI/models/diffusion_models/` | HuggingFace BFL |
| Wan2.2-I2V-A14B FP8 | `ComfyUI/models/diffusion_models/` | Comfy-Org Repackaged |
| Wan2.2 VAE | `ComfyUI/models/vae/` | Comfy-Org Repackaged |
| umt5_xxl_fp8_e4m3fn_scaled | `ComfyUI/models/text_encoders/` | Comfy-Org Repackaged |
| IPAdapter / PuLID 相关节点与模型 | 按节点要求 | ComfyUI Manager |

---

## 2. 第一阶段：角色资产与关键帧生产

### 2.1 生成角色圣经

1. 使用 DeepSeek / Claude 输出角色设计白皮书，包含：
   - 姓名、年龄、身份背景
   - 面部特征（脸型、五官、发型、发色、瞳色、特殊标记）
   - 服装锚点（材质、颜色、配饰、破损/污渍位置）
   - 性格关键词（影响表情与姿态）
   - 参考图方向（写实/科幻/电影感）

2. 将角色圣经保存至 `02_Scripts/character_bible_template.md`

### 2.2 Flux_Kontext + IPAdapter 角色一致性出图

1. 打开 `03_Workflows/Flux_Character_Consistency.json`
2. 加载角色参考图（正面、侧面、背面三视图）
3. 在 Prompt 中强制植入服装锚点与表情关键词
4. 设置参数：
   - 分辨率：1024×1024 或 1280×720（按镜头比例）
   - Steps：20–30
   - CFG：3.5–4.5
   - 使用 FP8 精度以节省显存
5. 批量生成 24 镜头关键帧（含首尾帧拆分共 29 张），覆盖核心场景
6. 盲测筛选：将图片随机打乱，由导演/美术判断是否认定为同一人

### 2.3 输出检查

- [ ] 角色三视图已保存至 `01_Assets/Characters/Ava/`
- [ ] 24 镜头关键帧（含首尾帧拆分共 29 张）已保存至 `01_Assets/Scenes/`
- [ ] 盲测通过（团队一致认为不"变脸"）

---

## 3. 第二阶段：视频生成

### 3.1 分镜表准备

1. 导演根据剧本输出分镜表，字段包括：
   - 镜头编号、场景、景别、运镜、时长
   - 生成方式（Wan2.2 本地 / 可灵云端）
   - 复杂度标注（标准 / 高复杂 / 转场）

### 3.2 标准镜头：Wan2.2 I2V 双专家

1. 打开 `03_Workflows/Wan22_Dual_Expert_Video.json`
2. 加载对应关键帧作为首帧
3. 设置参数：
   - 模型：Wan2.2-I2V-A14B FP8
   - 分辨率：480P/720P
   - 帧数：5 秒 ≈ 120 帧（24fps）
   - CFG：0.5–1.0（默认 0.5）
   - Denoise：0.6–0.8
   - 提示词：描述主体运动、镜头运动、环境氛围
4. 先生成 High Noise 版本获取大幅运动
5. 对崩坏帧使用 Low Noise Expert 进行修复
6. 保存原始片段至 `05_Output/Rough_Cuts/`

### 3.3 复杂镜头：可灵 2.5 Turbo 首尾帧

1. 准备起始帧与结束帧两张关键图
2. 调用可灵 API，参数：
   - duration: 5
   - aspect_ratio: "16:9"
   - mode: "pro"
   - version: "2.5-turbo"
3. 下载视频并编号保存

### 3.4 素材管理

- 命名规则：`SCENE_SHOT_TAKE_TOOL_vNN.mp4`
- 例：`S01_03_T01_Wan_v02.mp4` 表示第 1 场第 3 镜第 1 条，Wan2.2 生成，第 2 版

---

## 4. 第三阶段：后期与音效

### 4.1 粗剪

1. 剪映专业版导入所有原始片段
2. 按分镜表排列，调整节奏
3. 导出粗剪版本至 `05_Output/Rough_Cuts/roughcut_v01.mp4`

### 4.2 配音

1. ElevenLabs 创建角色声音：
   - 选择或克隆符合艾娃性格的女声
   - 调整 Stability、Similarity、Style 参数
2. 按对白脚本逐句生成
3. 导出 WAV/MP3 至 `01_Assets/Audio/Voices/`

### 4.3 配乐

1. Suno / Udio 输入提示词：
   - 风格：sci-fi, cinematic, ambient, electronic
   - 情绪：tense, hopeful, mysterious
   - 时长：与成片段落匹配
2. 生成 3-5 段备选音乐
3. 导出无水印版本至 `01_Assets/Audio/Music/`

### 4.4 音效

1. 环境音：风声、机械运转、飞船引擎、废墟回声
2. 动作音效：脚步声、衣物摩擦、金属碰撞
3. 来源：AudioLDM / ElevenLabs Sound Effects / 素材库

### 4.5 画质增强

1. Topaz Video AI 导入原始片段
2. 选择模型：
   - 超分 2x/4x：Proteus / Iris
   - 降噪：Nyx
   - 稳定：Stabilization
3. 输出 4K ProRes / H.265 至 `05_Output/Rough_Cuts/enhanced/`

---

## 5. 第四阶段：成片输出与资产归档

### 5.1 精剪与调色

1. DaVinci Resolve 导入增强后片段
2. 统一色调：Teal & Orange 科幻电影感
3. 添加 LUT、颗粒、暗角
4. 混合配音、音乐、音效
5. 输出母版：`05_Output/Final/奇点回响_4K_v01.mp4`

### 5.2 工作流归档

1. 导出最终 ComfyUI 工作流 JSON：
   - `03_Workflows/Flux_Character_Consistency.json`
   - `03_Workflows/Wan22_Dual_Expert_Video.json`
2. 记录节点依赖与模型版本
3. 打包角色资产库

### 5.3 发布

1. 全平台上传正片
2. 技术社区发布工作流教程
3. 收集反馈并归档至 `06_Research/failure_cases.md`

---

## 6. 命名规范

### 6.1 文件命名

```
项目代号_场景编号_镜头编号_版本_描述.扩展名
例：SF_S01_03_v02_AvaCloseUp.png
```

### 6.2 目录命名

```
YYYY-MM-DD_内容描述
例：2025-07-15_艾娃关键帧_v02
```

### 6.3 模型版本记录

每次工作流重大变更需记录：
- 模型名称与版本
- 节点插件版本
- 关键参数
- 生成结果截图

---

## 7. 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| Flux 出图角色不一致 | 参考图质量差 / 提示词未固定锚点 | 增加多角度参考图，强制服装/发型关键词 |
| Wan2.2 显存不足 | 未使用 FP8/GGUF / 分辨率过高 | 降低精度，使用 480P，启用 offload |
| 视频闪烁严重 | Denoise 过高 / 模型不匹配 | 降低 Denoise，换 Low Noise Expert |
| 手指/物体崩坏 | 长镜头运动幅度过大 | 切分镜头，使用可灵首尾帧约束 |
| 可灵 API 返回慢 | 队列拥堵 | 错峰生成，或启用 webhook |
| Topaz 输出偏色 | 模型选择不当 | 针对素材类型选择 Iris/Proteus/Nyx |

---

> 本 SOP 随项目推进持续更新。任何流程优化请在 Git commit message 中登记。
