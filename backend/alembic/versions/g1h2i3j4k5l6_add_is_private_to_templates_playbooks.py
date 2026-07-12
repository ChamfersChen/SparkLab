"""Add is_private field to templates and playbooks.

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-07-06

支持普通用户创建私有模板和流程，管理员创建的保持公开。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g1h2i3j4k5l6'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # templates 表添加 is_private 字段
    op.add_column('templates', sa.Column('is_private', sa.Boolean(), nullable=False, server_default='false'))
    
    # playbooks 表添加 is_private 字段
    op.add_column('playbooks', sa.Column('is_private', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('playbooks', 'is_private')
    op.drop_column('templates', 'is_private')
