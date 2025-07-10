from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'drop_config_columns'
down_revision = 'add_guild_multipliers'
branch_labels = None
depends_on = None

def upgrade():
    # Drop the old config columns
    with op.batch_alter_table('guilds') as batch_op:
        batch_op.drop_column('admin_role_id_list')
        batch_op.drop_column('text_channels_list')
        batch_op.drop_column('forum_channels_list')
        batch_op.drop_column('destination_channel_id')
        batch_op.drop_column('destination_channel_id_dev')
        batch_op.drop_column('text_multiplier')
        batch_op.drop_column('in_voice_boost_multiplier')

    # Add the new JSONB config column
    op.add_column('guilds', sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade():
    # Re-add the old config columns
    with op.batch_alter_table('guilds') as batch_op:
        batch_op.add_column(sa.Column('admin_role_id_list', postgresql.ARRAY(sa.BigInteger()), nullable=True))
        batch_op.add_column(sa.Column('text_channels_list', postgresql.ARRAY(sa.BigInteger()), nullable=True))
        batch_op.add_column(sa.Column('forum_channels_list', postgresql.ARRAY(sa.BigInteger()), nullable=True))
        batch_op.add_column(sa.Column('destination_channel_id', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('destination_channel_id_dev', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('text_multiplier', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('in_voice_boost_multiplier', sa.Integer(), nullable=True))

    # Drop the new JSONB config column
    op.drop_column('guilds', 'config')