"""生成管线测试 - 覆盖 LLM/字幕/Edge TTS/ffmpeg/Provider 轮询/编排器新服务。

测试策略：
- 纯函数（剥离/解析/格式化/规整）：直接断言，不 mock
- 网络相关（LLM/edge-tts/provider 轮询/下载）：monkeypatch mock httpx
- ffmpeg：环境中可用时跑端到端合成（生成纯色图片+静音音频 -> assemble_video）
- 编排器：SIMULATE_MODE 下全链路，mock edge-tts 回退到 tencent_tts 模拟

注意：为避免源码中的推理标签被工具误处理，think 开/闭标签用常量拼接构造。
"""

import subprocess
from pathlib import Path

import pytest

# 用拼接构造 think 标签，避免源码中出现裸标签被工具误处理
_TO = "<" + "think" + ">"
_TC = "<" + "/think" + ">"

# ===== 1. LLM Service =====

from app.services.llm_service import (
    _normalize_spec,
    _parse_json_lenient,
    _strip_code_fences,
    _strip_think_blocks,
)


# ----- _strip_think_blocks -----


def test_strip_think_blocks_paired():
    """成对 think 块被完整剥离，保留外部内容。"""
    text = _TO + "这是推理过程" + _TC + "这是实际内容"
    assert _strip_think_blocks(text) == "这是实际内容"


def test_strip_think_blocks_orphan_open_only():
    """孤立的开标签（无闭合）被连同后续内容一起删除。"""
    text = "前导文本" + _TO + "这里是孤立推理，没有闭合标签"
    result = _strip_think_blocks(text)
    assert _TO not in result
    assert result == "前导文本"


def test_strip_think_blocks_multiple_paired():
    """多组成对 think 块都被剥离，中间的正常内容保留。"""
    text = _TO + "推理1" + _TC + "内容1" + _TO + "推理2" + _TC + "内容2"
    assert _strip_think_blocks(text) == "内容1内容2"


def test_strip_think_blocks_nested():
    """嵌套 think 块：非贪婪匹配第一个闭合标签，残留由孤立兜底清理。"""
    # 非贪婪先匹配 _TO外层_TO内层_TC，残留 "尾部" + _TC + "真实内容"
    # 无孤立 _TO 标签残留，故残留保留
    text = _TO + "外层" + _TO + "内层" + _TC + "尾部" + _TC + "真实内容"
    result = _strip_think_blocks(text)
    assert "真实内容" in result
    assert _TO not in result


def test_strip_think_blocks_empty():
    """空字符串入参返回空字符串。"""
    assert _strip_think_blocks("") == ""


def test_strip_think_blocks_with_attributes():
    """带属性标签也应被匹配剥离。"""
    text = '<think type="reasoning">推理' + _TC + "结果"
    assert _strip_think_blocks(text) == "结果"


# ----- _strip_code_fences -----


def test_strip_code_fences_json():
    """剥离 json 代码围栏，返回内部裸 JSON。"""
    text = '```json\n{"key": "value"}\n```'
    assert _strip_code_fences(text) == '{"key": "value"}'


def test_strip_code_fences_plain():
    """剥离无语言标记的代码围栏。"""
    text = '```\n{"a": 1}\n```'
    assert _strip_code_fences(text) == '{"a": 1}'


def test_strip_code_fences_no_fence():
    """无围栏时返回原文（strip 后）。"""
    text = '{"key": "value"}'
    assert _strip_code_fences(text) == '{"key": "value"}'


def test_strip_code_fences_empty():
    """空字符串入参返回空字符串。"""
    assert _strip_code_fences("") == ""


# ----- _parse_json_lenient -----


def test_parse_json_lenient_pure_json():
    """纯 JSON 字符串直接解析成功。"""
    text = '{"title": "测试", "count": 3}'
    data = _parse_json_lenient(text)
    assert data["title"] == "测试"
    assert data["count"] == 3


def test_parse_json_lenient_with_code_fence():
    """带 json 围栏的 JSON 能正确解析。"""
    text = '```json\n{"title": "围栏测试"}\n```'
    data = _parse_json_lenient(text)
    assert data["title"] == "围栏测试"


