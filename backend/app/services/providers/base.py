"""Provider 抽象基类。

所有厂商生成能力（图片/视频/音频/口型/一致性锚定）统一实现此接口。
SIMULATE_MODE 下 generate() 直接走 _simulate() 返回占位资产，保证无 GPU、无 Key 也能跑通全链路。
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class AssetResult(BaseModel):
    """一次生成调用的结果。"""

    asset_id: int | None = None
    url: str = ""
    provider: str = ""
    meta: dict = {}


class BaseProvider(ABC):
    """生成能力 Provider 基类。"""

    name: str = ""
    # 能力集合: image / video / audio / lipsync / anchor
    capabilities: set[str] = set()

    def __init__(
        self,
        api_key: str = "",
        secret_id: str = "",
        secret_key: str = "",
        simulate: bool = False,
        base_url: str = "",
    ):
        self.api_key = api_key
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.simulate = simulate
        self.base_url = base_url

    @abstractmethod
    async def generate(self, kind: str, params: dict) -> AssetResult:
        """执行一次生成。

        kind: image / video / audio / lipsync / anchor
        params: 调用参数（prompt / ref_images / duration / voice / ...）
        """
        raise NotImplementedError

    async def _simulate(self, kind: str, params: dict) -> AssetResult:
        """无 Key / SIMULATE 模式下的占位结果，保证全链路可验证。"""
        return AssetResult(
            url=f"simulate://{self.name}/{kind}",
            provider=self.name,
            meta={"simulate": True, "kind": kind, **params},
        )
