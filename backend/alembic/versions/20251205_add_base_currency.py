"""Add base_currency to users

Revision ID: 20251205_add_base_currency
Revises: 20251202_154715_initial_migration
Create Date: 2025-12-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251205_add_base_currency'
down_revision: Union[str, None] = 'dcb9600fc8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add base_currency column with default USD
    op.add_column('users', sa.Column('base_currency', sa.String(3), nullable=False, server_default='USD'))


def downgrade() -> None:
    op.drop_column('users', 'base_currency')