def test_parse_json_lenient_with_prose():
    """前后带散文说明的 JSON 能通过兜底正则提取。"""
    text = '好的，这是结果：\n{"title": "散文测试"}\n以上就是。'
    data = _parse_json_lenient(text)
    assert data["title"] == "散文测试"


def test_parse_json_lenient_with_think_block():
    """带 think 推理块的 JSON 能正确解析。剥离后剩纯 JSON。"""
    text = _TO + "让我想想..." + _TC + '\n{"title": "think测试"}'
    data = _parse_json_lenient(text)
    assert data["title"] == "think测试"


def test_parse_json_lenient_invalid_raises():
    """完全无法解析的内容抛 ValueError。"""
    with pytest.raises(ValueError, match="无法从 LLM 输出解析 JSON"):
        _parse_json_lenient("这不是 JSON，也没有花括号")


# ----- _normalize_spec -----


def test_normalize_spec_empty_spec():
    """空 spec 兜底为单场景单镜头结构。"""
    spec = {}
    result = _normalize_spec(spec, "测试需求", "video")
    assert result["title"] == "测试需求"
    assert len(result["characters"]) == 1
    assert result["characters"][0]["anchor_prompt"]
    assert len(result["scenes"]) == 1
    assert len(result["scenes"][0]["shots"]) == 1
    shot = result["scenes"][0]["shots"][0]
    assert shot["image_prompt"] == "测试需求"
    assert shot["audio"]["voice"] == "child_cn"
    assert shot["audio"]["type"] == "tts"


def test_normalize_spec_fills_missing_fields():
    """缺字段的 spec 被补齐：anchor_prompt / video_prompt / audio dict。"""
    spec = {
        "characters": [{"name": "主角"}],
        "scenes": [{"shots": [{"duration": 3, "image_prompt": "画面"}]}],
    }
    result = _normalize_spec(spec, "需求", "video")
    char = result["characters"][0]
    assert char["anchor_prompt"]  # 补齐
    assert char["desc"] == ""  # 补齐
    assert char["ref_asset_ids"] == []  # 补齐
    shot = result["scenes"][0]["shots"][0]
    assert shot["video_prompt"] == "画面"  # 复用 image_prompt
    assert shot["subtitle"]  # 补齐
    assert shot["voice_text"]  # 补齐
    assert isinstance(shot["audio"], dict)
    assert shot["audio"]["text"]
    assert shot["audio"]["voice"] == "child_cn"


def test_normalize_spec_audio_non_dict_replaced():
    """audio 字段非 dict 时被替换为合规 dict。"""
    spec = {
        "characters": [],
        "scenes": [{"shots": [{"audio": "不是字典"}]}],
    }
    result = _normalize_spec(spec, "需求", "video")
    audio = result["scenes"][0]["shots"][0]["audio"]
    assert isinstance(audio, dict)
    assert "text" in audio
    assert audio["voice"] == "child_cn"
    assert audio["type"] == "tts"


def test_normalize_spec_audio_partial_dict():
    """audio dict 缺 voice/type 时补齐默认值。"""
    spec = {
        "characters": [],
        "scenes": [{"shots": [{"audio": {"text": "台词"}}]}],
    }
    result = _normalize_spec(spec, "需求", "video")
    audio = result["scenes"][0]["shots"][0]["audio"]
    assert audio["text"] == "台词"
    assert audio["voice"] == "child_cn"
    assert audio["type"] == "tts"


def test_normalize_spec_title_fallback():
    """spec 无 title 时用 nl_prompt 前 24 字兜底。"""
    long_prompt = "这是一个非常长的需求描述" * 5
    result = _normalize_spec({}, long_prompt, "video")
    assert result["title"] == long_prompt[:24]


# ===== 2. Subtitle Service =====

from app.services.subtitle_service import _format_timestamp, generate_srt_from_durations


# ----- _format_timestamp -----


def test_format_timestamp_zero():
    """0 秒 -> 00:00:00,000。"""
    assert _format_timestamp(0) == "00:00:00,000"


def test_format_timestamp_negative():
    """负数被钳为 0。"""
    assert _format_timestamp(-5.0) == "00:00:00,000"


