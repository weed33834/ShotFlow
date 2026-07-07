# 角色一致性提示词示例

> 本文件展示 ShotFlow 中主角「艾娃」的角色一致性提示词写法。
> 完整版见 [`01_Assets/Characters/Ava/README.md`](../01_Assets/Characters/Ava/README.md)。

---

## 角色锚点

在任何镜头提示词中，都必须保留以下锚点，确保艾娃跨镜头一致：

- **性别/年龄**：年轻女性，约 28 岁
- **发型**：深色短发，略凌乱，前额一缕碎发
- **面部特征**：浅色眼睛，轮廓柔和，表情偏冷峻
- **服装**：深灰色高领紧身衣 + 黑色战术马甲 + 银色项链
- **标志性元素**：左肩发光的蓝色接口、右手腕缠绕的数据线

---

## 示例提示词

### 镜头 S01_01 — 艾娃在废弃实验室醒来

```text
A young woman around 28 years old, short dark hair with a loose strand on forehead, light-colored eyes, soft facial features with a cold expression. She wears a dark gray turtleneck, black tactical vest, and a silver necklace. A glowing blue interface on her left shoulder, data cable wrapped around her right wrist. She wakes up on a metal table in an abandoned laboratory, dim cyan emergency lights, dust particles in the air, cinematic sci-fi atmosphere, 35mm film grain, shallow depth of field.
```

### 负面提示词

```text
extra fingers, mutated hands, deformed face, inconsistent hairstyle, wrong clothing, missing necklace, blurred face, low quality, watermark, text, logo
```

---

## 使用建议

1. 把角色描述作为每句提示词的固定前缀；
2. 场景描述放在角色描述之后；
3. 负面提示词中必须包含 `inconsistent hairstyle` 和 `wrong clothing`；
4. 生成后做盲测，相似度不达标的镜头重跑。
