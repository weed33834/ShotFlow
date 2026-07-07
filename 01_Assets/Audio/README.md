# 音频资产库

> 本项目音频资产统一存放目录，包含配音、配乐、音效三类素材。

## 规划文档（必读）

| 文档 | 内容 |
|------|------|
| [`voice_bibles.md`](./voice_bibles.md) | 角色声线圣经——锁定每个角色的 TTS 引擎、参数、情绪分段 |
| [`cue_sheet.md`](./cue_sheet.md) | 全片音频 cue sheet——对白/配乐/音效的入点出点与混音规则 |
| [`sfx_list.md`](./sfx_list.md) | 音效清单——每条 SFX 的用途、制作方式、授权状态 |

## 目录结构

```
01_Assets/Audio/
├── Dialogue/           # 角色配音
│   ├── Ava/            # 艾娃配音
│   ├── Core/           # 核心/系统音
│   └── Guides/         # 旁白/引导音
├── Music/              # 配乐
│   ├── Themes/         # 主题旋律
│   ├── Ambient/        # 环境氛围
│   └── Stems/          # 分轨文件
├── SFX/                # 音效
│   ├── Environment/    # 环境音
│   ├── Mechanical/     # 机械/科技音
│   └── UI/             # 界面/提示音
└── README.md           # 本文件
```

## 配音清单（示例）

| 文件 | 角色 | 对应镜头 | 时长 | 情绪 | 生成工具 |
|------|------|----------|------|------|----------|
| `Dialogue/Ava/Ava_S01_04_v1.wav` | 艾娃 | S01_04 | 2.8s | 低语、迷惘 | ElevenLabs |
| `Dialogue/Ava/Ava_S03_05_v1.wav` | 艾娃 | S03_05 | 4.2s | 震惊 | ElevenLabs |
| `Dialogue/Ava/Ava_S04_02_v1.wav` | 艾娃 | S04_02 | 3.5s | 悲伤 | ElevenLabs |
| `Dialogue/Ava/Ava_S05_03_v1.wav` | 艾娃 | S05_03 | 5.1s | 释然 | ElevenLabs |
| `Dialogue/Core/Core_S03_06_v1.wav` | 核心 | S03_06 | 6.0s | 中性、机械 | ElevenLabs |
| `Dialogue/Core/Core_S05_01_v1.wav` | 核心 | S05_01 | 4.5s | 中性、机械 | ElevenLabs |
| `Dialogue/Guides/Narrator_S05_06_v1.wav` | 旁白 | S05_06 | 7.2s | 沉静、史诗 | ElevenLabs |

## 配乐清单（示例）

| 文件 | 用途 | 时长 | 情绪 | 生成工具 |
|------|------|------|------|----------|
| `Music/Themes/Main_Theme_v1.wav` | 片头/片尾主题 | 45s | 史诗、苍凉 | Suno |
| `Music/Ambient/Ruins_Dawn_v1.wav` | S01 废墟氛围 | 60s | 空旷、神秘 | Suno |
| `Music/Ambient/Ship_Interior_v1.wav` | S02-S03 飞船内部 | 90s | 压抑、科技 | Suno |
| `Music/Ambient/Core_Awakening_v1.wav` | S03 核心觉醒 | 60s | 紧张、崇高 | Suno |
| `Music/Ambient/Memory_Fragments_v1.wav` | S04 记忆碎片 | 45s | 梦幻、忧伤 | Suno |
| `Music/Ambient/Resolution_v1.wav` | S05 结局升华 | 60s | 希望、宏大 | Suno |

## 音效清单（示例）

| 文件 | 用途 | 对应镜头 | 来源 |
|------|------|----------|------|
| `SFX/Environment/Wind_Ruins_v1.wav` | 废墟风声 | S01 | 素材库 |
| `SFX/Mechanical/Ship_Hum_Low_v1.wav` | 飞船低频轰鸣 | S02-S03 | AudioLDM |
| `SFX/Mechanical/Panel_Beep_v1.wav` | 面板启动 | S02_04 | 素材库 |
| `SFX/Mechanical/Core_Pulse_v1.wav` | 核心脉冲 | S03_06 | AudioLDM |
| `SFX/Mechanical/Data_Stream_v1.wav` | 数据流声 | S05_01 | AudioLDM |
| `SFX/Environment/Birds_Distant_v1.wav` | 远处鸟鸣 | S05_05 | 素材库 |
| `SFX/UI/Neural_Interface_Click_v1.wav` | 神经接口提示音 | S02_02 | 素材库 |

## 混音参数模板

```text
人声: -6 dBFS, 中频提升 2dB @ 2kHz, 高通 80Hz
配乐: -18 dBFS, 侧链压缩避让对白
音效: -20 dBFS, 分层分组
总线: -1 dBTP 峰值限制, LUFS -16 (网络平台)
```

## 使用说明

1. 使用 `elevenlabs_tts_api.py` 批量生成对白
2. 使用 `suno_music_api.py` 生成氛围音乐
3. 音效优先使用素材库，缺失部分用 AudioLDM 补全
4. 所有音频统一 48kHz / 24bit WAV，最终混音输出 48kHz / 16bit AAC
