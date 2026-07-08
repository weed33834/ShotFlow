"""Phase 2 集成测试：YAML 工作流参数化 + Provider 评分接入派发。

覆盖本次接线的两个关键集成点：
  1. build_workflow 优先走 YAML 参数化注入
     - Wan22 工作流：frames->WanImageToVideo.length、fps->SaveAnimatedWEBP.fps、
       steps/cfg->KSampler、negative_prompt->CLIPTextEncode[1]、prompt/seed 注入
     - 缺省参数保持 JSON 原值（inject_params 只注入 params 中存在的 key）
     - 无 YAML 配置时回退到 _inject_params（仅注入 prompt+seed）
  2. _dispatch 在 extra 缺 provider 时按 complexity + settings.HAS_GPU 自动择优
     - standard+has_gpu -> wan_i2v（兼容原 test_dispatch_default_provider）
     - complex+has_gpu -> 评分择优（5 选 1）
     - 无 GPU -> 只能选云端 provider（kling/cogvideox）
     - 显式 provider 优先于自动选择
     - 自动选择写回 extra._provider_source="auto" 供追溯

SIMULATE_MODE 下所有 adapter 短路返回模拟结果，端到端可跑。
"""

import pytest
from app.services.comfyui_service import build_workflow

# ===== build_workflow: YAML 驱动注入 =====


def test_build_workflow_wan22_yaml_injection():
    """build_workflow(video_i2v) 走 YAML 参数化，注入 frames/fps/steps/cfg/负向提示词。

    覆盖修复点：原 YAML 中 frames 错指 EmptyHunyuanLatentVideo、fps 完全缺 targeting，
    导致这两个参数永不注入。修复后 frames->WanImageToVideo.length、fps->SaveAnimatedWEBP.fps。
    """
    wf = build_workflow(
        task_type="video_i2v",
        prompt="Ava walking through ruined city",
        seed=42,
        extra={
            "frames": 81,
            "fps": 16,
            "steps": 25,
            "cfg": 1.0,
            "negative_prompt": "blurry, low quality",
        },
    )
    # 正向提示词 -> 第一个 CLIPTextEncode（node 5）
    clip_nodes = [n for n in wf.values() if n.get("class_type") == "CLIPTextEncode"]
    assert clip_nodes[0]["inputs"]["text"] == "Ava walking through ruined city"
    # 负向提示词 -> 第二个 CLIPTextEncode（node 7）
    assert clip_nodes[1]["inputs"]["text"] == "blurry, low quality"
    # seed/steps/cfg -> KSampler（node 8）
    ksampler = next(n for n in wf.values() if n.get("class_type") == "KSampler")
    assert ksampler["inputs"]["seed"] == 42
    assert ksampler["inputs"]["steps"] == 25
    assert ksampler["inputs"]["cfg"] == 1.0
    # frames -> WanImageToVideo.length（node 6）—— 原 targeting bug 修复点
    wan = next(n for n in wf.values() if n.get("class_type") == "WanImageToVideo")
    assert wan["inputs"]["length"] == 81
    # fps -> SaveAnimatedWEBP.fps（node 10）—— 原 targeting 完全缺失，已补
    saver = next(n for n in wf.values() if n.get("class_type") == "SaveAnimatedWEBP")
    assert saver["inputs"]["fps"] == 16


def test_build_workflow_wan22_keeps_json_defaults_when_extra_missing():
    """extra 不提供可选参数时，build_workflow 仅注入 prompt+seed，其余保持 JSON 原值。

    inject_params 只注入 params 中存在的 key，未提供的参数保持工作流 JSON 原值。
    这保证了"只覆盖想改的参数"的预期行为。
    """
    wf = build_workflow(
        task_type="video_i2v",
        prompt="test prompt",
        seed=100,
        extra={},
    )
    ksampler = next(n for n in wf.values() if n.get("class_type") == "KSampler")
    assert ksampler["inputs"]["seed"] == 100
    # steps/cfg 未提供 -> 保持 JSON 原值
    assert ksampler["inputs"]["steps"] == 30
    assert ksampler["inputs"]["cfg"] == 0.5
    # frames 未提供 -> WanImageToVideo.length 保持原值 120
    wan = next(n for n in wf.values() if n.get("class_type") == "WanImageToVideo")
    assert wan["inputs"]["length"] == 120
    # fps 未提供 -> SaveAnimatedWEBP.fps 保持原值 24
    saver = next(n for n in wf.values() if n.get("class_type") == "SaveAnimatedWEBP")
    assert saver["inputs"]["fps"] == 24


