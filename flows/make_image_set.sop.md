# 流程文件：一句话 → 角色各种照片/表情包集（image_set）

> 外部智能体读取并自行执行。ShotFlow 提供工具，不内置脑补。

## ⚠️ 版权提示（用户自担）
平台仅提供生成工具，素材版权由使用者负责。

## 触发条件
- 用户输入一句话，例如：「给我一套魔改奶龙奶娃的表情包，各种姿势」
- 意图识别判定 `output_type = "image_set"`

## 工具清单
同 `make_video.sop.md`（用 `consistency_anchor` / `generate_image` / `save_spec` / `list_assets`）。

## 步骤

### S1 意图识别 ［智能体 LLM］
- 输出：`{output_type:"image_set", subject:"奶龙奶娃", count:6~9, styles:["表情包","全身","坐姿","特写"]}`

### S2 需求脑补 ［智能体 LLM］
- 生成：角色圣经 + 表情/姿势清单（如：开心/惊讶/生气/比心/睡觉/吃饭）
- `save_spec`

### S3 一致性锚定 ［`consistency_anchor`］
- `provider=hunyuan_image`, 生成设定图 → 写回 `ref_asset_ids`

### S4 并行出图 ［`generate_image` × N，并行］
- 每表情：`generate_image(provider=hunyuan_image, prompt=表情描述, ref_images=[设定图])`
- 决策：国内直连优先 `hunyuan_image`；动漫风可 `novelai`/`liblib`；无 Key→占位

### S5 交付 ［ShotFlow］
- 所有图存 PostgreSQL，`list_assets` 返回网格预览 URL

## 验收
- [ ] 一套同角色多表情/姿势，长相一致
- [ ] 无需用户补充细节
