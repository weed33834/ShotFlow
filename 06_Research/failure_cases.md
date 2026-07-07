# ShotFlow — 失败案例记录表

> 记录生成过程中出现的崩坏、闪烁、不一致等问题，沉淀修复经验，避免重复踩坑。

## 知识库导航

> 本表是 Phase 2 失败案例的结构化知识库，按下述维度快速检索。新增案例后请同步更新本导航与月度统计。

### 按问题类型

- [1. 角色不一致](#1-角色不一致)
- [2. 视频崩坏](#2-视频崩坏)
- [3. 运动逻辑错误](#3-运动逻辑错误)
- [4. 画质问题](#4-画质问题)
- [5. 音频问题](#5-音频问题)
- [6. Provider 适配问题](#6-provider-适配问题)（P6 阶段新增）

### 按工具检索

| 工具 | 相关案例 |
|------|----------|
| Flux.1 Kontext + IPAdapter | F001, F002, F003, F004 |
| Wan2.2 I2V | F007, F008 |
| 可灵 2.5 Turbo | F005, F006, F009 |
| ComfyUI | F008 |
| Provider Adapter | F009, F010 |

### 按镜头号检索

- Ava正面肖像（F001）
- Ava侧面（F002）
- Ava颈后接口特写（F003）
- S01_01 废墟全景（F004）
- S03_04（F005）
- S05_04（F006）
- S01_02（F007）
- S02_03（F008）
- S04_01（F009）
- —（案例展示区 API）（F010）

### 状态统计

- 已解决：10
- 进行中：0
- 放弃：0
- 合计：10

---

## 填写规范

- 每次出现需要返工的生成结果，记录一条。
- 状态为"已解决"时需填写解决方案与最终参数。
- 每周末由 QA 汇总，在师生同步会上通报。

---

## 失败案例记录

| ID | 日期 | 镜头号 | 生成工具 | 问题描述 | 原始参数 | 失败截图 | 原因分析 | 解决方案 | 最终参数 | 状态 | 记录人 |
|----|------|--------|----------|----------|----------|----------|----------|----------|----------|------|--------|
| F001 | 2026-06-24 | Ava正面肖像 | Flux.1 Kontext + IPAdapter | 外套颜色偏蓝，与设定深灰色不符 | steps=24, cfg=4.0, IPAdapter=0.7 | N/A | 服装锚点词权重不足，蓝色环境光影响服装颜色 | 在提示词中增加 "dark gray patched windbreaker (right shoulder patch)" 并置于前部，IPAdapter weight 提升至 0.75 | steps=24, cfg=4.0, IPAdapter=0.75, 参考图数=4 | 已解决 | AI美术 |
| F002 | 2026-06-24 | Ava侧面 | Flux.1 Kontext + IPAdapter | 发型在侧面镜头中变长，出现刘海 | steps=24, cfg=4.0, IPAdapter=0.7 | N/A | 侧面参考图发型轮廓不清，模型默认补全长发 | 补充一张短发侧面清晰参考图，负面提示词加入 "long hair, bangs, different hairstyle" | steps=24, cfg=4.0, IPAdapter=0.8, 负面词强化 | 已解决 | AI美术 |
| F003 | 2026-06-24 | Ava颈后接口特写 | Flux.1 Kontext + IPAdapter | 接口发光颜色不稳定，时橙时红 | steps=24, cfg=4.0, IPAdapter=0.7 | N/A | 提示词中 "glowing orange" 位置靠后，被模型忽略 | 将 "glowing orange bracelet on left wrist" 与 "neural interface glowing orange" 提前，并增加 "bioluminescent orange" | steps=30, cfg=3.5, IPAdapter=0.8 | 已解决 | AI美术 |
| F004 | 2026-06-24 | S01_01 废墟全景 | Flux.1 Kontext | 画面偏卡通，缺少电影质感 | steps=20, cfg=5.0, sampler=dpmpp_2m | N/A | CFG过高导致画面过饱和，缺少胶片颗粒 | 降低 CFG 至 4.0，使用 euler/simple，增加 "film grain, dust particles, cinematic sci-fi lighting" | steps=24, cfg=4.0, sampler=euler | 已解决 | AI美术 |
| F005 | 2026-06-25 | S03_04 | 可灵 2.5 Turbo | 首帧与输入关键帧偏差过大，人物位置偏移 | duration=5, mode=pro, denoise=0.7 | N/A | 可灵 denoise 过高导致首帧保真度下降 | 降低 denoise 至 0.55，增强首尾帧约束权重 | duration=5, mode=pro, denoise=0.55 | 已解决 | AI视频操作员 |
| F006 | 2026-06-25 | S05_04 | 可灵 2.5 Turbo | 手部特写出现手指融合，违反物理逻辑 | duration=5, mode=pro, denoise=0.6 | N/A | 手部正面大特写超出模型生成能力 | 替换关键帧角度，采用手部遮挡/侧角度，避免手指正面特写 | duration=5, mode=pro, denoise=0.55 | 已解决 | AI视频操作员 |
| F007 | 2026-06-25 | S01_02 | Wan2.2 I2V | 人物脸部轻微漂移，相似度下降 | steps=30, cfg=0.5, denoise=0.7 | N/A | denoise 偏高导致面部特征扩散 | 对面部特写镜头改用 Low Noise Expert，denoise 0.5 | steps=30, cfg=0.5, denoise=0.5 | 已解决 | AI视频操作员 |
| F008 | 2026-07-03 | S02_03 | ComfyUI（Wan22_Dual_Expert_Video） | 提交 ComfyUI 工作流返回 422，positive_prompt 节点为空，整批生成中断并输出全黑帧 | workflow=Wan22_Dual_Expert_Video_api.json, prompt="", seed=88210 | N/A | 分镜表中 S02_03 提示词字段漏填，storyboard_to_video.py 直接把空字符串灌入 CLIPTextEncode 节点；ComfyUI 未拦截空 prompt，Wan2.2 在空文本下输出全黑帧 | 在 storyboard_to_video.py 提交前增加 prompt 非空校验（空则跳过并记日志），补全分镜表 S02_03 提示词 | workflow=Wan22_Dual_Expert_Video_api.json, prompt="Ava walks through ruined plaza, dust drifts, cinematic", seed=88210 | 已解决 | AI视频操作员 |
| F009 | 2026-07-03 | S04_01 | Provider Adapter（wan_i2v 默认 / 应为 kling） | 复杂转场镜头 S04_01 队列提交后崩坏（人物穿模、首尾帧不连续），排查发现实际走了 wan_i2v 而非 kling | shot_id=S04_01, extra={}（未传 provider）, denoise=0.6 | N/A | 提交时 extra 字段未携带 provider，ProviderRouter 默认回落 wan_i2v；wan_i2v 对首尾帧约束的复杂镜头支持不足导致穿模 | 提交复杂镜头时 extra 必须显式传 {"provider":"kling"}；在 render_queue.py 增加复杂镜头（is_complex=true）缺省 provider 的拦截告警 | shot_id=S04_01, extra={"provider":"kling"}, denoise=0.55, mode=pro | 已解决 | 后端工程 |
| F010 | 2026-07-03 | —（案例展示区 API） | 后端 CaseStudy API | 创建用户案例时 POST /api/v1/case-studies 返回 400，slug 冲突 | slug="ava", title="Ava Demo" | N/A | 多人测试时都用了 "ava" 这个泛化 slug，违反 slug 命名规范（应为 kebab-case 且含项目前缀）；CaseStudy 模型对 slug 加了唯一约束但 API 错误码语义不清 | 明确 slug 命名规范：<project>-<scene>-<version>（如 echo-ava-debut-v1）；CaseStudy API 在 slug 冲突时返回 409 而非 400 并附清晰错误信息 | slug="echo-ava-debut-v1", title="Ava Debut Showcase" | 已解决 | 后端工程 |

---

## 常见问题分类与参考方案

### 1. 角色不一致

| 症状 | 可能原因 | 参考方案 |
|------|----------|----------|
| 面部特征变化 | 参考图不足 / IPAdapter 权重过低 | 增加多角度参考图，提高 IPAdapter weight 至 0.8–1.0 |
| 服装颜色/款式突变 | 提示词未固定锚点 | 在正向提示词中强制写入完整服装描述 |
| 发型改变 | 负面提示词缺失 | 添加 "different hairstyle" 到负面词 |

### 2. 视频崩坏

| 症状 | 可能原因 | 参考方案 |
|------|----------|----------|
| 画面闪烁 | Denoise 过高 / CFG 不当 | 降低 Denoise 至 0.5–0.6，CFG 保持 0.5 |
| 手指融合/变形 | 长镜头运动幅度过大 | 切分为短镜头，或改用可灵首尾帧 |
| 物体穿模 | 模型对物理理解不足 | 使用 Low Noise Expert 修复，或 AE 逐帧修补 |
| 首帧偏离 | Denoise 过高 | 降至 0.5–0.6，或使用 img2img 锁定 |

### 3. 运动逻辑错误

| 症状 | 可能原因 | 参考方案 |
|------|----------|----------|
| 人物反向行走 | 提示词方向描述不清 | 明确 "walking toward camera" / "walking away" |
| 镜头运动不自然 | 运镜描述过于复杂 | 简化为单一运镜（推/拉/摇/移） |
| 表情僵硬 | 情绪关键词缺失 | 添加 "subtle expression change" |

### 4. 画质问题

| 症状 | 可能原因 | 参考方案 |
|------|----------|----------|
| AI 塑料感 | 提示词缺少质感词 | 添加 "film grain, natural skin texture, imperfections" |
| 色彩偏移 | 色调词冲突 | 统一使用 "teal and orange color grade" |
| 分辨率不足 | 原生分辨率过低 | 使用 Topaz 超分 2x–4x |

### 5. 音频问题

| 症状 | 可能原因 | 参考方案 |
|------|----------|----------|
| 配音不自然 | Stability 过高 | 降低 Stability 至 0.3–0.5 |
| 配乐情绪不符 | 提示词过于笼统 | 细化乐器、节奏、情绪描述 |
| 音画不同步 | 剪辑时间轴未对齐 | 在达芬奇中逐帧对齐波形 |

### 6. Provider 适配问题

> P6 阶段新增。多 Provider 适配（HunyuanVideo/LTX-Video/CogVideoX/Kling/Wan）引入的新一类失败。

| 症状 | 可能原因 | 参考方案 |
|------|----------|----------|
| 复杂镜头崩坏/穿模 | extra.provider 未传，默认回落 wan_i2v | 复杂镜头显式传 {"provider":"kling"}；render_queue.py 对 is_complex=true 缺省 provider 增加拦截告警 |
| Provider 调用 422/超时 | API key 未配置或 extra 参数与 Provider schema 不匹配 | 检查 .env 对应 Provider key；对照 ProviderAdapter schema 校验 extra 字段 |
| 模型输出风格不一致 | Provider 切换时未重置 denoise/seed | 切换 Provider 时重置 denoise 至该 Provider 推荐值，固定 seed 复现 |

---

## 月度统计模板

| 月份 | 总案例数 | 已解决 | 放弃 | 解决率 | 高频问题 TOP3 |
|------|----------|--------|------|--------|---------------|
| 2026-07 | 10 | 10 | 0 | 100% | 视频崩坏 / 角色不一致 / Provider 适配 |
| | | | | | |
| | | | | | |

---

> 本文件由 QA 负责维护，每周五更新。
