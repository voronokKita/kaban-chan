from copy import deepcopy
from datetime import datetime
import hashlib
import pathlib
import sys
import time
import unittest
from unittest.mock import Mock, patch, ANY

from telebot.apihelper import ApiTelegramException

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from kaban import helpers
from kaban.database import FeedsDB
from kaban.settings import (
    DataAlreadyExists, FeedFormatError, FeedPreprocessError,
    CMD_SUMMARY, CMD_DATE, CMD_LINK, SHORTCUT_LEN,
    WRONG_TOKEN, UID_NOT_FOUND, BOT_BLOCKED, BOT_TIMEOUT
)
from tests.fixtures.fixtures import (
    MockDB, reset_mock, TEST_DB,
    MOCK_DB_ENTRY, MOCK_POST, MOCK_FEED
)


@patch('kaban.helpers.log')
@patch('kaban.helpers.time')
@patch('kaban.helpers.exit_signal')
@patch('kaban.helpers.delete_user')
class SendMessage(unittest.TestCase):
    def test_normal_case(self, *args):
        mock_bot = Mock()
        with patch('kaban.helpers.resend_message') as mock_resend:
            mock_resend.return_value = False
            helpers.send_message(mock_bot, 42, 'hello')

        mock_bot.send_message.assert_called_once()
        mock_resend.assert_not_called()

        reset_mock(*args)

    def test_exceptions(self, foo, mock_exit, bar, mock_log):
        mock_bot = Mock()
        wrong = 'A request to the Telegram API was unsuccessful. ' \
                'Error code: 400. Description: Unauthorized'
        exceptions = [
            {'descr': WRONG_TOKEN.pattern, 'log': f'wrong telegram token - {wrong}'},
            {'descr': UID_NOT_FOUND.pattern, 'log': 'user/chat not found; uid deleted'},
            {'descr': BOT_BLOCKED.pattern, 'log': 'bot blocked; uid deleted'},
            {'descr': BOT_TIMEOUT.pattern, 'log': 'telegram timeout'},
            {'descr': 'undefined', 'log': 'undefined telegram problem'},
            {'descr': 'broken', 'log': 'broken'},
        ]
        for _dict in exceptions:
            if _dict['descr'] == 'broken': exc = TypeError(_dict['descr'])
            else:
                exc = ApiTelegramException(
                    'foo', 'bar', {'error_code': 400, 'description': _dict['descr']}
                )
            mock_bot.send_message.side_effect = exc
            with patch('kaban.helpers.resend_message') as mock_resend:
                mock_resend.return_value = False
                helpers.send_message(mock_bot, 42, 'hello')

            if _dict['descr'] == WRONG_TOKEN.pattern:
                mock_exit.assert_called_once()
                mock_log.critical.assert_called_with(_dict['log'])
            elif _dict['descr'] == 'broken':
                mock_resend.assert_called_once()
            else:
                mock_resend.assert_called_once()
                mock_log.warning.assert_called_with(_dict['log'])
            mock_log.reset_mock()

        reset_mock(foo, mock_exit, bar, mock_log)

    def test_resend_message(self, mock_delete_user, foo, mock_time, bar):
        mock_bot = Mock()
        exc = ApiTelegramException(
            'foo', 'bar', {'error_code': 400, 'description': BOT_BLOCKED.pattern}
        )
        mock_bot.send_message.side_effect = exc
        helpers.send_message(mock_bot, 42, 'hello')

        self.assertEqual(mock_bot.send_message.call_count, 4)
        self.assertEqual(mock_time.sleep.call_count, 4)
        mock_delete_user.assert_called_once()

        reset_mock(mock_delete_user, foo, mock_time, bar)


@patch('kaban.helpers.feed_switcher')
@patch('kaban.helpers.send_message')
class PostSender(MockDB):
    def test_normal_case(self, mock_message, mock_switcher):
        mock_db_entry = deepcopy(MOCK_DB_ENTRY)
        mock_post = deepcopy(MOCK_POST)

        helpers.send_a_post('bot', mock_post, mock_db_entry, 'dummy-feed')
        mock_message.assert_called_with('bot', mock_db_entry.uid, ANY)
        mock_switcher.assert_not_called()

        reset_mock(mock_message, mock_switcher)

    def test_feed_switcher_calls(self, foo, mock_switcher):
        mock_db_entry = deepcopy(MOCK_DB_ENTRY)
        mock_db_entry.short = None
        mock_db_entry.date = False
        mock_post = deepcopy(MOCK_POST)
        mock_post.summary = None
        mock_post.link = None

        helpers.send_a_post('bot', mock_post, mock_db_entry, 'dummy-feed')
        mock_switcher.assert_called_with(mock_db_entry.uid, ANY, 'dummy-feed')
        self.assertEqual(mock_switcher.call_count, 2)

        reset_mock(foo, mock_switcher)


