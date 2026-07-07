# Building ShotFlow: Architecture Lessons from an AIGC Short-Film Pipeline

English (current) | [中文](./architecture.zh.md)

> From character consistency to provider fallback — the design trade-offs behind an AIGC short-film pipeline.

ShotFlow started as a pile of ComfyUI JSON files and shell scripts we used to make a 3–5 minute sci-fi short, *Echo of the Singularity*. It has since grown into a FastAPI + Celery + React platform that lets a small team run the whole chain — script → keyframe → video → audio → post → delivery — from a browser. This post is the engineering retrospective: which decisions paid off, which ones we'd redo, and why.

It is written by engineers, for engineers. No marketing. When we picked a tool, we say what we traded away.

---

## 1. Why we built it

AIGC video looks effortless in a demo. Stretch it to a finished short and the same walls appear every time:

- **Character drift.** The same face looks like a different person in shot 3 and shot 15. Prompts alone don't hold a character; you need reference images bound into the pipeline.
- **Tool fragmentation.** Writing happens in one chat window, keyframes in ComfyUI, video in another, audio in a third. Nobody has the full picture, and assets never line up.
- **Non-reproducibility.** Generation parameters are scattered across ComfyUI nodes. A good take can't be rerun on another machine because nobody knows which knobs were turned.

We wrote about these pain points in detail in [`AIGC_Experience_Chain.md`](../../AIGC_Experience_Chain.md). The short version: every "wow" clip is the tip of an iceberg of manual rework, and the rework is invisible because nothing is logged.

### Why a pipeline, not a monolith

The temptation was to build one big app that does everything. We didn't, for three reasons:

1. **Each stage has a different failure mode.** Keyframe generation fails on character consistency; video fails on flicker and motion; audio fails on voice match. A monolith forces one error model on all of them.
2. **Each stage swaps tools fast.** Wan2.2 today, maybe HunyuanVideo tomorrow. If the model is bolted into a monolith, every swap is a rewrite.
3. **Teams specialize.** One person owns character consistency, another owns the edit. A pipeline with clear stage boundaries lets them work in parallel without stepping on each other.

So ShotFlow is a pipeline of stages, each with its own service, its own error handling, and its own swappable backend. The platform layer (FastAPI + Celery + Postgres + Redis) is the glue; the generation logic lives in the services underneath.

---

## 2. The pipeline at a glance

One sentence: **a one-line idea becomes a 4K master by passing through script → keyframes → video → audio → post → delivery, with every parameter logged so any frame can be reproduced.**

The tech stack, per stage:

| Stage | Tool / Model | Role |
|-------|--------------|------|
| Writing | DeepSeek / Claude | Script, world, character bible |
| Character consistency | Flux.1 Kontext + IPAdapter | On-model keyframes |
| Standard shots | Wan2.2 I2V 14B (local) | Image-to-video for dialogue and close-ups |
| Complex shots | Kling 2.5 Turbo (cloud) | Keyframe-to-keyframe for movement |
| Edit & grade | DaVinci Resolve | Cut + Teal-&-Orange grade |
| Voice | ElevenLabs | Character dialogue |
| Music | Suno / Udio | Atmospheric score |
| Upscale | Topaz Video AI | 4K + denoise |
| Pipeline host | ComfyUI | Node-based generation |
| Backend | FastAPI + SQLAlchemy + Celery | API, persistence, queue |
| Frontend | React 18 + Vite + Ant Design Pro | Admin console |

The full reasoning for each tool choice is in [`AIGC_Experience_Chain.md`](../../AIGC_Experience_Chain.md). The pipeline diagram lives in [`README.md`](../../README.md).

The interesting engineering decisions are not the tool choices — those are well-trodden. The interesting decisions are the four we'll spend the rest of this post on: YAML-driven workflow parameterization, provider scoring with fallback, a queue state machine with error classification, and the JWT + RBAC + SSE push model.

---

## 3. Decision 1: YAML-driven workflow parameterization

### The problem

A ComfyUI workflow is a JSON graph of nodes. To generate a keyframe you load `Flux_Character_Consistency_api.json`, find the `CLIPTextEncode` node, set its `text` input to your prompt, find the `KSampler` node, set its `seed` and `steps` and `cfg`, then POST the whole thing to `/prompt`. Do this for every shot, every reroll.

