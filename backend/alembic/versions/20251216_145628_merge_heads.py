"""merge_heads

Revision ID: 1c70b883495a
Revises: 00000000000001, 003_market_universe
Create Date: 2025-12-16 14:56:28.835436

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c70b883495a'
down_revision: Union[str, None] = ('00000000000001', '003_market_universe')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
