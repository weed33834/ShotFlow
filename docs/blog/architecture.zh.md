# 构建 ShotFlow：一条 AIGC 短片流水线的架构经验

[English](./architecture.md) | 中文（当前）

> 从角色一致性到 Provider 回退——一个 AIGC 短片流水线背后的设计权衡。

ShotFlow 最早是一堆 ComfyUI JSON 和 shell 脚本，我们用它做了一部 3–5 分钟的科幻短片《奇点回响》（*Echo of the Singularity*）。后来它长成了一个 FastAPI + Celery + React 平台，让一个小团队能从浏览器跑完整条链——剧本 → 关键帧 → 视频 → 音频 → 后期 → 交付。这篇文章是工程复盘：哪些决策站住了，哪些我们会重做，以及为什么。

写给工程师，给工程师看。不堆营销词。选一个工具，就讲清楚我们为此放弃了什么。

---

## 1. 为什么做这件事

AIGC 视频在 demo 里看起来毫不费力。可一旦拉成一部完整短片，每次都撞上同一堵墙：

- **角色漂移。** 同一张脸在 shot 3 和 shot 15 里像两个不同的人。光靠 prompt 抓不住角色，得把参考图绑进流水线。
- **工具割裂。** 写剧本在一个聊天窗口，关键帧在 ComfyUI，视频在另一个，音频在第三个。没人看全局，素材永远对不齐。
- **不可复现。** 生成参数散落在 ComfyUI 各个节点里。一个好 take 换台机器就跑不出来，因为没人记得拧了哪些旋钮。

这些痛点我们在 [`AIGC_Experience_Chain.md`](../../AIGC_Experience_Chain.md) 里写过详细版。一句话总结：每一个"哇"的镜头背后都是看不见的人工返工，而返工之所以看不见，是因为没有任何东西被记录下来。

### 为什么是流水线，不是单体

一开始的诱惑是做一个大而全的单体应用。我们没这么干，原因有三：

1. **每个阶段的失败模式不同。** 关键帧失败在角色一致性，视频失败在闪烁和运动，音频失败在声线匹配。单体应用会强行把一套错误模型套到所有阶段上。
2. **每个阶段换工具很快。** 今天用 Wan2.2，明天可能上 HunyuanVideo。如果模型焊死在单体里，每次替换都是重写。
3. **团队是分专业的。** 一个人盯角色一致性，另一个人盯剪辑。流水线清晰的阶段边界能让他们并行不踩脚。

所以 ShotFlow 是一条由多个阶段组成的流水线，每个阶段有自己的 service、自己的错误处理、自己可替换的后端。平台层（FastAPI + Celery + Postgres + Redis）是粘合剂，生成逻辑住在下面的 service 里。

---

## 2. 流水线一览

一句话：**一句 idea 变成 4K 母版，途径是 剧本 → 关键帧 → 视频 → 音频 → 后期 → 交付，每个参数都落库，任何一帧都能复现。**

按阶段的技术栈：

| 阶段 | 工具 / 模型 | 作用 |
|-------|--------------|------|
| 编剧 | DeepSeek / Claude | 剧本、世界观、角色圣经 |
| 角色一致性 | Flux.1 Kontext + IPAdapter | on-model 关键帧 |
| 标准镜头 | Wan2.2 I2V 14B（本地） | 对白和近景的图生视频 |
| 复杂镜头 | Kling 2.5 Turbo（云端） | 关键帧到关键帧的运动镜头 |
| 剪辑 & 调色 | DaVinci Resolve | 剪辑 + 青橙调色 |
| 配音 | ElevenLabs | 角色对白 |
| 配乐 | Suno / Udio | 氛围配乐 |
| 放大 | Topaz Video AI | 4K + 降噪 |
| 流水线宿主 | ComfyUI | 节点式生成 |
| 后端 | FastAPI + SQLAlchemy + Celery | API、持久化、队列 |
| 前端 | React 18 + Vite + Ant Design Pro | 管理控制台 |

每个工具选择的完整理由在 [`AIGC_Experience_Chain.md`](../../AIGC_Experience_Chain.md)，流水线图在 [`README.md`](../../README.md)。

