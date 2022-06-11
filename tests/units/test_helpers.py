from datetime import datetime
import hashlib
import time
import sys
import pathlib
import unittest
from unittest.mock import Mock, patch, ANY

from telebot.apihelper import ApiTelegramException

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if BASE_DIR not in sys.path:
    sys.path.append(str(BASE_DIR))

import kaban
from kaban import helpers
from kaban.settings import DataAlreadyExists, FeedFormatError, FeedPreprocessError
from kaban.settings import FeedsDB, CMD_SUMMARY, CMD_DATE, CMD_LINK, SHORTCUT_LEN
from kaban.settings import WRONG_TOKEN, UID_NOT_FOUND, BOT_BLOCKED, BOT_TIMEOUT

from tests.fixtures.fixtures import Fixtures, TEST_DB


class SendMessage(unittest.TestCase):
    @staticmethod
    def test_normal_case():
        with patch('kaban.helpers.log') as mock_log, \
                patch('kaban.helpers.delete_user') as mock_delete_user, \
                patch('kaban.helpers.resend_message') as mock_resend:
            mock_resend.return_value = False
            mock_bot = Mock()
            helpers.send_message(mock_bot, 42, 'hello')
            mock_bot.send_message.assert_called_once()
            mock_resend.assert_not_called()

    def test_exceptions(self):
        with patch('kaban.helpers.exit_signal') as mock_exit, \
                patch('kaban.helpers.log') as mock_log, \
                patch('kaban.helpers.delete_user') as mock_delete_user, \
                patch('kaban.helpers.resend_message') as mock_resend:
            mock_resend.return_value = False
            mock_bot = Mock()
            exceptions = [
                WRONG_TOKEN.pattern,
                UID_NOT_FOUND.pattern,
                BOT_BLOCKED.pattern,
                BOT_TIMEOUT.pattern,
                'undefined',
                'broken'
            ]
            for i, description in enumerate(exceptions):
                if description == 'broken': exc = TypeError(description)
                else:
                    exc = ApiTelegramException(
                        'foo', 'bar', {'error_code': 400, 'description': description}
                    )
                mock_bot.send_message.side_effect = exc
                helpers.send_message(mock_bot, 42, 'hello')
                if i == 0: mock_exit.assert_called_once()
                else: self.assertEqual(mock_resend.call_count, i)

    def test_resend_message(self):
        with patch('kaban.helpers.log') as mock_log, \
                patch('kaban.helpers.time') as mock_time, \
                patch('kaban.helpers.delete_user') as mock_delete_user:
            mock_bot = Mock()
            exc = ApiTelegramException(
                'foo', 'bar', {'error_code': 400, 'description': BOT_BLOCKED.pattern}
            )
            mock_bot.send_message.side_effect = exc
            helpers.send_message(mock_bot, 42, 'hello')

            self.assertEqual(mock_bot.send_message.call_count, 4)
            self.assertEqual(mock_time.sleep.call_count, 4)
            mock_delete_user.assert_called_once()


class PostSender(Fixtures):
    def test_normal_case(self):
        db_entry = Mock()
        db_entry.short = TEST_DB[0]['short']
        db_entry.summary = TEST_DB[0]['summary']
        db_entry.date = TEST_DB[0]['date']
        db_entry.link = TEST_DB[0]['link']
        db_entry.uid = TEST_DB[0]['uid']
        post = Mock()
        post.title = self.post_data['title']
        post.summary = self.post_data['summary']
        post.published_parsed = tuple(self.post_data['published_parsed'])
        post.link = self.post_data['link']

        with patch('kaban.helpers.send_message') as mock_sender_func, \
                patch('kaban.helpers.feed_switcher') as mock_switcher:
            helpers.send_a_post('bot', post, db_entry, 'dummy-feed')
            mock_sender_func.assert_called_with('bot', db_entry.uid, ANY)
            mock_switcher.assert_not_called()

    def test_feed_switcher_calls(self):
        db_entry = Mock()
        db_entry.short = None
        db_entry.date = False
        db_entry.uid = TEST_DB[0]['uid']
        post = Mock()
        post.title = self.post_data['title']
        post.summary = None
        post.link = None

        with patch('kaban.helpers.send_message') as mock_sender_func, \
                patch('kaban.helpers.feed_switcher') as mock_switcher:
            helpers.send_a_post('bot', post, db_entry, 'dummy-feed')
            mock_switcher.assert_called_with(db_entry.uid, ANY, 'dummy-feed')
            self.assertEqual(mock_switcher.call_count, 2)