def test_build_workflow_keyframe_flux_yaml_injection():
    """build_workflow(keyframe) 走 Flux YAML 参数化注入 steps/cfg/负向提示词。"""
    wf = build_workflow(
        task_type="keyframe",
        prompt="portrait of Ava",
        seed=7,
        extra={"steps": 20, "cfg": 7.0, "negative_prompt": "bad anatomy"},
    )
    ksampler = next(n for n in wf.values() if n.get("class_type") == "KSampler")
    assert ksampler["inputs"]["seed"] == 7
    assert ksampler["inputs"]["steps"] == 20
    assert ksampler["inputs"]["cfg"] == 7.0
    clip_nodes = [n for n in wf.values() if n.get("class_type") == "CLIPTextEncode"]
    assert clip_nodes[0]["inputs"]["text"] == "portrait of Ava"
    assert clip_nodes[1]["inputs"]["text"] == "bad anatomy"


def test_build_workflow_falls_back_when_no_yaml(monkeypatch):
    """task_type 无 YAML 配置时回退到 _inject_params（仅注入 prompt+seed）。

    回退路径不识别 extra 中的 steps/cfg 等参数，保持向后兼容。
    """
    monkeypatch.setattr(
        "app.services.workflow_config_service.get_workflow_by_task_type",
        lambda tt: None,
    )
    wf = build_workflow(
        task_type="video_i2v",
        prompt="fallback test",
        seed=999,
        extra={"steps": 50},  # 回退路径不注入 steps，应被忽略
    )
    ksampler = next(n for n in wf.values() if n.get("class_type") == "KSampler")
    assert ksampler["inputs"]["seed"] == 999
    # 回退路径不注入 steps -> 保持 JSON 原值 30
    assert ksampler["inputs"]["steps"] == 30


# ===== _dispatch: Provider 自动选择 =====


def _make_task(db_session, task_type="video_i2v", extra=None):
    from app.models.pipeline import RenderTask

    task = RenderTask(
        task_type=task_type,
        prompt="测试镜头",
        status="running",
        extra=extra or {},
    )
    db_session.add(task)
    db_session.commit()
    return task


def test_dispatch_auto_select_standard_with_gpu(db_session, monkeypatch):
    """extra 无 provider + HAS_GPU=True + complexity=standard -> 自动选 wan_i2v。

    兼容性验证：与原 test_dispatch_default_provider 行为一致，确保接线不破坏既有契约。
    """
    from app.core.config import settings
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", True)
    task = _make_task(db_session, extra={"seed": 1, "complexity": "standard"})
    result = _dispatch(db_session, task)
    assert result["status"] == "completed"
    assert "wan_i2v" in result["output_path"]


def test_dispatch_auto_select_complex_with_gpu(db_session, monkeypatch):
    """extra 无 provider + HAS_GPU=True + complexity=complex -> 评分择优（5 选 1）。

    不断言具体 provider（评分随权重变化），只断言落在 5 个候选之一，
    证明评分路径被实际调用而非硬编码 wan_i2v。
    """
    from app.core.config import settings
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", True)
    task = _make_task(db_session, extra={"seed": 2, "complexity": "complex"})
    result = _dispatch(db_session, task)
    assert result["status"] == "completed"
    all_providers = {"wan_i2v", "kling", "hunyuan_video", "ltx_video", "cogvideox"}
    assert any(p in result["output_path"] for p in all_providers), result["output_path"]


def test_dispatch_auto_select_no_gpu_picks_cloud_provider(db_session, monkeypatch):
    """extra 无 provider + HAS_GPU=False -> 只能选云端 provider（kling/cogvideox）。

    验证 HAS_GPU 开关生效：无 GPU 时本地 provider（wan_i2v/hunyuan_video/ltx_video）
    会被 recommend_provider 过滤掉，避免派发到本地 ComfyUI 后卡死。
    """
    from app.core.config import settings
    from app.services.provider_scorer import _PROVIDERS
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", False)
    task = _make_task(db_session, extra={"seed": 3, "complexity": "standard"})
    result = _dispatch(db_session, task)
    assert result["status"] == "completed"
    cloud_providers = [name for name, p in _PROVIDERS.items() if not p.requires_gpu]
    assert any(
        p in result["output_path"] for p in cloud_providers
    ), f"无 GPU 环境应选云端 provider {cloud_providers}，实际: {result['output_path']}"