真正有意思的工程决策不在工具选择上——那些已经被讨论透了。有意思的是接下来要讲的四个：YAML 驱动的工作流参数化、Provider 评分与回退、带错误分类的队列状态机、以及 JWT + RBAC + SSE 推送模型。

---

## 3. 决策 1：YAML 驱动的工作流参数化

### 问题在哪

一个 ComfyUI 工作流是一张 JSON 节点图。生成一张关键帧，你得加载 `Flux_Character_Consistency_api.json`，找到 `CLIPTextEncode` 节点，把它的 `text` 输入设成 prompt，找到 `KSampler` 节点，设 `seed`、`steps`、`cfg`，再把整张图 POST 到 `/prompt`。每个镜头、每次 reroll 都来一遍。

这逻辑第一版是硬编码在 Python 里的：遍历节点字典，找 `class_type == "CLIPTextEncode"`，覆写 `inputs.text`。能用，但意味着每次调参——换个负向提示词、改个步数——都是改代码再重新部署。团队里非工程师的同事什么都调不了。

### 决策

我们把参数定义从 Python 里抽出来，放进一个 YAML 文件：[`03_Workflows/workflows.yaml`](../../03_Workflows/workflows.yaml)。每个工作流条目声明自己的参数，更重要的是声明*每个参数打到节点图的哪个位置*：

```yaml
- name: "Flux_Character_Consistency"
  task_type: "keyframe"
  file_path: "03_Workflows/api/Flux_Character_Consistency_api.json"
  parameters:
    - key: "prompt"
      type: "text"
      required: true
      node_class: "CLIPTextEncode"
      node_input: "text"
    - key: "negative_prompt"
      type: "text"
      default: "lowres, bad anatomy, extra fingers, deformed"
      node_class: "CLIPTextEncode"
      node_input: "text"
      node_index: 1   # 第二个 CLIPTextEncode 节点是负向
    - key: "steps"
      type: "integer"
      default: 28
      min: 1
      max: 100
      node_class: "KSampler"
      node_input: "steps"
```

加载器（[`workflow_config_service.py`](../../backend/app/services/workflow_config_service.py)）读一次，`inject_params` 遍历工作流 JSON，按 `node_class` + `node_input` + `node_index` 匹配每个参数。

### 权衡：用 class + input + index 定位节点

ComfyUI 节点跨版本没有稳定 ID，但有 `class_type`。问题是：怎么定位"第*二*个 `CLIPTextEncode`"——负向提示词节点——而不用脆弱的位置索引。

我们选了 `node_class` + `node_input` + `node_index`，其中 `node_index` 是该 class 在图里的匹配序号。不完美：有人在 ComfyUI 编辑器里重排节点，`node_index` 就可能悄悄指向错误节点。我们接受这一点，因为另一条路——按自定义字段给节点命名——得手工改每份工作流 JSON，而我们有很多。class + index 出错频率低到可以忍，而且读 YAML 就能 debug。

我们早期确实踩了个真 bug（见第 7 节）：最早的 `inject_params` 对负向提示词的 `node_index` 处理不对，负向把正向覆盖了。一半关键帧出图是错的，过了一个星期才有人发现。

### 回退路径

不是每个 `task_type` 都已经有 YAML 条目。与其直接报错，[`comfyui_service.build_workflow`](../../backend/app/services/comfyui_service.py) 走回退：

```python
def build_workflow(task_type, prompt, seed, extra):
    wf_config = get_workflow_by_task_type(task_type)
    if wf_config:
        params = {"prompt": prompt, "seed": seed, **(extra or {})}
        errors = validate_params(wf_config, params)
        if errors:
            raise ValueError(f"参数校验失败: {', '.join(errors)}")
        return inject_params(wf_config, params)
    # 回退：无 YAML 配置时仅注入 prompt + seed
    workflow = _load_workflow(task_type)
    return _inject_params(workflow, prompt, seed, extra)
```

某个 `task_type` 有 YAML 配置就走参数化路径；没有就回退到老的硬编码 `_inject_params`，只注入 prompt 和 seed。这让我们能一个一个地迁移工作流，互不影响。

### 为什么注入前要先 validate