The first version of this logic was hardcoded in Python: walk the node dict, look for `class_type == "CLIPTextEncode"`, overwrite `inputs.text`. It worked, but it meant every parameter tweak — a new negative prompt, a different step count — was a code change and a redeploy. Non-engineers on the team couldn't tune anything.

### The decision

We pulled the parameter definitions out of Python and into a YAML file: [`03_Workflows/workflows.yaml`](../../03_Workflows/workflows.yaml). Each workflow entry declares its parameters and, crucially, *where in the node graph each parameter goes*:

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
      node_index: 1   # the SECOND CLIPTextEncode node is the negative
    - key: "steps"
      type: "integer"
      default: 28
      min: 1
      max: 100
      node_class: "KSampler"
      node_input: "steps"
```

The loader ([`workflow_config_service.py`](../../backend/app/services/workflow_config_service.py)) reads this once and `inject_params` walks the workflow JSON, matching each parameter by `node_class` + `node_input` + `node_index`.

### The trade-off: targeting by class + input + index

ComfyUI nodes don't have stable IDs across versions, but they do have a `class_type`. The question was how to address "the *second* `CLIPTextEncode`" — the negative prompt — without brittle positional indexing.

We went with `node_class` + `node_input` + `node_index`, where `node_index` is the ordinal match of that class in the graph. It's not perfect: if someone reorders nodes in the ComfyUI editor, `node_index` can silently point at the wrong node. We accepted that because the alternative — naming nodes by a custom field — requires editing every workflow JSON by hand, and we have a lot of them. Class + index is wrong rarely enough to live with, and it's debuggable by reading the YAML.

We did hit a real bug here early on (more in section 7): the original `inject_params` didn't handle `node_index` correctly for the negative prompt, so the negative prompt was overwriting the positive one. Half the keyframes came out wrong before we noticed.

### The fallback path

Not every `task_type` has a YAML entry yet. Rather than fail hard, [`comfyui_service.build_workflow`](../../backend/app/services/comfyui_service.py) falls back:

```python
def build_workflow(task_type, prompt, seed, extra):
    wf_config = get_workflow_by_task_type(task_type)
    if wf_config:
        params = {"prompt": prompt, "seed": seed, **(extra or {})}
        errors = validate_params(wf_config, params)
        if errors:
            raise ValueError(f"参数校验失败: {', '.join(errors)}")
        return inject_params(wf_config, params)
    # fallback: no YAML config, inject only prompt + seed
    workflow = _load_workflow(task_type)
    return _inject_params(workflow, prompt, seed, extra)
```

If a `task_type` has YAML config, we take the parameterized path. If not, we fall back to the old hardcoded `_inject_params` that only sets prompt and seed. This let us migrate workflows one at a time without breaking the others.

### Why validate before injecting

The YAML path calls `validate_params` *before* `inject_params`, and on failure it raises `ValueError`, not a generic error. That's deliberate: the queue's error classifier (section 5) maps `ValueError` to `invalid_prompt`, which is **not retryable**. A malformed parameter — `steps: 999` when the max is 100, or a missing required prompt — won't get better on retry. Validating up front prevents us from burning a GPU slot on a request that's guaranteed to fail or produce garbage.

This matters because GPU time is the expensive, scarce resource in this system. Wasting 5 minutes of a 4090 on a bad `cfg` value is worse than failing fast at validation.

---

## 4. Decision 2: Provider scoring + fallback

### The problem

Video generation has two kinds of providers, and they're good at different things:

- **Local models** (Wan2.2 I2V 14B, HunyuanVideo, LTX-Video): zero per-call cost, full control, but need a 24GB GPU and are weaker on complex camera moves.
- **Cloud APIs** (Kling 2.5 Turbo, CogVideoX): cost money per call, no local GPU needed, and Kling is notably stronger on keyframe-to-keyframe continuity for complex shots.

A standard dialogue close-up should go local (cheap, controllable). A dolly-through-a-hallway shot should go to Kling (capability). And when a provider fails, we'd rather fall back to the next best than fail the whole job.

### The decision: four-dimension scoring

[`provider_scorer.py`](../../backend/app/services/provider_scorer.py) scores each provider on four axes:

```python
@dataclass
class ProviderProfile:
    name: str
    quality: float      # 0-10
    speed: float        # 0-10, higher is faster
    cost: float         # 0-10, higher is cheaper
    capability: float   # 0-10, handling complex shots
    supports_i2v: bool = True
    supports_t2v: bool = False
    requires_gpu: bool = True