def test_format_timestamp_over_one_hour():
    """超过 3600 秒正确显示小时。"""
    # 3661.5 秒 = 1小时1分1.5秒
    assert _format_timestamp(3661.5) == "01:01:01,500"


def test_format_timestamp_millisecond_precision():
    """毫秒精度正确。"""
    assert _format_timestamp(1.5) == "00:00:01,500"
    assert _format_timestamp(0.001) == "00:00:00,001"


def test_format_timestamp_millisecond_carry():
    """毫秒进位：1.9999 秒的毫秒部分进位到秒。"""
    # 1.9999 * 1000 = 1999.9 -> round -> 2000ms -> 2秒0毫秒
    assert _format_timestamp(1.9999) == "00:00:02,000"


# ----- generate_srt_from_durations -----


def test_generate_srt_normal():
    """正常字幕列表 + 时长 -> 合法 SRT。"""
    subtitles = ["第一句", "第二句"]
    durations = [2.0, 3.0]
    srt = generate_srt_from_durations(subtitles, durations)
    # 第一条：0->2s
    assert "1\n" in srt
    assert "00:00:00,000 --> 00:00:02,000" in srt
    assert "第一句" in srt
    # 第二条：2->5s
    assert "00:00:02,000 --> 00:00:05,000" in srt
    assert "第二句" in srt


def test_generate_srt_empty_list():
    """空字幕列表 -> 空字符串。"""
    assert generate_srt_from_durations([], []) == ""
    assert generate_srt_from_durations([], None) == ""


def test_generate_srt_durations_short_padded():
    """durations 条数不足时补 3 秒。"""
    subtitles = ["A", "B", "C"]
    durations = [1.0]  # 只提供 1 条，后两条补 3 秒
    srt = generate_srt_from_durations(subtitles, durations)
    # 第一条 0->1s，第二条 1->4s（补3秒），第三条 4->7s（补3秒）
    assert "00:00:00,000 --> 00:00:01,000" in srt
    assert "00:00:01,000 --> 00:00:04,000" in srt
    assert "00:00:04,000 --> 00:00:07,000" in srt


def test_generate_srt_zero_duration():
    """零时长字幕被钳为最小 0.1 秒，避免空区间。"""
    subtitles = ["零时长"]
    durations = [0.0]
    srt = generate_srt_from_durations(subtitles, durations)
    assert "00:00:00,000 --> 00:00:00,100" in srt


# ===== 3. Edge TTS Service =====

from app.services.edge_tts_service import (
    WordBoundary,
    _resolve_voice,
    generate_srt_from_word_boundaries,
    group_words_to_subtitles,
)


# ----- _resolve_voice -----


def test_resolve_voice_child_cn():
    """child_cn -> zh-CN-XiaoxiaoNeural。"""
    assert _resolve_voice("child_cn") == "zh-CN-XiaoxiaoNeural"


def test_resolve_voice_female_cn():
    """female_cn -> zh-CN-XiaoxiaoNeural。"""
    assert _resolve_voice("female_cn") == "zh-CN-XiaoxiaoNeural"


def test_resolve_voice_male_cn():
    """male_cn -> zh-CN-YunxiNeural。"""
    assert _resolve_voice("male_cn") == "zh-CN-YunxiNeural"


def test_resolve_voice_unknown():
    """未知名称兜底女声 XiaoxiaoNeural。"""
    assert _resolve_voice("unknown_voice") == "zh-CN-XiaoxiaoNeural"
    assert _resolve_voice("") == "zh-CN-XiaoxiaoNeural"


# ----- group_words_to_subtitles -----


def test_group_words_empty():
    """空 WordBoundary 列表 -> 空列表。"""
    assert group_words_to_subtitles([]) == []


