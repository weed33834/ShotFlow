# 流程文件：一句话 → 动态漫画 / 漫剧（comic）

> 外部智能体读取并自行执行。产出：分镜图 + 对话气泡 + 镜头运动（可导出为漫剧视频）。

## ⚠️ 版权提示（用户自担）

## 触发条件
- 用户输入一句话，例如：「画一个奶龙奶娃大战外卖侠的搞笑漫画，6 格」
- 意图识别判定 `output_type = "comic"`

## 工具清单
`consistency_anchor` / `generate_image` / `generate_video`(做镜头推拉) / `save_spec` / `assemble`(拼页/转漫剧)。

## 步骤

### S1 意图识别 ［智能体 LLM］
- 输出：`{output_type:"comic", panels:6, style:"条漫", genre:"搞笑"}`

### S2 需求脑补（漫画脚本） ［智能体 LLM］
- 生成：分格脚本（每格：画面描述 + 对话气泡文字 + 镜头运动）
- `save_spec`（scenes 即格，shots 即单格内图层）

### S3 角色锚定 ［`consistency_anchor`］

### S4 出格 ［`generate_image` × N 并行］
- 每格：`generate_image(provider=novelai 或 liblib 或 hunyuan_image, prompt=格描述, ref_images=[设定图])`
- 动漫专精优先 `novelai`；LoRA 生态用 `liblib`；无 Key→占位

### S5 动态化（可选） ［`generate_video`］
- 对关键格做镜头推拉/摇移，生成漫剧片段

### S6 组装 ［`assemble`］
- 拼条漫长图 / 或导出漫剧视频（格图+镜头运动+气泡）

### S7 交付 ［ShotFlow］

## 验收
- [ ] 分格叙事完整，有对话气泡
- [ ] 角色一致