def test_dispatch_explicit_provider_overrides_auto(db_session, monkeypatch):
    """extra.provider 显式指定时跳过自动选择。

    即使 HAS_GPU=False 且指定了 requires_gpu=True 的 provider，仍尊重显式选择
    （调用方需自行承担风险），证明显式优先于自动。
    """
    from app.core.config import settings
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", False)
    task = _make_task(
        db_session,
        extra={"seed": 4, "provider": "hunyuan_video"},  # hunyuan_video requires_gpu=True
    )
    result = _dispatch(db_session, task)
    assert result["status"] == "completed"
    assert "hunyuan" in result["output_path"]


def test_dispatch_auto_select_writes_provider_source(db_session, monkeypatch):
    """自动选择路径写回 extra._provider_source='auto' 供事后追溯。

    通过 spy 捕获 adapter.submit 收到的 extra，验证 provider 与 _provider_source 已写入。
    """
    from app.core.config import settings
    from app.services import provider_adapters
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", True)
    captured: dict = {}
    real_adapter = provider_adapters.get_adapter("wan_i2v")
    real_submit = real_adapter.submit

    def _spy_submit(task_type, prompt, seed, extra):
        captured["extra"] = dict(extra)
        return real_submit(task_type, prompt, seed, extra)

    monkeypatch.setattr(real_adapter, "submit", _spy_submit)

    task = _make_task(db_session, extra={"seed": 5})
    _dispatch(db_session, task)
    assert captured["extra"].get("_provider_source") == "auto"
    assert captured["extra"].get("provider") == "wan_i2v"


def test_dispatch_explicit_provider_does_not_write_source(db_session, monkeypatch):
    """显式 provider 路径不写 _provider_source（区分自动/手动选择）。"""
    from app.core.config import settings
    from app.services import provider_adapters
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", True)
    captured: dict = {}
    real_adapter = provider_adapters.get_adapter("hunyuan_video")
    real_submit = real_adapter.submit

    def _spy_submit(task_type, prompt, seed, extra):
        captured["extra"] = dict(extra)
        return real_submit(task_type, prompt, seed, extra)

    monkeypatch.setattr(real_adapter, "submit", _spy_submit)

    task = _make_task(db_session, extra={"seed": 6, "provider": "hunyuan_video"})
    _dispatch(db_session, task)
    assert "_provider_source" not in captured["extra"]
    assert captured["extra"].get("provider") == "hunyuan_video"


# ===== 深化 A: 自动选择 provider 后 extra 持久化到 DB =====


def test_dispatch_auto_select_persists_extra_to_db(db_session, monkeypatch):
    """自动选择路径把 provider + _provider_source 写回 task.extra 并落库。

    覆盖修复点：原实现只改局部变量 extra，未写回 task.extra，导致
    mark_completed 后自动选择的 provider 信息丢失，无法事后追溯。
    """
    from app.core.config import settings
    from app.models.pipeline import RenderTask
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", True)
    task = _make_task(db_session, extra={"seed": 11, "complexity": "standard"})
    _dispatch(db_session, task)

    # 重新从 DB 读取，验证 extra 已持久化（不是只改内存对象）
    db_session.expire_all()
    reloaded = db_session.get(RenderTask, task.id)
    assert reloaded.extra.get("provider") == "wan_i2v"
    assert reloaded.extra.get("_provider_source") == "auto"


def test_dispatch_explicit_provider_does_not_persist_source(db_session, monkeypatch):
    """显式 provider 路径不写 _provider_source 到 DB（区分自动/手动选择）。"""
    from app.core.config import settings
    from app.models.pipeline import RenderTask
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", True)
    task = _make_task(db_session, extra={"seed": 12, "provider": "hunyuan_video"})
    _dispatch(db_session, task)

    db_session.expire_all()
    reloaded = db_session.get(RenderTask, task.id)
    assert "_provider_source" not in reloaded.extra
    assert reloaded.extra.get("provider") == "hunyuan_video"


# ===== 深化 B: build_workflow 参数校验 =====


def test_build_workflow_validation_missing_required_prompt():
    """必填 prompt 缺失时 build_workflow 抛 ValueError（不送 ComfyUI）。"""
    with pytest.raises(ValueError, match="prompt"):
        build_workflow(
            task_type="video_i2v",
            prompt="",  # prompt 必填
            seed=1,
            extra={},
        )


