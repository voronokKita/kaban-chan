import sys
import pathlib
import unittest
from unittest.mock import Mock, patch

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if BASE_DIR not in sys.path:
    sys.path.append(str(BASE_DIR))

import kaban
from kaban.settings import DataAlreadyExists, FeedFormatError

from tests.fixtures.fixtures import Fixtures, TEST_DB


class TestPostSender(unittest.TestCase):
    def setUpClass(self):
        self.db_entry = Mock()
        self.db_entry.short = 'shortcut'
        self.db_entry.summary = True
        self.db_entry.date = True
        self.db_entry.link = True

    def NormalCase(self):
        kaban.helpers.send_a_post('bot', self.post, self.db_entry, 'dummy')


class TestFeedCheckOut(Fixtures):
    @patch('kaban.helpers.SQLSession')
    def test_feed_exists(self, mock_session):
        mock_session.return_value = self.SQLSession()
        with self.assertRaises(DataAlreadyExists):
            kaban.helpers.check_out_feed(TEST_DB[0]['feed'], TEST_DB[0]['uid'], first_time=False)

    @patch('kaban.helpers.feedparser')
    @patch('kaban.helpers.SQLSession')
    def test_feed_dont_exists(self, mock_session, mock_feedparser):
        mock_feedparser.parse.return_value = None
        mock_session.return_value = self.SQLSession()
        kaban.helpers.check_out_feed('dummy', 999, first_time=False)
        mock_session.assert_called_once()
        kaban.helpers.check_out_feed(TEST_DB[0]['feed'], 999, first_time=False)
        kaban.helpers.check_out_feed('dummy', TEST_DB[0]['uid'], first_time=False)
        mock_feedparser.parse.assert_not_called()

    @patch('kaban.helpers.feedparser')
    @patch('kaban.helpers.SQLSession')
    def test_feed_parser(self, mock_session, mock_feedparser):
        mock_session.return_value = self.SQLSession()
        post = Mock()
        post.published_parsed = True
        post.title = True
        parsed_feed = Mock()
        parsed_feed.entries = [post]
        parsed_feed.href = True

        mock_feedparser.parse.return_value = parsed_feed
        kaban.helpers.check_out_feed('dummy', 999)
        mock_feedparser.parse.assert_called_once()

    @patch('kaban.helpers.feedparser')
    @patch('kaban.helpers.SQLSession')
    def test_feed_parser_error(self, mock_session, mock_feedparser):
        mock_session.return_value = self.SQLSession()

        mock_feedparser.parse.return_value = None
        with self.assertRaises(FeedFormatError):
            kaban.helpers.check_out_feed('dummy', 999)

        parsed_feed = Mock()
        parsed_feed.entries = []
        mock_feedparser.parse.return_value = parsed_feed
        with self.assertRaises(FeedFormatError):
            kaban.helpers.check_out_feed('dummy', 999)

        post = Mock()
        post.published_parsed = None
        post.title = None
        parsed_feed = Mock()
        parsed_feed.entries = [post]
        parsed_feed.href = None
        mock_feedparser.parse.return_value = parsed_feed
        with self.assertRaises(FeedFormatError):
            kaban.helpers.check_out_feed('dummy', 999)

        mock_feedparser.parse.side_effect = Exception
        with self.assertRaises(Exception):
            kaban.helpers.check_out_feed('dummy', 999)


class TestSum(unittest.TestCase):
    def setUp(self):
        self.sum = kaban.helpers.sum  # makeSomethingDB

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
