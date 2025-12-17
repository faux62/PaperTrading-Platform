"""Add portfolio currency fields to position table

This migration adds:
- avg_cost_portfolio: Average cost in portfolio base currency
- entry_exchange_rate: FX rate used at time of purchase (native -> portfolio)

These fields support the Single Currency Model where:
- avg_cost remains in NATIVE currency (e.g., USD for AAPL)
- avg_cost_portfolio stores the converted value in PORTFOLIO currency (e.g., EUR)
- entry_exchange_rate records the FX rate for audit trail

Revision ID: 20251216_145900
Revises: 1c70b883495a
Create Date: 2025-12-16 14:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from decimal import Decimal


# revision identifiers, used by Alembic.
revision: str = '20251216_145900'
down_revision: Union[str, None] = '1c70b883495a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add avg_cost_portfolio column
    op.add_column('positions', sa.Column(
        'avg_cost_portfolio', 
        sa.Numeric(precision=15, scale=4), 
        nullable=True,
        server_default='0'
    ))
    
    # Add entry_exchange_rate column
    op.add_column('positions', sa.Column(
        'entry_exchange_rate', 
        sa.Numeric(precision=15, scale=6), 
        nullable=True,
        server_default='1.0'
    ))
    
    # Initialize existing positions: copy avg_cost to avg_cost_portfolio
    # (assumes existing positions are in same currency as portfolio or need manual review)
    op.execute("""
        UPDATE positions 
        SET avg_cost_portfolio = avg_cost,
            entry_exchange_rate = 1.0
        WHERE avg_cost_portfolio IS NULL
    """)


def downgrade() -> None:
    op.drop_column('positions', 'entry_exchange_rate')
    op.drop_column('positions', 'avg_cost_portfolio')
