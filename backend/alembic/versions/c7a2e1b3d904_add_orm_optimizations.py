"""add orm optimizations: shot unique constraint, render_task composite index

Revision ID: c7a2e1b3d904
Revises: acb1c452945a
Create Date: 2026-07-06 12:00:00.000000

新增：
  - shots 表 (project_id, shot_code) 复合唯一约束，避免同项目内重复镜头编号
  - render_tasks 表 (status, priority) 复合索引，优化队列列表查询热路径
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c7a2e1b3d904"
down_revision: Union[str, None] = "acb1c452945a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 同项目内 shot_code 唯一
    op.create_unique_constraint("uq_shot_project_code", "shots", ["project_id", "shot_code"])
    # 队列列表热路径：status 过滤 + priority 排序
    op.create_index(
        "ix_render_tasks_status_priority",
        "render_tasks",
        ["status", "priority"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_render_tasks_status_priority", table_name="render_tasks")
    op.drop_constraint("uq_shot_project_code", "shots", type_="unique")
