"""
Revision ID: add_guild_multipliers_and_member_guildid_array
Revises: e9a8f844d9a0
Create Date: 2025-06-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_guild_multipliers_and_member_guildid_array'
down_revision = 'e9a8f844d9a0'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to guilds
    op.add_column('guilds', sa.Column('text_multiplier', sa.Integer(), nullable=True))
    op.add_column('guilds', sa.Column('in_voice_boost_multiplier', sa.Integer(), nullable=True))
    # Alter members.guild_id to ARRAY(BigInteger)
    op.alter_column('members', 'guild_id',
        existing_type=sa.BigInteger(),
        type_=postgresql.ARRAY(sa.BigInteger()),
        existing_nullable=False)
    # Remove foreign key constraint if it exists
    with op.batch_alter_table('members') as batch_op:
        batch_op.drop_constraint('members_guild_id_fkey', type_='foreignkey')

def downgrade():
    # Remove new columns from guilds
    op.drop_column('guilds', 'text_multiplier')
    op.drop_column('guilds', 'in_voice_boost_multiplier')
    # Revert members.guild_id to BigInteger
    op.alter_column('members', 'guild_id',
        existing_type=postgresql.ARRAY(sa.BigInteger()),
        type_=sa.BigInteger(),
        existing_nullable=False)
    # Re-add foreign key constraint
    with op.batch_alter_table('members') as batch_op:
        batch_op.create_foreign_key('members_guild_id_fkey', 'guilds', ['guild_id'], ['id'])