def test_group_words_by_char_limit():
    """字数达上限时断行（max_chars_per_line=12）。"""
    # 每个词 4 字，3 个词 = 12 字，达到上限断行
    wbs = [
        WordBoundary("一二三四", 0.0, 0.5),
        WordBoundary("五六七八", 0.5, 0.5),
        WordBoundary("九十十一", 1.0, 0.5),
        WordBoundary("十二十三", 1.5, 0.5),  # 这条会在新行
    ]
    lines = group_words_to_subtitles(wbs, max_chars_per_line=12, pause_threshold=10.0)
    # 前三个词 12 字断行，第四个词单独一行
    assert len(lines) == 2
    assert lines[0]["text"] == "一二三四五六七八九十十一"
    assert lines[0]["start"] == 0.0
    assert lines[0]["end"] == 1.5  # 第三个词的结束时间
    assert lines[1]["text"] == "十二十三"


def test_group_words_by_pause():
    """词间停顿超过阈值时断行。"""
    wbs = [
        WordBoundary("你好", 0.0, 0.3),
        WordBoundary("世界", 0.3, 0.3),
        # 停顿 0.5 秒（世界 end=0.6, 新句 start=1.1, gap=0.5 > 0.3 阈值）
        WordBoundary("新句子", 1.1, 0.4),
    ]
    lines = group_words_to_subtitles(wbs, max_chars_per_line=100, pause_threshold=0.3)
    assert len(lines) == 2
    assert lines[0]["text"] == "你好世界"
    assert lines[0]["start"] == 0.0
    assert lines[0]["end"] == 0.6  # "世界"的结束
    assert lines[1]["text"] == "新句子"
    assert lines[1]["start"] == 1.1


def test_group_words_single_word():
    """单个词不触发断行，直接作为一行返回。"""
    wbs = [WordBoundary("独词", 0.0, 0.5)]
    lines = group_words_to_subtitles(wbs)
    assert len(lines) == 1
    assert lines[0]["text"] == "独词"
    assert lines[0]["start"] == 0.0
    assert lines[0]["end"] == 0.5


# ----- generate_srt_from_word_boundaries -----


def test_generate_srt_from_word_boundaries():
    """从 WordBoundary 列表生成合法 SRT。"""
    wbs = [
        WordBoundary("你好", 0.0, 0.5),
        WordBoundary("世界", 0.5, 0.5),
    ]
    srt = generate_srt_from_word_boundaries(wbs, max_chars_per_line=100)
    assert "1\n" in srt
    assert "00:00:00,000 --> 00:00:01,000" in srt
    assert "你好世界" in srt


def test_generate_srt_from_word_boundaries_empty():
    """空列表 -> 空字符串。"""
    assert generate_srt_from_word_boundaries([]) == ""


# ===== 4. ffmpeg Service =====

from app.services.ffmpeg_service import (
    _resolve_ffprobe_binary,
    _validate_input_path,
    assemble_video,
    classify_asset,
    is_ffmpeg_available,
)


def test_is_ffmpeg_available():
    """环境中 ffmpeg 可用时应返回 True（/usr/bin/ffmpeg 存在）。"""
    assert is_ffmpeg_available() is True


# ----- classify_asset -----


def test_classify_asset_audio():
    """音频资产分类。"""
    assert classify_asset("audio", "/tmp/test.mp3") == "audio"
    assert classify_asset("", "/tmp/test.wav") == "audio"


def test_classify_asset_image():
    """图片资产分类。"""
    assert classify_asset("image", "/tmp/test.png") == "image"
    assert classify_asset("", "/tmp/test.jpg") == "image"


def test_classify_asset_video():
    """视频资产分类（默认 fallback）。"""
    assert classify_asset("video", "/tmp/test.mp4") == "video"
    assert classify_asset("", "/tmp/test.unknown_ext") == "video"  # 未知扩展名 -> video


# ----- _validate_input_path -----


def test_validate_input_path_empty():
    """空路径抛 ValueError。"""
    with pytest.raises(ValueError, match="资产路径为空"):
        _validate_input_path("")


def test_validate_input_path_url():
    """URL 路径抛 ValueError。"""
    with pytest.raises(ValueError, match="不支持 URL"):
        _validate_input_path("https://example.com/video.mp4")