class FeedCheckOut(Fixtures):
    def test_feed_exists(self):
        with patch('kaban.helpers.SQLSession') as mock_session, \
                patch('kaban.helpers.feedparser') as mock_feedparser:
            mock_session.return_value = self.SQLSession()
            with self.assertRaises(DataAlreadyExists):
                helpers.check_out_feed(
                    TEST_DB[0]['feed'], TEST_DB[0]['uid'], first_time=False
                )
                mock_feedparser.parse.assert_not_called()

    def test_feed_dont_exists(self):
        with patch('kaban.helpers.SQLSession') as mock_session, \
                patch('kaban.helpers.feedparser') as mock_feedparser:
            mock_session.return_value = self.SQLSession()
            helpers.check_out_feed('dummy-feed', 0, first_time=False)
            helpers.check_out_feed(TEST_DB[0]['feed'], 0, first_time=False)
            helpers.check_out_feed('dummy-feed', TEST_DB[0]['uid'], first_time=False)
            self.assertEqual(mock_session.call_count, 3)

    def test_feed_parser(self):
        dummy_post = Mock()
        dummy_post.published_parsed = True
        dummy_post.title = True
        dummy_feed = Mock()
        dummy_feed.entries = [dummy_post]
        dummy_feed.href = True

        with patch('kaban.helpers.SQLSession') as mock_session, \
                patch('kaban.helpers.feedparser') as mock_feedparser:
            mock_session.return_value = self.SQLSession()
            mock_feedparser.parse.return_value = dummy_feed
            helpers.check_out_feed('dummy-feed', 0)
            mock_feedparser.parse.assert_called_once()

    def test_feed_parser_error(self):
        with patch('kaban.helpers.SQLSession') as mock_session, \
                patch('kaban.helpers.feedparser') as mock_feedparser:
            mock_session.return_value = self.SQLSession()

            mock_feedparser.parse.return_value = None
            with self.assertRaises(FeedFormatError):
                helpers.check_out_feed('dummy-feed', 0)

            dummy_feed = Mock()
            dummy_feed.entries = []
            mock_feedparser.parse.return_value = dummy_feed
            with self.assertRaises(FeedFormatError):
                helpers.check_out_feed('dummy-feed', 0)

            dummy_post = Mock()
            dummy_post.published_parsed = None
            dummy_post.title = None
            dummy_feed.entries = [dummy_post]
            dummy_feed.href = None
            mock_feedparser.parse.return_value = dummy_feed
            with self.assertRaises(FeedFormatError):
                helpers.check_out_feed('dummy-feed', 0)

            mock_feedparser.parse.side_effect = Exception
            with self.assertRaises(Exception):
                helpers.check_out_feed('dummy-feed', 0)


