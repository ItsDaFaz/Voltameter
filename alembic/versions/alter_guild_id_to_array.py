from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'alter_guild_id_to_array'
down_revision = 'consolidate_guild_config'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass