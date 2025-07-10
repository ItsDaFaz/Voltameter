"""
Revision ID: add_guild_multipliers
Revises: e9a8f844d9a0
Create Date: 2025-06-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_guild_multipliers'
down_revision = 'e9a8f844d9a0'
#down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to guilds
    op.add_column('guilds', sa.Column('text_multiplier', sa.Integer(), nullable=True))
    op.add_column('guilds', sa.Column('in_voice_boost_multiplier', sa.Integer(), nullable=True))

    # Add a new temporary column for the array
    op.add_column('members', sa.Column('guild_id_array', postgresql.ARRAY(sa.BigInteger()), nullable=True))

    # Copy old guild_id into the new array column
    op.execute("UPDATE members SET guild_id_array = ARRAY[guild_id]")

    # Drop the old foreign key constraint if it exists
    # with op.batch_alter_table('members') as batch_op:
    #     batch_op.drop_constraint('members_guild_id_fkey', type_='foreignkey')

    # Drop the old column and rename the new one
    op.drop_column('members', 'guild_id')
    op.alter_column('members', 'guild_id_array', new_column_name='guild_id', existing_type=postgresql.ARRAY(sa.BigInteger()), nullable=False)

def downgrade():
    # Remove new columns from guilds
    op.drop_column('guilds', 'text_multiplier')
    op.drop_column('guilds', 'in_voice_boost_multiplier')

    # Add back the old column
    op.add_column('members', sa.Column('guild_id_old', sa.BigInteger(), nullable=True))

    # Copy the first element of the array back to the old column
    op.execute("UPDATE members SET guild_id_old = guild_id[1]")

    # Drop the array column and rename the old one back
    op.drop_column('members', 'guild_id')
    op.alter_column('members', 'guild_id_old', new_column_name='guild_id', existing_type=sa.BigInteger(), nullable=False)

    # Re-add the foreign key constraint
    with op.batch_alter_table('members') as batch_op:
        batch_op.create_foreign_key('members_guild_id_fkey', 'guilds', ['guild_id'], ['id'])
