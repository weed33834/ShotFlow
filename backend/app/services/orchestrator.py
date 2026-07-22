"""默认编排器：读 flow.sop + 脑补 Spec + 调工具出片（人用 UI 入口兜底）。

外部智能体（WorkBuddy / 元器 / 百炼 / Dify）跳过本编排器，直接读 flow.sop 调 /tools 路由自行执行。
本编排器让「人也能用」：有 LLM Key 时调 LLM 真实脑补分镜；无 Key 回退硬编码模板。
音频优先用 edge-tts（免费 + WordBoundary 精确字幕时间轴），失败回退 tencent_tts。
"""

import logging
from pathlib import Path

from app.core.config import settings
from app.models import Asset
from app.schemas.spec import AssembleReq, SpecSaveReq, ToolGenerateReq
from app.services import tools_service as svc
from app.services.llm_service import generate_script_spec

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Orchestrator:
    async def run(
        self,
        nl_prompt: str,
        output_type: str,
        db,
        project_id=None,
        *,
        video_aspect: str = "",
        voice_name: str = "",
        subtitle_enabled: bool = True,
        bgm_enabled: bool = True,
        local_asset_ids: list[int] | None = None,
    ) -> int:
        # 读流程文件（存在性校验，实际脑补见 _brain）
        flow_path = PROJECT_ROOT / "flows" / f"make_{output_type}.sop.md"
        if not flow_path.exists():
            raise ValueError(f"未找到流程文件: {flow_path}")

        # S1+S2 意图识别 + 需求脑补（有 LLM Key 调 LLM；无 Key 回退硬编码模板）
        spec_data = await self._brain(nl_prompt, output_type)

        # 用户前端选择的参数覆盖 spec 中的默认值
        # voice_name 非空时覆盖所有镜头的 audio.voice，让用户能控制配音声音
        if voice_name:
            for scene in spec_data.get("scenes", []):
                for shot in scene.get("shots", []):
                    if isinstance(shot.get("audio"), dict):
                        shot["audio"]["voice"] = voice_name

        spec = svc.save_spec(
            SpecSaveReq(
                project_id=project_id,
                output_type=output_type,
                intent=nl_prompt,
                data=spec_data,
            ),
            db,
        )

        # S3 一致性锚定
        anchor_result = await svc.anchor(
            ToolGenerateReq(
                provider="hunyuan_image",
                kind="anchor",
                params={"prompt": spec_data["characters"][0]["anchor_prompt"]},
            ),
            db,
            spec_id=spec.id,
        )

        # 收集所有生成的 asset_id，供 S5 组装使用
        asset_ids: list[int] = []
        video_asset_ids: list[int] = []  # 视频资产 ID（供 lip_sync 使用）
        audio_asset_ids: list[int] = []  # 音频资产 ID（供 lip_sync 使用）
        if anchor_result and anchor_result.asset_id:
            asset_ids.append(anchor_result.asset_id)

        # S4 逐镜生成（image + video + audio）
        # edge-tts 的 WordBoundary 跨镜头累积，用于精确字幕时间轴
        all_word_boundaries: list = []  # list[WordBoundary]，带跨镜头偏移
        _tts_time_offset = 0.0  # 已生成音频的累计时长，用于对齐后续镜头的字幕时间

        for scene in spec_data["scenes"]:
            for shot in scene["shots"]:
                img_result = await svc.run_tool(
                    ToolGenerateReq(
                        provider="hunyuan_image",
                        kind="image",
                        params={"prompt": shot["image_prompt"]},
                    ),
                    db,
                    spec_id=spec.id,
                )
                if img_result and img_result.asset_id:
                    asset_ids.append(img_result.asset_id)

                vid_result = await svc.run_tool(
                    ToolGenerateReq(
                        provider="wanx",
                        kind="video",
                        params={"prompt": shot["video_prompt"], "duration": shot.get("duration", 5)},
                    ),
                    db,
                    spec_id=spec.id,
                )
                if vid_result and vid_result.asset_id:
                    asset_ids.append(vid_result.asset_id)
                    video_asset_ids.append(vid_result.asset_id)

                # 音频生成：优先 edge-tts（带 WordBoundary 精确字幕），失败回退 tencent_tts
                audio_text = shot["audio"]["text"]
                audio_voice = shot["audio"]["voice"]
                _audio_ids_before = len(asset_ids)
                tts_wbs = await self._generate_audio(
                    audio_text, audio_voice, spec.id, db, asset_ids, _tts_time_offset,
                )
                # 记录新增的音频 asset_id（_generate_audio 可能追加 1 个）
                if len(asset_ids) > _audio_ids_before:
                    audio_asset_ids.append(asset_ids[-1])

                if tts_wbs is not None:
                    # edge-tts 成功：记录 WordBoundary（已带偏移），更新累计时长
                    all_word_boundaries.extend(tts_wbs)
                    _tts_time_offset += tts_wbs[-1].end if tts_wbs else 0.0
                else:
                    # 回退 tencent_tts：字幕时间轴用 shot duration 估算
                    _tts_time_offset += float(shot.get("duration", 5))

        # S4.5 可选口型同步（HeyGen），无 Key 或 SIMULATE 模式时静默跳过
        await self._try_lip_sync(video_asset_ids, audio_asset_ids, spec.id, db)

        # S5 组装成片
        # 有 edge-tts WordBoundary 时用精确时间轴，否则用 shot duration 估算
        # subtitle_enabled=False 时传空字幕列表，ffmpeg 跳过字幕烧录
        if subtitle_enabled:
            subtitles, subtitle_durations = self._build_subtitle_data(
                spec_data, all_word_boundaries
            )
        else:
            subtitles, subtitle_durations = [], []

        # bgm_enabled=True 时尝试生成 BGM（Suno），失败则静默跳过
        bgm_asset_id = None
        if bgm_enabled:
            bgm_asset_id = await self._generate_bgm(spec_data, spec.id, db)

        # 用户上传的本地素材追加到生成资产之后参与拼接/混音
        # 去重避免同一 asset_id 被重复拼接（用户可能误传已生成的 id）
        if local_asset_ids:
            for aid in local_asset_ids:
                if aid not in asset_ids:
                    asset_ids.append(aid)

        # 组装时传入 video_aspect 控制输出分辨率，bgm_enabled 控制是否混入 BGM
        await svc.assemble(
            AssembleReq(
                spec_id=spec.id,
                asset_ids=asset_ids,
                subtitles=subtitles,
                subtitle_durations=subtitle_durations,
                video_aspect=video_aspect,
                bgm_enabled=bgm_enabled,
            ),
            db,
        )
        return spec.id

    async def _generate_audio(
        self,
        text: str,
        voice: str,
        spec_id: int,
        db,
        asset_ids: list[int],
        time_offset: float,
    ) -> list | None:
        """生成配音音频，优先 edge-tts（带 WordBoundary），失败回退 tencent_tts。

        返回 edge-tts 的 WordBoundary 列表（已加 time_offset 偏移）；
        edge-tts 失败时回退 tencent_tts 并返回 None（字幕时间轴用估算）。
        """
        # 尝试 edge-tts（免费 + WordBoundary 精确字幕）
        try:
            from app.services.edge_tts_service import generate_tts_with_subtitles

            tts_result = await generate_tts_with_subtitles(text, voice)
            if tts_result and tts_result.word_boundaries:
                # 创建 Asset 记录（edge-tts 音频不在 provider 体系内，直接入库）
                asset = Asset(
                    asset_type="audio",
                    path=tts_result.audio_path,
                    filename=Path(tts_result.audio_path).name,
                    project_id=None,
                    tags=["edge_tts", "tts"],
                    meta={
                        "voice": voice,
                        "text": text,
                        "duration": tts_result.duration,
                        "engine": "edge_tts",
                    },
                )
                db.add(asset)
                db.commit()
                db.refresh(asset)
                asset_ids.append(asset.id)

                # WordBoundary 加偏移，使跨镜头字幕时间轴连续
                for wb in tts_result.word_boundaries:
                    wb.start += time_offset
                return tts_result.word_boundaries
        except Exception as exc:
            logger.warning("edge-tts 失败，回退 tencent_tts: %s", exc)

        # 回退 tencent_tts（走 provider 体系，无 WordBoundary）
        aud_result = await svc.run_tool(
            ToolGenerateReq(
                provider="tencent_tts",
                kind="audio",
                params={"text": text, "voice": voice},
            ),
            db,
            spec_id=spec_id,
        )
        if aud_result and aud_result.asset_id:
            asset_ids.append(aud_result.asset_id)
        return None

    async def _generate_bgm(self, spec_data: dict, spec_id: int, db) -> int | None:
        """尝试生成背景音乐（Suno），失败静默跳过。

        BGM 是可选增强，不应阻断主流程。无 SUNO_API_KEY 或 SIMULATE 模式时
        返回 None，assemble 时不传 BGM 轨。
        """
        try:
            bgm_result = await svc.run_tool(
                ToolGenerateReq(
                    provider="suno",
                    kind="audio",
                    params={
                        "prompt": f"为《{spec_data.get('title', '短片')}》生成背景音乐，轻快风格",
                        "kind": "music",
                    },
                ),
                db,
                spec_id=spec_id,
            )
            if bgm_result and bgm_result.asset_id:
                return bgm_result.asset_id
        except Exception as exc:
            logger.warning("BGM 生成失败（Suno），跳过: %s", exc)
        return None

    async def _try_lip_sync(
        self,
        video_asset_ids: list[int],
        audio_asset_ids: list[int],
        spec_id: int,
        db,
    ) -> None:
        """可选口型同步（HeyGen），无 Key 或失败时静默跳过。

        仅在 HEYGEN_API_KEY 已配置且非 SIMULATE 模式时尝试。
        lip_sync 是锦上添花功能，不阻断主流程。
        """
        if not settings.HEYGEN_API_KEY or settings.SIMULATE_MODE:
            return
        if not video_asset_ids or not audio_asset_ids:
            return
        try:
            await svc.run_tool(
                ToolGenerateReq(
                    provider="heygen",
                    kind="lipsync",
                    params={
                        "video_asset_id": video_asset_ids[-1],
                        "audio_asset_id": audio_asset_ids[-1],
                    },
                ),
                db,
                spec_id=spec_id,
            )
            logger.info("lip_sync 完成 (HeyGen)")
        except Exception as exc:
            logger.warning("lip_sync 失败（HeyGen），跳过: %s", exc)

    def _build_subtitle_data(
        self,
        spec_data: dict,
        word_boundaries: list,
    ) -> tuple[list[str], list[float]]:
        """构建字幕文本列表 + 时长列表。

        有 edge-tts WordBoundary 时用精确时间轴（group_words_to_subtitles），
        否则用 shot duration 估算（兼容回退路径）。
        """
        if word_boundaries:
            # 精确路径：从 WordBoundary 分组出字幕行 + 真实时长
            from app.services.edge_tts_service import group_words_to_subtitles

            lines = group_words_to_subtitles(word_boundaries)
            if lines:
                texts = [ln["text"] for ln in lines]
                durations = [ln["end"] - ln["start"] for ln in lines]
                return texts, durations

        # 估算路径：用 shot subtitle + shot duration（与原始行为一致）
        subtitles = []
        durations = []
        for sc in spec_data["scenes"]:
            for sh in sc["shots"]:
                subtitles.append(sh["subtitle"])
                durations.append(float(sh.get("duration", 5)))
        return subtitles, durations

    async def _brain(self, nl_prompt: str, output_type: str) -> dict:
        """脑补 Spec：有 LLM Key 时调 LLM 真实生成分镜；无 Key 回退硬编码模板。"""
        if settings.LLM_API_KEY:
            try:
                spec = await generate_script_spec(nl_prompt, output_type)
                # 补齐编排器下游消费的 wrapper 字段（LLM 返回不含这些）
                spec.setdefault("intent", nl_prompt)
                spec.setdefault("output_type", output_type)
                spec.setdefault("style_anchor", {"provider": "hunyuan_image", "ref_asset_ids": []})
                spec.setdefault("assembly", {"subtitles": True, "bgm": True, "resolution": "1080p"})
                logger.info("LLM brain 成功: title=%s, scenes=%d", spec.get("title"), len(spec.get("scenes", [])))
                return spec
            except Exception as exc:
                # LLM 失败时回退硬编码，不让编排器完全不可用（网络/限流/key失效等）
                logger.warning("LLM brain 失败，回退硬编码模板: %s", exc)
        return self._brain_fallback(nl_prompt, output_type)

    def _brain_fallback(self, nl_prompt: str, output_type: str) -> dict:
        """硬编码模板脑补（无 LLM 或 LLM 失败时的兜底）。"""
        if any(k in nl_prompt for k in ["奶龙", "奶娃", "龙"]):
            subject = "奶龙奶娃"
        elif any(k in nl_prompt for k in ["猫", "狗", "宠"]):
            subject = "萌宠主角"
        else:
            subject = "主角"
        return {
            "intent": nl_prompt,
            "output_type": output_type,
            "style_anchor": {"provider": "hunyuan_image", "ref_asset_ids": []},
            "characters": [
                {
                    "name": subject,
                    "anchor_prompt": f"{subject}，圆润卡通风格，高饱和色彩，夸张表情",
                    "ref_asset_ids": [],
                }
            ],
            "scenes": [
                {
                    "index": 1,
                    "description": "自动脑补场景",
                    "shots": [
                        {
                            "index": i + 1,
                            "duration": 5,
                            "image_prompt": f"{subject}做出动作{i + 1}",
                            "video_prompt": f"{subject}生动动作{i + 1}",
                            "audio": {"text": f"台词{i + 1}", "voice": "child_cn", "type": "tts"},
                            "subtitle": f"台词{i + 1}",
                        }
                        for i in range(3)
                    ],
                }
            ],
            "assembly": {"subtitles": True, "bgm": True, "resolution": "1080p"},
        }
