import sys
import pathlib
import unittest
from unittest.mock import Mock

from sqlalchemy.orm import Session as SQLSession

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if BASE_DIR not in sys.path:
    sys.path.append(str(BASE_DIR))

from kaban import helpers
from kaban.settings import FeedsDB

from tests.fixtures.database import db


class TestFeedCheckOut(unittest.TestCase):
    def setUp(self):
        self.check_out_feed = helpers.check_out_feed

    def foo(self):
        with SQLSession(db) as session:
            db_entry = session.query(FeedsDB).first()
        #result = self.check_out_feed(feed=db_entry.feed, uid=db_entry.uid, first_time=False)

class TestSum(unittest.TestCase):
    def setUp(self):
        self.sum = helpers.sum  # makeSomethingDB

    def tearDown(self):
        self.sum = None  # deleteSomethingDB

    def test_list_int(self):
        data = [5, 5, 5]
        result = self.sum(data)
        self.assertEqual(result, 15)

    def test_list_float(self):
        data = [5.5, 5.5, 5.5]
        result = self.sum(data)
        self.assertEqual(result, 16.5)


if __name__ == '__main__':
    unittest.main()
