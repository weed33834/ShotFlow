"""工具服务：调用 Provider 生成资产 + 组装成片。

这是 ShotFlow 暴露给外部智能体的「能力中台」核心实现。
所有 generate_* 在 SIMULATE_MODE 下返回占位资产（url=simulate://...），保证无 Key 跑通全链路。
"""

import time
from pathlib import Path

from app.core.config import settings
from app.models import Asset, GenerationTask, Spec
from app.services.providers import get_provider
from app.schemas.spec import AssembleReq, ToolGenerateReq, ToolResult

# 本地素材上传文件大小上限（100MB），防止占用过多磁盘/带宽
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
# 扩展名 → asset_type 映射，上传时按后缀自动归类
_EXT_ASSET_TYPE: dict[str, str] = {
    ".jpg": "image", ".jpeg": "image", ".png": "image",
    ".webp": "image", ".bmp": "image", ".gif": "image",
    ".mp4": "video", ".mov": "video", ".mkv": "video",
    ".avi": "video", ".webm": "video", ".flv": "video", ".m4v": "video",
    ".mp3": "audio", ".wav": "audio", ".aac": "audio",
    ".m4a": "audio", ".ogg": "audio", ".flac": "audio",
}


def _classify_by_extension(filename: str) -> str:
    """按文件名扩展名归类资产类型（image/video/audio）。

    上传文件没有 provider 提供的 kind 信息，只能用扩展名做兜底分类，
    与 ffmpeg_service.classify_asset 保持一致的后缀表。
    """
    ext = Path(filename).suffix.lower()
    if ext in _EXT_ASSET_TYPE:
        return _EXT_ASSET_TYPE[ext]
    # 未知扩展名默认按视频处理（assemble 时若实际是图片/音频由 classify_asset 再细分）
    return "video"


