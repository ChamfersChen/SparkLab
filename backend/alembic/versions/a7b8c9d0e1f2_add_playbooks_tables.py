"""add playbooks tables

Revision ID: a7b8c9d0e1f2
Revises: 8a3d6c1f2e4b
Create Date: 2026-06-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = '8a3d6c1f2e4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'playbooks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('goal', sa.Text(), nullable=False),
        sa.Column('input', sa.Text(), nullable=False),
        sa.Column('output', sa.Text(), nullable=False),
        sa.Column('example', sa.Text(), nullable=False),
        sa.Column('variable_hints', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='playbook_status', create_constraint=True),
            nullable=False,
        ),
        sa.Column('use_count', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_playbooks_status', 'playbooks', ['status'])
    op.create_index('ix_playbooks_creator_id', 'playbooks', ['creator_id'])
    op.create_index('ix_playbooks_use_count_created_at', 'playbooks', ['use_count', 'created_at'])

    op.create_table(
        'playbook_steps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('playbook_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['playbook_id'], ['playbooks.id'], ondelete='CASCADE'),
        # templates 是软删除,不能级联物理删;管理员 hard_delete 时由 service 层校验引用
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('playbook_id', 'step_order', name='uq_playbook_steps_playbook_order'),
    )
    op.create_index('ix_playbook_steps_template_id', 'playbook_steps', ['template_id'])

    op.create_table(
        'playbook_tags',
        sa.Column('playbook_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['playbook_id'], ['playbooks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('playbook_id', 'tag_id'),
    )


def downgrade() -> None:
    op.drop_table('playbook_tags')
    op.drop_index('ix_playbook_steps_template_id', table_name='playbook_steps')
    op.drop_table('playbook_steps')
    op.drop_index('ix_playbooks_use_count_created_at', table_name='playbooks')
    op.drop_index('ix_playbooks_creator_id', table_name='playbooks')
    op.drop_index('ix_playbooks_status', table_name='playbooks')
    op.drop_table('playbooks')
