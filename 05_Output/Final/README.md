# 05_Output/Final — 最终成片与交付文件

> 本目录存放项目最终交付物与母版文件。  
> 以 ShotFlow /《奇点回响》为示例，实际项目请按需求调整规格。

---

## 目录结构

```
05_Output/Final/
├── README.md                     # 本文件
├── delivery_specs.md             # 最终交付规格书
├── assembly_guide.md             # 终剪装配指南（从 EDL + 素材到锁定母版）
├── asset_manifest.md             # 完整资产清单（镜头/对白/配乐/音效/校验和）
├── credits.md                    # 片尾字幕（演职/工具/授权说明）
├── color_grading_notes.md        # 调色记录
├── final_mix_notes.md            # 最终混音记录
├── upscale_and_repair_notes.md   # Topaz 超分与瑕疵修复记录
├── subtitles/                    # 字幕目录
│   ├── README.md
│   ├── echo_of_singularity.zh.srt  # 中文字幕（SRT）
│   ├── echo_of_singularity.en.srt  # 英文字幕（SRT）
│   └── echo_of_singularity.zh.ass  # 中文样式字幕（ASS，影院烧录用）
├── shotflow_4k_master.mp4    # 4K 最终成片（示例文件名）
├── shotflow_1080p.mp4        # 1080P 网络版（示例文件名）
├── shotflow_vertical.mp4     # 竖版短视频（示例文件名）
└── shotflow_stereo.wav       # 独立立体声母版（示例文件名）
```

---

## 标准交付物清单

| 文件 | 规格 | 用途 |
|------|------|------|
| 4K 母版 | 3840×2160 / 24fps / H.264 或 H.265 / 立体声 | 存档、投奖、大屏播放 |
| 1080P 网络版 | 1920×1080 / 24fps / H.264 / AAC | B站/YouTube/视频号 |
| 竖版短视频 | 1080×1920 / 24fps / H.264 / AAC | 抖音/小红书/Instagram Reels |
| 独立音频母版 | 48kHz / 16bit / 立体声 WAV | 播客、广播、混音存档 |
| 调色 LUT | `.cube` | 统一风格、快速复用 |
| 达芬奇工程文件 | `.drp` | 后期修改与版本管理 |
| 混音工程文件 | `.fairlight` / DAW 工程 | 音频修改与版本管理 |

---

## 质量检查

最终交付前必须通过以下检查：

- [ ] 4K 母版无压缩伪影、无闪烁、无黑帧
- [ ] 音画同步，无爆音、无削波
- [ ] 字幕清晰可读，无错别字
- [ ] 各平台版本已按规格导出
- [ ] 文件命名符合 `项目名_分辨率_版本.扩展名` 规范
- [ ] 所有工程文件与 LUT 已归档

---

> 详细规格见 [`delivery_specs.md`](./delivery_specs.md)。
