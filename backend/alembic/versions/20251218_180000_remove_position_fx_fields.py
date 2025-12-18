"""Remove avg_cost_portfolio and entry_exchange_rate from positions

With Approach B (dynamic FX rates), these fields become redundant:
- avg_cost_portfolio: Now calculated on-demand using current exchange rate
- entry_exchange_rate: Historical rate still available in TRADES.exchange_rate for audit

Revision ID: 20251218_180000
Revises: 20251218_drop_cash_balances
Create Date: 2025-12-18 18:00:00.000000

"""
from typing import Sequence, Union
from decimal import Decimal

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251218_180000'
down_revision: Union[str, None] = '20251218_drop_cash_balances'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove FX-related fields from positions table."""
    # Check if columns exist before dropping (for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('positions')]
    
    if 'avg_cost_portfolio' in columns:
        op.drop_column('positions', 'avg_cost_portfolio')
    
    if 'entry_exchange_rate' in columns:
        op.drop_column('positions', 'entry_exchange_rate')


def downgrade() -> None:
    """Restore FX-related fields to positions table."""
    op.add_column(
        'positions',
        sa.Column(
            'entry_exchange_rate',
            sa.Numeric(precision=20, scale=8),
            nullable=True
        )
    )
    op.add_column(
        'positions',
        sa.Column(
            'avg_cost_portfolio',
            sa.Numeric(precision=20, scale=8),
            nullable=True
        )
    )