@patch('kaban.helpers.feedparser')
@patch('kaban.helpers.SQLSession')
class FeedCheckOut(MockDB):
    def test_feed_exists(self, mock_session, mock_feedparser):
        mock_session.return_value = self.SQLSession()
        with self.assertRaises(DataAlreadyExists):
            helpers.check_out_feed(
                TEST_DB[0]['feed'], TEST_DB[0]['uid'], first_time=False
            )
            mock_feedparser.parse.assert_not_called()

        reset_mock(mock_session, mock_feedparser)

    def test_feed_dont_exists(self, mock_session, foo):
        mock_session.return_value = self.SQLSession()
        helpers.check_out_feed('dummy-feed', 0, first_time=False)
        helpers.check_out_feed(TEST_DB[0]['feed'], 0, first_time=False)
        helpers.check_out_feed('dummy-feed', TEST_DB[0]['uid'], first_time=False)

        self.assertEqual(mock_session.call_count, 3)

        reset_mock(mock_session, foo)

    def test_feed_parser(self, mock_session, mock_feedparser):
        mock_feed = deepcopy(MOCK_FEED)
        mock_feedparser.parse.return_value = mock_feed
        mock_session.return_value = self.SQLSession()

        helpers.check_out_feed('dummy-feed', 0)
        mock_feedparser.parse.assert_called_once()

        reset_mock(mock_session, mock_feedparser)

    def test_feed_parser_errors(self, mock_session, mock_feedparser):
        mock_session.return_value = self.SQLSession()

        mock_feedparser.parse.return_value = None
        with self.assertRaises(FeedFormatError):
            helpers.check_out_feed('dummy-feed', 0)

        mock_feed = deepcopy(MOCK_FEED)
        mock_feed.entries[0].published_parsed = None
        mock_feed.entries[0].title = None
        mock_feedparser.parse.return_value = mock_feed
        with self.assertRaises(FeedFormatError):
            helpers.check_out_feed('dummy-feed', 0)

        mock_feed.entries = []
        mock_feedparser.parse.return_value = mock_feed
        with self.assertRaises(FeedFormatError):
            helpers.check_out_feed('dummy-feed', 0)

        mock_feedparser.parse.side_effect = Exception
        with self.assertRaises(Exception):
            helpers.check_out_feed('dummy-feed', 0)

        reset_mock(mock_session, mock_feedparser)


@patch('kaban.helpers.info')
@patch('kaban.helpers.new_feed_preprocess')
@patch('kaban.helpers.SQLSession')
class AddNewFeed(MockDB):
    def test_normal_case(self, mock_session, mock_feed_preprc, foo):
        mock_session.return_value = self.SQLSession()
        result = helpers.add_new_feed('bot', 142142, 'dummy-feed')

        self.assertEqual(result, 'New web feed added!')
        mock_feed_preprc.assert_called_with('bot', 142142, 'dummy-feed')

        with self.SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == 142142, FeedsDB.feed == 'dummy-feed'
            ).first()
            self.assertIsNotNone(db_entry)

        reset_mock(mock_session, mock_feed_preprc, foo)

    def test_except_case(self, mock_session, mock_feed_preprc, foo):
        mock_session.return_value = self.SQLSession()
        mock_feed_preprc.side_effect = FeedPreprocessError
        result = helpers.add_new_feed('bot', 142142, 'dummy-feed')

        self.assertIn('some issues', result)

        reset_mock(mock_session, mock_feed_preprc, foo)


@patch('kaban.helpers.log')
@patch('kaban.helpers.feedparser')
@patch('kaban.helpers.send_a_post')
@patch('kaban.helpers.SQLSession')
class NewFeedPreprocess(MockDB):
    def test_normal_case(self, mock_session, mock_poster, mock_feedparser, foo):
        mock_session.return_value = self.SQLSession()
        mock_post = deepcopy(MOCK_POST)
        mock_feedparser.parse().entries = [mock_post]
        post_title = hashlib.md5(
            mock_post.title.strip().encode()
        ).hexdigest()
        post_date = datetime.fromtimestamp(
            time.mktime(mock_post.published_parsed)
        )

        helpers.new_feed_preprocess('bot', TEST_DB[0]['uid'], TEST_DB[0]['feed'])
        mock_poster.assert_called_with('bot', mock_post, ANY, TEST_DB[0]['feed'])

        with self.SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == TEST_DB[0]['uid'],
                FeedsDB.feed == TEST_DB[0]['feed'],
            ).first()
            self.assertEqual(db_entry.last_posts, post_title)
            self.assertEqual(db_entry.last_check, post_date)

        reset_mock(mock_session, mock_poster, mock_feedparser, foo)

    def test_except_case(self, mock_session, *args):
        mock_session.return_value = self.SQLSession()
        with self.assertRaises(FeedPreprocessError):
            helpers.new_feed_preprocess('bot', TEST_DB[0]['uid'], None)

        reset_mock(mock_session, *args)


