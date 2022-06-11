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


TEST_DB = [
    {
        'uid': 42,
        'feed': 'https://feeds.feedburner.com/PythonInsider',
        'last_posts': 'eed88bab961aeadf2a7fcad594630f01 /// 1264ffbb3b77e31eeb8d97e167e4df3a',
        'last_check': datetime.fromisoformat('2022-06-06 17:33:00'),
        'summary': True, 'date': True, 'link': True, 'short': 'python'
    },
    {
        'uid': 42,
        'feed': 'https://www.wired.com/feed/category/business/latest/rss',
        'last_posts': 'c80aa8404ad0825822273e1897b9dcac /// 9fcac0d44dae6aaee0b5567a490d0748',
        'last_check': datetime.fromisoformat('2022-06-07 11:00:00'),
        'summary': True, 'date': True, 'link': True, 'short': None
    },
    {
        'uid': 9999,
        'feed': 'https://www.wired.com/feed/category/culture/latest/rss',
        'last_posts': '76ad4e66532c683ca2e41048fe234ec3 /// fa0aaf1980f2f19b297ad8b669974a4f',
        'last_check': datetime.fromisoformat('2022-06-07 10:00:00'),
        'summary': False, 'date': False, 'link': False, 'short': None
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
        # db
        cls.db_uri = pathlib.Path(__file__).resolve().parent / "database.sqlite3"
        cls.db = sqlalchemy.create_engine(f"sqlite:///{cls.db_uri}", future=True)

        cls.SQLSession = sessionmaker(cls.db)

        if cls.db_uri.exists():
            cls.db_uri.unlink()
        SQLAlchemyBase.metadata.create_all(cls.db)

        with cls.SQLSession() as session:
            for data in TEST_DB:
                new_entry = FeedsDB(
                    uid=data['uid'], feed=data['feed'],
                    last_posts=data['last_posts'], last_check=data['last_check'],
                    summary=data['summary'], date=data['date'], link=data['link'],
                    short=data['short']
                )
                session.add(new_entry)
            else:
                session.commit()

        # feedparser
        with open(pathlib.Path(__file__).resolve().parent / 'feed.json') as f:
            cls.feed_data = json.load(f)
            cls.post_data = cls.feed_data['entries'][9]
        """
        cls.db_entry = Mock()
        cls.db_entry.id = 1
        cls.db_entry.uid = TEST_DB[0]['uid']
        cls.db_entry.feed = TEST_DB[0]['feed']
        cls.db_entry.last_posts = TEST_DB[0]['last_posts']
        cls.db_entry.last_check = TEST_DB[0]['last_check']
        cls.db_entry.summary = TEST_DB[0]['summary']
        cls.db_entry.date = TEST_DB[0]['date']
        cls.db_entry.link = TEST_DB[0]['link']
        cls.db_entry.short = TEST_DB[0]['short']

        cls.feed = Mock()
        cls.feed.href = cls.feed_data['href']

        cls.post = Mock()
        cls.post.title = cls.post_data['title']
        cls.post.summary = cls.post_data['summary']
        cls.post.published_parsed = tuple(cls.post_data['published_parsed'])
        cls.post.link = cls.post_data['link']
        """

    @classmethod
    def tearDownClass(cls):
        cls.db_uri.unlink()
