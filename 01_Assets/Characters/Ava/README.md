# 角色资产库 — 艾娃 (Ava)

> 女主角：28岁女性，前星际考古学家

## 角色锚点

```text
Ava, 28-year-old woman, short dark hair, amber eyes, light scar under right eye,
cybernetic neural interface glowing on back of neck, dark gray patched windbreaker
(right shoulder patch), black turtleneck, dark cargo pants, scuffed military boots,
glowing orange bracelet on left wrist, weathered data terminal at waist
```

## 目录结构

```
01_Assets/Characters/Ava/
├── Front/              # 正面参考图
├── Side/               # 侧面参考图
├── Back/               # 背面参考图
├── Expressions/        # 表情参考图
├── Turnaround/         # 三视图合成
└── README.md           # 本文件
```

## 资产生成状态

> 以下子目录与 PNG 文件尚未生成。脚本与工作流已就绪，在 GPU 环境运行 `08_Automation/batch_keyframe_gen.py` 后产出。

| 计划文件 | 描述 | 状态 |
|------|------|------|
| `Front/Ava_front_v01.png` | 正面肖像 | 待生成 |
| `Side/Ava_side_v01.png` | 右侧面 | 待生成 |
| `Back/Ava_back_v01.png` | 背面（展示颈后接口） | 待生成 |
| `Expressions/Ava_neutral_v01.png` | 中性表情 | 待生成 |
| `Expressions/Ava_alert_v01.png` | 警觉表情 | 待生成 |
| `Expressions/Ava_sad_smile_v01.png` | 悲伤微笑 | 待生成 |
| `Turnaround/Ava_turnaround_v01.png` | 三视图合成 | 待生成 |

## 一致性标准

- 盲测方案已就绪（见 `06_Research/qa_and_blind_test.md`），待实机验证
- 目标跨镜头相似度: >95%
- 不可变特征: 短发、琥珀色眼睛、右眼下疤痕、颈后神经接口、右肩补丁、橙色手镯

## 使用说明

生成资产后，在 ComfyUI IPAdapter 节点中优先使用 `Turnaround/Ava_turnaround_v01.png` 作为全局参考。
在特写镜头中，使用 `Expressions/` 下对应表情作为辅助参考。
