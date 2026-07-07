"""Provider 适配层测试 — SIMULATE_MODE 下验证统一接口与注册表。"""

import pytest
from app.services.provider_adapters import (
    available_providers,
    get_adapter,
)

# 全部已注册 provider
ALL_PROVIDERS = ["wan_i2v", "hunyuan_video", "ltx_video", "cogvideox", "kling"]

# 各 provider 模拟输出路径中应包含的可识别片段
PROVIDER_PATH_SUBSTR = {
    "wan_i2v": "wan_i2v",
    "hunyuan_video": "hunyuan",
    "ltx_video": "ltx",
    "cogvideox": "cogvideox",
    "kling": "kling",
}


def _extra_for(provider_name: str) -> dict:
    """kling 需要 shot_id，其余 provider 无特殊参数。"""
    return {"shot_id": "S01_04"} if provider_name == "kling" else {}


def test_get_adapter_returns_registered():
    """所有 5 个 provider 都能取到，且 name 属性一致。"""
    for name in ALL_PROVIDERS:
        adapter = get_adapter(name)
        assert adapter.name == name


def test_get_adapter_unknown_raises():
    """未知 provider 抛 ValueError。"""
    with pytest.raises(ValueError):
        get_adapter("unknown_provider")


def test_available_providers():
    """返回包含 5 个 provider。"""
    providers = available_providers()
    for name in ALL_PROVIDERS:
        assert name in providers


def test_wan_i2v_adapter_simulate():
    """SIMULATE_MODE 下 wan_i2v submit/poll/result 返回正确结构。"""
    adapter = get_adapter("wan_i2v")
    job_id = adapter.submit("video_i2v", "test", 1, {})
    assert job_id
    assert adapter.poll(job_id) == "completed"
    r = adapter.result(job_id)
    assert r["status"] == "completed"
    assert r["prompt_id"] == job_id
    assert r["output_path"]


def test_hunyuan_adapter_simulate():
    """SIMULATE_MODE 下 hunyuan_video submit/poll/result 返回正确结构。"""
    adapter = get_adapter("hunyuan_video")
    job_id = adapter.submit("video_i2v", "test", 2, {})
    assert job_id
    assert adapter.poll(job_id) == "completed"
    r = adapter.result(job_id)
    assert r["status"] == "completed"
    assert r["prompt_id"] == job_id
    assert r["output_path"]


def test_ltx_adapter_simulate():
    """SIMULATE_MODE 下 ltx_video submit/poll/result 返回正确结构。"""
    adapter = get_adapter("ltx_video")
    job_id = adapter.submit("video_i2v", "test", 3, {})
    assert job_id
    assert adapter.poll(job_id) == "completed"
    r = adapter.result(job_id)
    assert r["status"] == "completed"
    assert r["prompt_id"] == job_id
    assert r["output_path"]


def test_cogvideox_adapter_simulate():
    """SIMULATE_MODE 下 cogvideox submit/poll/result 返回正确结构（云端用 job_id 键）。"""
    adapter = get_adapter("cogvideox")
    job_id = adapter.submit("video_i2v", "test", 4, {})
    assert job_id
    assert adapter.poll(job_id) == "completed"
    r = adapter.result(job_id)
    assert r["status"] == "completed"
    assert r["job_id"] == job_id
    assert r["output_path"]


def test_kling_adapter_simulate():
    """SIMULATE_MODE 下 kling submit/poll/result 返回正确结构。"""
    adapter = get_adapter("kling")
    job_id = adapter.submit("video_i2v", "test", 5, {"shot_id": "S01_04"})
    assert job_id
    assert adapter.poll(job_id) == "completed"
    r = adapter.result(job_id)
    assert r["status"] == "completed"
    assert r["job_id"] == job_id
    assert r["output_path"]


@pytest.mark.parametrize("provider_name", ALL_PROVIDERS)
def test_adapter_output_path_pattern(provider_name):
    """各 adapter 模拟输出路径含 provider 名（可识别片段）。"""
    adapter = get_adapter(provider_name)
    job_id = adapter.submit("video_i2v", "test", 99, _extra_for(provider_name))
    result = adapter.result(job_id)
    expected = PROVIDER_PATH_SUBSTR[provider_name]
    assert (
        expected in result["output_path"]
    ), f"{provider_name} 输出路径未含 '{expected}': {result['output_path']}"
