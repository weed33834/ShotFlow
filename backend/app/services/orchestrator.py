"""默认编排器：读 flow.sop + 脑补 Spec + 调工具出片（人用 UI 入口兜底）。

外部智能体（WorkBuddy / 元器 / 百炼 / Dify）跳过本编排器，直接读 flow.sop 调 /tools 路由自行执行。
本编排器让「人也能用」：SIMULATE 模式用模板脑补；有 Key 时调千问脑补（Phase E 接入）。
"""

from pathlib import Path

from app.core.config import settings
from app.schemas.spec import AssembleReq, SpecSaveReq, ToolGenerateReq
from app.services import tools_service as svc

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Orchestrator:
    async def run(self, nl_prompt: str, output_type: str, db, project_id=None) -> int:
        # 读流程文件（存在性校验，实际脑补见 _brain）
        flow_path = PROJECT_ROOT / "flows" / f"make_{output_type}.sop.md"
        if not flow_path.exists():
            raise ValueError(f"未找到流程文件: {flow_path}")

        # S1+S2 意图识别 + 需求脑补（SIMULATE 模板；真实调 LLM 见 Phase E）
        spec_data = self._brain(nl_prompt, output_type)
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
        await svc.anchor(
            ToolGenerateReq(
                provider="hunyuan_image",
                kind="anchor",
                params={"prompt": spec_data["characters"][0]["anchor_prompt"]},
            ),
            db,
        )

        # S4 并行生成（每镜 image + video + audio，SIMULATE 占位）
        for scene in spec_data["scenes"]:
            for shot in scene["shots"]:
                await svc.run_tool(
                    ToolGenerateReq(
                        provider="hunyuan_image",
                        kind="image",
                        params={"prompt": shot["image_prompt"]},
                    ),
                    db,
                )
                await svc.run_tool(
                    ToolGenerateReq(
                        provider="wanx",
                        kind="video",
                        params={"prompt": shot["video_prompt"], "duration": shot["duration"]},
                    ),
                    db,
                )
                await svc.run_tool(
                    ToolGenerateReq(
                        provider="tencent_tts",
                        kind="audio",
                        params={"text": shot["audio"]["text"], "voice": shot["audio"]["voice"]},
                    ),
                    db,
                )

        # S5 组装成片
        subtitles = [s["subtitle"] for sc in spec_data["scenes"] for s in sc["shots"]]
        await svc.assemble(AssembleReq(spec_id=spec.id, asset_ids=[], subtitles=subtitles), db)
        return spec.id

    def _brain(self, nl_prompt: str, output_type: str) -> dict:
        """SIMULATE 模板脑补：基于关键词生成角色圣经 + 分镜（无 LLM 可验证全链路）。"""
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
