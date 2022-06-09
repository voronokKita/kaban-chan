from datetime import datetime
import sys
import pathlib
import json
import unittest
from unittest.mock import Mock

import sqlalchemy
from sqlalchemy.orm import sessionmaker

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if BASE_DIR not in sys.path:
    sys.path.append(str(BASE_DIR))

from kaban.settings import SQLAlchemyBase, FeedsDB, WebhookDB
from kaban.settings import MASTER_UID


TEST_DB = [
    {
        'uid': MASTER_UID,
        'feed': 'https://feeds.feedburner.com/PythonInsider',
        'last_posts': 'eed88bab961aeadf2a7fcad594630f01 /// 1264ffbb3b77e31eeb8d97e167e4df3a',
        'last_check': datetime.fromisoformat('2022-06-06 17:33:00'),
        'summary': True, 'date': True, 'link': True, 'short': None
    },
    {
        'uid': MASTER_UID,
        'feed': 'https://www.wired.com/feed/category/business/latest/rss',
        'last_posts': 'c80aa8404ad0825822273e1897b9dcac /// 9fcac0d44dae6aaee0b5567a490d0748',
        'last_check': datetime.fromisoformat('2022-06-07 11:00:00'),
        'summary': True, 'date': True, 'link': True, 'short': None
    },
    {
        'uid': MASTER_UID,
        'feed': 'https://www.wired.com/feed/category/culture/latest/rss',
        'last_posts': '76ad4e66532c683ca2e41048fe234ec3 /// fa0aaf1980f2f19b297ad8b669974a4f',
        'last_check': datetime.fromisoformat('2022-06-07 10:00:00'),
        'summary': True, 'date': True, 'link': True, 'short': None
    },
    {
        'uid': 13000000000,
        'feed': 'https://www.wired.com/feed/category/science/latest/rss',
        'last_posts': '78f5b21fb5214a338635c0f6a158f057',
        'last_check': datetime.fromisoformat('2022-06-07 12:00:00'),
        'summary': True, 'date': True, 'link': True, 'short': None
    },
]

class Fixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # <db>
        cls.test_db = TEST_DB
        cls.db_uri = pathlib.Path(__file__).resolve().parent / "database.sqlite3"
        cls.db = sqlalchemy.create_engine(f"sqlite:///{cls.db_uri}", future=True)

        cls.SQLSession = sessionmaker(cls.db)

        if cls.db_uri.exists():
            cls.db_uri.unlink()
        SQLAlchemyBase.metadata.create_all(cls.db)

        with cls.SQLSession() as session:
            for data in cls.test_db:
                new_entry = FeedsDB(
                    uid=data['uid'], feed=data['feed'],
                    last_posts=data['last_posts'], last_check=data['last_check'],
                    summary=data['summary'], date=data['date'], link=data['link'],
                    short=data['short']
                )
                session.add(new_entry)
            else:
                session.commit()
        # </db>

        # <feedparser>
        with open(pathlib.Path(__file__).resolve().parent / 'feed.json') as f:
            feed = json.load(f)
            post = feed['entries'][9]

        cls.post = Mock()
        cls.post.title = post['title']
        cls.post.summary = post['summary']
        cls.post.published_parsed = post['published_parsed']
        cls.post.link = post['link']
        # </feedparser>

    @classmethod
    def tearDownClass(cls):
        cls.db_uri.unlink()