YAML 路径在 `inject_params` *之前* 调 `validate_params`，失败时抛 `ValueError`，不是通用异常。这是故意的：队列的错误分类器（第 5 节）把 `ValueError` 归到 `invalid_prompt`，**不可重试**。一个坏参数——`steps: 999` 超过上限 100，或必填 prompt 缺失——重试也不会变好。提前校验能避免拿一个注定失败的请求去占 GPU 槽位。

这很重要，因为 GPU 时间是这套系统里最贵、最稀缺的资源。拿 5 分钟 4090 算力去跑一个 `cfg` 值就错的请求，比在校验阶段快速失败更糟。

---

## 4. 决策 2：Provider 评分 + 回退

### 问题在哪

视频生成有两类 provider，各有所长：

- **本地模型**（Wan2.2 I2V 14B、HunyuanVideo、LTX-Video）：单次调用零成本，完全可控，但需要 24GB GPU，复杂运镜偏弱。
- **云端 API**（Kling 2.5 Turbo、CogVideoX）：按次付费，无需本地 GPU，Kling 在关键帧到关键帧的连续性上明显更强。

一个标准对白近景应该走本地（便宜、可控）。一个推进穿越走廊的镜头应该给 Kling（能力）。当 provider 失败时，比起直接把整个任务判死，我们更愿意回退到次优。

### 决策：四维评分

[`provider_scorer.py`](../../backend/app/services/provider_scorer.py) 给每个 provider 打四个维度的分：

```python
@dataclass
class ProviderProfile:
    name: str
    quality: float      # 0-10
    speed: float        # 0-10，越大越快
    cost: float         # 0-10，越大越便宜
    capability: float   # 0-10，处理复杂镜头的能力
    supports_i2v: bool = True
    supports_t2v: bool = False
    requires_gpu: bool = True
```

总分是加权和：

```python
def score_provider(provider, weights):
    return (
        provider.quality * weights.quality
        + provider.speed * weights.speed
        + provider.cost * weights.cost
        + provider.capability * weights.capability
    )
```

默认权重是 `quality=0.4, speed=0.2, cost=0.25, capability=0.15`。我们偏向质量和成本——短片是看脸的，而我们有 GPU，本地几乎免费——capability 给得低，因为大多数镜头是标准镜头不是复杂镜头。这些数字是项目经验手调的，不是测出来的。我们诚实承认：它们是起点，权重可配。

### rank_providers：降序候选队列

`rank_providers` 返回按分数降序、按 `has_gpu` 过滤后的完整列表：

```python
def rank_providers(complexity="standard", weights=None, has_gpu=True):
    candidates = [p for p in _PROVIDERS.values() if has_gpu or not p.requires_gpu]
    scored = [(p.name, round(score_provider(p, weights), 2)) for p in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
```

派发循环消费的就是这条队列。第一个 provider 是最佳猜测；失败就试下一个，依此类推。

### 显式 vs 自动：契约不同

这是我们最满意的设计决策，因为它编码了一个真实的产品差异。在 [`render_tasks.py`](../../backend/app/tasks/render_tasks.py) 里，`_dispatch` 对 `extra.provider`（显式）和自动路径是完全不同的处理：

```python
if "provider" in extra:
    # 显式：用户点名要这个。失败直接抛，不回退。
    provider = extra["provider"]
    adapter = get_adapter(provider)
    job_id = adapter.submit(ttype, prompt, seed, extra)
    if adapter.poll(job_id) == "failed":
        raise RuntimeError(f"provider {provider} 任务 {job_id} 执行失败")
    return adapter.result(job_id)

# 自动：按评分队列，失败回退。
ranked = rank_providers(complexity=complexity, has_gpu=settings.HAS_GPU)
tried = []
for provider, _score in ranked:
    tried.append(provider)
    try:
        result = _run_provider_once(get_adapter(provider), ttype, prompt, seed, extra)
        if len(tried) > 1:
            extra = {**extra, "_fallback_reason": f"首选 {chosen} 失败，回退到 {provider}"}
        return result
    except ProviderFailed:
        continue
raise RuntimeError(f"所有 provider 均失败，已尝试 {tried}")
```

