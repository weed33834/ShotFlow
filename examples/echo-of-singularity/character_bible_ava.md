# Character Bible — Ava

> Protagonist of *Echo of the Singularity* (奇点回响).
> This is the locked reference used to keep her consistent across all 24 shots.

---

## Identity

| Field | Value |
|-------|-------|
| Full name | Ava |
| Age | 28 |
| Occupation | Former interstellar archaeologist, now a ruins drifter |
| World | 47 years after the collapse of human civilization |
| Personality | Solitary, resilient, curious, reserved |

---

## Visual anchors (never change)

These details must appear in every shot that shows Ava, regardless of framing or lighting.

### Face
- Short dark hair, slightly messy, left side often tucked behind ear
- Amber eyes, slight downward tilt at the outer corners
- Light scar under the right eye
- Oval face, clear jawline
- Thin lips, usually pressed into a tense line

### Body
- Height ~168 cm, lean but visibly muscular
- Right shoulder of jacket has a worn patch
- Left wrist wears a glowing orange bracelet
- Waist carries a weathered data terminal

### Clothing
- Dark gray patched windbreaker (right shoulder patch)
- Black turtleneck
- Dark cargo pants, reinforced at the knees
- Scuffed military boots

### Signature tech
- Neural interface at the back of the neck
  - Normally dim
  - Glows orange when near the Core
  - Pulses in rhythm with the Core's "heartbeat"

---

## Expression map

| Emotion | Look | Posture |
|---------|------|---------|
| Lost | Eyes unfocused, lips parted | Standing still, hand on terminal |
| Alert | Eyes narrowed, jaw set | Slight crouch, hand near waist |
| Determined | Chin up, gaze fixed | Long strides forward |
| Sad | Lids lowered, slow breath | Leaning against wall, shoulders slightly hunched |
| Resigned peace | Soft gaze, faint smile | Walking into light, interface dim |

---

## Prompt template (English)

Use this exact prompt fragment in every positive prompt that includes Ava:

```text
Ava, 28-year-old woman, short dark hair, amber eyes, light scar under right eye,
cybernetic neural interface glowing on back of neck, dark gray patched windbreaker
(right shoulder patch), black turtleneck, dark cargo pants, scuffed military boots,
glowing orange bracelet on left wrist, weathered data terminal at waist
```

Add scene-specific action and lighting after this block.

---

## Prompt template (Chinese)

中文提示词模板：

```text
艾娃，28岁女性，深色短发，琥珀色眼睛，右眼下方浅疤，
颈后发光的神经接口，深灰色右肩补丁防风夹克，黑色高领内搭，
深色工装裤，磨损军靴，左手腕发光手环，腰间旧数据终端
```

---

## Reference set

The generated reference images are stored in [`../../01_Assets/Characters/Ava/`](../../01_Assets/Characters/Ava/).

| File | Use case |
|------|----------|
| `Front/Ava_front_v01.png` | Primary face reference |
| `Side/Ava_side_v01.png` | Profile check |
| `Back/Ava_back_v01.png` | Neural interface visibility |
| `Expressions/Ava_neutral_v01.png` | Default expression |
| `Expressions/Ava_alert_v01.png` | Tense scenes |
| `Expressions/Ava_sad_smile_v01.png` | Climax and ending |
| `Turnaround/Ava_turnaround_v01.png` | Global IPAdapter anchor |

---

## Consistency rules

1. **Scar stays on the right eye** — flip checks required for any mirrored shot.
2. **Neural interface glows orange, never blue or green**, except in the final scene where it goes dark.
3. **Bracelet glow matches interface pulse** in scenes 2–4; both go dark in scene 5.
4. **Jacket patch stays on the right shoulder** — watch for left/right confusion in wide shots.
5. **Hair length stays short** — no sudden long hair or different parting.

---

> Any shot that breaks one of these anchors goes back for retake.
