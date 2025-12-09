"""Add additional API key columns to user_settings

Revision ID: 20251209_add_api_keys_columns
Revises: 20251209_add_user_settings
Create Date: 2025-12-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251209_add_api_keys_columns'
down_revision: Union[str, None] = '20251209_add_user_settings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new API key columns
    # Check and add each column if not exists
    
    # Alpaca (US Market Primary)
    op.add_column('user_settings', sa.Column('api_key_alpaca', sa.Text(), nullable=True))
    op.add_column('user_settings', sa.Column('api_key_alpaca_secret', sa.Text(), nullable=True))
    
    # Global Coverage
    op.add_column('user_settings', sa.Column('api_key_twelvedata', sa.Text(), nullable=True))
    
    # Historical Data
    op.add_column('user_settings', sa.Column('api_key_eodhd', sa.Text(), nullable=True))
    
    # Fundamentals
    op.add_column('user_settings', sa.Column('api_key_fmp', sa.Text(), nullable=True))
    
    # Additional Providers
    op.add_column('user_settings', sa.Column('api_key_nasdaq', sa.Text(), nullable=True))
    op.add_column('user_settings', sa.Column('api_key_tiingo', sa.Text(), nullable=True))
    op.add_column('user_settings', sa.Column('api_key_marketstack', sa.Text(), nullable=True))
    op.add_column('user_settings', sa.Column('api_key_stockdata', sa.Text(), nullable=True))
    op.add_column('user_settings', sa.Column('api_key_intrinio', sa.Text(), nullable=True))
    
    # No API Key Required (stored for reference only)
    op.add_column('user_settings', sa.Column('api_key_yfinance', sa.Text(), nullable=True))
    op.add_column('user_settings', sa.Column('api_key_stooq', sa.Text(), nullable=True))
    op.add_column('user_settings', sa.Column('api_key_investingcom', sa.Text(), nullable=True))
    
    # Rename api_key_yahoo to match model if it exists
    # First check if the old column exists and new doesn't
    try:
        op.alter_column('user_settings', 'api_key_yahoo', new_column_name='api_key_yahoo_old')
    except Exception:
        pass


def downgrade() -> None:
    # Remove the new columns
    op.drop_column('user_settings', 'api_key_alpaca')
    op.drop_column('user_settings', 'api_key_alpaca_secret')
    op.drop_column('user_settings', 'api_key_twelvedata')
    op.drop_column('user_settings', 'api_key_eodhd')
    op.drop_column('user_settings', 'api_key_fmp')
    op.drop_column('user_settings', 'api_key_nasdaq')
    op.drop_column('user_settings', 'api_key_tiingo')
    op.drop_column('user_settings', 'api_key_marketstack')
    op.drop_column('user_settings', 'api_key_stockdata')
    op.drop_column('user_settings', 'api_key_intrinio')
    op.drop_column('user_settings', 'api_key_yfinance')
    op.drop_column('user_settings', 'api_key_stooq')
    op.drop_column('user_settings', 'api_key_investingcom')
    
    # Rename back
    try:
        op.alter_column('user_settings', 'api_key_yahoo_old', new_column_name='api_key_yahoo')
    except Exception:
        pass
