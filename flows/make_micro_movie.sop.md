# 流程文件：一句话 → 带字幕微电影（micro_movie）

> 外部智能体读取并自行执行。= 多镜 video + 剧本 + 配音 + 字幕，成片更长（1~5min）。

## ⚠️ 版权提示（用户自担）

## 触发条件
- 用户输入一句话，例如：「做个 2 分钟奶龙奶娃的搞笑微电影，有剧情」
- 意图识别判定 `output_type = "micro_movie"`，时长 > 60s

## 工具清单
同 `make_video.sop.md`（额外用 `generate_audio` 做 BGM + `assemble` 多镜拼接）。

## 步骤

### S1 意图识别 ［智能体 LLM］
- 输出：`{output_type:"micro_movie", duration:120, genre:"搞笑", structure:"起承转合"}`

### S2 需求脑补（剧本） ［智能体 LLM］
- 生成：三幕剧本（每幕 2~4 镜）+ 角色圣经 + 台词 + 笑点节奏
- `save_spec`（scenes 含多幕多镜）

### S3 一致性锚定 ［`consistency_anchor`］

### S4 分镜生成（按幕并行，幕内串行） ［`generate_image`→`generate_video`→`generate_audio`］
- 长片分镜：每镜 ≤ 15s，用 `wanx`/`kling`；BGM 用 `suno`/`generate_audio(type="bgm")`
- 决策：总时长超 30s 必漂移 → 靠设定图锚定 + 分镜控制

### S5 组装 ［`assemble`］
- 拼接多幕 + 混 BGM + 硬压台词字幕 + 转场

### S6 交付 ［ShotFlow］

## 验收
- [ ] 有完整剧情结构，非随机拼接
- [ ] 字幕 + 配音 + BGM 齐全
- [ ] 角色一致