契约是：**你显式点名一个 provider，我们尊重。** 我们不会在背后偷偷把 Kling 换成 Wan2.2，因为你选 Kling 有理由——可能在测试，可能要它特定的运动风格。显式失败让你自己决定怎么办。你不指定，我们就优化并回退。

当回退*真的*发生时，我们把 `_fallback_reason` 写进 `extra`，留审计痕迹。你随时能查到某个镜头其实没跑在你以为的 provider 上。

### 回退异常收得很窄

注意只有 `ProviderFailed` 触发回退——它是 `adapter.poll` 返回 `"failed"` 时抛的异常。`get_adapter` 抛的 `ValueError`（未知 provider 名）或 `submit` 的网络错误**不**回退，直接上抛到 `mark_failed`。理由：poll 阶段的 "failed" 通常意味着 provider 处理不了这个输入但系统健康，换一个 provider 试是合理的；网络错误或未知 provider 意味着结构性问题，换每个 provider 都只会得到一堆一样的失败。

---

## 5. 决策 3：队列状态机 + 错误分类

### 状态机

每个渲染任务在 [`queue_service.py`](../../backend/app/services/queue_service.py) 里走一个小状态机：

```
pending -> running -> completed
                    -> failed   (retry_count < max_retry 且可重试时 => 回 pending)
任何状态 -> cancelled
```

状态存在 Postgres 里，不只是 Celery 里。这是整套系统里最重要的一个选择：**数据库是事实来源，Celery 只是执行器。** worker 崩了任务不会丢——它在 DB 里还是 `running`，恢复循环会捡起来。

### 为什么用应用层重试，不用 Celery autoretry

Celery 自带 `autoretry_for` 和重试参数。我们没用。[`render_tasks.py`](../../backend/app/tasks/render_tasks.py) 的 docstring 写得很清楚：

```python
@celery_app.task(
    name="render.run",
    bind=True,
    # P5: 去掉 autoretry_for，重试全由 mark_failed 控制，
    # 按错误分类决定 retryable，避免与 Celery 计数叠加产生语义混乱。
)
```

原因是双重计数。Celery 和应用层都重试就是一团乱：DB 里的 retry_count 和 Celery 内部计数对不上，两边都触发重试，你回答不了"这个任务到底重试了几次"这么简单的问题。单一来源——`mark_failed` 决定可重试性、自增 `retry_count`、重新 `delay`——数学就干净了。

重试决策在 `mark_failed` 里：

```python
if retryable and task.retry_count < task.max_retry:
    task.retry_count += 1
    task.status = "pending"
    db.commit()
    run_render_task.delay(task_id)   # 重新派发
else:
    task.status = "failed"
```

### 错误分类：不是所有错误都一样

`classify_error` 决定一个错误值不值得重试。永久性和暂时性错误在这里分道：

```python
def classify_error(exc):
    msg = str(exc).lower()
    # 永久性：重试也没用
    if isinstance(exc, (ValueError, KeyError, FileNotFoundError)):
        return "invalid_prompt", False
    if "api key" in msg or "unauthorized" in msg or "401" in msg or "403" in msg:
        return "auth", False
    if "not found" in msg and "workflow" in msg:
        return "invalid_prompt", False
    # 暂时性：超时、网络抖动、5xx
    if "timeout" in msg or "timed out" in msg:
        return "timeout", True
    if "connection" in msg or "502" in msg or "503" in msg or "504" in msg:
        return "timeout", True
    # 兜底：给一次机会
    return "unknown", True
```

分类对应行为：

- `invalid_prompt` / `auth`：永久。坏参数或缺 API key。重试白烧资源。直接 `failed`。
- `timeout` / 暂时性 5xx：可重试。云 provider 抽风了，再试一次。
- `unknown`：可重试，乐观处理。宁可多试一次，也不想误杀一个本来能成的任务。

这就是为什么 YAML 的 `validate_params` 抛 `ValueError`——它经 `classify_error` 路由到 `invalid_prompt` 桶，绝不浪费 GPU 周期。

### 崩溃恢复

