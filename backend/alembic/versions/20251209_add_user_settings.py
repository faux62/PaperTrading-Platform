"""Add user_settings table

Revision ID: 20251209_add_user_settings
Revises: 20251205_add_base_currency
Create Date: 2025-12-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251209_add_user_settings'
down_revision: Union[str, None] = '20251205_add_base_currency'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_settings table
    op.create_table('user_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        # Data Provider API Keys (encrypted)
        sa.Column('api_key_alphavantage', sa.Text(), nullable=True),
        sa.Column('api_key_finnhub', sa.Text(), nullable=True),
        sa.Column('api_key_polygon', sa.Text(), nullable=True),
        sa.Column('api_key_yahoo', sa.Text(), nullable=True),
        # Theme settings
        sa.Column('theme', sa.String(length=20), nullable=True, server_default='dark'),
        # Notification settings
        sa.Column('notifications_email', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('notifications_push', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('notifications_trade_execution', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('notifications_price_alerts', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('notifications_portfolio_updates', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('notifications_market_news', sa.Boolean(), nullable=True, server_default='false'),
        # Display settings
        sa.Column('display_compact_mode', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('display_show_percent_change', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('display_default_chart_period', sa.String(length=10), nullable=True, server_default='1M'),
        sa.Column('display_chart_type', sa.String(length=20), nullable=True, server_default='candlestick'),
        # Timestamps
        sa.Column('password_changed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_settings_id'), 'user_settings', ['id'], unique=False)
    op.create_index(op.f('ix_user_settings_user_id'), 'user_settings', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_settings_user_id'), table_name='user_settings')
    op.drop_index(op.f('ix_user_settings_id'), table_name='user_settings')
    op.drop_table('user_settings')
