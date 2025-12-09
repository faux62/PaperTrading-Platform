"""Add IBKR-style multi-currency cash management

Revision ID: 20251209_add_cash_balances
Revises: 20251209_merge_heads
Create Date: 2025-12-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251209_add_cash_balances'
down_revision: Union[str, None] = '20251209_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create cash_balances table (multi-currency cash per portfolio)
    op.create_table('cash_balances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('balance', sa.Numeric(precision=15, scale=2), server_default='0.00'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('portfolio_id', 'currency', name='uq_portfolio_currency')
    )
    op.create_index(op.f('ix_cash_balances_id'), 'cash_balances', ['id'], unique=False)
    op.create_index(op.f('ix_cash_balances_portfolio_id'), 'cash_balances', ['portfolio_id'], unique=False)
    
    # Create fx_transactions table (currency conversion history)
    op.create_table('fx_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('from_currency', sa.String(length=3), nullable=False),
        sa.Column('to_currency', sa.String(length=3), nullable=False),
        sa.Column('from_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('to_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('exchange_rate', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fx_transactions_id'), 'fx_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_fx_transactions_portfolio_id'), 'fx_transactions', ['portfolio_id'], unique=False)
    
    # Migrate existing cash_balance from portfolios to cash_balances table
    # This creates a cash balance entry in the portfolio's base currency
    op.execute("""
        INSERT INTO cash_balances (portfolio_id, currency, balance, created_at, updated_at)
        SELECT id, currency, cash_balance, created_at, updated_at
        FROM portfolios
        WHERE cash_balance > 0
    """)


def downgrade() -> None:
    # Migrate cash back to portfolios table (only base currency)
    op.execute("""
        UPDATE portfolios p
        SET cash_balance = COALESCE((
            SELECT cb.balance 
            FROM cash_balances cb 
            WHERE cb.portfolio_id = p.id AND cb.currency = p.currency
        ), p.cash_balance)
    """)
    
    op.drop_index(op.f('ix_fx_transactions_portfolio_id'), table_name='fx_transactions')
    op.drop_index(op.f('ix_fx_transactions_id'), table_name='fx_transactions')
    op.drop_table('fx_transactions')
    
    op.drop_index(op.f('ix_cash_balances_portfolio_id'), table_name='cash_balances')
    op.drop_index(op.f('ix_cash_balances_id'), table_name='cash_balances')
    op.drop_table('cash_balances')
