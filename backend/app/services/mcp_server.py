"""MCP Server：将 ShotFlow 的生成能力暴露为标准 MCP 工具。

外部智能体（WorkBuddy / 腾讯元器 / 阿里百炼 / Dify）通过 MCP 协议零改造调用 ShotFlow 出片。
启动：在 backend 目录 `python -m app.services.mcp_server run`（FastMCP 提供 CLI）。
传输：默认 streamable-http / SSE，端口在 mcp 配置中指定。
"""

from app.db.session import SessionLocal
from app.schemas.spec import AssembleReq, ToolGenerateReq
from app.services import tools_service as svc
from fastmcp import FastMCP

mcp = FastMCP("ShotFlow")


def _db():
    return SessionLocal()


@mcp.tool
async def consistency_anchor(provider: str, prompt: str, reference_images: list[str] = None) -> dict:
    """生成角色/风格设定图（一致性锚点）。后续所有图/视频带此图可保持长相一致。

    Args:
        provider: 厂商名，如 hunyuan_image
        prompt: 角色/风格描述
        reference_images: 参考图 URL 列表（首张通常为空）
    """
    db = _db()
    try:
        req = ToolGenerateReq(provider=provider, kind="anchor", params={"prompt": prompt, "ref_images": reference_images or []})
        return (await svc.anchor(req, db)).model_dump()
    finally:
        db.close()


@mcp.tool
async def generate_image(provider: str, prompt: str, ref_images: list[str] = None, params: dict = None) -> dict:
    """文生图 / 图生图。

    Args:
        provider: 厂商名（hunyuan_image / wanx / novelai / liblib / jimeng）
        prompt: 画面描述
        ref_images: 参考图 URL（用于一致性）
        params: 额外参数（seed / size / style 等）
    """
    db = _db()
    try:
        p = {"prompt": prompt, "ref_images": ref_images or []}
        if params:
            p.update(params)
        req = ToolGenerateReq(provider=provider, kind="image", params=p)
        return (await svc.run_tool(req, db)).model_dump()
    finally:
        db.close()


@mcp.tool
async def generate_video(provider: str, prompt: str, image_urls: list[str] = None, duration: int = 5, params: dict = None) -> dict:
    """文生视频 / 图生视频。

    Args:
        provider: 厂商名（wanx / kling / hunyuan_video / jimeng / runway）
        prompt: 动态描述
        image_urls: 首帧/参考图 URL（图生视频）
        duration: 时长（秒）
        params: 额外参数（resolution / sound 等）
    """
    db = _db()
    try:
        p = {"prompt": prompt, "image_urls": image_urls or [], "duration": duration}
        if params:
            p.update(params)
        req = ToolGenerateReq(provider=provider, kind="video", params=p)
        return (await svc.run_tool(req, db)).model_dump()
    finally:
        db.close()


@mcp.tool
async def generate_audio(provider: str, text: str, voice: str = "child_cn", audio_type: str = "tts") -> dict:
    """TTS / 配音 / BGM / SFX。

    Args:
        provider: 厂商名（tencent_tts / suno / heygen）
        text: 文本（BGM 传描述）
        voice: 音色名
        audio_type: tts / bgm / sfx
    """
    db = _db()
    try:
        req = ToolGenerateReq(provider=provider, kind="audio", params={"text": text, "voice": voice, "audio_type": audio_type})
        return (await svc.run_tool(req, db)).model_dump()
    finally:
        db.close()


@mcp.tool
async def lip_sync(provider: str, video_url: str, audio_url: str) -> dict:
    """口型同步：让视频角色对口型。

    Args:
        provider: heygen 等
        video_url: 视频 URL
        audio_url: 音频 URL
    """
    db = _db()
    try:
        req = ToolGenerateReq(provider=provider, kind="lipsync", params={"video_url": video_url, "audio_url": audio_url})
        return (await svc.run_tool(req, db)).model_dump()
    finally:
        db.close()


@mcp.tool
async def assemble(spec_id: int = None, asset_ids: list[int] = None, subtitles: list[str] = None) -> dict:
    """组装成片：拼接多镜视频 + 混音 + 硬压字幕。

    Args:
        spec_id: 关联 Spec ID
        asset_ids: 参与组装的资产 ID 列表
        subtitles: 每镜字幕文本
    """
    db = _db()
    try:
        req = AssembleReq(spec_id=spec_id, asset_ids=asset_ids or [], subtitles=subtitles or [])
        return (await svc.assemble(req, db)).model_dump()
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
