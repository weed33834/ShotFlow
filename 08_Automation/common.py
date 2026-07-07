"""08_Automation 共享工具模块。

所有 08_Automation 脚本通过 ``from common import PROJECT_ROOT`` 引用项目根目录，
避免在每个脚本中重复 ``Path(__file__).resolve().parent.parent``。
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
