# Poster / Cover Spec

> 各发布平台封面与海报的视觉规格——发布前按本规格出图。
> Project: ShotFlow / *Echo of the Singularity* (example)
> License: MIT

封面是点击率的决定性因素。本规格锁定每个平台的尺寸、构图、字体、
色彩、出图源，避免发布前临时拼图。

---

## 一、平台尺寸矩阵

| 平台 | 尺寸 (px) | 画幅 | 文件 | 大小上限 | 关键安全区 |
|------|-----------|------|------|----------|------------|
| Bilibili 横版封面 | 1146×717 | 16:10 | cover_landscape_1146x717.jpg | ≤ 5 MB | 中间 920×500 之外为 UI 遮挡区 |
| Bilibili 竖版封面 | 1080×1920 | 9:16 | cover_portrait_1080x1920.jpg | ≤ 5 MB | 上下 200 px 为标题遮挡区 |
| YouTube 缩略图 | 1280×720 | 16:9 | thumbnail_1280x720.jpg | ≤ 2 MB | 右下 80×80 为时间码遮挡 |
| 抖音 / 视频号封面 | 1080×1920 | 9:16 | cover_vertical_1080x1920.jpg | ≤ 5 MB | 下方 400 px 为描述遮挡 |
| 小红书封面 | 1080×1920 / 1080×1080 | 9:16 / 1:1 | cover_xhs_{v,s}.jpg | ≤ 10 MB | 全图可见，无遮挡 |
| Instagram Reels 封面 | 1080×1920 | 9:16 | cover_insta_1080x1920.jpg | ≤ 8 MB | 下方 250 px 为 UI 遮挡 |
| 电影节正式海报 | 2000×3000 | 2:3 | poster_festival_2000x3000.jpg | 按影展要求 | 留 200 px 出血 |

---

## 二、视觉规范（全平台通用）

### 色彩

- 主色：青橙色调（Teal & Orange）——与影片 LUT 一致
- 废墟/环境：青灰 `#2C3E50` ~ `#34495E`
- 艾娃/核心高光：暖橙 `#E67E22` ~ `#F39C12`
- 文字：白 `#FFFFFF`（带 2 px 黑色描边）
- 副文字：浅灰 `#BDC3C7`

### 字体

| 用途 | 字体 | 备选 |
|------|------|------|
| 中文标题 | Source Han Serif SC Heavy（思源宋体 Heavy） | Songti SC Black |
| 英文标题 | Cormorant Garamond Bold | Playfair Display |
| 副标题 | Source Han Sans SC Medium | Noto Sans SC |
| 平台标签 | Inter Medium | Helvetica Neue |

### 构图原则

1. **主体居中或左下**——艾娃的侧脸或背影占画面 40-60%
2. **核心元素右上**——奇点核心光球作为视觉锚点
3. **标题压底**——中英文标题并排，副标题（AIGC 短片）在标题下方
4. **留白避让 UI**——按各平台安全区避让遮挡区
5. **不堆元素**——一张封面最多 3 个视觉元素（人物 + 核心 + 标题）

---

## 三、出图源（Prompt 模板）

### 横版封面（Bilibili / YouTube）

```text
Cinematic film poster, 16:9, teal and orange color grade,
a lone wanderer woman (short dark hair, amber eyes, dark gray jacket
with glowing orange wristband) seen from behind, looking up at a
cracked glowing spherical AI core floating in a ruined futuristic
city, dramatic god rays through dust, sci-fi mystery poetic mood,
35mm film grain, high contrast, no text, no watermark.
Negative: text, watermark, logo, signature, cartoon, anime.
```

生成参数：Flux.1 Kontext [dev] / 1024×576 / seed: 42 / steps: 30 / guidance: 3.5

### 竖版封面（抖音 / 小红书 / 视频号 / Reels）

```text
Vertical cinematic film poster, 9:16, teal and orange color grade,
close-up of a wanderer woman (short dark hair, amber eyes, glowing
orange neural interface on the back of her neck), her face partially
lit by a warm orange glow from below, ruins and dust in the dark
background, sci-fi mystery mood, 35mm film grain, no text.
Negative: text, watermark, logo, signature, cartoon, anime.
```

生成参数：Flux.1 Kontext [dev] / 576×1024 / seed: 17 / steps: 30 / guidance: 3.5

### 电影节海报（2000×3000）

竖版封面为基础，叠加排版层：

- 顶部 600 px：影展 logo 区（按影展要求留白）
- 中部 1600 px：主视觉（竖版封面图）
- 底部 800 px：标题 + 制作信息
  - "Echo of the Singularity" + 《奇点回响》
  - 副标题："An AIGC short film by ShotFlow Contributors"
  - 角标："MIT | https://github.com/MS33834/ShotFlow"

---

## 四、出图与排版流程

1. **生成底图**：用 `03_Workflows/flux_keyframe_workflow.json` 跑上述
   prompt，得到底图 PNG。
2. **超分**：Topaz Video AI / Gigapixel 放大到目标分辨率（≥ 2×）。
3. **调色**：套用项目 LUT `05_Output/Final/shotflow_grade.cube`，与正片统一。
4. **排版**：在 Figma / Photoshop / Affinity Photo 中按本规格叠字。
5. **导出**：JPEG quality 85，sRGB，文件大小按平台要求控制。
6. **归档**：源文件 + 导出图都存入 `09_Release/posters/{platform}/`。

---

## 五、文字内容（中文）

### 主标题（始终出现）

```text
奇点回响
```

### 副标题（按平台选择）

| 平台 | 副标题 |
|------|--------|
| Bilibili | AIGC 科幻短片 · ShotFlow 工作流开源 |
| YouTube | An AIGC Sci-Fi Short Film · Open-source workflow |
| 抖音 | AIGC 科幻短片 · 4 分钟 |
| 小红书 | 用 AI 做了一部 4 分钟科幻短片 |
| 视频号 | AIGC 科幻短片 · 完整工作流开源 |
| Instagram | An AIGC Sci-Fi Short |
| 电影节 | An AIGC short film · MIT |

### 角标（小字，可选）

```text
github.com/MS33834/ShotFlow · MIT
```

---

## 六、审核清单

每张封面发布前核对：

- [ ] 分辨率符合平台规格
- [ ] 安全区避让正确（无重要元素被 UI 遮挡）
- [ ] 字体已嵌入（避免目标机器缺字）
- [ ] 文件大小在平台限制内
- [ ] 无错别字（中英文标题拼写）
- [ ] 色彩与影片 LUT 一致
- [ ] 已标注 AIGC 创作（按平台要求）
- [ ] 已包含开源仓库链接（角落小字）
- [ ] 无版权水印（freesound 等素材的 logo 不能出现）

---

## 七、版本管理

```
09_Release/posters/
├── bilibili/
│   ├── cover_landscape_v1.psd      # 源文件
│   └── cover_landscape_v1.jpg      # 导出
├── youtube/
├── douyin/
├── xiaohongshu/
├── wechat/
├── instagram/
└── festival/
    ├── poster_v1.psd
    └── poster_v1.jpg
```

每次调整必须 bump 版本号，不得覆盖已发布版本。

---

> 本规格为《奇点回响》示例，实际项目按视觉风格与平台政策调整。
