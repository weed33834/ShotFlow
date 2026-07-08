# SFX List — 音效清单

> 全片音效清单，按"环境 / 机械 / UI"三类分组，列出每条音效的用途、
> 入点、出处、授权状态。
> Project: ShotFlow / *Echo of the Singularity* (example)

> 与 [`cue_sheet.md`](./cue_sheet.md) 第三节"音效轨"互补：
> cue sheet 给时间码，本文件给制作工艺与授权链路。

---

## 一、环境音效（Environment）

| ID | 文件 | 用途 | 入点 | 长度 | 制作方式 | 授权 |
|----|------|------|------|------|----------|------|
| ENV-01 | `Wind_Ruins_v1.wav` | 废墟风声床（S01 全场景） | 0:00 | 80 s | freesound.org CC0 素材，loop 拼接 3 次 | CC0 |
| ENV-02 | `Footstep_Gravel_v1.wav` | 艾娃碎石脚步（S01_02） | 0:10 | 9 s | freesound.org CC0 多条素材叠加，按 S01_02 节奏剪辑 | CC0 |
| ENV-03 | `Birds_Distant_v1.wav` | 远处鸟鸣（S05_05） | 3:43 | 22 s | freesound.org CC0，低通滤波 -6 dB 处理 | CC0 |

> 环境音多为 CC0 素材库拼贴。每条用到的 freesound ID 记录在
> `01_Assets/Audio/SFX/_freesound_log.csv`（不提交，仅本地存档）。

---

## 二、机械音效（Mechanical）

| ID | 文件 | 用途 | 入点 | 长度 | 制作方式 | 授权 |
|----|------|------|------|------|----------|------|
| MEC-01 | `Ship_Hum_Low_v1.wav` | 飞船低频轰鸣床（S02-S03） | 1:20 | 70 s | AudioLDM 生成（prompt: "low-frequency metallic hum, abandoned spaceship, eerie ambience, looping"） | AudioLDM output |
| MEC-02 | `Panel_Beep_v1.wav` | 面板启动（S02_04） | 0:59 | 10 s | freesound.org CC0 + 高通滤波 + 包络 | CC0 |
| MEC-03 | `Hatch_Hydraulic_v1.wav` | 舱门液压打开（S02_05） | 1:09 | 11 s | freesound.org CC0 工业气动门素材 + 低频增强 | CC0 |
| MEC-04 | `Core_Pulse_v1.wav` | 核心脉冲（S03_06） | 2:17 | 13 s | AudioLDM 生成（prompt: "rhythmic low pulse, sci-fi energy core, breathing"），与 D-02 节奏对齐 | AudioLDM output |
| MEC-05 | `Data_Stream_v1.wav` | 数据流声（S05_01） | 3:10 | 12 s | AudioLDM 生成（prompt: "high-frequency data stream, digital noise, swishing"） | AudioLDM output |

---

## 三、UI / 界面音效（UI）

| ID | 文件 | 用途 | 入点 | 长度 | 制作方式 | 授权 |
|----|------|------|------|------|----------|------|
| UI-01 | `Neural_Interface_Click_v1.wav` | 神经接口提示音（S02_02） | 0:45 | 6 s | freesound.org CC0 电子提示音 + 混响 1.2 s | CC0 |
| UI-02 | `Bloom_Whoosh_v1.wav` | 光芒扩散 whoosh（S05_04） | 3:38 | 5 s | freesound.org CC0 风声素材，时间拉伸 +0.5 oct | CC0 |

---

## 四、AudioLDM 生成参数记录

AudioLDM 生成的音效（MEC-01 / 04 / 05）参数如下，便于复现：

```yaml
model: AudioLDM2
text_prompt: <见各 ID 行>
audio_length: 10.0          # 秒
num_inference_steps: 200
guidance_scale: 3.5
seed: 42                    # 固定 seed 保证可复现
output_format: wav
sample_rate: 48000
```

完整生成脚本：`08_Automation/audioldm_sfx_gen.py`（仓库未含此脚本，参考
上述参数与 [AudioLDM2 官方仓库](https://github.com/haoheliu/AudioLDM2) 自行实现）

---

## 五、授权合规

- **CC0 素材**：可商用，无署名义务。本案例仍按惯例在
  [`05_Output/Final/credits.md`](../../05_Output/Final/credits.md) 中致谢
  freesound.org 社区。
- **AudioLDM 输出**：AudioLDM 模型本身基于 CC-BY-NC-SA-4.0，生成内容
  建议仅用于非商用场景。本仓库整体 CNCL 协议一致。
- 详细授权链路见 [`06_Research/licensing_compliance.md`](../../06_Research/licensing_compliance.md)。

---

## 六、目录结构

```
01_Assets/Audio/SFX/
├── Environment/
│   ├── Wind_Ruins_v1.wav
│   ├── Footstep_Gravel_v1.wav
│   └── Birds_Distant_v1.wav
├── Mechanical/
│   ├── Ship_Hum_Low_v1.wav
│   ├── Panel_Beep_v1.wav
│   ├── Hatch_Hydraulic_v1.wav
│   ├── Core_Pulse_v1.wav
│   └── Data_Stream_v1.wav
├── UI/
│   ├── Neural_Interface_Click_v1.wav
│   └── Bloom_Whoosh_v1.wav
├── _freesound_log.csv      # 本地存档，不入仓库
└── README.md               # （沿用本目录现有 README）
```

---

> 本清单为《奇点回响》示例，实际项目按画面需求增删。