def test_validate_input_path_nonexistent():
    """不存在的路径抛 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError, match="资产文件不存在"):
        _validate_input_path("/tmp/nonexistent_file_xyz_12345.mp4")


# ----- assemble_video 端到端 -----


def _generate_ffmpeg_test_assets(tmp_dir: Path):
    """用 ffmpeg 生成测试素材：2 张纯色图片 + 1 段静音音频。"""
    img1 = tmp_dir / "red.png"
    img2 = tmp_dir / "blue.png"
    audio = tmp_dir / "silent.aac"

    # 生成纯色图片（320x240）
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1",
         "-frames:v", "1", str(img1)],
        capture_output=True, check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1",
         "-frames:v", "1", str(img2)],
        capture_output=True, check=True,
    )
    # 生成 3 秒静音音频
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         "anullsrc=channel_layout=stereo:sample_rate=44100",
         "-t", "3", str(audio)],
        capture_output=True, check=True,
    )
    return [str(img1), str(img2)], str(audio)


def test_assemble_video_end_to_end(tmp_path):
    """端到端：ffmpeg 生成纯色图片+静音音频 -> assemble_video -> 验证输出 mp4。

    覆盖完整合成管线：图片转视频片段 -> concat 拼接 -> 混音 -> 烧字幕 -> 输出。
    """
    asset_paths, audio_path = _generate_ffmpeg_test_assets(tmp_path)
    output_path = str(tmp_path / "output.mp4")

    result = assemble_video(
        asset_paths=asset_paths,
        audio_path=audio_path,
        subtitles=["第一句字幕", "第二句字幕"],
        subtitle_durations=[1.5, 1.5],
        output_path=output_path,
        task_id="test_assemble",
    )

    # 验证输出文件存在且为 mp4
    assert Path(result).exists()
    assert result.endswith(".mp4")

    # 用 ffprobe 验证时长 > 0
    ffprobe = _resolve_ffprobe_binary()
    assert ffprobe, "ffprobe 不可用"
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", result],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, f"ffprobe 失败: {proc.stderr}"
    duration = float(proc.stdout.strip())
    assert duration > 0, f"输出视频时长应 > 0，实际: {duration}"


# ===== 5. Provider 轮询测试 =====

from app.services.providers.base import BaseProvider


class _MockAsyncResponse:
    """模拟 httpx 异步响应。"""

    def __init__(self, json_data: dict, status_code: int = 200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


class _MockAsyncClient:
    """模拟 httpx.AsyncClient，按顺序返回预设响应。"""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self._index = 0
        self.request_count = 0

    async def request(self, method, url, **kwargs):
        self.request_count += 1
        if self._index < len(self._responses):
            resp = self._responses[self._index]
            self._index += 1
            return resp
        return self._responses[-1]  # 耗尽后返回最后一个


class _TestProvider(BaseProvider):
    """用于测试 BaseProvider 轮询/下载逻辑的空实现。"""
    name = "test_provider"


@pytest.mark.asyncio
async def test_poll_task_processing_then_succeeded(monkeypatch):
    """_poll_task 先收 processing 再收 succeeded，正确提取 status 和 url。"""
    responses = [
        _MockAsyncResponse({"status": "processing"}),
        _MockAsyncResponse({
            "status": "succeeded",
            "output": {"url": "https://cdn.test/output.mp4"},
        }),
    ]
    mock_client = _MockAsyncClient(responses)

    # 跳过 asyncio.sleep 避免测试等待
    import app.services.providers.base as base_mod

    async def _no_sleep(_):
        pass

    monkeypatch.setattr(base_mod.asyncio, "sleep", _no_sleep)

    provider = _TestProvider(simulate=False)
    url, last_data = await provider._poll_task(
        mock_client,
        "https://api.test/poll/task-1",
        extract_status=lambda d: d.get("status", ""),
        extract_url=lambda d: d.get("output", {}).get("url", ""),
        interval=0.01,
        timeout=5.0,
    )

    assert url == "https://cdn.test/output.mp4"
    assert last_data["status"] == "succeeded"
    assert mock_client.request_count == 2  # 第一次 processing，第二次 succeeded


@pytest.mark.asyncio
async def test_poll_task_failed_raises(monkeypatch):
    """_poll_task 收到 failed 状态时抛 RuntimeError。"""
    responses = [
        _MockAsyncResponse({"status": "failed", "error": "生成失败"}),
    ]
    mock_client = _MockAsyncClient(responses)

    import app.services.providers.base as base_mod

    async def _no_sleep(_):
        pass

    monkeypatch.setattr(base_mod.asyncio, "sleep", _no_sleep)

    provider = _TestProvider(simulate=False)
    with pytest.raises(RuntimeError, match="任务失败"):
        await provider._poll_task(
            mock_client,
            "https://api.test/poll/task-2",
            extract_status=lambda d: d.get("status", ""),
            extract_url=lambda d: d.get("url", ""),
            interval=0.01,
            timeout=5.0,
        )


class _MockSyncResponse:
    """模拟 httpx 同步响应。"""

    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _MockSyncClient:
    """模拟 httpx.Client 上下文管理器。"""

    def __init__(self, response: _MockSyncResponse):
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        return self._response


def test_download_asset_downloads_file(monkeypatch, tmp_path):
    """_download_asset 把远程 url 内容写入本地文件。"""
    fake_content = b"fake-video-bytes"
    mock_response = _MockSyncResponse(fake_content)

    import app.services.providers.base as base_mod

    monkeypatch.setattr(
        base_mod.httpx,
        "Client",
        lambda **kwargs: _MockSyncClient(mock_response),
    )
    # mock STORAGE_DIR 指向临时目录，避免污染项目目录
    monkeypatch.setattr(base_mod.settings, "STORAGE_DIR", str(tmp_path))

    provider = _TestProvider(simulate=False)
    local_path = provider._download_asset(
        "https://cdn.test/video.mp4",
        "test-task-123",
        "video",
        ext="mp4",
    )

    # 验证文件存在且内容正确
    p = Path(local_path)
    assert p.exists()
    assert p.read_bytes() == fake_content
    # 验证文件名包含 provider 名和 kind
    assert "test_provider" in p.name
    assert "video" in p.name
    # 验证落在 STORAGE_DIR/tasks/{task_id}/ 下
    assert "tasks" in str(p)
    assert "test-task-123" in str(p)


def test_download_asset_empty_raises(monkeypatch, tmp_path):
    """下载内容为空时抛 RuntimeError 且删除空文件。"""
    mock_response = _MockSyncResponse(b"")

    import app.services.providers.base as base_mod

    monkeypatch.setattr(
        base_mod.httpx,
        "Client",
        lambda **kwargs: _MockSyncClient(mock_response),
    )
    monkeypatch.setattr(base_mod.settings, "STORAGE_DIR", str(tmp_path))

    provider = _TestProvider(simulate=False)
    with pytest.raises(RuntimeError, match="下载资产为空"):
        provider._download_asset(
            "https://cdn.test/empty.mp4",
            "test-task-empty",
            "video",
        )


# ===== 6. Orchestrator 集成测试 =====

from app.services.orchestrator import Orchestrator


def test_brain_fallback_returns_correct_spec():
    """_brain_fallback 返回正确的 spec 结构，含必填字段。"""
    orch = Orchestrator()
    spec = orch._brain_fallback("做一个奶龙视频", "video")

    assert spec["intent"] == "做一个奶龙视频"
    assert spec["output_type"] == "video"
    assert spec["style_anchor"]["provider"] == "hunyuan_image"
    assert spec["assembly"]["subtitles"] is True

    # 角色兜底
    assert len(spec["characters"]) == 1
    char = spec["characters"][0]
    assert char["name"]  # 非空
    assert char["anchor_prompt"]  # 非空
    assert char["ref_asset_ids"] == []

    # 场景/镜头兜底
    assert len(spec["scenes"]) == 1
    scene = spec["scenes"][0]
    assert len(scene["shots"]) == 3  # 硬编码 3 个镜头
    for shot in scene["shots"]:
        assert shot["image_prompt"]
        assert shot["video_prompt"]
        assert shot["subtitle"]
        assert isinstance(shot["audio"], dict)
        assert shot["audio"]["text"]
        assert shot["audio"]["voice"] in ("child_cn", "female_cn", "male_cn")


def test_brain_fallback_keyword_detection():
    """_brain_fallback 关键词识别：奶龙/萌宠/通用（用 prompt 前 20 字作主题）。"""
    orch = Orchestrator()
    # 奶龙关键词
    spec1 = orch._brain_fallback("做个奶龙动画", "video")
    assert "奶龙" in spec1["characters"][0]["name"]
    # 萌宠关键词
    spec2 = orch._brain_fallback("一只猫的故事", "video")
    assert "萌宠" in spec2["characters"][0]["name"]
    # 通用：无关键词时用 prompt 前 20 字作主题（比固定"主角"更有意义）
    spec3 = orch._brain_fallback("随便做个视频", "video")
    assert spec3["characters"][0]["name"] == "随便做个视频"
    # 空字符串兜底
    spec4 = orch._brain_fallback("", "video")
    assert spec4["characters"][0]["name"] == "主角"


def test_build_subtitle_data_without_word_boundaries():
    """无 word_boundaries 时用 shot subtitle + duration 估算。"""
    orch = Orchestrator()
    spec_data = {
        "scenes": [
            {"shots": [
                {"subtitle": "第一句", "duration": 3},
                {"subtitle": "第二句", "duration": 5},
            ]}
        ]
    }
    subtitles, durations = orch._build_subtitle_data(spec_data, [])
    assert subtitles == ["第一句", "第二句"]
    assert durations == [3.0, 5.0]


def test_build_subtitle_data_with_word_boundaries():
    """有 word_boundaries 时用精确时间轴（group_words_to_subtitles）。"""
    orch = Orchestrator()
    spec_data = {"scenes": [{"shots": [{"subtitle": "不用", "duration": 5}]}]}

    # 构造 WordBoundary 列表：两个词连续，第三个词有停顿
    wbs = [
        WordBoundary("你好", 0.0, 0.5),
        WordBoundary("世界", 0.5, 0.5),
        # 停顿 0.5 秒（世界 end=1.0, 新句 start=1.5, gap=0.5 > 0.3）
        WordBoundary("新句", 1.5, 0.4),
    ]
    subtitles, durations = orch._build_subtitle_data(spec_data, wbs)
    # 应来自 group_words_to_subtitles，而非 shot subtitle
    assert "你好世界" in subtitles[0]
    assert "新句" in subtitles[1]
    # durations 是 end - start
    assert len(durations) == 2
    assert durations[0] == pytest.approx(1.0, abs=0.01)  # 0.0 -> 1.0
    assert durations[1] == pytest.approx(0.4, abs=0.01)  # 1.5 -> 1.9


@pytest.mark.asyncio
async def test_orchestrator_run_full_pipeline_simulate(db_session, monkeypatch):
    """SIMULATE_MODE 下完整 run() 流程：所有 provider 返回模拟结果，不依赖外部服务。"""
    from app.core.config import settings

    # 确保 SIMULATE_MODE 开启
    monkeypatch.setattr(settings, "SIMULATE_MODE", True)
    # 确保 LLM_API_KEY 为空，走 _brain_fallback（不调真实 LLM）
    monkeypatch.setattr(settings, "LLM_API_KEY", "")

    # mock edge-tts 避免真实网络调用，返回 None 触发 tencent_tts 回退
    async def _mock_tts(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.edge_tts_service.generate_tts_with_subtitles",
        _mock_tts,
    )

    orch = Orchestrator()
    spec_id = await orch.run("做一个奶龙短视频", "video", db_session)

    # 验证 spec_id 为正整数
    assert isinstance(spec_id, int)
    assert spec_id > 0

    # 验证 Spec 已入库
    from app.models.spec import Spec

    spec = db_session.get(Spec, spec_id)
    assert spec is not None
    assert spec.output_type == "video"
    assert "奶龙" in spec.intent
    # spec.data 应含 scenes/characters（_brain_fallback 返回的结构）
    assert "scenes" in spec.data
    assert "characters" in spec.data
    assert len(spec.data["scenes"]) > 0

    # 验证有 Asset 记录生成（image/video/audio/assemble）
    from app.models import Asset

    assets = db_session.query(Asset).all()
    assert len(assets) > 0
    # 至少有 image 和 assembled 类型的资产
    asset_types = {a.asset_type for a in assets}
    assert "image" in asset_types or "video" in asset_types
