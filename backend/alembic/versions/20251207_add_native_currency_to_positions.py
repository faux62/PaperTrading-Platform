"""Add native_currency to positions

Revision ID: 20251207_add_native_currency
Revises: 20251209_add_user_settings
Create Date: 2025-12-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251207_add_native_currency'
down_revision: Union[str, None] = '20251209_add_user_settings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add native_currency column with default USD
    op.add_column('positions', sa.Column('native_currency', sa.String(3), nullable=False, server_default='USD'))


def downgrade() -> None:
    op.drop_column('positions', 'native_currency')
