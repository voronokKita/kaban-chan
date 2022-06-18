from datetime import datetime
import json
import pathlib
import sys
import unittest
from unittest.mock import Mock

import telebot
import sqlalchemy
from sqlalchemy.orm import sessionmaker

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from kaban.settings import MASTER_UID
from kaban.database import SQLAlchemyBase, FeedsDB


# last one should be the MASTER_UID
TEST_DB = [
    {
        'uid': 42,
        'feed': 'https://feeds.feedburner.com/PythonInsider',
        'last_posts': 'eed88bab961aeadf2a7fcad594630f01 /// 1264ffbb3b77e31eeb8d97e167e4df3a',
        'last_check': datetime.fromisoformat('2022-01-13 10:00:00'),
        'summary': True, 'date': True, 'link': True, 'short': 'python'
    },
    {
        'uid': 42,
        'feed': 'https://www.wired.com/feed/category/business/latest/rss',
        'last_posts': 'c80aa8404ad0825822273e1897b9dcac /// 9fcac0d44dae6aaee0b5567a490d0748',
        'last_check': datetime.fromisoformat('2022-01-13 10:00:00'),
        'summary': True, 'date': True, 'link': True, 'short': None
    },
    {
        'uid': 9999,
        'feed': 'https://www.wired.com/feed/category/culture/latest/rss',
        'last_posts': '76ad4e66532c683ca2e41048fe234ec3 /// fa0aaf1980f2f19b297ad8b669974a4f',
        'last_check': datetime.fromisoformat('2022-01-13 10:00:00'),
        'summary': False, 'date': False, 'link': False, 'short': None
    },
    {
        'uid': MASTER_UID,
        'feed': 'https://www.wired.com/feed/category/science/latest/rss',
        'last_posts': '78f5b21fb5214a338635c0f6a158f057',
        'last_check': datetime.fromisoformat('2022-01-13 10:00:00'),
        'summary': True, 'date': True, 'link': True, 'short': None
    },
]
MOCK_DB_ENTRY = Mock()
MOCK_DB_ENTRY.id = 1
MOCK_DB_ENTRY.uid = TEST_DB[0]['uid']
MOCK_DB_ENTRY.feed = TEST_DB[0]['feed']
MOCK_DB_ENTRY.last_posts = TEST_DB[0]['last_posts']
MOCK_DB_ENTRY.last_check = TEST_DB[0]['last_check']
MOCK_DB_ENTRY.summary = TEST_DB[0]['summary']
MOCK_DB_ENTRY.date = TEST_DB[0]['date']
MOCK_DB_ENTRY.link = TEST_DB[0]['link']
MOCK_DB_ENTRY.short = TEST_DB[0]['short']


class MockDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_uri = BASE_DIR / 'tests' / 'fixtures' / 'database.sqlite3'
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

    @classmethod
    def tearDownClass(cls):
        cls.db_uri.unlink()


# feedparser
with open(BASE_DIR / 'tests' / 'fixtures' / 'feed.json') as f:
    FEED_DATA = json.load(f)
    POST_DATA = FEED_DATA['entries'][9]

MOCK_POST = Mock()
MOCK_POST.title = POST_DATA['title']
MOCK_POST.summary = POST_DATA['summary']
MOCK_POST.published_parsed = tuple(POST_DATA['published_parsed'])
MOCK_POST.link = POST_DATA['link']

MOCK_FEED = Mock()
MOCK_FEED.href = FEED_DATA['href']
MOCK_FEED.entries = [MOCK_POST]


# telegram load json
with open(BASE_DIR / 'tests' / 'fixtures' / 'tg_request.json') as f:
    TG_REQUEST = f.read().strip()


def make_update(s: str) -> telebot.types.Update:
    tg_request = json.loads(TG_REQUEST)
    tg_request['message']['text'] = s
    request = json.dumps(tg_request)
    update = telebot.types.Update.de_json(request)
    return update


def make_request(s: str) -> str:
    tg_request = json.loads(TG_REQUEST)
    tg_request['message']['text'] = s
    request = json.dumps(tg_request)
    return request


# clear mock objects
def reset_mock(*mock_list) -> None:
    [mock.reset_mock() for mock in mock_list]
