# ShotFlow × 外部智能体 集成指南

> 目标：让任意 MCP/OpenAPI 兼容智能体（WorkBuddy / 腾讯元器 / 阿里百炼 / Dify）**零改造**驱动 ShotFlow 出片。
> 本目录提供免费、文件形式的暴露物，无需付费工具接入：

| 文件 | 用途 | 给谁用 |
|---|---|---|
| `shotflow.mcp.json` | MCP server 启动清单（stdio 拉起 `python -m app.services.mcp_server`） | MCP 客户端（Claude Desktop / Cline / WorkBuddy MCP / 元器） |
| `server_card.json` | MCP Server Card（v2.1 自动发现元数据） | 支持 Server Cards 的发现器 |
| `openapi.json` | REST API 3.0 规约 | 走 HTTP 的客户端 / 代码生成 |
| `make_nailong_video.sop.md` | 「奶龙奶娃捧腹大笑」视频专用 SOP（智能体自执行说明书） | 读 flow 文件的智能体 |
| `../flows/make_*.sop.md` | 通用 SOP（video/image_set/micro_movie/comic/vn） | 同上 |

---

## 1. 平台心智模型（务必先读）

ShotFlow **不内置「脑补」逻辑**。它做的是两件事：

1. **提供详细 SOP 流程文件**（`flows/*.sop.md`）——告诉智能体「怎么编排、每一步调哪个工具、输入输出是什么」。
2. **暴露生成工具**（MCP 6 个 + REST 同源）——智能体读 SOP 后**自己**按步骤调用这些工具跑完整条链路；ShotFlow 只负责真正的生成动作与资产登记。

```
用户一句话
   │
   ▼
外部智能体（读 flows/*.sop.md，自行脑补细节、拆分镜头）
   │  循环调用
   ▼
ShotFlow 工具层（consistency_anchor / generate_* / lip_sync / assemble）
   │  SIMULATE 模式返回 simulate:// 占位；配置 Key 后返回真实 URL
   ▼
资产落库（Spec + Asset），成片由 assemble 产出
```

---

## 2. 三种接入方式（选其一）

### A. MCP（推荐，最省事）
把 `shotflow.mcp.json` 的 `mcpServers.ShotFlow` 段拷进你的 MCP 客户端配置（如 WorkBuddy 的 MCP 配置 / Claude Desktop 的 `claude_desktop_config.json`）：
```json
{
  "mcpServers": {
    "ShotFlow": {
      "command": "python",
      "args": ["-m", "app.services.mcp_server"],
      "env": { "PYTHONPATH": "backend", "SIMULATE_MODE": "true" }
    }
  }
}
```
启动 backend 所在环境后，客户端会拉起 stdio MCP server，自动拿到 6 个工具。

### B. REST（HTTP）
`uvicorn backend.app.main:app --port 8000` 后，按 `openapi.json` 调 `http://localhost:8000/api/v1/...`。
一句话出片：`POST /api/v1/generate {"nl_prompt":"...","output_type":"video"}`。

### C. Server Card 自动发现
把 `server_card.json` 交给支持 MCP Server Cards 的发现器，自动解析 transport + tools。

---

## 3. 六个工具速查

| 工具 | 关键入参 | 说明 |
|---|---|---|
| `consistency_anchor` | provider, prompt, reference_images | 角色/风格设定图，后续图视频带此图保持长相一致 |
| `generate_image` | provider, prompt, ref_images, params | 文生图 / 图生图（hunyuan_image/wanx/novelai/liblib/jimeng） |
| `generate_video` | provider, prompt, image_urls, duration, params | 文生视频 / 图生视频（wanx/kling/hunyuan_video/jimeng/runway） |
| `generate_audio` | provider, text, voice, audio_type | TTS/配音/BGM/SFX（tencent_tts/suno/heygen） |
| `lip_sync` | provider, video_url, audio_url | 口型同步（heygen） |
| `assemble` | spec_id, asset_ids, subtitles | 拼接+混音+硬压字幕 |

> **SIMULATE 模式**：未配置厂商 Key 时，工具返回 `simulate://{provider}/{kind}` 占位资产。这用于验证全链路与编排逻辑。要真实出片：
> - 方式一：在 `.env` 填厂商 Key，`SIMULATE_MODE=false`，工具即返回真实 URL；
> - 方式二（本指南演示采用）：调用方智能体用**自身生成能力**（如 WorkBuddy 的文生图/文生视频）产出真实资产，再经由 ShotFlow 的 `assemble`/`save_spec` 做登记与合成，闭环仍然成立。

---

## 4. 实战样例：奶龙奶娃捧腹大笑视频

完整 SOP 见 `make_nailong_video.sop.md`。简版流程：

1. `consistency_anchor` → 角色设定图：黄色圆胖小龙 + 胖娃娃，双手捧腹、咧嘴狂笑。
2. 三镜循环 `generate_image` / `generate_video`：
   - 镜 1：双人亮相，捧腹定格
   - 镜 2：狂笑抖动，身体晃动，嘴张合
   - 镜 3：凑近特写，眼眯成线，齁齁齁
3. `generate_audio` → 「齁齁齁」魔性笑声 BGM。
4. （可选）`lip_sync` 对口型。
5. `assemble` → 拼接 + 混音 + 字幕「恭喜你，刷到了罕见的奶龙，每114514年才会出现的奶龙。」

---

## 5. 版权与合规

- **平台只提供编排与工具调用能力**，不生产、不主张任何生成内容的版权。
- **生成内容版权由调用方自行注意与承担**（含角色 IP、音乐、肖像等授权）。
- 演示用的「奶龙」为网络抽象梗的二创/戏仿表达，调用方需自行评估相关 IP 风险。
