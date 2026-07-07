# Distribution Kit

> 各发布平台的内容包规格——按平台准备一份完整交付包，避免临时拼凑。
> Project: ShotFlow / *Echo of the Singularity* (example)
> License: MIT

每个平台的发布包必须包含：母版视频、封面、标题/简介、标签、字幕、
版权声明。下表给出每个平台的具体规格，发布前用
[`release_checklist.md`](./release_checklist.md) 逐项核对。

---

## 一、发布平台矩阵

| 平台 | 主视频 | 副视频 | 封面 | 字幕 | 描述长度 | 标签 | AIGC 标识 |
|------|--------|--------|------|------|----------|------|-----------|
| Bilibili | 1080p H.264 | 竖版 1080×1920 | 1146×717（横）/ 1080×1920（竖） | 软字幕 zh.srt | ≤ 1000 字 | 10 个 | 必须勾选"AIGC 创作" |
| YouTube | 4K H.264 | 1080p H.264 | 1280×720 | zh.srt + en.srt | ≤ 5000 字符 | 15 个 | 描述首行注明 "AI-generated short film" |
| 抖音 | 1080×1920 H.264 | — | 1080×1920 | 烧录 zh | ≤ 2200 字 | 8 个 | 必须勾选"AIGC 创作" |
| 小红书 | 1080×1920 H.264 | 1080×1080 | 1080×1920 | 烧录 zh | ≤ 1000 字 | 10 个 | 必须勾选 |
| 微信视频号 | 1080×1920 H.264 | — | 1080×1920 | 烧录 zh | ≤ 800 字 | 5 个 | 必须勾选 |
| Instagram Reels | 1080×1920 H.264 | — | 1080×1920 | 烧录 en | ≤ 2200 字符 | 30 个 | 描述首行注明 |
| 电影节投奖 | 4K ProRes 422 HQ | — | 1920×1080 | zh+en .srt | 按影展要求 | — | 按《生成式 AI 服务管理暂行办法》显著标识 |

---

## 二、Bilibili 发布包

### 目录结构

```
release_bilibili/
├── ShotFlow_1080p_v10.mp4           # 主视频
├── ShotFlow_1080x1920_v10.mp4       # 竖版（同步发到抖音时复用）
├── cover_landscape_1146x717.jpg
├── cover_portrait_1080x1920.jpg
├── echo_of_singularity.zh.srt
├── title.txt                        # 标题
├── description.txt                  # 简介
├── tags.txt                         # 标签
└── LICENSE.txt                      # MIT 简版
```

### title.txt 示例

```text
【AIGC 短片】奇点回响｜4 分钟看完一场跨越 47 年的对话｜ShotFlow 工作流开源
```

### description.txt 模板

```text
本片为 AIGC 生成内容（AI-Generated Content），使用 ShotFlow 工业化流水线制作。

【作品信息】
片名：奇点回响 (Echo of the Singularity)
时长：4 分 10 秒
分辨率：4K / 24fps
制作周期：6 周
工具链：Flux.1 Kontext + IPAdapter（角色一致性）→ Wan2.2 / 可灵（视频生成）→ DaVinci Resolve（剪辑调色）→ ElevenLabs（配音）→ Suno（配乐）

【故事】
人类文明崩溃后的第 47 年，流浪者艾娃在废墟中找到沉睡的奇点核心。
四十七年来，只有她能听见核心的回响……

【开源】
完整工作流、SOP、ComfyUI JSON、自动化脚本、Web 平台（FastAPI + React）
均已开源：
GitHub  https://github.com/MS33834/ShotFlow
GitCode https://gitcode.com/badhope/ShotFlow

【授权】
本作品采用 MIT 开源协议——允许自由使用、修改、分发、商用，
（须保留版权与许可声明）。
```

### tags.txt

```text
AIGC, AI视频, AI短片, ComfyUI, Wan2.2, Flux, 科幻短片, 短片, AI动画, 奇点回响
```

---

## 三、YouTube 发布包

### 目录结构

```
release_youtube/
├── ShotFlow_4K_v10.mp4              # 主视频（4K）
├── ShotFlow_1080p_v10.mp4           # 备用 1080p
├── thumbnail_1280x720.jpg           # 自定义封面
├── echo_of_singularity.zh.srt       # 中文字幕（软）
├── echo_of_singularity.en.srt       # 英文字幕（软）
├── title.txt
├── description.txt
├── tags.txt
└── LICENSE.txt
```

