"""Update portfolio fields for new requirements

Revision ID: 20251209_portfolio
Revises: 20251209_merge_heads
Create Date: 2025-12-09

Changes:
- Add strategy_period_weeks field (default 12 weeks)
- Change is_active from string to boolean
- Add check constraints for initial_capital (min 100, step 100)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251209_portfolio'
down_revision = '20251209_add_cash_balances'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add strategy_period_weeks column
    op.add_column('portfolios', sa.Column('strategy_period_weeks', sa.Integer(), nullable=True, server_default='12'))
    
    # Create a new boolean is_active_bool column
    op.add_column('portfolios', sa.Column('is_active_bool', sa.Boolean(), nullable=True, server_default='true'))
    
    # Migrate data from string is_active to boolean
    op.execute("""
        UPDATE portfolios 
        SET is_active_bool = CASE 
            WHEN is_active = 'active' THEN true 
            ELSE false 
        END
    """)
    
    # Set NOT NULL constraint
    op.alter_column('portfolios', 'is_active_bool', nullable=False)
    
    # Drop old column and rename new one
    op.drop_column('portfolios', 'is_active')
    op.alter_column('portfolios', 'is_active_bool', new_column_name='is_active')
    
    # Update initial_capital default to 10000 (100 * 100)
    op.alter_column('portfolios', 'initial_capital', 
                    server_default='10000.00')
    
    # Add check constraint for initial_capital (min 100, must be multiple of 100)
    op.create_check_constraint(
        'ck_portfolios_initial_capital_min',
        'portfolios',
        'initial_capital >= 100'
    )


def downgrade() -> None:
    # Drop check constraint
    op.drop_constraint('ck_portfolios_initial_capital_min', 'portfolios')
    
    # Revert initial_capital default
    op.alter_column('portfolios', 'initial_capital', 
                    server_default='100000.00')
    
    # Create string is_active column
    op.add_column('portfolios', sa.Column('is_active_str', sa.String(20), nullable=True, server_default='active'))
    
    # Migrate data back
    op.execute("""
        UPDATE portfolios 
        SET is_active_str = CASE 
            WHEN is_active = true THEN 'active' 
            ELSE 'archived' 
        END
    """)
    
    # Set NOT NULL and drop boolean column
    op.alter_column('portfolios', 'is_active_str', nullable=False)
    op.drop_column('portfolios', 'is_active')
    op.alter_column('portfolios', 'is_active_str', new_column_name='is_active')
    
    # Drop strategy_period_weeks column
    op.drop_column('portfolios', 'strategy_period_weeks')
