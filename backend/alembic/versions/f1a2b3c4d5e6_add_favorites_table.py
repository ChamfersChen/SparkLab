"""add favorites table

用户收藏功能: 支持收藏模板和工作流两种类型。

表设计:
  favorites  — 用户收藏记录,联合唯一约束 (user_id, target_type, target_id)

升级: 建表 + 索引
降级: drop 索引 + drop 表

Revision ID: f1a2b3c4d5e6
Revises: eb0365cdfa9e
Create Date: 2026-07-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'eb0365cdfa9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建枚举类型
    favorite_target_type = sa.Enum('template', 'playbook', name='favorite_target_type')
    favorite_target_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'favorites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('target_type', sa.Enum('template', 'playbook', name='favorite_target_type'), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'target_type', 'target_id', name='uq_user_favorite_target'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_favorites_user_id', 'favorites', ['user_id'])
    op.create_index('ix_favorites_user_target', 'favorites', ['user_id', 'target_type', 'target_id'])


def downgrade() -> None:
    op.drop_index('ix_favorites_user_target', table_name='favorites')
    op.drop_index('ix_favorites_user_id', table_name='favorites')
    op.drop_table('favorites')
    sa.Enum(name='favorite_target_type').drop(op.get_bind(), checkfirst=True)
