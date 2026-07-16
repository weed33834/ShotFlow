"""project_health_check —— ShotFlow 仓库结构健康巡检。

快速核验关键目录 / 模块是否到位，并验证 video_quality_check 能正常导入。
用于本地与 CI 的轻量自检（不依赖后端服务）。

用法：
    python 08_Automation/project_health_check.py
退出码：0 = 健康；1 = 核心模块不可用（如 video_quality_check 导入失败）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 期望存在的核心目录 / 文件（缺失仅告警，不致命）
EXPECTED_DIRS = ["backend", "frontend", "flows", "03_Workflows"]
EXPECTED_FILES = ["README.md", "README.zh.md", "pyproject.toml"]


def main() -> int:
    print(f"[health] 仓库根: {ROOT}")
    problems: list[str] = []

    for d in EXPECTED_DIRS:
        if not (ROOT / d).is_dir():
            problems.append(f"缺少目录: {d}/")
    for f in EXPECTED_FILES:
        if not (ROOT / f).is_file():
            problems.append(f"缺少文件: {f}")

    # 核心模块可导入性校验（致命项）
    try:
        sys.path.insert(0, str(ROOT / "08_Automation"))
        import video_quality_check  # noqa: F401

        print(
            f"[health] video_quality_check 加载成功，"
            f"阈值项 {len(video_quality_check.THRESHOLDS)} 个"
        )
    except Exception as e:  # noqa: BLE001
        print(f"[health] 致命错误: 无法导入 video_quality_check: {e}")
        return 1

    if problems:
        print("[health] 告警（非致命）:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("[health] 核心目录与文件齐备")

    print("[health] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
