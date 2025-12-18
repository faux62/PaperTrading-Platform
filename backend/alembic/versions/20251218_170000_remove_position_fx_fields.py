"""Remove avg_cost_portfolio and entry_exchange_rate from positions

With Approach B (dynamic FX rates), these fields become redundant:
- avg_cost_portfolio: Now calculated on-demand using current exchange rate
- entry_exchange_rate: Historical rate still available in TRADES.exchange_rate for audit

Revision ID: 20251218_170000
Revises: 20251218_163000
Create Date: 2025-12-18 17:00:00.000000

"""
from typing import Sequence, Union
from decimal import Decimal

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251218_170000'
down_revision: Union[str, None] = '20251218_163000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove FX-related fields from positions table."""
    op.drop_column('positions', 'avg_cost_portfolio')
    op.drop_column('positions', 'entry_exchange_rate')


def downgrade() -> None:
    """Restore FX-related fields to positions table."""
    op.add_column(
        'positions',
        sa.Column(
            'entry_exchange_rate',
            sa.Numeric(precision=15, scale=6),
            nullable=True,
            server_default='1.0'
        )
    )
    op.add_column(
        'positions',
        sa.Column(
            'avg_cost_portfolio',
            sa.Numeric(precision=15, scale=4),
            nullable=True,
            server_default='0'
        )
    )