```

The score is a weighted sum:

```python
def score_provider(provider, weights):
    return (
        provider.quality * weights.quality
        + provider.speed * weights.speed
        + provider.cost * weights.cost
        + provider.capability * weights.capability
    )
```

The default weights are `quality=0.4, speed=0.2, cost=0.25, capability=0.15`. We tilted toward quality and cost — a short film is judged on look, and we have a GPU so local is nearly free — while keeping capability low because most of our shots are standard, not complex. These numbers are hand-tuned from project experience, not measured. We're honest about that: they're starting points, and the weights are configurable.

### rank_providers: a descending candidate queue

`rank_providers` returns the full list of providers sorted by score, filtered by `has_gpu`:

```python
def rank_providers(complexity="standard", weights=None, has_gpu=True):
    candidates = [p for p in _PROVIDERS.values() if has_gpu or not p.requires_gpu]
    scored = [(p.name, round(score_provider(p, weights), 2)) for p in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
```

This queue is what the dispatch loop consumes. The first provider is the best guess; if it fails, the next one is tried, and so on.

### Explicit vs. automatic: a contract difference

This is the design decision we're most happy about, because it encodes a real product distinction. In [`render_tasks.py`](../../backend/app/tasks/render_tasks.py), the `_dispatch` function treats `extra.provider` (explicit) and the auto path completely differently:

```python
if "provider" in extra:
    # Explicit: user asked for this one. Fail hard, no fallback.
    provider = extra["provider"]
    adapter = get_adapter(provider)
    job_id = adapter.submit(ttype, prompt, seed, extra)
    if adapter.poll(job_id) == "failed":
        raise RuntimeError(f"provider {provider} 任务 {job_id} 执行失败")
    return adapter.result(job_id)

# Automatic: ranked queue, fall back on failure.
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

The contract: **if you explicitly name a provider, we respect that.** We don't silently swap Kling for Wan2.2 behind your back, because you picked Kling for a reason — maybe you're testing, maybe you need its specific motion style. Failing explicitly lets you decide what to do. If you leave it to us, we optimize and fall back.

When a fallback *does* happen, we write `_fallback_reason` into `extra` so there's an audit trail. You can always find out your shot didn't run on the provider you expected.

### The fallback exception is narrow

Note that only `ProviderFailed` triggers fallback — that's the exception raised when `adapter.poll` returns `"failed"`. A `ValueError` from `get_adapter` (unknown provider name) or a network error from `submit` does **not** fall back; it propagates up to `mark_failed`. The reasoning: a poll-time "failed" usually means the provider choked on the input but the system is healthy, so trying another provider is reasonable. A network error or unknown-provider error means something is structurally wrong, and trying every other provider will just produce a pile of identical failures.

---

## 5. Decision 3: Queue state machine + error classification

### The state machine

Every render task moves through a small state machine in [`queue_service.py`](../../backend/app/services/queue_service.py):

```
pending -> running -> completed
                    -> failed   (retry_count < max_retry AND retryable => back to pending)
any state -> cancelled
```

The states are stored in Postgres, not just in Celery. This is the single most important choice in the whole system: **the database is the source of truth, Celery is just the executor.** When a worker crashes, the task isn't lost — it's still `running` in the DB, and the recovery loop will pick it up.

### Why application-layer retry, not Celery autoretry

Celery has `autoretry_for` and retry kwargs built in. We don't use them. From the docstring of [`render_tasks.py`](../../backend/app/tasks/render_tasks.py):

```python
@celery_app.task(
    name="render.run",
    bind=True,
    # P5: removed autoretry_for. Retry is fully controlled by mark_failed,
    # decided by error class => retryable, to avoid double-counting with Celery.
)
```

The reason is double-counting. If both Celery and the application layer retry, you get a mess: the retry counter in the DB drifts from Celery's internal count, retries fire from both sides, and you can't answer the simple question "how many times has this task been retried?" With one source of truth — `mark_failed` decides retryability, increments `retry_count`, and re-`delay`s — the math is clean.

The retry decision lives in `mark_failed`:

```python
if retryable and task.retry_count < task.max_retry:
    task.retry_count += 1
    task.status = "pending"
    db.commit()
    run_render_task.delay(task_id)   # re-dispatch
else:
    task.status = "failed"
```

### Error classification: not all errors are equal

`classify_error` decides whether an error is worth retrying. This is where permanent and transient errors diverge:

```python
def classify_error(exc):
    msg = str(exc).lower()
    # Permanent: retrying won't help
    if isinstance(exc, (ValueError, KeyError, FileNotFoundError)):
        return "invalid_prompt", False
    if "api key" in msg or "unauthorized" in msg or "401" in msg or "403" in msg:
        return "auth", False
    if "not found" in msg and "workflow" in msg:
        return "invalid_prompt", False
    # Transient: timeouts, network blips, 5xx
    if "timeout" in msg or "timed out" in msg:
        return "timeout", True
    if "connection" in msg or "502" in msg or "503" in msg or "504" in msg:
        return "timeout", True
    # Unknown: give it one shot
    return "unknown", True
```

The categories map to behavior:

- `invalid_prompt` / `auth`: permanent. Bad parameters or missing API key. Retrying burns resources for nothing. Goes straight to `failed`.
- `timeout` / transient 5xx: retryable. The cloud provider had a blip; try again.
- `unknown`: retryable, optimistically. We'd rather over-retry once than kill a job that would have succeeded.

This is why the YAML `validate_params` raises `ValueError` — it routes through `classify_error` into the `invalid_prompt` bucket and never wastes a GPU cycle.

### Crash recovery

Workers crash. OOM, network drops, the machine reboots. To handle this, the Celery config ([`celery_app.py`](../../backend/app/tasks/celery_app.py)) sets two flags:

```python
task_acks_late=True,                  # ack only after completion
task_reject_on_worker_lost=True,      # on crash, task goes back to the queue
worker_prefetch_multiplier=1,         # long tasks: take one at a time
```

And a beat task runs `recover_stuck_tasks` every 60 seconds. It looks for `running` tasks whose heartbeat (`locked_at`) is stale past `STUCK_TIMEOUT_SECONDS = 300`, revokes the old Celery task (so a recovering worker doesn't race a fresh one), and resets the task to `pending` for re-dispatch:

```python
def recover_stuck_tasks(db):
    stuck = select(RenderTask).where(RenderTask.status == "running")
    for task in stuck:
        if not task.locked_at or _heartbeat_stale(task.locked_at):
            celery_app.control.revoke(task.celery_task_id, terminate=False)
            task.status = "pending"
            task.worker_id = ""
            task.locked_at = None
    # re-dispatch only the recovered ones
```

The revoke-before-reset ordering matters: without it, you can get two workers running the same `task_id`, which is a fine way to double-spend GPU and produce duplicate outputs.

---

## 6. Decision 4: JWT + RBAC + SSE

### Why SSE, not polling

A render queue is a classic case for push. A job can sit `pending` for ten minutes and then flip to `running` in a second. Polling every 2 seconds means either hammering the server or being slow to notice state changes. Server-Sent Events give us cheap, one-way push from server to browser, which is exactly the direction we need.

The SSE endpoint ([`queue.py`](../../backend/app/api/v1/queue.py)) is straightforward:

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

Right now this pushes aggregate stats every 2 seconds — a coarse but simple design. We explicitly left a note in the code that this can be upgraded to Redis pub/sub for per-task pushes later. Coarse polling-via-SSE was enough to ship; precise eventing is a future optimization.

### The SSE auth wrinkle

Here's the catch: the browser's `EventSource` API **cannot set custom headers**. Our normal auth flow is `Authorization: Bearer <jwt>` in a header. That works for every fetch-based call but is impossible for `EventSource`. Two options: a separate short-lived ticket, or pass the token in the query string.

We went with the query string, with a dedicated dependency:

```python
def get_current_user_from_query(
    db=Depends(get_db), token: str | None = Query(default=None)
) -> User:
    """SSE-only: EventSource can't set headers, so token goes in query.
    Shares the same validation as the header path."""
    return _resolve_user(db, token)
```

The same `_resolve_user` backs both paths, so validation is identical. The trade-off is that the token ends up in server access logs and browser history. For an internal admin console on a trusted network, that's acceptable; for a public-facing app we'd switch to a short-lived ticket. We're honest that this is a known compromise.

The frontend hook ([`useQueueStream.ts`](../../frontend/src/hooks/useQueueStream.ts)) handles reconnect with exponential backoff:

```typescript
es.onerror = () => {
  setConnected(false);
  es.close();
  const delay = Math.min(1000 * 2 ** retryRef.current, 30000);
  retryRef.current += 1;
  timer = window.setTimeout(connect, delay);
};
```

Capped at 30 seconds, so a long backend blip doesn't spiral into absurd waits.

### RBAC: who can touch the queue

Not every logged-in user should be able to submit or cancel jobs. The queue's write endpoints — submit, retry, cancel, change priority — go through `require_queue_write_role`:

```python
QUEUE_WRITE_ROLES = {"admin", "director", "algo_engineer", "video_operator", "ops", "pm"}

def require_queue_write_role(current: User = Depends(get_current_user)) -> User:
    if current.is_superuser or current.role in QUEUE_WRITE_ROLES:
        return current
    raise HTTPException(status_code=403, detail="当前角色无权操作渲染队列")
```

Read endpoints (list, stats, status) just need `get_current_user`. This split prevents a viewer from accidentally killing someone else's 4-minute render. JWT handles identity; RBAC handles authorization; the role set is small and explicit so it's easy to audit.

### Frontend choices

On the frontend we picked TanStack Query for server state (caching, refetching, mutations) and Ant Design Pro for the layout and table components. TanStack Query because the queue UI is fundamentally a list of server-state rows that change underneath you — exactly its sweet spot. Ant Design Pro because the admin console is internal tooling where a polished component library ships faster than a bespoke design system, and the team already knew antd. We didn't pick it for elegance; we picked it for velocity.

---

## 7. What we'd do differently

Honest reflection, because pretending we got everything right helps no one.

### The YAML node-targeting bug

The early `inject_params` didn't correctly handle `node_index`. The matcher was supposed to skip the first `CLIPTextEncode` (positive prompt) and write the negative prompt to the second one. Instead, it wrote both to the first, so the negative prompt overwrote the positive. Keyframes came out missing their actual prompt and just had the negative text. We shipped that for a week before someone noticed the prompts looked wrong. The fix was small — track `matched` count properly — but the lesson was that "obvious" graph-walking code needs a test that asserts the *second* node got the value, not just that *some* node did.

### Provider scoring wasn't wired into dispatch at first

`provider_scorer.py` existed before the fallback loop did. We built the scorer, admired the scores, and then… the dispatch code still called a single hardcoded provider. The scoring was dead code until we wrote `rank_providers` and the `_dispatch` fallback loop. The lesson: a scoring function without a consumer is a spec, not a feature. We should have wired the dispatch path at the same time as the scorer, or not built the scorer yet.

### The `extra` persistence bug

`extra` is a JSON column on `RenderTask` that carries provider, complexity, fallback reason, output path, and more. Early on, the dispatch code mutated `extra` in place during fallback but didn't always commit the update. So the `_fallback_reason` we wrote to "preserve an audit trail" sometimes wasn't actually persisted — the very thing it existed to record. The fix was to explicitly `db.commit()` after writing `extra`, but for a while the audit trail had holes. JSON blob columns are convenient and dangerous: it's easy to forget they don't auto-flush.

### Things we'd reconsider

- **Coarse SSE.** Pushing all stats every 2s is wasteful when nothing changes. Redis pub/sub per-task would be cleaner, but it's more infrastructure. We'll likely do it once the team grows.
- **Hand-tuned provider scores.** The `quality=8.5` numbers are guesses from experience. We'd like to back them with measured PSNR/SSIM or blind-test win rates, but that's a research project, not an engineering task.
- **`classify_error` is string-matching.** It works, but it's fragile — a provider that changes its error message spelling can move a transient error into `unknown`. A structured error contract from each adapter would be better, and is on the list.

---

## 8. Conclusion

ShotFlow is not a product. It's scaffolding for AIGC short films — the boring glue between ComfyUI, cloud APIs, and an edit suite that nobody else seemed to want to write. The four decisions in this post (YAML parameterization, provider scoring with fallback, an application-layer queue state machine, and JWT + RBAC + SSE) are the ones we'd defend, and the bugs in section 7 are the ones we'd warn you about.

The repo is [`ShotFlow`](../../README.md), alpha and actively developed. The example film *Echo of the Singularity* is a worked case study, not a demo reel — every artifact from script to EDL is in the tree. If you're building something similar, grab a piece (the character-consistency setup, the render queue, the YAML config) and drop it into your own pipeline. Contributions welcome — new ComfyUI workflows, better provider scores, cleaner error contracts, translations. See [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

The point of a pipeline is that the next film is cheaper to make than the last one. We're trying to make the next one cheaper, for us and for anyone who picks this up.
