"""Drop deprecated cash_balances table

Revision ID: 20251218_drop_cash_balances
Revises: 20251216_145900_add_portfolio_currency_fields_to_position
Create Date: 2025-12-18

The cash_balances table was part of the IBKR-style multi-currency system.
It has been replaced by the Single Currency Model where portfolio.cash_balance
is the ONLY source of truth for cash.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251218_drop_cash_balances'
down_revision: Union[str, None] = '20251216_145900'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the deprecated cash_balances table."""
    # Drop the table
    op.drop_table('cash_balances')


def downgrade() -> None:
    """Recreate cash_balances table (for rollback only)."""
    op.create_table(
        'cash_balances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('balance', sa.Numeric(15, 2), default=0.00),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('portfolio_id', 'currency', name='uq_portfolio_currency')
    )
    op.create_index('ix_cash_balances_id', 'cash_balances', ['id'])
    op.create_index('ix_cash_balances_portfolio_id', 'cash_balances', ['portfolio_id'])
