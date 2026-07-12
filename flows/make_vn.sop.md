# 流程文件：一句话 → 视觉小说（vn）

> 外部智能体读取并自行执行。产出：立绘 + 背景 + 选项分支 + 配音，可导出为 VN 引擎工程或演示视频。

## ⚠️ 版权提示（用户自担）

## 触发条件
- 用户输入一句话，例如：「做个奶龙奶娃的互动视觉小说，有分支选择」
- 意图识别判定 `output_type = "vn"`

## 工具清单
`consistency_anchor` / `generate_image`(立绘+背景) / `generate_audio`(角色配音) / `save_spec` / `assemble`(导出工程/演示)。

## 步骤

### S1 意图识别 ［智能体 LLM］
- 输出：`{output_type:"vn", branches:true, scenes:3~5}`

### S2 需求脑补（VN 脚本） ［智能体 LLM］
- 生成：场景流（每场景：背景描述 + 立绘位置 + 台词 + 选项分支树）
- `save_spec`（scenes = 节点，shots = 该节点对话行）

### S3 资产锚定 ［`consistency_anchor` × N 角色 + 背景］
- 每个角色一张设定图；若干背景图

### S4 出立绘/背景 ［`generate_image` 并行］
- 立绘：`provider=hunyuan_image/novelai`，透明背景优先
- 背景：`provider=wanx/hunyuan_image`

### S5 配音 ［`generate_audio`］
- 每句台词 `type="tts"`，按角色选 voice

### S6 组装 ［`assemble`］
- 导出 Ren'Py 风格脚本（label + 立绘 + 选项）或演示视频

### S7 交付 ［ShotFlow］

## 验收
- [ ] 有分支选项结构
- [ ] 立绘/背景/配音齐全，角色一致
