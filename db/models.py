from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Member(Base):
    __tablename__ = 'members'
    id = Column(BigInteger, primary_key=True, index=True)
    # Add more attributes later
    messages = relationship('Message', back_populates='author')

class Message(Base):
    __tablename__ = 'messages'
    id = Column(BigInteger, primary_key=True, index=True)
    author_id = Column(BigInteger, ForeignKey('members.id'))
    timestamp = Column(DateTime(timezone=True), nullable=False)
    

    author = relationship('Member', back_populates='messages')
