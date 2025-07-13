"""drop config from guild

Revision ID: 634699f0a803
Revises: ce511d803000
Create Date: 2025-07-13 23:32:16.921372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '634699f0a803'
down_revision: Union[str, None] = 'ce511d803000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('guilds', 'config')
    pass


def downgrade() -> None:
    op.add_column('guilds', sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))
    # Note: Downgrading JSONB data is not straightforward, so we leave it as
    pass