def test_build_workflow_validation_out_of_range():
    """frames 超出 max 范围时 build_workflow 抛 ValueError。

    Wan22 YAML 定义 frames min=9 max=161，传 999 应被拦截。
    覆盖修复点：原 build_workflow 不校验，会把 length=999 注入到 ComfyUI，
    要等 GPU 跑完才失败。
    """
    with pytest.raises(ValueError, match="frames"):
        build_workflow(
            task_type="video_i2v",
            prompt="test",
            seed=1,
            extra={"frames": 999},  # 超过 max 161
        )


def test_build_workflow_validation_below_min():
    """frames 低于 min 范围时 build_workflow 抛 ValueError。"""
    with pytest.raises(ValueError, match="frames"):
        build_workflow(
            task_type="video_i2v",
            prompt="test",
            seed=1,
            extra={"frames": 1},  # 低于 min 9
        )


def test_build_workflow_validation_wrong_type():
    """steps 传字符串（应为 integer）时 build_workflow 抛 ValueError。"""
    with pytest.raises(ValueError, match="steps"):
        build_workflow(
            task_type="video_i2v",
            prompt="test",
            seed=1,
            extra={"steps": "not-a-number"},
        )


def test_build_workflow_validation_boundary_values_pass():
    """边界值（min/max）应通过校验，正常注入。"""
    wf = build_workflow(
        task_type="video_i2v",
        prompt="boundary test",
        seed=5,
        extra={"frames": 9, "fps": 8, "steps": 1, "cfg": 0.0},
    )
    wan = next(n for n in wf.values() if n.get("class_type") == "WanImageToVideo")
    assert wan["inputs"]["length"] == 9
    saver = next(n for n in wf.values() if n.get("class_type") == "SaveAnimatedWEBP")
    assert saver["inputs"]["fps"] == 8
    ksampler = next(n for n in wf.values() if n.get("class_type") == "KSampler")
    assert ksampler["inputs"]["steps"] == 1
    assert ksampler["inputs"]["cfg"] == 0.0


def test_build_workflow_validation_error_classified_non_retryable():
    """参数校验抛的 ValueError 被 classify_error 归为 invalid_prompt（不可重试）。

    验证错误分类契约：永久性参数错误不应触发重试，避免无谓消耗 GPU。
    """
    from app.services.queue_service import classify_error

    try:
        build_workflow(task_type="video_i2v", prompt="", seed=1, extra={})
        assert False, "应抛 ValueError"
    except ValueError as e:
        error_class, retryable = classify_error(e)
        assert error_class == "invalid_prompt"
        assert retryable is False


def test_build_workflow_fallback_path_skips_validation(monkeypatch):
    """回退路径（无 YAML 配置）不做校验，保持向后兼容。

    回退路径无参数规格可用，validate_params 无从校验，故不调用。
    """
    monkeypatch.setattr(
        "app.services.workflow_config_service.get_workflow_by_task_type",
        lambda tt: None,
    )
    # 即使传了"非法"的 steps（回退路径不识别），也不抛错
    wf = build_workflow(
        task_type="video_i2v",
        prompt="fallback",
        seed=999,
        extra={"steps": 99999},  # 回退路径不校验，应被忽略
    )
    ksampler = next(n for n in wf.values() if n.get("class_type") == "KSampler")
    assert ksampler["inputs"]["seed"] == 999
    assert ksampler["inputs"]["steps"] == 30  # JSON 原值


# ===== 深化 C: Provider 失败回退 =====


def test_dispatch_fallback_to_second_choice(db_session, monkeypatch):
    """自动选择路径首选(wan_i2v)失败时回退到次优(hunyuan_video)成功。

    覆盖回退逻辑：rank_providers 降序队列 wan_i2v > hunyuan_video > ...，
    patch wan_i2v.poll=failed 后应跳到 hunyuan_video 并成功。
    """
    from app.core.config import settings
    from app.services import provider_adapters
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", True)
    # 让首选 wan_i2v 失败
    wan_adapter = provider_adapters.get_adapter("wan_i2v")
    monkeypatch.setattr(wan_adapter, "poll", lambda job_id: "failed")

    task = _make_task(db_session, extra={"seed": 21, "complexity": "standard"})
    result = _dispatch(db_session, task)
    assert result["status"] == "completed"
    # 回退到次优 hunyuan_video
    assert "hunyuan" in result["output_path"]


