"""add members guild association

Revision ID: ce511d803000
Revises: 9962839b15b4
Create Date: 2025-07-10 18:02:15.378316

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ce511d803000'
down_revision: Union[str, None] = '9962839b15b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # 1. Create the association table
    op.create_table(
        'member_guild_association',
        sa.Column('member_id', sa.BigInteger(), nullable=False),
        sa.Column('guild_id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guild_id'], ['guilds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('member_id', 'guild_id')
    )

    # 2. Create temporary function to unnest array and insert
    op.execute("""
    CREATE OR REPLACE FUNCTION migrate_guild_ids()
    RETURNS void AS $$
    DECLARE
        member_record RECORD;
        guild_id_val BIGINT;
    BEGIN
        FOR member_record IN SELECT id, guild_id FROM members LOOP
            FOREACH guild_id_val IN ARRAY member_record.guild_id LOOP
                INSERT INTO member_guild_association (member_id, guild_id)
                VALUES (member_record.id, guild_id_val)
                ON CONFLICT DO NOTHING;
            END LOOP;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # 3. Execute the migration function
    op.execute("SELECT migrate_guild_ids()")

    # 4. Drop the temporary function
    op.execute("DROP FUNCTION migrate_guild_ids()")

    # 5. Drop the old array column
    op.drop_column('members', 'guild_id')

    # 6. Add index for performance
    op.create_index('ix_member_guild_association_guild_id', 'member_guild_association', ['guild_id'])

def downgrade():
    # 1. Re-add the guild_id array column
    op.add_column(
        'members',
        sa.Column('guild_id', postgresql.ARRAY(sa.BigInteger()), nullable=False, server_default='{}')
    )

    # 2. Migrate data back from association table to array
    op.execute("""
    UPDATE members m
    SET guild_id = (
        SELECT array_agg(guild_id)
        FROM member_guild_association a
        WHERE a.member_id = m.id
    )
    """)

    # 3. Drop the association table
    op.drop_table('member_guild_association')