### description.txt 模板

```text
AI-generated short film · 4K · 4:10

"Echo of the Singularity" — a 4-minute sci-fi micro-short made entirely with
AIGC tools, produced with the ShotFlow open-source pipeline.

Open-source workflow: https://github.com/MS33834/ShotFlow
License: MIT (open source, commercial use permitted)

Tools: Flux.1 Kontext + IPAdapter (character consistency), Wan2.2 &
Kling 2.5 (video), DaVinci Resolve (edit/grade), ElevenLabs (voice),
Suno (music).

Story:
Forty-seven years after the collapse of human civilization, a wanderer
named Ava discovers the dormant Singularity Core. She is the only one
who can hear its echo...

0:00 Scene 1 — Waking Ruins
0:35 Scene 2 — Ship Wreck
1:20 Scene 3 — Core Chamber
2:30 Scene 4 — Memory Fragments
3:10 Scene 5 — Choice and Echo

#AIGC #AIVideo #ShortFilm #ComfyUI #Wan2.2 #Flux #SciFi
```

---

## 四、抖音 / 小红书 / 视频号 / Reels 发布包（竖版合集）

四个平台共用一组竖版物料，仅标题/简介/标签按平台调整。

```
release_vertical/
├── ShotFlow_1080x1920_v10.mp4       # 竖版主视频
├── ShotFlow_1x1_v10.mp4             # 方版（小红书）
├── cover_vertical_1080x1920.jpg
├── cover_square_1080x1080.jpg       # 小红书
├── subtitles_burned_zh.mp4          # 烧录字幕版（按平台规则）
├── douyin/{title,description,tags}.txt
├── xiaohongshu/{title,description,tags}.txt
├── wechat/{title,description,tags}.txt
└── instagram/{title,description,tags}.txt
```

竖版剪辑要点：

- 主镜头保留，但景别从"大全景"改为"中近景"为主
- 字幕字号 +50%，位置上移至画面中部
- 时长压缩到 60–90 秒（剪高潮段：S03_04 + S05_04 + S05_06）
- 片尾 5 秒固定：标题 + 开源仓库链接

---

## 五、电影节投奖发布包

```
release_festival/
├── ShotFlow_4K_ProRes_v10.mov       # ProRes 422 HQ 母版
├── ShotFlow_4K_Master_v10.mp4       # H.265 备份
├── cover_1920x1080.jpg
├── echo_of_singularity.zh.srt
├── echo_of_singularity.en.srt
├── director_statement.pdf           # 创作阐述（≤ 1 页）
├── production_notes.pdf             # 制作说明（AIGC 工具链 + 流程图）
├── credit_list.pdf                  # 完整片尾字幕
└── license_declaration.pdf          # 授权声明（MIT + 第三方工具授权链）
```

投奖注意事项：

- 大多数电影节要求"AIGC 类作品"单独申报，不与真人短片混评
- 部分影展（如 Sundance、戛纳短片单元）对 AIGC 内容有专门条款，提交前
  逐项核对
- `license_declaration.pdf` 必须列出所有第三方模型/服务的授权状态——
  参考 [`06_Research/licensing_compliance.md`](../06_Research/licensing_compliance.md)

---

## 六、发布前最终检查

每平台发布前，对照 [`release_checklist.md`](./release_checklist.md) 完成：

- [ ] 母版已通过 [`08_Automation/video_quality_check.py`](../08_Automation/video_quality_check.py) 全部检查
- [ ] 字幕无错别字（zh + en 都已校对）
- [ ] 标题/简介无违规词
- [ ] 已勾选平台 AIGC 创作标识
- [ ] 封面分辨率符合平台规格
- [ ] 开源仓库链接已加入简介
- [ ] MIT 开源协议声明已加入简介
- [ ] LICENSE.txt 已随包附送
- [ ] 发布时间已与 [`06_Research/release_platforms.md`](../06_Research/release_platforms.md) 计划一致

---

> 本规格为《奇点回响》示例，实际项目按目标平台政策调整。
> 平台政策可能更新，发布前以平台最新官方文档为准。
