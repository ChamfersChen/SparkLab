"""drop playbook_steps.template_id, add content column

重构: PlaybookStep 不再引用 Template; 每个 step 自带 prompt content (Markdown + {{var}} +
{{prev_output}})。Template 模块保持独立, 但 Playbook 不再依赖。

升级: drop FK + drop index + drop column + add content
降级: drop content + add column (FK / index 由 alembic 重加)

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FK_NAME = 'playbook_steps_template_id_fkey'
_INDEX_NAME = 'ix_playbook_steps_template_id'


def upgrade() -> None:
    # 1) drop FK by name (alembic 不会在 drop_column 时自动 drop FK)
    op.drop_constraint(_FK_NAME, 'playbook_steps', type_='foreignkey')
    # 2) drop index
    op.drop_index(_INDEX_NAME, table_name='playbook_steps')
    # 3) drop column
    op.drop_column('playbook_steps', 'template_id')
    # 4) add new content column
    op.add_column(
        'playbook_steps',
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
    )


def downgrade() -> None:
    op.drop_column('playbook_steps', 'content')
    op.add_column(
        'playbook_steps',
        sa.Column('template_id', sa.Integer(), nullable=False, server_default='0'),
    )
    op.execute('ALTER TABLE playbook_steps ALTER COLUMN template_id DROP DEFAULT')
    op.create_index(_INDEX_NAME, 'playbook_steps', ['template_id'])
    op.create_foreign_key(
        _FK_NAME,
        'playbook_steps',
        'templates',
        ['template_id'],
        ['id'],
        ondelete='RESTRICT',
    )
