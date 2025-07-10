from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, BigInteger, String, Table
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy import ARRAY
Base = declarative_base()

# Add this association table
member_guild_association = Table(
    'member_guild_association',
    Base.metadata,
    Column('member_id', BigInteger, ForeignKey('members.id'), primary_key=True),
    Column('guild_id', BigInteger, ForeignKey('guilds.id'), primary_key=True)
)
class Guild(Base):
    __tablename__ = "guilds"
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    config = Column(MutableDict.as_mutable(JSONB), default=dict)
    
    # Updated relationship (now many-to-many)
    members = relationship(
        "Member",
        secondary=member_guild_association,
        back_populates="guilds",  # Matches Member.guilds
    )
    messages = relationship("Message", back_populates="guild")


class Member(Base):
    __tablename__ = "members"
    id = Column(BigInteger, primary_key=True, index=True)
    
    # Removed guild_id (now handled by association table)
    guilds = relationship(
        "Guild",
        secondary=member_guild_association,
        back_populates="members",  # Matches Guild.members
    )
    messages = relationship("Message", back_populates="author")


class Message(Base):
    __tablename__ = 'messages'
    id = Column(BigInteger, primary_key=True, index=True)
    author_id = Column(BigInteger, ForeignKey('members.id'))
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))  
    timestamp = Column(DateTime(timezone=True), nullable=False)
    guild = relationship('Guild', back_populates='messages')
    author = relationship('Member', back_populates='messages')
