# 奇点回响 — 示例案例研究

[English](./README.md) | 中文

> 一部完整的 AIGC 短片工作流，以 3–5 分钟科幻微短剧《奇点回响》为例进行演示。

本目录包含 ShotFlow 中所用示例项目的完整计划与制作过程记录。它展示了仓库中的通用流程模板如何对应到一个真实（尽管是虚构的）制片项目。

---

## 包含内容

| 文档 | 用途 |
|------|------|
| [`production_plan.zh.md`](./production_plan.zh.md) | 示例项目的排期、里程碑、交付物与风险计划。 |
| [`production_log.zh.md`](./production_log.zh.md) | 逐日制作记录、决策与卡点。 |
| [`character_bible_ava.zh.md`](./character_bible_ava.zh.md) | 女主角艾娃的锁定角色参考。 |
| [`shot_tracker.zh.md`](./shot_tracker.zh.md) | 24 个镜头的进度表：状态、生成器、种子、审核人。 |

实际剧本、分镜与关键帧提示词位于：

- [`../../02_Scripts/script_and_worldbuilding.md`](../../02_Scripts/script_and_worldbuilding.md)
- [`../../02_Scripts/detailed_storyboard.md`](../../02_Scripts/detailed_storyboard.md)
- [`../../02_Scripts/keyframe_prompts.md`](../../02_Scripts/keyframe_prompts.md)

---

## 基本信息

- **项目代号**：ShotFlow
- **中文名**：奇点回响
- **类型**：科幻 / 悬疑 / 诗意
- **片长**：约 4 分 10 秒
- **镜头数**：5 场 24 镜
- **关键帧数**：29 张参考帧
- **主角**：艾娃，28 岁，前星际考古学家
- **核心技术难点**：跨镜头角色一致性
- **主要工具栈**：Flux.1 Kontext + IPAdapter、Wan2.2 I2V、可灵 2.5 Turbo

---

## 这个示例的意义

大多数 AIGC 视频演示停留在几个酷炫片段。本案例研究展示的是片段背后的文档：剧本如何变成分镜，分镜如何变成参考帧，参考帧如何变成视频，以及如何追踪进度以避免项目在第 3 周崩盘。

如果你想用 ShotFlow 做自己的影片，把这些文件的内容替换成你的故事，保留结构即可。

---

## 阅读顺序

1. `production_plan.zh.md` — 原计划与时间表
2. `character_bible_ava.zh.md` — 主角是谁，为什么她在每镜中看起来都一样
3. [`../../02_Scripts/detailed_storyboard.md`](../../02_Scripts/detailed_storyboard.md) — 24 镜拆解
4. `shot_tracker.zh.md` — 哪些镜头已完成，哪些需要重跑
5. `production_log.zh.md` — 制作期间实际发生了什么
6. [`../../AIGC_Experience_Chain.zh.md`](../../AIGC_Experience_Chain.zh.md) — 本示例如何嵌入更大的工作流

---

> 由 ShotFlow 团队维护。最后更新 2026-06-25。
