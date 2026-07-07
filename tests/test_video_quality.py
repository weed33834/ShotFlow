"""Tests for video_quality_check.py.

These tests mock ffprobe / opencv so they do not require real video files
or external binaries. They cover edge cases such as low resolution, heavy
flicker, blurry frames, and black/white frames.
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "08_Automation"))

import video_quality_check as vqc


@pytest.fixture(autouse=True)
def reset_thresholds():
    """Keep original thresholds so tests are independent."""
    original = vqc.THRESHOLDS.copy()
    yield
    vqc.THRESHOLDS.clear()
    vqc.THRESHOLDS.update(original)


@pytest.fixture
def mock_cv2():
    """Mock cv2 and numpy modules so check_video enters frame-analysis branch."""
    fake_cv2 = mock.MagicMock()
    fake_numpy = mock.MagicMock()
    with mock.patch.dict("sys.modules", {"cv2": fake_cv2, "numpy": fake_numpy}):
        yield fake_cv2


def make_ffprobe(width: int = 1280, height: int = 720, fps: float = 24.0, duration: float = 5.0):
    """Build a fake ffprobe dict matching run_ffprobe output."""
    return {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": width,
                "height": height,
                "avg_frame_rate": f"{int(fps * 1000)}/1000",
            }
        ],
        "format": {"duration": str(duration)},
    }


class TestAnalyzeFunctions:
    def test_analyze_sharpness_import_error_returns_negative(self):
        with mock.patch.dict("sys.modules", {"cv2": None}):
            assert vqc.analyze_sharpness("frame.png") == -1

    def test_analyze_brightness_import_error_returns_default(self):
        with mock.patch.dict("sys.modules", {"cv2": None}):
            mean, is_black, is_white = vqc.analyze_brightness("frame.png")
            assert mean == 128
            assert is_black is False
            assert is_white is False

    def test_analyze_flicker_too_few_frames(self):
        assert vqc.analyze_flicker([]) == 0
        assert vqc.analyze_flicker(["one.png"]) == 0


@pytest.mark.usefixtures("mock_cv2")
class TestCheckVideo:
    def test_check_video_passes(self, tmp_path):
        video = tmp_path / "good.mp4"
        video.write_text("dummy")

        with (
            mock.patch.object(vqc, "run_ffprobe", return_value=make_ffprobe()),
            mock.patch("video_quality_check.extract_frames", return_value=["f1.png", "f2.png"]),
            mock.patch("video_quality_check.analyze_sharpness", return_value=200.0),
            mock.patch(
                "video_quality_check.analyze_brightness", return_value=(128.0, False, False)
            ),
            mock.patch("video_quality_check.analyze_flicker", return_value=10.0),
            mock.patch("os.remove"),
        ):
            result = vqc.check_video(str(video), str(tmp_path / "temp"))

        assert result["score"] == 100
        assert result["issues"] == []
        assert result["resolution"] == "1280x720"
        assert result["fps"] == 24.0

    def test_check_video_low_resolution(self, tmp_path):
        video = tmp_path / "lowres.mp4"
        video.write_text("dummy")

        with (
            mock.patch.object(vqc, "run_ffprobe", return_value=make_ffprobe(height=480)),
            mock.patch("video_quality_check.extract_frames", return_value=[]),
        ):
            result = vqc.check_video(str(video), str(tmp_path / "temp"))

        assert any("分辨率" in issue for issue in result["issues"])
        assert result["score"] == 80

    def test_check_video_wrong_fps(self, tmp_path):
        video = tmp_path / "30fps.mp4"
        video.write_text("dummy")

        with (
            mock.patch.object(vqc, "run_ffprobe", return_value=make_ffprobe(fps=30.0)),
            mock.patch("video_quality_check.extract_frames", return_value=[]),
        ):
            result = vqc.check_video(str(video), str(tmp_path / "temp"))

        assert any("帧率" in issue for issue in result["issues"])
        assert result["score"] == 90

    def test_check_video_too_short(self, tmp_path):
        video = tmp_path / "short.mp4"
        video.write_text("dummy")

        with (
            mock.patch.object(vqc, "run_ffprobe", return_value=make_ffprobe(duration=1.0)),
            mock.patch("video_quality_check.extract_frames", return_value=[]),
        ):
            result = vqc.check_video(str(video), str(tmp_path / "temp"))

        assert any("时长" in issue for issue in result["issues"])
        assert result["score"] == 85

    def test_check_video_black_frames(self, tmp_path):
        video = tmp_path / "black.mp4"
        video.write_text("dummy")

        with (
            mock.patch.object(vqc, "run_ffprobe", return_value=make_ffprobe()),
            mock.patch(
                "video_quality_check.extract_frames", return_value=["f1.png", "f2.png", "f3.png"]
            ),
            mock.patch("video_quality_check.analyze_sharpness", return_value=200.0),
            mock.patch(
                "video_quality_check.analyze_brightness",
                return_value=(5.0, True, False),
            ),
            mock.patch("video_quality_check.analyze_flicker", return_value=10.0),
            mock.patch("os.remove"),
        ):
            result = vqc.check_video(str(video), str(tmp_path / "temp"))

        assert any("黑帧" in issue for issue in result["issues"])
        assert result["score"] == 80

    def test_check_video_white_frames(self, tmp_path):
        video = tmp_path / "white.mp4"
        video.write_text("dummy")

        with (
            mock.patch.object(vqc, "run_ffprobe", return_value=make_ffprobe()),
            mock.patch("video_quality_check.extract_frames", return_value=["f1.png", "f2.png"]),
            mock.patch("video_quality_check.analyze_sharpness", return_value=200.0),
            mock.patch(
                "video_quality_check.analyze_brightness",
                return_value=(250.0, False, True),
            ),
            mock.patch("video_quality_check.analyze_flicker", return_value=10.0),
            mock.patch("os.remove"),
        ):
            result = vqc.check_video(str(video), str(tmp_path / "temp"))

        assert any("白帧" in issue for issue in result["issues"])
        assert result["score"] == 80

    def test_check_video_blurry(self, tmp_path):
        video = tmp_path / "blurry.mp4"
        video.write_text("dummy")

        with (
            mock.patch.object(vqc, "run_ffprobe", return_value=make_ffprobe()),
            mock.patch("video_quality_check.extract_frames", return_value=["f1.png"]),
            mock.patch("video_quality_check.analyze_sharpness", return_value=50.0),
            mock.patch(
                "video_quality_check.analyze_brightness", return_value=(128.0, False, False)
            ),
            mock.patch("video_quality_check.analyze_flicker", return_value=10.0),
            mock.patch("os.remove"),
        ):
            result = vqc.check_video(str(video), str(tmp_path / "temp"))

        assert any("锐度" in issue for issue in result["issues"])
        assert result["score"] == 85

    def test_check_video_heavy_flicker(self, tmp_path):
        video = tmp_path / "flicker.mp4"
        video.write_text("dummy")

        with (
            mock.patch.object(vqc, "run_ffprobe", return_value=make_ffprobe()),
            mock.patch("video_quality_check.extract_frames", return_value=["f1.png", "f2.png"]),
            mock.patch("video_quality_check.analyze_sharpness", return_value=200.0),
            mock.patch(
                "video_quality_check.analyze_brightness", return_value=(128.0, False, False)
            ),
            mock.patch("video_quality_check.analyze_flicker", return_value=50.0),
            mock.patch("os.remove"),
        ):
            result = vqc.check_video(str(video), str(tmp_path / "temp"))

        assert any("闪烁" in issue for issue in result["issues"])
        assert result["score"] == 85

    def test_check_video_ffprobe_error(self, tmp_path):
        video = tmp_path / "broken.mp4"
        video.write_text("dummy")

        with mock.patch.object(vqc, "run_ffprobe", return_value={"error": "ffprobe not found"}):
            result = vqc.check_video(str(video), str(tmp_path / "temp"))

        assert result["score"] == 0
        assert any("无法读取" in issue for issue in result["issues"])

    def test_check_video_no_video_stream(self, tmp_path):
        video = tmp_path / "novideo.mp4"
        video.write_text("dummy")

        with mock.patch.object(
            vqc, "run_ffprobe", return_value={"streams": [{"codec_type": "audio"}]}
        ):
            result = vqc.check_video(str(video), str(tmp_path / "temp"))

        assert result["score"] == 0
        assert any("视频流" in issue for issue in result["issues"])


class TestRunFfprobe:
    def test_run_ffprobe_error_handling(self):
        with mock.patch(
            "subprocess.run",
            side_effect=FileNotFoundError("ffprobe not found"),
        ):
            result = vqc.run_ffprobe("/tmp/missing.mp4")
        assert "error" in result
