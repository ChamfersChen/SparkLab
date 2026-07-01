"""add filled_prompt and final_result columns

v4 改造: 三栏 PlaybookRun 后, 用户在右栏"最终结果"区填的内容也要保存,
且后端在 create_run 时把每个 step 的补充后 prompt 算出来快照到 step 行.

变更:
  - playbook_run_steps 加 filled_prompt (server 现算的 step filled content 快照)
  - playbook_runs 加 final_result (用户在右栏填的最终结果 Markdown 源文本)

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-01 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'playbook_run_steps',
        sa.Column('filled_prompt', sa.Text(), nullable=True),
    )
    op.add_column(
        'playbook_runs',
        sa.Column('final_result', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('playbook_runs', 'final_result')
    op.drop_column('playbook_run_steps', 'filled_prompt')