def test_dispatch_fallback_writes_reason_to_db(db_session, monkeypatch):
    """回退发生时 extra._fallback_reason 落库供事后追溯。"""
    from app.core.config import settings
    from app.models.pipeline import RenderTask
    from app.services import provider_adapters
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", True)
    wan_adapter = provider_adapters.get_adapter("wan_i2v")
    monkeypatch.setattr(wan_adapter, "poll", lambda job_id: "failed")

    task = _make_task(db_session, extra={"seed": 22})
    _dispatch(db_session, task)

    db_session.expire_all()
    reloaded = db_session.get(RenderTask, task.id)
    assert reloaded.extra.get("_fallback_reason"), "应记录回退原因"
    assert "wan_i2v" in reloaded.extra["_fallback_reason"]
    assert "hunyuan" in reloaded.extra["_fallback_reason"]
    assert reloaded.extra.get("provider") == "hunyuan_video"


def test_dispatch_no_fallback_reason_when_first_succeeds(db_session, monkeypatch):
    """首选成功时不写 _fallback_reason（未发生回退）。"""
    from app.core.config import settings
    from app.models.pipeline import RenderTask
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", True)
    task = _make_task(db_session, extra={"seed": 23})
    _dispatch(db_session, task)

    db_session.expire_all()
    reloaded = db_session.get(RenderTask, task.id)
    assert "_fallback_reason" not in reloaded.extra
    assert reloaded.extra.get("provider") == "wan_i2v"


def test_dispatch_all_providers_fail_raises(db_session, monkeypatch):
    """所有候选 provider 都失败时抛 RuntimeError（交由 mark_failed 处理）。"""
    from app.core.config import settings
    from app.services import provider_adapters
    from app.services.provider_scorer import _PROVIDERS
    from app.tasks.render_tasks import _dispatch

    monkeypatch.setattr(settings, "HAS_GPU", True)
    # patch 全部 5 个 provider 的 poll 都失败（含云端，避免回退到云端成功）
    for name in _PROVIDERS:
        adapter = provider_adapters.get_adapter(name)
        monkeypatch.setattr(adapter, "poll", lambda job_id: "failed")

    task = _make_task(db_session, extra={"seed": 24})
    with pytest.raises(RuntimeError, match="所有 provider 均失败"):
        _dispatch(db_session, task)


def test_dispatch_explicit_provider_failure_does_not_fallback(db_session, monkeypatch):
    """显式 provider 失败时直接抛 RuntimeError，不回退到次优。

    契约：用户明确指定 provider，失败尊重用户选择不擅自换，
    交由上层 mark_failed 按错误分类决定是否重试。
    """
    from app.services import provider_adapters
    from app.tasks.render_tasks import _dispatch

    wan_adapter = provider_adapters.get_adapter("wan_i2v")
    monkeypatch.setattr(wan_adapter, "poll", lambda job_id: "failed")

    task = _make_task(db_session, extra={"seed": 25, "provider": "wan_i2v"})  # 显式指定
    with pytest.raises(RuntimeError, match="执行失败"):
        _dispatch(db_session, task)


def test_rank_providers_sorted_desc_by_score():
    """rank_providers 返回按分数降序的候选队列，has_gpu=True 时含本地 provider。"""
    from app.services.provider_scorer import rank_providers

    ranked = rank_providers(complexity="standard", has_gpu=True)
    names = [name for name, _ in ranked]
    # cogvideox 是占位 adapter（enabled=False），被 rank_providers 过滤，候选仅 4 个
    assert set(names) == {"wan_i2v", "kling", "hunyuan_video", "ltx_video"}
    # 降序：分数递减
    scores = [s for _, s in ranked]
    assert scores == sorted(scores, reverse=True)
    # wan_i2v 综合分最高（8.15），应排第一
    assert names[0] == "wan_i2v"


def test_rank_providers_filters_local_when_no_gpu():
    """rank_providers(has_gpu=False) 过滤掉 requires_gpu=True 的本地 provider。"""
    from app.services.provider_scorer import rank_providers

    ranked = rank_providers(has_gpu=False)
    names = [name for name, _ in ranked]
    # 仅云端且 enabled 的 provider：cogvideox 虽云端但 enabled=False（占位），被过滤
    assert set(names) == {"kling"}
    assert "wan_i2v" not in names  # 本地，被过滤
    assert "cogvideox" not in names  # 占位 adapter，被 enabled 过滤