@patch('kaban.helpers.info')
@patch('kaban.helpers.SQLSession')
class DeleteFeed(MockDB):
    def test_normal_case(self, mock_session, foo):
        mock_session.return_value = self.SQLSession()
        result = helpers.delete_a_feed(TEST_DB[0]['feed'], TEST_DB[0]['uid'])
        self.assertEqual(result, "Done.")

        with self.SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == TEST_DB[0]['uid'],
                FeedsDB.feed == TEST_DB[0]['feed']
            ).first()
            self.assertIsNone(db_entry)

        reset_mock(mock_session, foo)

    def test_except_case(self, mock_session, foo):
        mock_session.return_value = self.SQLSession()
        result = helpers.delete_a_feed('dummy-feed', 142142)
        self.assertIn('Check for errors', result)

        reset_mock(mock_session, foo)


class ListUserFeeds(MockDB):
    def test_normal_case(self):
        with patch('kaban.helpers.SQLSession') as mock_session:
            mock_session.return_value = self.SQLSession()
            result = helpers.list_user_feeds(TEST_DB[0]['uid'])

            self.assertIn(TEST_DB[0]['feed'], result)
            self.assertIn(TEST_DB[1]['feed'], result)
            self.assertIn("summary: on, date: on, link: on", result)

            result2 = helpers.list_user_feeds(TEST_DB[2]['uid'])
            self.assertIn("summary: off, date: off, link: off", result2)


class FeedShortcut(MockDB):
    def test_normal_case(self):
        with patch('kaban.helpers.SQLSession') as mock_session:
            mock_session.return_value = self.SQLSession()
            helpers.feed_shortcut(TEST_DB[0]['uid'], '', TEST_DB[0]['feed'])
            helpers.feed_shortcut(TEST_DB[1]['uid'], 'wired/business', TEST_DB[1]['feed'])

        with self.SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == TEST_DB[0]['uid'],
                FeedsDB.feed == TEST_DB[0]['feed']
            ).first()
            self.assertEqual(db_entry.short, None)

            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == TEST_DB[1]['uid'],
                FeedsDB.feed == TEST_DB[1]['feed']
            ).first()
            self.assertEqual(db_entry.short, 'wired/business')

    def test_exception_case(self):
        with patch('kaban.helpers.SQLSession') as mock_session:
            mock_session.return_value = self.SQLSession()
            shortcut = 'c' * (SHORTCUT_LEN + 1)
            with self.assertRaises(IndexError):
                helpers.feed_shortcut(142142, shortcut, 'dummy-feed')


class FeedSwitcher(MockDB):
    def test_normal_case(self):
        with patch('kaban.helpers.SQLSession') as mock_session:
            mock_session.return_value = self.SQLSession()
            helpers.feed_switcher(TEST_DB[0]['uid'], CMD_SUMMARY, TEST_DB[0]['feed'])
            helpers.feed_switcher(TEST_DB[0]['uid'], CMD_DATE, TEST_DB[0]['feed'])
            helpers.feed_switcher(TEST_DB[0]['uid'], CMD_LINK, TEST_DB[0]['feed'])

        with self.SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == TEST_DB[0]['uid'],
                FeedsDB.feed == TEST_DB[0]['feed']
            ).first()
            self.assertTrue(db_entry.summary is False and
                            db_entry.date is False and
                            db_entry.link is False)


class DeleteUser(MockDB):
    def test_normal_case(self):
        with patch('kaban.helpers.SQLSession') as mock_session, \
                patch('kaban.helpers.delete_a_feed') as mock_delete_a_feed:
            mock_session.return_value = self.SQLSession()
            helpers.delete_user(TEST_DB[0]['uid'])

            expected = [TEST_DB[0]['uid'], TEST_DB[0]['uid']]
            result = [
                mock_delete_a_feed.call_args_list[0].args[1],
                mock_delete_a_feed.call_args_list[1].args[1]
            ]
            self.assertTrue(expected == result)


if __name__ == '__main__':
    unittest.main()
