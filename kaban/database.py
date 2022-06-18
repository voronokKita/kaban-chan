from datetime import datetime

import sqlalchemy as sql
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from kaban.settings import BASE_DIR, SHORTCUT_LEN, Path, Engine


POSTS_TO_STORE = 50

DB_URI: Path = BASE_DIR / "resources" / "database.sqlite3"
db: Engine = sql.create_engine(f"sqlite:///{DB_URI}", future=True)
SQLSession = sessionmaker(db)
SQLAlchemyBase = declarative_base()


class FeedsDB(SQLAlchemyBase):
    __tablename__ = "feeds"
    id = sql.Column(sql.Integer, primary_key=True)
    uid = sql.Column(sql.Integer, index=True, nullable=False)
    feed = sql.Column(sql.Text, nullable=False)
    last_posts = sql.Column(sql.Text, nullable=False, default=' ')
    last_check = sql.Column(sql.DateTime, nullable=False, default=datetime.now)
    summary = sql.Column(sql.Boolean, nullable=False, default=True)
    date = sql.Column(sql.Boolean, nullable=False, default=True)
    link = sql.Column(sql.Boolean, nullable=False, default=True)
    short = sql.Column(sql.String(SHORTCUT_LEN), nullable=True, default=None)
    def __str__(self):
        return f"<feed entry #{self.id!r}>"


class WebhookDB(SQLAlchemyBase):
    __tablename__ = "webhook"
    id = sql.Column(sql.Integer, primary_key=True)
    data = sql.Column(sql.Text, nullable=False)
    def __str__(self):
        return f"<web message #{self.id!r}>"


if not DB_URI.exists():
    SQLAlchemyBase.metadata.create_all(db)