worker 会崩。OOM、网络掉、机器重启。为了兜住，Celery 配置（[`celery_app.py`](../../backend/app/tasks/celery_app.py)）设了两个开关：

```python
task_acks_late=True,                  # 执行完才 ack
task_reject_on_worker_lost=True,      # 崩溃时任务重回队列
worker_prefetch_multiplier=1,         # 长任务一次只取一个，避免堆积
```

还有个 beat 任务每 60 秒跑一次 `recover_stuck_tasks`。它找心跳（`locked_at`）超过 `STUCK_TIMEOUT_SECONDS = 300` 的 `running` 任务，先 revoke 旧 Celery 任务（避免恢复的 worker 和新派发的 worker 抢同一个 task_id），再重置成 `pending` 重新派发：

```python
def recover_stuck_tasks(db):
    stuck = select(RenderTask).where(RenderTask.status == "running")
    for task in stuck:
        if not task.locked_at or _heartbeat_stale(task.locked_at):
            celery_app.control.revoke(task.celery_task_id, terminate=False)
            task.status = "pending"
            task.worker_id = ""
            task.locked_at = None
    # 只重新派发真正被回收的
```

先 revoke 再 reset 这个顺序很关键：不这么做可能两个 worker 跑同一个 `task_id`，那是双花 GPU、产出重复文件的捷径。

---

## 6. 决策 4：JWT + RBAC + SSE

### 为什么 SSE，不轮询

渲染队列是经典的推送场景。一个任务可能 `pending` 等十分钟，然后一秒内翻成 `running`。每 2 秒轮询要么猛敲服务器，要么慢半拍才注意到状态变化。Server-Sent Events 给我们廉价的服务端到浏览器单向推送，方向正好是我们需要的。

SSE 端点（[`queue.py`](../../backend/app/api/v1/queue.py)）很直接：

```python
@router.get("/stream/events")
async def stream_events(db=Depends(get_db), current=Depends(get_current_user_from_query)):
    async def event_generator():
        while True:
            stats = queue_stats(db)
            yield {"event": "stats", "data": json.dumps(stats)}
            await asyncio.sleep(2)
    return EventSourceResponse(event_generator())
```

现在每 2 秒推一次聚合 stats——粗粒度但简单。我们在代码里明确留了注释，之后可以升级成 Redis pub/sub 做单任务精准推送。粗粒度的"借 SSE 轮询"够发布，精准事件化是未来的优化。

### SSE 鉴权的坑

问题在这：浏览器 `EventSource` API **不能设自定义 header**。我们正常的鉴权流是 header 里带 `Authorization: Bearer <jwt>`。这对每个 fetch 调用都行，对 `EventSource` 不可能。两条路：单独发个短时 ticket，或者把 token 放 query string。

我们选了 query string，配一个专门的依赖：

```python
def get_current_user_from_query(
    db=Depends(get_db), token: str | None = Query(default=None)
) -> User:
    """SSE 专用：EventSource 不能设 header，token 只能放 query。
    和 header 路径共用同一套校验。"""
    return _resolve_user(db, token)
```

两条路径背后都是同一个 `_resolve_user`，校验完全一致。代价是 token 会进服务端 access log 和浏览器历史。对一个可信内网的管理控制台，这可以接受；对外网应用我们会换成短时 ticket。我们诚实承认这是个已知的妥协。

前端 hook（[`useQueueStream.ts`](../../frontend/src/hooks/useQueueStream.ts)）用指数退避重连：

```typescript
es.onerror = () => {
  setConnected(false);
  es.close();
  const delay = Math.min(1000 * 2 ** retryRef.current, 30000);
  retryRef.current += 1;
  timer = window.setTimeout(connect, delay);
};
```

封顶 30 秒，避免后端长时间抽风时退避出离谱的等待。

### RBAC：谁能动队列

不是每个登录用户都能提交或取消任务。队列的写端点——提交、重试、取消、改优先级——都过 `require_queue_write_role`：

```python
QUEUE_WRITE_ROLES = {"admin", "director", "algo_engineer", "video_operator", "ops", "pm"}

def require_queue_write_role(current: User = Depends(get_current_user)) -> User:
    if current.is_superuser or current.role in QUEUE_WRITE_ROLES:
        return current
    raise HTTPException(status_code=403, detail="当前角色无权操作渲染队列")
```

