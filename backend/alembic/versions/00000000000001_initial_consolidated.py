"""Initial consolidated migration - Creates all tables from scratch

Revision ID: 00000000000001
Revises: None
Create Date: 2024-12-09

This migration creates all tables needed for the PaperTrading Platform.
Run with a fresh database to create the complete schema.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '00000000000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables."""
    
    # ===========================================
    # 1. USERS TABLE
    # ===========================================
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('email', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('username', sa.String(100), unique=True, index=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('base_currency', sa.String(3), default='USD', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )
    
    # ===========================================
    # 2. USER_SETTINGS TABLE
    # ===========================================
    op.create_table(
        'user_settings',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True),
        # API Keys (encrypted)
        sa.Column('api_key_alpaca', sa.Text(), nullable=True),
        sa.Column('api_key_alpaca_secret', sa.Text(), nullable=True),
        sa.Column('api_key_polygon', sa.Text(), nullable=True),
        sa.Column('api_key_finnhub', sa.Text(), nullable=True),
        sa.Column('api_key_twelvedata', sa.Text(), nullable=True),
        sa.Column('api_key_eodhd', sa.Text(), nullable=True),
        sa.Column('api_key_fmp', sa.Text(), nullable=True),
        sa.Column('api_key_alphavantage', sa.Text(), nullable=True),
        sa.Column('api_key_nasdaq', sa.Text(), nullable=True),
        sa.Column('api_key_tiingo', sa.Text(), nullable=True),
        sa.Column('api_key_marketstack', sa.Text(), nullable=True),
        sa.Column('api_key_stockdata', sa.Text(), nullable=True),
        sa.Column('api_key_intrinio', sa.Text(), nullable=True),
        sa.Column('api_key_yahoo_old', sa.Text(), nullable=True),
        sa.Column('api_key_yfinance', sa.Text(), nullable=True),
        sa.Column('api_key_stooq', sa.Text(), nullable=True),
        sa.Column('api_key_investingcom', sa.Text(), nullable=True),
        # Theme settings
        sa.Column('theme', sa.String(20), default='dark'),
        # Notification settings
        sa.Column('notifications_email', sa.Boolean(), default=True),
        sa.Column('notifications_push', sa.Boolean(), default=True),
        sa.Column('notifications_trade_execution', sa.Boolean(), default=True),
        sa.Column('notifications_price_alerts', sa.Boolean(), default=True),
        sa.Column('notifications_portfolio_updates', sa.Boolean(), default=True),
        sa.Column('notifications_market_news', sa.Boolean(), default=False),
        # Display settings
        sa.Column('display_compact_mode', sa.Boolean(), default=False),
        sa.Column('display_show_percent_change', sa.Boolean(), default=True),
        sa.Column('display_default_chart_period', sa.String(10), default='1M'),
        sa.Column('display_chart_type', sa.String(20), default='candlestick'),
        # Security
        sa.Column('password_changed_at', sa.DateTime(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # ===========================================
    # 3. PORTFOLIOS TABLE
    # ===========================================
    risk_profile_enum = sa.Enum('aggressive', 'balanced', 'prudent', name='riskprofile')
    risk_profile_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('risk_profile', risk_profile_enum, server_default='balanced'),
        sa.Column('strategy_period_weeks', sa.Integer(), default=12, nullable=False),
        sa.Column('initial_capital', sa.Numeric(15, 2), default=10000.00),
        sa.Column('cash_balance', sa.Numeric(15, 2), default=10000.00),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint('initial_capital >= 100', name='ck_portfolios_initial_capital_min'),
    )
    op.create_index('ix_portfolios_user_id', 'portfolios', ['user_id'])
    
    # ===========================================
    # 4. POSITIONS TABLE
    # ===========================================
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('exchange', sa.String(20), nullable=True),
        sa.Column('native_currency', sa.String(3), default='USD', nullable=False),
        sa.Column('quantity', sa.Numeric(15, 4), default=0),
        sa.Column('avg_cost', sa.Numeric(15, 4), default=0),
        sa.Column('current_price', sa.Numeric(15, 4), default=0),
        sa.Column('market_value', sa.Numeric(15, 2), default=0),
        sa.Column('unrealized_pnl', sa.Numeric(15, 2), default=0),
        sa.Column('unrealized_pnl_percent', sa.Numeric(8, 4), default=0),
        sa.Column('opened_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_positions_portfolio_id', 'positions', ['portfolio_id'])
    
    # ===========================================
    # 5. TRADES TABLE
    # ===========================================
    trade_type_enum = sa.Enum('buy', 'sell', name='tradetype')
    order_type_enum = sa.Enum('market', 'limit', 'stop', 'stop_limit', name='ordertype')
    trade_status_enum = sa.Enum('pending', 'executed', 'partial', 'cancelled', 'failed', name='tradestatus')
    
    trade_type_enum.create(op.get_bind(), checkfirst=True)
    order_type_enum.create(op.get_bind(), checkfirst=True)
    trade_status_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('exchange', sa.String(20), nullable=True),
        sa.Column('native_currency', sa.String(3), default='USD', nullable=False),
        sa.Column('exchange_rate', sa.Numeric(15, 6), nullable=True),
        sa.Column('trade_type', trade_type_enum, nullable=False),
        sa.Column('order_type', order_type_enum, server_default='market'),
        sa.Column('status', trade_status_enum, server_default='pending'),
        sa.Column('quantity', sa.Numeric(15, 4), nullable=False),
        sa.Column('price', sa.Numeric(15, 4), nullable=True),
        sa.Column('executed_price', sa.Numeric(15, 4), nullable=True),
        sa.Column('executed_quantity', sa.Numeric(15, 4), nullable=True),
        sa.Column('total_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('commission', sa.Numeric(10, 2), default=0),
        sa.Column('realized_pnl', sa.Numeric(15, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
    )
    op.create_index('ix_trades_portfolio_id', 'trades', ['portfolio_id'])
    
    # ===========================================
    # 6. CASH_BALANCES TABLE (Multi-currency)
    # ===========================================
    op.create_table(
        'cash_balances',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('balance', sa.Numeric(15, 2), default=0.00),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('portfolio_id', 'currency', name='uq_portfolio_currency'),
    )
    
    # ===========================================
    # 7. FX_TRANSACTIONS TABLE
    # ===========================================
    op.create_table(
        'fx_transactions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('from_currency', sa.String(3), nullable=False),
        sa.Column('to_currency', sa.String(3), nullable=False),
        sa.Column('from_amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('to_amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('exchange_rate', sa.Numeric(15, 6), nullable=False),
        sa.Column('executed_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # ===========================================
    # 8. WATCHLISTS TABLE
    # ===========================================
    op.create_table(
        'watchlists',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_watchlists_user_id', 'watchlists', ['user_id'])
    
    # ===========================================
    # 9. WATCHLIST_SYMBOLS TABLE (Association)
    # ===========================================
    op.create_table(
        'watchlist_symbols',
        sa.Column('watchlist_id', sa.Integer(), sa.ForeignKey('watchlists.id', ondelete='CASCADE')),
        sa.Column('symbol', sa.String(20)),
        sa.Column('added_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # ===========================================
    # 10. ALERTS TABLE
    # ===========================================
    alert_type_enum = sa.Enum('price_above', 'price_below', 'percent_change_up', 'percent_change_down', name='alerttype')
    alert_status_enum = sa.Enum('active', 'triggered', 'expired', 'disabled', name='alertstatus')
    
    alert_type_enum.create(op.get_bind(), checkfirst=True)
    alert_status_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('alert_type', alert_type_enum, nullable=False),
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('status', alert_status_enum, server_default='active', nullable=False),
        sa.Column('is_recurring', sa.Boolean(), default=False),
        sa.Column('triggered_at', sa.DateTime(), nullable=True),
        sa.Column('triggered_price', sa.Float(), nullable=True),
        sa.Column('note', sa.String(500), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_alerts_user_id', 'alerts', ['user_id'])
    
    # ===========================================
    # 11. BOT_SIGNALS TABLE
    # ===========================================
    signal_type_enum = sa.Enum(
        'trade_suggestion', 'position_alert', 'risk_warning', 'market_alert',
        'price_level', 'volume_spike', 'ml_prediction', 'news_alert',
        'rebalance_suggestion', 'trailing_stop',
        name='signaltype'
    )
    signal_priority_enum = sa.Enum('low', 'medium', 'high', 'urgent', name='signalpriority')
    signal_status_enum = sa.Enum('pending', 'accepted', 'ignored', 'expired', 'executed', name='signalstatus')
    signal_direction_enum = sa.Enum('long', 'short', 'close', 'reduce', 'hold', name='signaldirection')
    
    signal_type_enum.create(op.get_bind(), checkfirst=True)
    signal_priority_enum.create(op.get_bind(), checkfirst=True)
    signal_status_enum.create(op.get_bind(), checkfirst=True)
    signal_direction_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table(
        'bot_signals',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='SET NULL'), nullable=True),
        sa.Column('signal_type', signal_type_enum, nullable=False, index=True),
        sa.Column('priority', signal_priority_enum, server_default='medium', nullable=False),
        sa.Column('status', signal_status_enum, server_default='pending', nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=True, index=True),
        sa.Column('direction', signal_direction_enum, nullable=True),
        # Trade suggestion details
        sa.Column('suggested_entry', sa.Float(), nullable=True),
        sa.Column('suggested_stop_loss', sa.Float(), nullable=True),
        sa.Column('suggested_take_profit', sa.Float(), nullable=True),
        sa.Column('suggested_quantity', sa.Integer(), nullable=True),
        sa.Column('risk_reward_ratio', sa.Float(), nullable=True),
        sa.Column('risk_percent', sa.Float(), nullable=True),
        # Market data at signal time
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('current_volume', sa.Float(), nullable=True),
        # Signal content
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        # ML/Analysis metadata
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('ml_model_used', sa.String(50), nullable=True),
        sa.Column('technical_indicators', sa.JSON(), nullable=True),
        # Source tracking
        sa.Column('source', sa.String(50), nullable=False, server_default='bot'),
        sa.Column('source_alert_id', sa.Integer(), sa.ForeignKey('alerts.id', ondelete='SET NULL'), nullable=True),
        # User action tracking
        sa.Column('user_action_at', sa.DateTime(), nullable=True),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('resulting_trade_id', sa.Integer(), sa.ForeignKey('trades.id', ondelete='SET NULL'), nullable=True),
        # Validity
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # ===========================================
    # 12. BOT_REPORTS TABLE
    # ===========================================
    op.create_table(
        'bot_reports',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False, index=True),
        sa.Column('report_date', sa.DateTime(), nullable=False, index=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('total_signals', sa.Integer(), default=0),
        sa.Column('trades_suggested', sa.Integer(), default=0),
        sa.Column('alerts_triggered', sa.Integer(), default=0),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_bot_reports_user_id', 'bot_reports', ['user_id'])


def downgrade() -> None:
    """Drop all tables in reverse order."""
    
    # Drop tables (reverse order of creation for FK constraints)
    op.drop_table('bot_reports')
    op.drop_table('bot_signals')
    op.drop_table('alerts')
    op.drop_table('watchlist_symbols')
    op.drop_table('watchlists')
    op.drop_table('fx_transactions')
    op.drop_table('cash_balances')
    op.drop_table('trades')
    op.drop_table('positions')
    op.drop_table('portfolios')
    op.drop_table('user_settings')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS signaldirection')
    op.execute('DROP TYPE IF EXISTS signalstatus')
    op.execute('DROP TYPE IF EXISTS signalpriority')
    op.execute('DROP TYPE IF EXISTS signaltype')
    op.execute('DROP TYPE IF EXISTS alertstatus')
    op.execute('DROP TYPE IF EXISTS alerttype')
    op.execute('DROP TYPE IF EXISTS tradestatus')
    op.execute('DROP TYPE IF EXISTS ordertype')
    op.execute('DROP TYPE IF EXISTS tradetype')
    op.execute('DROP TYPE IF EXISTS riskprofile')
