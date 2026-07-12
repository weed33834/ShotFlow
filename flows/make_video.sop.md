# 流程文件：一句话 → 15 秒短视频（video）

> 本文件由外部智能体（WorkBuddy / 元器 / 百炼 / Dify）读取并自行执行。
> ShotFlow 只提供工具（MCP/OpenAPI），不内置脑补逻辑。智能体读此文件后自己跑完整个流程。

## ⚠️ 版权提示（用户自担）
本平台仅提供生成工具。所用角色 / 音乐 / 肖像 / 素材须由使用者确保有权使用。平台不做授权拦截。

---

## 触发条件
- 用户输入一句话描述，例如：「魔改奶龙奶娃捧腹大笑 15 秒」
- 意图识别判定 `output_type = "video"`，时长 ≤ 60s

---

## 工具清单（ShotFlow 暴露，智能体按需调用）
| 工具 | 用途 | 关键参数 |
|---|---|---|
| `save_spec` | 写回中央规格 | `project_id`, `spec`(JSON) |
| `consistency_anchor` | 生成角色/风格设定图（一致性锚点） | `provider`, `prompt`, `reference_images[]` |
| `generate_image` | 文生图/图生图 | `provider`, `prompt`, `ref_images[]`, `params` |
| `generate_video` | 文生视频/图生视频 | `provider`, `prompt`, `image_urls[]`, `duration` |
| `generate_audio` | TTS/配音/BGM/SFX | `provider`, `text`, `voice`, `audio_type` |
| `lip_sync` | 口型同步 | `provider`, `video_url`, `audio_url` |
| `assemble` | 字幕/拼接/混音成片 | `spec_id`, `asset_ids[]`, `subtitles[]` |
| `get_status` / `list_assets` | 查询 | `task_id` / `project_id` |

> 所有 `generate_*` 在 `SIMULATE_MODE=true`（无 Key）时返回占位资产，全链路仍可验证。

---

## 步骤（每步注明：执行者 / 工具 / 输入 / 输出 / 决策）

### S1 意图识别 ［执行者：智能体自带 LLM］
- 输入：用户原话
- 输出：`{output_type:"video", duration:15, mood:"捧腹大笑", subject:"奶龙奶娃", style:"魔改meme", target_platform:"抖音"}`
- 决策：
  - 若含真人肖像 → 提示用户「肖像版权自担」
  - 若 duration > 30s → 建议拆成多镜（每镜 ≤ 15s，避免长视频漂移）
  - 若未指明时长 → 默认 15s

### S2 需求脑补（扩写详细 Spec） ［执行者：智能体自带 LLM，依据下方指引］
- 指引（智能体据此生成，不要直接问用户）：
  - **角色圣经**：名字、外貌（颜色/体型/五官）、性格、口头禅、标志性动作
  - **分镜**：3–5 镜，每镜含：景别（近/中/全）、动作、台词/笑点、时长
  - **风格锚点**：参考图方向（如「圆润卡通、高饱和、夸张表情」）
- 输出：完整 Spec JSON（结构见下），调用 `save_spec`
- Spec 结构示例：
```json
{
  "intent": "魔改奶龙奶娃捧腹大笑15秒",
  "output_type": "video",
  "style_anchor": {"provider": "hunyuan_image", "ref_asset_ids": []},
  "characters": [{"name": "奶龙奶娃", "anchor_prompt": "圆润蓝色小龙宝宝，大眼，爱笑", "ref_asset_ids": []}],
  "scenes": [{"index": 1, "description": "奶娃看到笑话", "shots": [
    {"index": 1, "duration": 5, "image_prompt": "奶龙奶娃瞪大眼睛看手机", "video_prompt": "奶娃身体前倾好奇", "audio": {"text": "哈哈这是什么", "voice": "child_cn", "type": "tts"}, "subtitle": "哈哈这是什么"},
    {"index": 2, "duration": 5, "image_prompt": "奶娃捂肚子", "video_prompt": "奶娃前仰后合", "audio": {"text": "笑死我了", "voice": "child_cn", "type": "tts"}, "subtitle": "笑死我了"},
    {"index": 3, "duration": 5, "image_prompt": "奶娃躺地打滚", "video_prompt": "奶娃满地打滚捧腹", "audio": {"text": "哈哈哈哈", "voice": "child_cn", "type": "tts"}, "subtitle": "哈哈哈哈"}
  ]}],
  "assembly": {"subtitles": true, "bgm": true, "resolution": "1080p"}
}
```

### S3 一致性锚定 ［执行者：调用 `consistency_anchor`］
- 调用：`provider=hunyuan_image`, `prompt=角色圣经的anchor_prompt`, `reference_images=[]`
- 输出：角色设定图 `asset_id` → 写回 `Spec.style_anchor.ref_asset_ids` 与各角色 `ref_asset_ids`
- 复用：后续所有图/视频均带此设定图，保证长相一致

### S4 并行生成（按镜） ［执行者：智能体调度工具，各镜并行］
- 每镜循环：
  1. `generate_image(provider=hunyuan_image, prompt=镜image_prompt, ref_images=[设定图])` → 镜静帧
  2. `generate_video(provider=wanx 或 kling, prompt=镜video_prompt, image_urls=[静帧], duration=镜时长)` → 镜视频
  3. `generate_audio(provider=tencent_tts 或 heygen, text=镜台词, voice=..., type="tts")` → 镜音频
- 决策（视频厂商）：
  - 国内直连优先 `wanx` / `kling`
  - 需口型同步 → 用 `heygen` 替代 `generate_video`+`generate_audio`（一步出对口型视频）
  - 无 Key（SIMULATE）→ 全部返回占位
- 异常处理：某镜失败 → 重试 1 次；仍失败 → 标记该镜用占位，继续其余镜，最后汇报

### S5 组装成片 ［执行者：调用 `assemble`］
- 调用：`spec_id`, `asset_ids=[所有镜视频+音频]`, `subtitles=[每镜台词]`
- 动作：ffmpeg 拼接多镜视频 + 混音 + 硬压字幕 → 输出成片
- 输出：成品 video `asset_id` + `url`

### S6 交付 ［执行者：ShotFlow］
- 成品存 PostgreSQL，返回 `url` 给智能体 / 网页 UI 预览

---

## 验收标准
- [ ] 一句话进入，无需用户再补充细节（智能体自主脑补）
- [ ] 角色各镜长相一致（设定图锚定）
- [ ] 成片含台词字幕 + 配音
- [ ] 时长符合用户要求（±2s）
- [ ] 全程无人工介入（除非含真人肖像需提示）
