"""add_alternative_source_url

Revision ID: 6431e9c20a05
Revises: 068070344237
Create Date: 2026-06-16 12:36:23.071025

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6431e9c20a05'
down_revision: Union[str, Sequence[str], None] = '068070344237'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('stories', sa.Column('alternative_source_url', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('stories', 'alternative_source_url')
