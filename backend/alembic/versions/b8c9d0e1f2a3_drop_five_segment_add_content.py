"""drop 5-segment fields, add content column

重构: Template / Playbook 改成单 content 字段,不再用五段式 role/goal/input/output/example。
playbook_steps 也同步: 不再带五段,引用模板的 content 即可。

由于这是不兼容重构, 数据丢弃:
  - DROP: templates.role/goal/input/output/example
  - DROP: playbooks.role/goal/input/output/example
  - DROP: playbook_steps.name(展示用,合并进 step 引用的模板) → 保留以免破坏 step 名,这里不动
  - ADD: templates.content  Text NOT NULL DEFAULT ''
  - ADD: playbooks.content  Text NOT NULL DEFAULT ''
  - 注意: playbook_steps 不需要 content(它引用模板)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # templates: drop 5 columns, add content
    op.drop_column('templates', 'role')
    op.drop_column('templates', 'goal')
    op.drop_column('templates', 'input')
    op.drop_column('templates', 'output')
    op.drop_column('templates', 'example')
    op.add_column('templates', sa.Column('content', sa.Text(), nullable=False, server_default=''))

    # playbooks: drop 5 columns, add content
    op.drop_column('playbooks', 'role')
    op.drop_column('playbooks', 'goal')
    op.drop_column('playbooks', 'input')
    op.drop_column('playbooks', 'output')
    op.drop_column('playbooks', 'example')
    op.add_column('playbooks', sa.Column('content', sa.Text(), nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('templates', 'content')
    op.add_column('templates', sa.Column('example', sa.Text(), nullable=False, server_default=''))
    op.add_column('templates', sa.Column('output', sa.Text(), nullable=False, server_default=''))
    op.add_column('templates', sa.Column('input', sa.Text(), nullable=False, server_default=''))
    op.add_column('templates', sa.Column('goal', sa.Text(), nullable=False, server_default=''))
    op.add_column('templates', sa.Column('role', sa.Text(), nullable=False, server_default=''))

    op.drop_column('playbooks', 'content')
    op.add_column('playbooks', sa.Column('example', sa.Text(), nullable=False, server_default=''))
    op.add_column('playbooks', sa.Column('output', sa.Text(), nullable=False, server_default=''))
    op.add_column('playbooks', sa.Column('input', sa.Text(), nullable=False, server_default=''))
    op.add_column('playbooks', sa.Column('goal', sa.Text(), nullable=False, server_default=''))
    op.add_column('playbooks', sa.Column('role', sa.Text(), nullable=False, server_default=''))
