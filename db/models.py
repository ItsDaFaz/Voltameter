from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, BigInteger,ARRAY, String
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Guild(Base):
    __tablename__ = 'guilds'
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    admin_role_id_list = Column(ARRAY(BigInteger))
    text_channels_list = Column(ARRAY(BigInteger))
    forum_channels_list = Column(ARRAY(BigInteger))
    destination_channel_id = Column(BigInteger, nullable=True)
    destination_channel_id_dev = Column(BigInteger, nullable=True)
    members = relationship('Member', back_populates='guild')
    messages = relationship('Message', back_populates='guild')
    

class Member(Base):
    __tablename__ = 'members'
    id = Column(BigInteger, primary_key=True, index=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'), nullable=False)
    messages = relationship('Message', back_populates='author')
    guild = relationship('Guild', back_populates='members')

class Message(Base):
    __tablename__ = 'messages'
    id = Column(BigInteger, primary_key=True, index=True)
    author_id = Column(BigInteger, ForeignKey('members.id'))
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))  
    timestamp = Column(DateTime(timezone=True), nullable=False)
    guild = relationship('Guild', back_populates='messages')
    author = relationship('Member', back_populates='messages')
