"""
Migration script to consolidate Guild config fields into a single JSONB column and update Member.guild_id type.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'consolidate_guild_config'
down_revision = 'drop_config_columns'  # Set this to the previous migration's revision ID
branch_labels = None
depends_on = None

def upgrade():
    # Remove old config columns from guilds
    with op.batch_alter_table('guilds') as batch_op:
        # batch_op.drop_column('admin_role_id_list')
        # batch_op.drop_column('text_channels_list')
        # batch_op.drop_column('forum_channels_list')
        # batch_op.drop_column('destination_channel_id')
        # batch_op.drop_column('destination_channel_id_dev')
        # batch_op.drop_column('text_multiplier')
        # batch_op.drop_column('in_voice_boost_multiplier')
        batch_op.add_column(sa.Column('configs', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Change members.guild_id from ARRAY(BigInteger) to BigInteger
    with op.batch_alter_table('members') as batch_op:
        batch_op.alter_column('guild_id',
            existing_type=postgresql.ARRAY(sa.BigInteger()),
            type_=sa.BigInteger(),
            postgresql_using='guild_id[1]')  # Take first element if array exists

def downgrade():
    # Revert members.guild_id to ARRAY(BigInteger)
    with op.batch_alter_table('members') as batch_op:
        batch_op.alter_column('guild_id',
            existing_type=sa.BigInteger(),
            type_=postgresql.ARRAY(sa.BigInteger()),
            postgresql_using='ARRAY[guild_id]')

    # Remove configs column and add back old columns to guilds
    with op.batch_alter_table('guilds') as batch_op:
        batch_op.drop_column('configs')
        batch_op.add_column(sa.Column('admin_role_id_list', postgresql.ARRAY(sa.BigInteger())))
        batch_op.add_column(sa.Column('text_channels_list', postgresql.ARRAY(sa.BigInteger())))
        batch_op.add_column(sa.Column('forum_channels_list', postgresql.ARRAY(sa.BigInteger())))
        batch_op.add_column(sa.Column('destination_channel_id', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('destination_channel_id_dev', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('text_multiplier', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('in_voice_boost_multiplier', sa.Integer(), nullable=True))
