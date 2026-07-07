# ShotFlow — 关键帧提示词汇总表

> 本表覆盖《奇点回响》全部 24 个镜头的关键帧生成提示词，供 AI 美术操作员在 ComfyUI 中直接使用。
>
> 本文件为可复用模板，以《奇点回响》为示例，实际项目请按真实分镜替换。

## 通用锚点

### 艾娃角色锚点（每镜必含）

```
Ava, 28-year-old woman, short dark hair, amber eyes, light scar under right eye, 
cybernetic neural interface glowing on back of neck, dark gray patched windbreaker 
(right shoulder patch), black turtleneck, dark cargo pants, scuffed military boots, 
glowing orange bracelet on left wrist, weathered data terminal at waist
```

### 场景氛围词（按需添加）

```
cinematic sci-fi lighting, film grain, teal and orange color grade, 
dust particles in air, volumetric light, depth of field, 8K, highly detailed
```

### 负面提示词（每镜必含）

```
bad anatomy, deformed face, extra limbs, extra fingers, blurry, low quality, 
inconsistent character, different person, mutated hands, watermark, text, 
plastic skin, oversaturated, cartoon, anime
```

---

## 场景一：废墟苏醒

### S01_01 — 废墟大全景（T2V / 纯场景）

| 项目 | 内容 |
|------|------|
| 景别 | 大全景 |
| 生成方式 | Wan2.2 T2V |
| 分辨率 | 1280×720 |

**正向提示词**：
```
Vast ruined futuristic city at dawn, collapsed highway bridges, overturned vehicles 
half-buried in sand, crumbling skyscrapers covered in vines and rust, thick clouds 
with golden light beams piercing through, dust particles floating in air, 
cinematic sci-fi, teal and orange color grade, film grain, epic scale, 8K
```

### S01_02 — 艾娃走出废墟（I2V）

| 项目 | 内容 |
|------|------|
| 景别 | 中景 |
| 生成方式 | Wan2.2 I2V |
| 分辨率 | 1280×720 |

**正向提示词**：
```
[艾娃锚点], walking slowly out from behind massive concrete debris, 
left hand reaching toward data terminal at waist, cautious expression, 
looking around, ruined city background, morning light, dust particles, 
cinematic sci-fi, teal and orange color grade, film grain, 8K
```

### S01_03 — 艾娃眼部特写（I2V）

| 项目 | 内容 |
|------|------|
| 景别 | 特写 |
| 生成方式 | Wan2.2 I2V |
| 分辨率 | 1280×720 |

**正向提示词**：
```
Extreme close-up of Ava's eyes, amber pupils contracting, expression shifting 
from confusion to alertness, breath forming white mist in cold air, 
short dark hair framing face, light scar under right eye visible, 
cinematic sci-fi, shallow depth of field, teal and orange color grade, film grain, 8K
```

### S01_04 — 艾娃走向飞船（可灵首尾帧）

| 项目 | 内容 |
|------|------|
| 景别 | 全景 |
| 生成方式 | 可灵首尾帧 |
| 分辨率 | 1280×720 |

**起始帧提示词**：
```
[艾娃锚点], walking away from camera toward distant crashed spaceship, 
ruined city landscape, morning light, wide shot from behind, 
cinematic sci-fi, teal and orange color grade, film grain, 8K
```

**结束帧提示词**：
```
[艾娃锚点], standing at side angle near crashed spaceship hull, 
looking up at massive rusted spacecraft, ruined city background, 
cinematic sci-fi, teal and orange color grade, film grain, 8K
```

---

## 场景二：飞船残骸

### S02_01 — 艾娃仰望飞船（I2V）

```
[艾娃锚点], standing before massive crashed spaceship, looking up, 
ship hull covered in rust and vines, neural interface on neck beginning 
to glow faint orange, cinematic sci-fi, low angle shot, 
teal and orange color grade, film grain, 8K
```

### S02_02 — 颈后接口特写（I2V）

```
Extreme close-up of back of Ava's neck, cybernetic neural interface, 
orange-red light pulsing beneath skin like heartbeat, short dark hair 
pushed aside, skin texture detail, cinematic sci-fi, 
teal and orange color grade, film grain, 8K
```

### S02_03 — 触碰飞船外壳（I2V）

```
[艾娃锚点], reaching hand to touch spaceship hull, fingertips grazing 
cold rusted metal, dust falling, medium close-up, handheld camera feel, 
cinematic sci-fi, teal and orange color grade, film grain, 8K
```

### S02_04 — 飞船面板亮起（I2V）

```
Close-up of damaged spaceship hull panel, cracked metal surface suddenly 
illuminating with faint orange glow, responding to touch, dust particles, 
cinematic sci-fi, teal and orange color grade, film grain, 8K
```

### S02_05 — 舱门打开（可灵首尾帧）

**起始帧**：
```
[艾娃锚点], standing before closed spaceship hatch door, hesitation, 
dark corridor visible beyond, cinematic sci-fi, teal and orange color grade, 8K
```

**结束帧**：
```
[艾娃锚点], stepping into spaceship interior through open hatch, 
dark deep corridor ahead, faint orange light from within, 
cinematic sci-fi, teal and orange color grade, 8K
```

---

## 场景三：核心 chamber

### S03_01 — 飞船内部走廊（I2V）

```
Long corridor inside crashed spaceship, broken screens and exposed cables 
on both sides, at the end a glowing spherical device floating in mid-air, 
cracked core with orange light pulsing, data streams on walls, 
cinematic sci-fi, teal and orange color grade, film grain, 8K
```

### S03_02 — 艾娃沿走廊前行（I2V）

