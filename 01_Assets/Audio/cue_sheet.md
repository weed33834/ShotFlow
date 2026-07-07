# Audio Cue Sheet

> 全片音频触发清单——剪辑时按此表把对白 / 配乐 / 音效对到时间线。
> Project: ShotFlow / *Echo of the Singularity* (example)
> 总时长：~4:10（250 秒）

时间码基于 [`examples/echo-of-singularity/shot_tracker.md`](../../examples/echo-of-singularity/shot_tracker.md)
的镜头时间码。剪辑时如以 `05_Output/EDL/shotflow_v01.edl` 的 5 秒/镜粗剪为准，
需重新对齐。

---

## 一、对白轨（A1）

| Cue | 角色 | In | Out | Length | 文件 | 备注 |
|-----|------|----|----|--------|------|------|
| D-01 | Ava | 0:01:14:00 | 0:01:20:00 | 2.8 s | `Dialogue/Ava/Ava_S02_05_v1.wav` | 低语，画外内心独白 |
| D-02 | Core | 0:01:54:00 | 0:02:02:00 | 4.0 s | `Dialogue/Core/Core_S03_04_v1.wav` | 首次出现，无画面来源 |
| D-03 | Ava | 0:02:07:00 | 0:02:13:00 | 4.2 s | `Dialogue/Ava/Ava_S03_05_v1.wav` | 震惊抬头 |
| D-04 | Core | 0:02:13:00 | 0:02:21:00 | 6.0 s | `Dialogue/Core/Core_S03_05_v1.wav` | 接 D-03，无停顿 |
| D-05 | Core | 0:02:43:00 | 0:02:53:00 | 6.5 s | `Dialogue/Core/Core_S04_02_v1.wav` | 配合记忆蒙太奇 |
| D-06 | Ava | 0:02:55:00 | 0:03:02:00 | 3.5 s | `Dialogue/Ava/Ava_S04_03_v1.wav` | 跪在核心前 |
| D-07 | Core | 0:03:11:00 | 0:03:22:00 | 9.0 s | `Dialogue/Core/Core_S05_01_v1.wav` | 星图展开时 |
| D-08 | Ava | 0:03:23:00 | 0:03:30:00 | 5.1 s | `Dialogue/Ava/Ava_S05_02_v1.wav` | 悲伤微笑 |
| D-09 | Core | 0:03:38:00 | 0:03:43:00 | 4.5 s | `Dialogue/Core/Core_S05_04_v1.wav` | 光芒扩散，唯一带温度的一句 |
| D-10 | Narrator | 0:04:06:00 | 0:04:10:00 | 7.2 s | `Dialogue/Guides/Narrator_S05_06_v1.wav` | 片尾字幕配 |

---

## 二、配乐轨（A3 主题 + A4 氛围）

| Cue | 用途 | In | Out | Length | 文件 |
|-----|------|----|----|--------|------|
| M-01 | 片头主题 | 0:00:00:00 | 0:00:10:00 | 10 s | `Music/Themes/Main_Theme_v1.wav` |
| M-02 | S01 废墟氛围 | 0:00:10:00 | 0:01:20:00 | 70 s | `Music/Ambient/Ruins_Dawn_v1.wav` |
| M-03 | S02-S03 飞船内部 | 0:01:20:00 | 0:02:30:00 | 70 s | `Music/Ambient/Ship_Interior_v1.wav` |
| M-04 | S03 核心觉醒 | 0:01:52:00 | 0:02:30:00 | 38 s | `Music/Ambient/Core_Awakening_v1.wav` |
| M-05 | S04 记忆碎片 | 0:02:30:00 | 0:03:10:00 | 40 s | `Music/Ambient/Memory_Fragments_v1.wav` |
| M-06 | S05 结局升华 | 0:03:10:00 | 0:04:05:00 | 55 s | `Music/Ambient/Resolution_v1.wav` |
| M-07 | 片尾主题（再现） | 0:04:05:00 | 0:04:10:00 | 5 s | `Music/Themes/Main_Theme_v1.wav` |

**混音规则**：

- 对白出现时，A3/A4 通过侧链压缩 -6 dB 避让
- M-04 与 M-03 在 0:01:52–0:02:30 重叠，M-04 起势渐入（fade in 2 s）
- M-06 → M-07 在 0:04:05 处硬切 + 0.5 s 交叉淡化

---

## 三、音效轨（A5 点状 + A6 环境床）

| Cue | 用途 | In | Out | 文件 | 类型 |
|-----|------|----|----|------|------|
| F-01 | 废墟风声床 | 0:00:00:00 | 0:01:20:00 | `SFX/Environment/Wind_Ruins_v1.wav` | 环境（A6） |
| F-02 | 碎石脚步 | 0:00:10:00 | 0:00:19:00 | `SFX/Environment/Footstep_Gravel_v1.wav` | 点状（A5） |
| F-03 | 飞船低频轰鸣床 | 0:01:20:00 | 0:02:30:00 | `SFX/Mechanical/Ship_Hum_Low_v1.wav` | 环境（A6） |
| F-04 | 神经接口提示音 | 0:00:45:00 | 0:00:51:00 | `SFX/UI/Neural_Interface_Click_v1.wav` | 点状（A5） |
| F-05 | 面板启动 | 0:00:59:00 | 0:01:09:00 | `SFX/Mechanical/Panel_Beep_v1.wav` | 点状（A5） |
| F-06 | 舱门液压打开 | 0:01:09:00 | 0:01:20:00 | `SFX/Mechanical/Hatch_Hydraulic_v1.wav` | 点状（A5） |
| F-07 | 核心脉冲 | 0:02:17:00 | 0:02:30:00 | `SFX/Mechanical/Core_Pulse_v1.wav` | 点状（A5） |
| F-08 | 数据流声 | 0:03:10:00 | 0:03:22:00 | `SFX/Mechanical/Data_Stream_v1.wav` | 点状（A5） |
| F-09 | 光芒扩散 whoosh | 0:03:38:00 | 0:03:43:00 | `SFX/UI/Bloom_Whoosh_v1.wav` | 点状（A5） |
| F-10 | 远处鸟鸣 | 0:03:43:00 | 0:04:05:00 | `SFX/Environment/Birds_Distant_v1.wav` | 环境（A6） |

---

## 四、总混音目标

```text
对白 A1     -6 dBFS    HPF 80 Hz, +2 dB @ 2 kHz
配乐 A3/A4 -18 dBFS    侧链压缩避让 A1
点状 A5    -20 dBFS    分层分组，按画面位置 pan
环境 A6    -24 dBFS    持续低垫，不抢戏

总线         -1 dBTP    LUFS -16 (web)  /  LUFS -14 (cinema)
```

---

## 五、版本管理

每次混音版本变化必须 bump 文件名版本号：

- `Final_Mix_v01.wav` — 粗混
- `Final_Mix_v05.wav` — 调整对白清晰度后
- `Final_Mix_v10.wav` — 锁定母版

母版锁定后不得覆盖，如需修改另起 v11。

---

> 本 cue sheet 为《奇点回响》示例，实际项目按镜头表重排。