读端点（list、stats、status）只要 `get_current_user`。这个切分防止一个 viewer 误杀别人跑了 4 分钟的 render。JWT 管身份，RBAC 管授权，角色集合小而显式，容易审计。

### 前端选型

前端我们选了 TanStack Query 管服务端状态（缓存、重新拉取、mutation），Ant Design Pro 做布局和表格组件。TanStack Query 是因为队列 UI 本质上是一堆"会在你眼皮底下变化"的服务端状态行——正是它的甜区。Ant Design Pro 是因为管理控制台是内部工具，一个成熟的组件库比自己搭设计系统上得快，而且团队已经熟 antd。我们选它不是为了优雅，是为了速度。

---

## 7. 我们会重做的事

诚实反思，因为装作全对没人得益。

### YAML 节点定位 bug

最早的 `inject_params` 没正确处理 `node_index`。匹配器本该跳过第一个 `CLIPTextEncode`（正向提示词），把负向写到第二个。结果两个都写到了第一个，负向把正向覆盖了。出图的关键帧丢了真正的 prompt，只剩负向文本。上线一周才有人发现 prompt 看着不对。修复很小——正确累加 `matched` 计数——但教训是："看着显然"的图遍历代码需要一个断言*第二个*节点拿到值的测试，而不是断言*某个*节点拿到值。

### Provider 评分一开始没接进派发

`provider_scorer.py` 比回退循环更早存在。我们造了评分器，欣赏了分数，然后……派发代码还在调一个硬编码的 provider。评分是死代码，直到我们写了 `rank_providers` 和 `_dispatch` 的回退循环。教训是：没有消费者的评分函数只是规格，不是功能。我们应该在造评分器的同时把派发路径接上，或者干脆先别造评分器。

### `extra` 持久化 bug

`extra` 是 `RenderTask` 上的一个 JSON 列，装着 provider、complexity、回退原因、输出路径等等。早期派发代码在回退时原地改了 `extra`，但没总是提交更新。于是我们写来"留审计痕迹"的 `_fallback_reason` 有时根本没落库——恰好丢了它存在就是为了记的东西。修复是在写完 `extra` 后显式 `db.commit()`，但有一阵子审计痕迹是有洞的。JSON blob 列又方便又危险：很容易忘它不会自动 flush。

### 会重新考虑的几件事

- **粗粒度 SSE。** 没变化时每 2 秒推全量 stats 是浪费。Redis pub/sub 做单任务推送更干净，但基础设施更重。团队长大一点我们大概率会做。
- **手调的 provider 分数。** `quality=8.5` 这些数字是经验估计。我们想用实测的 PSNR/SSIM 或盲评胜率来支撑，但那是研究项目，不是工程任务。
- **`classify_error` 是字符串匹配。** 能用，但脆——provider 改个错误信息拼写就能把一个暂时性错误挪到 `unknown`。每个 adapter 给一个结构化错误契约会更好，已在清单上。

---

## 8. 结语

ShotFlow 不是产品。它是 AIGC 短片的脚手架——ComfyUI、云 API 和剪辑套件之间那种没人愿意写的无聊粘合剂。这篇文章里的四个决策（YAML 参数化、Provider 评分与回退、应用层队列状态机、JWT + RBAC + SSE）是我们愿意为之辩护的，第 7 节里的 bug 是我们会拿来提醒你的。

仓库是 [`ShotFlow`](../../README.md)，alpha 阶段，正在积极开发。示例短片《奇点回响》是一个完整案例，不是 demo 合集——从剧本到 EDL 的每个产物都在仓库里。如果你在做类似的事，拿一块走（角色一致性配置、渲染队列、YAML 配置）放进你自己的流水线。欢迎贡献——新的 ComfyUI 工作流、更好的 provider 评分、更干净的错误契约、翻译。见 [`CONTRIBUTING.md`](../../CONTRIBUTING.md)。

流水线的意义是让下一部片子比上一部更便宜。我们在试着把下一部做便宜，为我们自己，也为任何拿起这个项目的人。
