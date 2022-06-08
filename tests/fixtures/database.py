from datetime import datetime
import sys
import pathlib

import sqlalchemy as sql
from sqlalchemy.orm import Session as SQLSession

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from kaban.settings import SQLAlchemyBase, FeedsDB

DB_URI = pathlib.Path(__file__).resolve().parent / "database.sqlite3"
db = sql.create_engine(f"sqlite:///{DB_URI}", future=True)


if not DB_URI.exists():
    test_db = [
        {
            'uid': 1266575762,
             'feed': 'https://feeds.feedburner.com/PythonInsider',
             'last_posts': 'eed88bab961aeadf2a7fcad594630f01 /// 1264ffbb3b77e31eeb8d97e167e4df3a',
             'last_check': datetime.fromisoformat('2022-06-06 17:33:00'),
             'summary': True, 'date': True, 'link': True, 'short': None
        },
        {
            'uid': 1266575762,
            'feed': 'https://www.wired.com/feed/category/busine',
            'last_posts': 'c80aa8404ad0825822273e1897b9dcac /// 9fcac0d44dae6aaee0b5567a490d0748',
            'last_check': datetime.fromisoformat('2022-06-07 11:00:00'),
            'summary': True, 'date': True, 'link': True, 'short': None
        },
        {
            'uid': 1266575762,
            'feed': 'https://www.wired.com/feed/category/cultur',
            'last_posts': '76ad4e66532c683ca2e41048fe234ec3 /// fa0aaf1980f2f19b297ad8b669974a4f',
            'last_check': datetime.fromisoformat('2022-06-07 10:00:00'),
            'summary': True, 'date': True, 'link': True, 'short': None
        },
        {
            'uid': 1266575762,
            'feed': 'https://www.wired.com/feed/category/scienc',
            'last_posts': '78f5b21fb5214a338635c0f6a158f057',
            'last_check': datetime.fromisoformat('2022-06-07 12:00:00'),
            'summary': True, 'date': True, 'link': True, 'short': None
        },
    ]

    SQLAlchemyBase.metadata.create_all(db)

    with SQLSession(db) as session:
        for data in test_db:
            new_entry = FeedsDB(
                uid=data['uid'], feed=data['feed'],
                last_posts=data['last_posts'], last_check=data['last_check'],
                summary=data['summary'], date=data['date'], link=data['link'],
                short=data['short']
            )
            session.add(new_entry)
        else:
            session.commit()
