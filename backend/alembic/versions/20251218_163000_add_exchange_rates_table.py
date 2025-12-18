"""Add exchange_rates table for FX rate caching

This migration adds the exchange_rates table to cache forex rates locally.
Rates are updated every hour by a scheduled job, eliminating the need
for on-demand API calls during trading operations.

Supported currency pairs (4 currencies × 3 = 12 pairs):
- EUR/USD, EUR/GBP, EUR/CHF
- USD/EUR, USD/GBP, USD/CHF
- GBP/EUR, GBP/USD, GBP/CHF
- CHF/EUR, CHF/USD, CHF/GBP

Revision ID: 20251218_163000
Revises: 20251218_drop_cash_balances
Create Date: 2025-12-18 16:30:00.000000

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251218_163000'
down_revision: Union[str, None] = '20251218_drop_cash_balances'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create exchange_rates table."""
    op.create_table(
        'exchange_rates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('base_currency', sa.String(3), nullable=False),
        sa.Column('quote_currency', sa.String(3), nullable=False),
        sa.Column('rate', sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column('source', sa.String(50), nullable=False, server_default='frankfurter'),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.UniqueConstraint('base_currency', 'quote_currency', name='uq_exchange_rates_pair')
    )
    
    # Create index for fast lookups
    op.create_index(
        'ix_exchange_rates_pair', 
        'exchange_rates', 
        ['base_currency', 'quote_currency']
    )
    
    # Seed initial rates (approximate values, will be updated by job)
    # These are fallback values in case the job hasn't run yet
    now = datetime.utcnow().isoformat()
    op.execute(f"""
        INSERT INTO exchange_rates (base_currency, quote_currency, rate, source, fetched_at, created_at, updated_at)
        VALUES 
            ('EUR', 'USD', 1.05, 'seed', '{now}', '{now}', '{now}'),
            ('EUR', 'GBP', 0.86, 'seed', '{now}', '{now}', '{now}'),
            ('EUR', 'CHF', 0.94, 'seed', '{now}', '{now}', '{now}'),
            ('USD', 'EUR', 0.95, 'seed', '{now}', '{now}', '{now}'),
            ('USD', 'GBP', 0.82, 'seed', '{now}', '{now}', '{now}'),
            ('USD', 'CHF', 0.89, 'seed', '{now}', '{now}', '{now}'),
            ('GBP', 'EUR', 1.16, 'seed', '{now}', '{now}', '{now}'),
            ('GBP', 'USD', 1.22, 'seed', '{now}', '{now}', '{now}'),
            ('GBP', 'CHF', 1.09, 'seed', '{now}', '{now}', '{now}'),
            ('CHF', 'EUR', 1.06, 'seed', '{now}', '{now}', '{now}'),
            ('CHF', 'USD', 1.12, 'seed', '{now}', '{now}', '{now}'),
            ('CHF', 'GBP', 0.92, 'seed', '{now}', '{now}', '{now}')
    """)


def downgrade() -> None:
    """Drop exchange_rates table."""
    op.drop_index('ix_exchange_rates_pair', table_name='exchange_rates')
    op.drop_table('exchange_rates')
