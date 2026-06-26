"""add users and activation_codes

Revision ID: 157c579d20eb
Revises:
Create Date: 2026-06-26 09:46:46.654009

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '157c579d20eb'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users 表（先创建，不含指向 activation_codes 的 FK）
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('USER', 'ADMIN', 'SUPER_ADMIN', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('activation_code_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # 2. activation_codes 表（含指向 users 的 FK）
    op.create_table('activation_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=14), nullable=False),
        sa.Column('status', sa.Enum('UNUSED', 'USED', 'DISABLED', name='activationcodestatus'), nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activation_codes_code'), 'activation_codes', ['code'], unique=True)

    # 3. users.activation_code_id → activation_codes.id（两表都已存在）
    op.create_foreign_key(
        'fk_users_activation_code',
        'users', 'activation_codes',
        ['activation_code_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_activation_code', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_activation_codes_code'), table_name='activation_codes')
    op.drop_table('activation_codes')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS activationcodestatus')
