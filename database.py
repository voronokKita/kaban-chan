from variables import *

import sqlalchemy
from sqlalchemy import Column
from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.orm import declarative_base

#? id user_id
#? id rss
# id user_id rss updated
# id time message
engine = sqlalchemy.create_engine(f"sqlite:///{DB}", echo=True, future=True)  #  +pysqlite
connection = engine.connect()
#metadata = sqlalchemy.MetaData()
SQLAlchemyBase = declarative_base()


class WebFeeds(SQLAlchemyBase):
    __tablename__ = "web_feeds"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    web_feed = Column(Text, nullable=False)
    last_check = Column(DateTime, nullable=True, default=None)
    def __repr__(self):
        return f"<feed #{self.id!r}>"


class Messages(SQLAlchemyBase):
    __tablename__ = "webhook_messages_socket"
    id = Column(Integer, primary_key=True)
    time = Column(DateTime, nullable=False)
    message = Column(Text, nullable=False)
    def __repr__(self):
        return f"<message #{self.id!r}>"
