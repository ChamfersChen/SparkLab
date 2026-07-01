"""add playbook_runs tables

工作流运行结果保存: 用户跑完一个 playbook 后, 把每步粘回的 AI 结果 (user_output)
按 step 持久化下来, 用于个人中心 "我的运行记录" 回看。

表设计:
  playbook_runs       — 一个用户对某工作流的一次"完整跑完"记录
  playbook_run_steps  — 每步保存: step_order + step_name 快照 + user_output (NULL = 该步未粘回)

升级: 建 2 表 + 2 索引
降级: drop 索引 + drop 表

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'playbook_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('playbook_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['playbook_id'], ['playbooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_playbook_runs_user_created',
        'playbook_runs',
        ['user_id', sa.text('created_at DESC')],
    )

    op.create_table(
        'playbook_run_steps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(length=200), nullable=False),
        sa.Column('user_output', sa.Text(), nullable=True),
        sa.Column('form_values_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['playbook_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_playbook_run_steps_run',
        'playbook_run_steps',
        ['run_id', 'step_order'],
    )


def downgrade() -> None:
    op.drop_index('ix_playbook_run_steps_run', table_name='playbook_run_steps')
    op.drop_table('playbook_run_steps')
    op.drop_index('ix_playbook_runs_user_created', table_name='playbook_runs')
    op.drop_table('playbook_runs')
