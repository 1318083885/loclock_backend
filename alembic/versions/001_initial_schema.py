"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-11-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建users表
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index('idx_users_username', 'users', ['username'], unique=False)
    op.create_index('idx_users_role', 'users', ['role'], unique=False)

    # 创建links表
    op.create_table(
        'links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('short_code', sa.String(length=50), nullable=False),
        sa.Column('target_url', sa.String(), nullable=False),
        sa.Column('center_lat', sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column('center_lng', sa.Numeric(precision=11, scale=8), nullable=False),
        sa.Column('radius_meters', sa.Integer(), nullable=False),
        sa.Column('location_name', sa.String(length=255), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('visit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('denied_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('short_code')
    )
    op.create_index('idx_links_short_code', 'links', ['short_code'], unique=False)
    op.create_index('idx_links_created_by', 'links', ['created_by'], unique=False)
    op.create_index('idx_links_is_active', 'links', ['is_active'], unique=False)

    # 创建access_logs表
    op.create_table(
        'access_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('link_id', sa.Integer(), nullable=False),
        sa.Column('visitor_lat', sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column('visitor_lng', sa.Numeric(precision=11, scale=8), nullable=True),
        sa.Column('distance_meters', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('access_granted', sa.Boolean(), nullable=False),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('accessed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['link_id'], ['links.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_access_logs_link_id', 'access_logs', ['link_id'], unique=False)
    op.create_index('idx_access_logs_accessed_at', 'access_logs', ['accessed_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_access_logs_accessed_at', table_name='access_logs')
    op.drop_index('idx_access_logs_link_id', table_name='access_logs')
    op.drop_table('access_logs')
    
    op.drop_index('idx_links_is_active', table_name='links')
    op.drop_index('idx_links_created_by', table_name='links')
    op.drop_index('idx_links_short_code', table_name='links')
    op.drop_table('links')
    
    op.drop_index('idx_users_role', table_name='users')
    op.drop_index('idx_users_username', table_name='users')
    op.drop_table('users')