async def save_upload(file, asset_type_hint: str, db) -> ToolResult:
    """保存上传的本地素材文件并入库为 Asset。

    file: starlette UploadFile（FastAPI 注入）
    asset_type_hint: 前端传入的类型提示，空则按扩展名自动判断
    返回 ToolResult(asset_id, url=本地绝对路径, provider="upload", meta)
    """
    # 读取文件内容到内存（已限制 100MB，避免超大文件 OOM）
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"上传文件过大：{len(content)} bytes，上限 {MAX_UPLOAD_BYTES} bytes（100MB）"
        )

    # 时间戳前缀防止同名文件互相覆盖
    ts = int(time.time() * 1000)
    safe_name = Path(file.filename or "upload.bin").name
    upload_dir = Path(settings.STORAGE_DIR) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{ts}_{safe_name}"
    dest.write_bytes(content)

    asset_type = asset_type_hint or _classify_by_extension(safe_name)
    asset = Asset(
        asset_type=asset_type,
        path=str(dest),
        filename=safe_name,
        size_bytes=len(content),
        project_id=None,
        tags=["upload", asset_type],
        meta={
            "original_filename": safe_name,
            "size": len(content),
            "mime": file.content_type or "",
        },
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return ToolResult(
        asset_id=asset.id,
        url=str(dest),
        provider="upload",
        meta=asset.meta,
    )


def _provider_kwargs(provider: str) -> dict:
    """按 provider 名映射配置中的 Key。"""
    s = settings
    mapping = {
        "hunyuan_image": {"secret_id": s.TENCENT_SECRET_ID, "secret_key": s.TENCENT_SECRET_KEY},
        "hunyuan_video": {"secret_id": s.TENCENT_SECRET_ID, "secret_key": s.TENCENT_SECRET_KEY},
        "tencent_tts": {"secret_id": s.TENCENT_SECRET_ID, "secret_key": s.TENCENT_SECRET_KEY},
        "wanx": {"api_key": s.DASHSCOPE_API_KEY},
        "cosyvoice": {"api_key": s.DASHSCOPE_API_KEY, "base_url": "https://dashscope.aliyuncs.com/api/v1"},
        # GPT-SoVITS 为本地自建服务，无 api_key；base_url 由 GPTSOVITS_API_URL 注入
        "gptsovits": {"base_url": getattr(s, "GPTSOVITS_API_URL", "") or ""},
        "kling": {"api_key": s.KLING_API_KEY, "base_url": s.KLING_BASE_URL},
        "jimeng": {"api_key": s.JIMENG_API_KEY, "base_url": s.JIMENG_BASE_URL},
        "runway": {"api_key": s.RUNWAY_API_KEY},
        "heygen": {"api_key": s.HEYGEN_API_KEY},
        "suno": {"api_key": s.SUNO_API_KEY, "base_url": s.SUNO_BASE_URL},
        "liblib": {"api_key": s.LIBLIB_API_KEY},
        "novelai": {"api_key": s.NOVELAI_API_KEY},
    }
    return mapping.get(provider, {})


async def run_tool(req: ToolGenerateReq, db, tool: str = "generate", spec_id: int | None = None) -> ToolResult:
    """执行一次生成工具，存 GenerationTask + Asset，返回结果。"""
    provider = get_provider(req.provider, simulate=settings.SIMULATE_MODE, **_provider_kwargs(req.provider))
    # 记录任务
    task = GenerationTask(tool=tool, provider=req.provider, params=req.params, status="running", spec_id=spec_id)
    db.add(task)
    db.commit()
    db.refresh(task)

    result = await provider.generate(req.kind, req.params)

    # 存资产
    asset = Asset(
        asset_type=req.kind,
        path=result.url or f"simulate://{req.provider}/{req.kind}",
        filename=result.url.split("/")[-1] or f"{req.provider}_{req.kind}",
        project_id=None,
        tags=[req.provider, req.kind],
        meta=result.meta,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    task.status = "completed" if result.url else "failed"
    task.result_asset_id = asset.id
    db.commit()

    return ToolResult(asset_id=asset.id, url=result.url, provider=result.provider, meta=result.meta)


async def anchor(req: ToolGenerateReq, db, spec_id: int | None = None) -> ToolResult:
    """一致性锚定（角色/风格设定图）。"""
    return await run_tool(req, db, tool="consistency_anchor", spec_id=spec_id)


async def assemble(req: AssembleReq, db) -> ToolResult:
    """组装成片：ffmpeg 拼接 + 混音 + 硬压字幕（SIMULATE 返回占位）。"""
    task = GenerationTask(tool="assemble", provider="ffmpeg", params=req.model_dump(), status="running", spec_id=req.spec_id)
    db.add(task)
    db.commit()
    db.refresh(task)

    if settings.SIMULATE_MODE:
        asset = Asset(
            asset_type="video",
            path="simulate://ffmpeg/assemble",
            filename="assembled.mp4",
            project_id=req.spec_id,
            tags=["assemble", "simulate"],
            meta={"simulate": True, "asset_ids": req.asset_ids, "subtitles": req.subtitles},
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        task.status = "completed"
        task.result_asset_id = asset.id
        db.commit()
        return ToolResult(asset_id=asset.id, url=asset.path, provider="ffmpeg", meta=asset.meta)

    # 真实组装：用 ffmpeg 拼接 asset_ids 对应视频 + 混音 + 字幕硬压
    # 延迟导入避免无 ffmpeg 环境 import 报错（ffmpeg_service 自身不做 import 期检查）
    from pathlib import Path

    from app.services.ffmpeg_service import assemble_video, classify_asset, is_ffmpeg_available

    if not is_ffmpeg_available():
        msg = (
            "ffmpeg 不可用：未配置 FFMPEG_PATH 且 PATH 中未找到 ffmpeg。"
            "请安装 ffmpeg 或在 .env 中设置 FFMPEG_PATH，或开启 SIMULATE_MODE 走模拟流程。"
        )
        task.status = "failed"
        task.error = msg
        db.commit()
        raise RuntimeError(msg)

    # 查 asset_ids 对应的 Asset 记录，按请求顺序排列
    assets = db.query(Asset).filter(Asset.id.in_(req.asset_ids)).all()
    asset_map = {a.id: a for a in assets}
    ordered_assets = [asset_map[aid] for aid in req.asset_ids if aid in asset_map]

    if not ordered_assets:
        msg = f"未找到任何有效资产: asset_ids={req.asset_ids}"
        task.status = "failed"
        task.error = msg
        db.commit()
        raise ValueError(msg)

    # 按类型分类：video/image → 拼接素材，audio → 配音/BGM
    # 跳过 simulate:// 路径（失败的生成会返回占位路径）
    asset_paths: list[str] = []
    audio_candidates: list[str] = []
    for a in ordered_assets:
        if a.path and a.path.startswith("simulate://"):
            continue
        kind = classify_asset(a.asset_type, a.path)
        if kind == "audio":
            audio_candidates.append(a.path)
        else:
            asset_paths.append(a.path)

    # 第一个音频作配音，第二个作 BGM（AssembleReq 不区分，按顺序约定）
    # bgm_enabled=False 时不用第二个音频做 BGM
    audio_path = audio_candidates[0] if audio_candidates else ""
    bgm_path = audio_candidates[1] if (len(audio_candidates) > 1 and req.bgm_enabled) else ""

    if not asset_paths:
        msg = "没有可拼接的视频/图片资产（asset_ids 全为音频）"
        task.status = "failed"
        task.error = msg
        db.commit()
        raise ValueError(msg)

    # 输出路径：STORAGE_DIR/assembled/assemble_{task_id}.mp4
    output_dir = Path(settings.STORAGE_DIR) / "assembled"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / f"assemble_{task.id}.mp4")

    try:
        result_path = assemble_video(
        asset_paths=asset_paths,
        audio_path=audio_path,
        subtitles=req.subtitles,
        subtitle_durations=req.subtitle_durations or None,
        bgm_path=bgm_path,
        output_path=output_path,
        task_id=str(task.id),
        video_aspect=req.video_aspect,
        transition=getattr(req, "transition", ""),
        ken_burns=getattr(req, "ken_burns", True),
        color_grading=getattr(req, "color_grading", "none"),
    )
    except Exception as e:
        task.status = "failed"
        task.error = str(e)[:2000]
        db.commit()
        raise

    # 存成片为 Asset 记录
    asset = Asset(
        asset_type="video",
        path=result_path,
        filename=Path(result_path).name,
        project_id=req.spec_id,
        tags=["assemble", "ffmpeg"],
        meta={"asset_ids": req.asset_ids, "subtitles": req.subtitles},
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    task.status = "completed"
    task.result_asset_id = asset.id
    db.commit()
    return ToolResult(asset_id=asset.id, url=result_path, provider="ffmpeg", meta=asset.meta)


def save_spec(req, db) -> Spec:
    spec = Spec(
        project_id=req.project_id,
        output_type=req.output_type,
        intent=req.intent,
        data=req.data,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec
