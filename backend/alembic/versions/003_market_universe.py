"""Add market_universe and price_bars tables

Revision ID: 003_market_universe
Revises: 
Create Date: 2025-12-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_market_universe'
down_revision: Union[str, None] = None  # Update this to your last migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create market_universe table
    op.create_table(
        'market_universe',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('asset_type', sa.Enum('STOCK', 'ETF', 'INDEX', 'ADR', name='assettype'), nullable=True),
        sa.Column('region', sa.Enum('US', 'UK', 'EU', 'ASIA', 'GLOBAL', name='marketregion'), nullable=False),
        sa.Column('exchange', sa.String(20), nullable=True),
        sa.Column('currency', sa.String(10), nullable=True, default='USD'),
        sa.Column('indices', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=[]),
        sa.Column('sector', sa.String(100), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('priority', sa.Integer(), nullable=True, default=1),
        sa.Column('last_quote_update', sa.DateTime(), nullable=True),
        sa.Column('last_ohlcv_update', sa.DateTime(), nullable=True),
        sa.Column('last_fundamental_update', sa.DateTime(), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=True, default=0),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_market_universe_symbol', 'market_universe', ['symbol'], unique=True)
    op.create_index('ix_market_universe_region_active', 'market_universe', ['region', 'is_active'])
    op.create_index('ix_market_universe_exchange', 'market_universe', ['exchange'])
    op.create_index('ix_market_universe_priority', 'market_universe', ['priority', 'is_active'])
    
    # Create price_bars table
    op.create_table(
        'price_bars',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('timeframe', sa.Enum('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', name='timeframe'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        sa.Column('adjusted_close', sa.Float(), nullable=True),
        sa.Column('vwap', sa.Float(), nullable=True),
        sa.Column('trade_count', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_price_bars_symbol', 'price_bars', ['symbol'])
    op.create_index('ix_price_bars_timestamp', 'price_bars', ['timestamp'])
    op.create_index('ix_price_bars_symbol_tf_ts', 'price_bars', ['symbol', 'timeframe', 'timestamp'])
    op.create_index('ix_price_bars_unique', 'price_bars', ['symbol', 'timeframe', 'timestamp'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_price_bars_unique', table_name='price_bars')
    op.drop_index('ix_price_bars_symbol_tf_ts', table_name='price_bars')
    op.drop_index('ix_price_bars_timestamp', table_name='price_bars')
    op.drop_index('ix_price_bars_symbol', table_name='price_bars')
    op.drop_table('price_bars')
    
    op.drop_index('ix_market_universe_priority', table_name='market_universe')
    op.drop_index('ix_market_universe_exchange', table_name='market_universe')
    op.drop_index('ix_market_universe_region_active', table_name='market_universe')
    op.drop_index('ix_market_universe_symbol', table_name='market_universe')
    op.drop_table('market_universe')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS timeframe')
    op.execute('DROP TYPE IF EXISTS assettype')
    op.execute('DROP TYPE IF EXISTS marketregion')
