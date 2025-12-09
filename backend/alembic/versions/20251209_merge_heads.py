"""Merge bot_signals and api_keys branches

Revision ID: 20251209_merge_heads
Revises: bot_signals_001, 20251209_add_api_keys_columns
Create Date: 2025-12-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251209_merge_heads'
down_revision: Union[str, Sequence[str], None] = ('bot_signals_001', '20251209_add_api_keys_columns')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migration - nothing to do."""
    pass


def downgrade() -> None:
    """Merge migration - nothing to do."""
    pass
