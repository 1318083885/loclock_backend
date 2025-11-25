"""increase_totp_secret_length

Revision ID: 4efce910ef21
Revises: 3662f07fbbea
Create Date: 2025-11-24 13:43:50.556466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4efce910ef21'
down_revision: Union[str, None] = '3662f07fbbea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 增加totp_secret字段长度从32到200
    op.alter_column('users', 'totp_secret',
                    existing_type=sa.String(32),
                    type_=sa.String(200),
                    existing_nullable=True)


def downgrade() -> None:
    # 回滚：减少totp_secret字段长度从200到32
    op.alter_column('users', 'totp_secret',
                    existing_type=sa.String(200),
                    type_=sa.String(32),
                    existing_nullable=True)