```
[艾娃锚点], walking down spaceship corridor toward glowing core, 
wrist bracelet and neck interface glowing brighter, illuminating tense 
side profile, broken screens around, cinematic sci-fi, 
teal and orange color grade, film grain, 8K
```

### S03_03 — 右手握拳特写（I2V）

```
Close-up of Ava's right hand, slightly trembling, clenching into fist, 
scuffed military jacket sleeve visible, orange glow from interface 
reflecting on skin, cinematic sci-fi, teal and orange color grade, 8K
```

### S03_04 — 艾娃站在核心前（可灵首尾帧）

**起始帧**：
```
[艾娃锚点], standing before massive cracked spherical core, orange light 
breathing inside, data streams flowing on walls, wide shot, 
cinematic sci-fi, teal and orange color grade, 8K
```

**结束帧**：
```
[艾娃锚点], standing closer to core, core light intensifying, 
data streams forming star map around her, wide shot from different angle, 
cinematic sci-fi, teal and orange color grade, 8K
```

### S03_05 — 艾娃震惊抬头（I2V）

```
[艾娃锚点], shocked expression, looking up searching for source of voice, 
medium close-up, orange core light on face, fear and curiosity in eyes, 
cinematic sci-fi, teal and orange color grade, film grain, 8K
```

### S03_06 — 核心光芒增强（I2V）

```
[艾娃锚点], face illuminated by intense orange light from core, 
eyes showing mix of fear and desire, slow push-in, cracked core in 
background glowing brighter, cinematic sci-fi, 
teal and orange color grade, film grain, 8K
```

---

## 场景四：记忆碎片

### S04_01 — 记忆碎片蒙太奇（I2V）

```
Surreal montage of memory fragments: childhood room with warm light, 
blurred faces of parents, blinding surgical light, glittering city skyline 
before the silence, dreamlike superimposition, cinematic sci-fi, 
teal and orange color grade, film grain, 8K
```

### S04_02 — 艾娃闭眼流泪（I2V）

```
[艾娃锚点], eyes tightly closed, single tear rolling down cheek, 
neural interface flashing intensely, orange light pulsing, 
extreme close-up, cinematic sci-fi, teal and orange color grade, 8K
```

### S04_03 — 艾娃跪在核心前（可灵首尾帧）

**起始帧**：
```
[艾娃锚点], kneeling before core, hands holding head, core light 
gently wrapping around her like embrace, medium shot, 
cinematic sci-fi, teal and orange color grade, 8K
```

**结束帧**：
```
[艾娃锚点], kneeling, looking up at core with exhausted expression, 
core light softening, data streams calming, medium shot, 
cinematic sci-fi, teal and orange color grade, 8K
```

---

## 场景五：选择与回响

### S05_01 — 星图展开（I2V）

```
Vast space inside spaceship, data streams converging into giant star map, 
countless glowing points each representing dormant singularity node, 
[艾娃锚点] small figure in center, epic scale, cinematic sci-fi, 
teal and orange color grade, film grain, 8K
```

### S05_02 — 艾娃站起悬手（I2V）

```
[艾娃锚点], slowly standing up, hand hovering above core surface 
without touching, tense expression, medium close-up, handheld, 
cinematic sci-fi, teal and orange color grade, film grain, 8K
```

### S05_03 — 悲伤微笑触碰核心（I2V）

```
[艾娃锚点], sad smile on face, hand gently placed on core surface, 
orange light rippling from contact point, close-up, 
cinematic sci-fi, teal and orange color grade, film grain, 8K
```

### S05_04 — 核心光芒扩散（可灵首尾帧）

**起始帧**：
```
[艾娃锚点], hand on core, core light shifting from orange to soft blue-white, 
wide shot, data streams expanding outward, cinematic sci-fi, 8K
```

**结束帧**：
```
Blue-white light spreading across entire ruined city, dormant machines 
awakening with low resonance, epic wide shot, [艾娃锚点] silhouette 
in light, cinematic sci-fi, teal and orange color grade, 8K
```

### S05_05 — 艾娃走出飞船（I2V）

```
[艾娃锚点], walking out of spaceship, ruined city still desolate but 
clouds parting, single beam of sunlight falling on her, neck interface 
no longer glowing, peaceful expression, full shot, 
cinematic sci-fi, teal and orange color grade, film grain, 8K
```

### S05_06 — 无人机上升大全景（T2V）

```
Aerial view rising slowly, tiny figure of woman walking through vast 
ruined city, morning light spreading across horizon, faint electronic 
resonance in wind, epic scale, cinematic sci-fi, 
teal and orange color grade, film grain, 8K
```

---

## 生成参数预设

### Flux.1 Kontext 出图参数

| 参数 | 值 |
|------|-----|
| Steps | 24 |
| CFG | 4.0 |
| Sampler | euler |
| Scheduler | simple |
| 分辨率 | 1024×1024 或 1280×720 |
| 精度 | FP8 |
| Batch Size | 4 |

### Wan2.2 I2V 视频参数

| 参数 | 值 |
|------|-----|
| Steps | 30 |
| CFG | 0.5 |
| Denoise | 0.7 |
| 帧数 | 120（5s × 24fps） |
| 分辨率 | 720P |
| 精度 | FP8 |

### 可灵 2.5 Turbo 参数

| 参数 | 值 |
|------|-----|
| Duration | 5s |
| Aspect Ratio | 16:9 |
| Mode | pro |
| Version | 2.5-turbo |

---

## 使用说明

1. `[艾娃锚点]` 处替换为本文件顶部"艾娃角色锚点"完整文本。
2. 每次生成后保留 seed 值，便于复现与微调。
3. 同一场景的多个镜头建议使用相同 seed 系列以保持光影一致。
4. 生成结果按 `SF_场景号_镜头号_版本.png` 命名保存至 `01_Assets/Scenes/`。
