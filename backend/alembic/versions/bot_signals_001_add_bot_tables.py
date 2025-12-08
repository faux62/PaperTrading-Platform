"""Add bot signals and reports tables

Revision ID: bot_signals_001
Revises: 20251207_add_native_currency
Create Date: 2025-12-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bot_signals_001'
down_revision: Union[str, None] = '20251207_add_native_currency'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create bot_signals table
    op.create_table(
        'bot_signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=True),
        
        # Signal identification
        sa.Column('signal_type', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        
        # Symbol info
        sa.Column('symbol', sa.String(20), nullable=True),
        sa.Column('direction', sa.String(20), nullable=True),
        
        # Trade suggestion details
        sa.Column('suggested_entry', sa.Float(), nullable=True),
        sa.Column('suggested_stop_loss', sa.Float(), nullable=True),
        sa.Column('suggested_take_profit', sa.Float(), nullable=True),
        sa.Column('suggested_quantity', sa.Integer(), nullable=True),
        sa.Column('risk_reward_ratio', sa.Float(), nullable=True),
        sa.Column('risk_percent', sa.Float(), nullable=True),
        
        # Current market data
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('current_volume', sa.Float(), nullable=True),
        
        # Signal content
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        
        # ML metadata
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('ml_model_used', sa.String(50), nullable=True),
        sa.Column('technical_indicators', sa.JSON(), nullable=True),
        
        # Source tracking
        sa.Column('source', sa.String(50), nullable=False, server_default='bot'),
        sa.Column('source_alert_id', sa.Integer(), nullable=True),
        
        # User action tracking
        sa.Column('user_action_at', sa.DateTime(), nullable=True),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('resulting_trade_id', sa.Integer(), nullable=True),
        
        # Validity
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        
        # Primary key
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for bot_signals
    op.create_index('ix_bot_signals_user_id', 'bot_signals', ['user_id'])
    op.create_index('ix_bot_signals_signal_type', 'bot_signals', ['signal_type'])
    op.create_index('ix_bot_signals_status', 'bot_signals', ['status'])
    op.create_index('ix_bot_signals_symbol', 'bot_signals', ['symbol'])
    op.create_index('ix_bot_signals_created_at', 'bot_signals', ['created_at'])
    
    # Create foreign keys for bot_signals
    op.create_foreign_key(
        'fk_bot_signals_user_id',
        'bot_signals', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_bot_signals_portfolio_id',
        'bot_signals', 'portfolios',
        ['portfolio_id'], ['id'],
        ondelete='SET NULL'
    )
    # Note: FK to alerts table removed - alerts table may not exist yet
    # op.create_foreign_key(
    #     'fk_bot_signals_source_alert_id',
    #     'bot_signals', 'alerts',
    #     ['source_alert_id'], ['id'],
    #     ondelete='SET NULL'
    # )
    op.create_foreign_key(
        'fk_bot_signals_resulting_trade_id',
        'bot_signals', 'trades',
        ['resulting_trade_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create bot_reports table
    op.create_table(
        'bot_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Report type
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('report_date', sa.DateTime(), nullable=False),
        
        # Content
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        
        # Summary stats
        sa.Column('total_signals', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trades_suggested', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('alerts_triggered', sa.Integer(), nullable=False, server_default='0'),
        
        # Read status
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        
        # Primary key
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for bot_reports
    op.create_index('ix_bot_reports_user_id', 'bot_reports', ['user_id'])
    op.create_index('ix_bot_reports_report_type', 'bot_reports', ['report_type'])
    op.create_index('ix_bot_reports_report_date', 'bot_reports', ['report_date'])
    
    # Create foreign key for bot_reports
    op.create_foreign_key(
        'fk_bot_reports_user_id',
        'bot_reports', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Drop foreign keys first
    op.drop_constraint('fk_bot_reports_user_id', 'bot_reports', type_='foreignkey')
    op.drop_constraint('fk_bot_signals_resulting_trade_id', 'bot_signals', type_='foreignkey')
    # op.drop_constraint('fk_bot_signals_source_alert_id', 'bot_signals', type_='foreignkey')
    op.drop_constraint('fk_bot_signals_portfolio_id', 'bot_signals', type_='foreignkey')
    op.drop_constraint('fk_bot_signals_user_id', 'bot_signals', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_bot_reports_report_date', 'bot_reports')
    op.drop_index('ix_bot_reports_report_type', 'bot_reports')
    op.drop_index('ix_bot_reports_user_id', 'bot_reports')
    op.drop_index('ix_bot_signals_created_at', 'bot_signals')
    op.drop_index('ix_bot_signals_symbol', 'bot_signals')
    op.drop_index('ix_bot_signals_status', 'bot_signals')
    op.drop_index('ix_bot_signals_signal_type', 'bot_signals')
    op.drop_index('ix_bot_signals_user_id', 'bot_signals')
    
    # Drop tables
    op.drop_table('bot_reports')
    op.drop_table('bot_signals')
