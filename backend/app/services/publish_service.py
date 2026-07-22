"""自动发布服务 — 将生成的视频发布到短视频平台。

支持平台：抖音、B站、小红书。
当前为 API 桩实现（stub），各平台需配置对应的 access_token / cookie 后才能真实发布。

设计参考 MoneyPrinterTurbo 的自动发布理念：生成完成后可选自动发布到平台。
MoneyPrinterTurbo 未实现此功能，ShotFlow 作为"工业化生产平台"率先补齐。
"""

import logging
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# 支持的平台列表
SUPPORTED_PLATFORMS = ["douyin", "bilibili", "xiaohongshu"]


class PublishError(Exception):
    """发布异常。"""


class PublishResult:
    """发布结果。"""

    def __init__(
        self,
        success: bool,
        platform: str,
        video_url: str = "",
        publish_id: str = "",
        error: str = "",
    ):
        self.success = success
        self.platform = platform
        self.video_url = video_url
        self.publish_id = publish_id
        self.error = error


def publish_video(
    video_path: str,
    platform: str,
    title: str = "",
    description: str = "",
    tags: list[str] | None = None,
    cover_path: str = "",
) -> PublishResult:
    """将视频发布到指定平台。

    Args:
        video_path: 本地视频文件路径
        platform: 平台名（douyin/bilibili/xiaohongshu）
        title: 视频标题
        description: 视频描述
        tags: 标签列表
        cover_path: 封面图路径（可选）
    Returns:
        PublishResult
    """
    if settings.SIMULATE_MODE:
        logger.info("[模拟] 发布视频到 %s: %s", platform, title)
        return PublishResult(
            success=True,
            platform=platform,
            video_url=f"simulate://publish/{platform}/{int(time.time())}",
            publish_id=f"sim_{platform}_{int(time.time())}",
        )

    if platform not in SUPPORTED_PLATFORMS:
        raise PublishError(f"不支持的平台: {platform}，支持: {SUPPORTED_PLATFORMS}")

    if not Path(video_path).exists():
        raise PublishError(f"视频文件不存在: {video_path}")

    # 各平台发布适配器
    if platform == "douyin":
        return _publish_douyin(video_path, title, description, tags, cover_path)
    elif platform == "bilibili":
        return _publish_bilibili(video_path, title, description, tags, cover_path)
    elif platform == "xiaohongshu":
        return _publish_xiaohongshu(video_path, title, description, tags, cover_path)
    else:
        raise PublishError(f"平台 {platform} 适配器未实现")


def _publish_douyin(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None,
    cover_path: str,
) -> PublishResult:
    """发布到抖音。

    抖音开放平台 API：需要 access_token + open_id。
    流程：上传视频 → 创建发布任务 → 轮询发布状态。
    """
    access_token = getattr(settings, "DOUYIN_ACCESS_TOKEN", "")
    if not access_token:
        return PublishResult(
            success=False, platform="douyin",
            error="DOUYIN_ACCESS_TOKEN 未配置，无法发布到抖音",
        )

    base_url = "https://open.douyin.com"
    headers = {"access-token": access_token, "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=300) as client:
            # 1. 上传视频
            with open(video_path, "rb") as f:
                upload_resp = client.post(
                    f"{base_url}/api/douyin/v1/video/upload_video/",
                    headers=headers,
                    files={"video": (Path(video_path).name, f)},
                )
            if upload_resp.status_code != 200:
                return PublishResult(False, "douyin", error=f"上传失败: {upload_resp.status_code}")
            video_data = upload_resp.json().get("data", {})
            video_id = video_data.get("video", {}).get("video_id", "")
            if not video_id:
                return PublishResult(False, "douyin", error="未返回 video_id")

            # 2. 创建发布任务
            body = {
                "video_id": video_id,
                "text": f"{title} {description} {' '.join(f'#{t}' for t in (tags or []))}",
            }
            publish_resp = client.post(
                f"{base_url}/api/douyin/v1/video/create_video/",
                headers=headers,
                json=body,
            )
            if publish_resp.status_code != 200:
                return PublishResult(False, "douyin", error=f"发布失败: {publish_resp.status_code}")
            pub_data = publish_resp.json().get("data", {})
            item_id = pub_data.get("item_id", "")

            return PublishResult(
                success=True, platform="douyin",
                publish_id=item_id,
                video_url=f"https://www.douyin.com/video/{item_id}" if item_id else "",
            )
    except httpx.HTTPError as exc:
        raise PublishError(f"抖音发布请求失败: {exc}") from exc


def _publish_bilibili(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None,
    cover_path: str,
) -> PublishResult:
    """发布到 B站。

    B站 API：需要 access_token（SESSDATA cookie 或 OAuth）。
    流程：预上传 → 上传分片 → 合并 → 提交发布。
    """
    sessdata = getattr(settings, "BILIBILI_SESSDATA", "")
    if not sessdata:
        return PublishResult(
            success=False, platform="bilibili",
            error="BILIBILI_SESSDATA 未配置，无法发布到B站",
        )

    base_url = "https://api.bilibili.com"
    headers = {"Cookie": f"SESSDATA={sessdata}"}
    tags_str = ",".join(tags or [])

    try:
        with httpx.Client(timeout=600) as client:
            # 1. 预上传
            file_size = Path(video_path).stat().st_size
            pre_resp = client.post(
                f"{base_url}/x/preupload",
                headers=headers,
                data={"name": Path(video_path).name, "size": file_size},
            )
            if pre_resp.status_code != 200:
                return PublishResult(False, "bilibili", error=f"预上传失败: {pre_resp.status_code}")
            pre_data = pre_resp.json().get("data", {})
            upload_url = pre_data.get("endpoint", "")
            biz_id = pre_data.get("biz_id", "")

            # 2. 上传（简化版，实际需分片上传）
            with open(video_path, "rb") as f:
                upload_resp = client.post(upload_url, files={"file": f})
            if upload_resp.status_code != 200:
                return PublishResult(False, "bilibili", error="视频上传失败")

            # 3. 提交发布
            body = {
                "title": title[:80],
                "desc": description,
                "tag": tags_str,
                "copyright": 1,  # 1=自制
            }
            pub_resp = client.post(
                f"{base_url}/x/vu/client/add",
                headers=headers,
                json=body,
            )
            if pub_resp.status_code != 200:
                return PublishResult(False, "bilibili", error=f"发布失败: {pub_resp.status_code}")
            pub_data = pub_resp.json().get("data", {})
            bvid = pub_data.get("bvid", "")

            return PublishResult(
                success=True, platform="bilibili",
                publish_id=bvid,
                video_url=f"https://www.bilibili.com/video/{bvid}" if bvid else "",
            )
    except httpx.HTTPError as exc:
        raise PublishError(f"B站发布请求失败: {exc}") from exc


def _publish_xiaohongshu(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None,
    cover_path: str,
) -> PublishResult:
    """发布到小红书（桩实现，需逆向 API 或官方开放平台接入）。"""
    return PublishResult(
        success=False, platform="xiaohongshu",
        error="小红书发布尚未实现，需接入官方开放平台 API",
    )


def get_publish_config() -> dict:
    """返回发布配置状态，供前端展示。"""
    return {
        "platforms": SUPPORTED_PLATFORMS,
        "douyin_configured": bool(getattr(settings, "DOUYIN_ACCESS_TOKEN", "")),
        "bilibili_configured": bool(getattr(settings, "BILIBILI_SESSDATA", "")),
        "xiaohongshu_configured": False,
    }