class AddNewFeed(Fixtures):
    def test_normal_case(self):
        with patch('kaban.helpers.info') as mock_info, \
                patch('kaban.helpers.SQLSession') as mock_session, \
                patch('kaban.helpers.new_feed_preprocess') as mock_feed_preprc:
            mock_session.return_value = self.SQLSession()
            result = helpers.add_new_feed('bot', 142142, 'dummy-feed')
            self.assertEqual(result, 'New web feed added!')
            mock_feed_preprc.assert_called_with('bot', 142142, 'dummy-feed')

        with self.SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == 142142, FeedsDB.feed == 'dummy-feed'
            ).first()
            self.assertIsNotNone(db_entry)

    def test_except_case(self):
        with patch('kaban.helpers.info') as mock_info, \
                patch('kaban.helpers.SQLSession') as mock_session, \
                patch('kaban.helpers.new_feed_preprocess') as mock_feed_preprc:
            mock_session.return_value = self.SQLSession()
            mock_feed_preprc.side_effect = FeedPreprocessError
            result = helpers.add_new_feed('bot', 142142, 'dummy-feed')
            self.assertIn('some issues', result)


class NewFeedPreprocess(Fixtures):
    def test_normal_case(self):
        post = Mock()
        post.title = self.post_data['title']
        post.published_parsed = tuple(self.post_data['published_parsed'])

        with patch('kaban.helpers.log') as mock_log, \
                patch('kaban.helpers.SQLSession') as mock_session, \
                patch('kaban.helpers.feedparser') as mock_feedparser, \
                patch('kaban.helpers.send_a_post') as mock_post_sender:
            mock_session.return_value = self.SQLSession()
            mock_feedparser.parse().entries = [post]

            helpers.new_feed_preprocess('bot', TEST_DB[0]['uid'], TEST_DB[0]['feed'])
            mock_post_sender.assert_called_with('bot', post, ANY, TEST_DB[0]['feed'])

        title = hashlib.md5(
            post.title.strip().encode()
        ).hexdigest()
        top_post_date = datetime.fromtimestamp(
            time.mktime(post.published_parsed)
        )
        with self.SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == TEST_DB[0]['uid'],
                FeedsDB.feed == TEST_DB[0]['feed'],
            ).first()
            self.assertEqual(db_entry.last_posts, title)
            self.assertEqual(db_entry.last_check, top_post_date)

    def test_except_case(self):
        with patch('kaban.helpers.log') as mock_log, \
                patch('kaban.helpers.SQLSession') as mock_session, \
                patch('kaban.helpers.send_a_post') as mock_post_sender:
            mock_session.return_value = self.SQLSession()
            with self.assertRaises(FeedPreprocessError):
                helpers.new_feed_preprocess('bot', TEST_DB[0]['uid'], None)


class DeleteFeed(Fixtures):
    def test_normal_case(self):
        with patch('kaban.helpers.info') as mock_info, \
                patch('kaban.helpers.SQLSession') as mock_session:
            mock_session.return_value = self.SQLSession()
            result = helpers.delete_a_feed(TEST_DB[0]['feed'], TEST_DB[0]['uid'])
            self.assertEqual(result, "Done.")

        with self.SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == TEST_DB[0]['uid'],
                FeedsDB.feed == TEST_DB[0]['feed']
            ).first()
            self.assertIsNone(db_entry)

    def test_except_case(self):
        with patch('kaban.helpers.info') as mock_info, \
                patch('kaban.helpers.SQLSession') as mock_session:
            mock_session.return_value = self.SQLSession()
            result = helpers.delete_a_feed('dummy-feed', 142142)
            self.assertIn('Check for errors', result)


class ListUserFeeds(Fixtures):
    def test_normal_case(self):
        with patch('kaban.helpers.SQLSession') as mock_session:
            mock_session.return_value = self.SQLSession()
            result = helpers.list_user_feeds(TEST_DB[0]['uid'])
            self.assertIn(TEST_DB[0]['feed'], result)
            self.assertIn(TEST_DB[1]['feed'], result)
            self.assertIn("summary: on, date: on, link: on", result)
            result2 = helpers.list_user_feeds(TEST_DB[2]['uid'])
            self.assertIn("summary: off, date: off, link: off", result2)


class FeedShortcut(Fixtures):
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


class FeedSwitcher(Fixtures):
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


class DeleteUser(Fixtures):
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
