from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, BigInteger, String
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
Base = declarative_base()


class Guild(Base):
    __tablename__ = 'guilds'
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    configs = Column(MutableDict.as_mutable(JSONB), default=dict)  # Consolidated config field
    members = relationship('Member', back_populates='guild')
    messages = relationship('Message', back_populates='guild')
    

class Member(Base):
    __tablename__ = 'members'
    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, nullable=False)  # Revert to BigInteger for now
    messages = relationship('Message', back_populates='author')
    # Removed ForeignKey constraint from guild_id, as it is now an array
    # Relationship to Guild may need to be rethought, as a member can now belong to multiple guilds
    # guild = relationship('Guild', back_populates='members')

class Message(Base):
    __tablename__ = 'messages'
    id = Column(BigInteger, primary_key=True, index=True)
    author_id = Column(BigInteger, ForeignKey('members.id'))
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))  
    timestamp = Column(DateTime(timezone=True), nullable=False)
    guild = relationship('Guild', back_populates='messages')
    author = relationship('Member', back_populates='messages')
