from datetime import datetime
import hashlib
import time
import sys
import requests
import pathlib
import threading
import unittest
from unittest.mock import Mock, patch, mock_open, ANY

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if BASE_DIR not in sys.path:
    sys.path.append(str(BASE_DIR))

import kaban
from kaban import updater
from kaban import bot_config
from kaban.settings import FeedsDB, EXIT_EVENT

from tests.fixtures.fixtures import Fixtures, TEST_DB


@patch('kaban.updater.log')
class SetUpdater(Fixtures):
    try: requests.get('https://core.telegram.org/')
    except Exception: no_internet = True
    else: no_internet = False

    def test_normal_case(self, mock_log):
        post = Mock()
        post.title = self.post_data['title']
        post.published_parsed = tuple(self.post_data['published_parsed'])
        feed = Mock()
        feed.entries = [post]

        with patch('kaban.updater.SQLSession') as mock_session, \
                patch('kaban.updater.feedparser') as mock_feedparser:
            mock_session.return_value = self.SQLSession()
            mock_feedparser.parse.return_value = feed

            upd = updater.UpdaterThread(Mock())
            upd.notifications = Mock()
            upd.notifications.exists.return_value = False
            upd._updater = Mock()

            upd.start()
            EXIT_EVENT.set()
            time.sleep(0.05)
            upd.stop()

            upd.notifications.exists.assert_called_once()
            upd._updater.assert_called()
            for i, call in enumerate(upd._updater.call_args_list):
                self.assertEqual(TEST_DB[i]['feed'], call.args[1])

    def test_exception(self, mock_log):
        upd = updater.UpdaterThread(bot_config.get_bot())
        upd._load = Mock()
        upd._load.side_effect = Exception
        upd.start()
        time.sleep(0.05)
        with self.assertRaises(Exception):
            upd.stop()

    @unittest.skipIf(no_internet, 'no internet')
    def test_with_internet(self, mock_log):
        # It's impossible to know how long it will take to process~
        test_event = threading.Event()
        with patch('kaban.updater.SQLSession') as mock_session, \
                patch('kaban.helpers.send_message') as mock_sender:
            mock_session.return_value = self.SQLSession()
            upd = updater.UpdaterThread(bot_config.get_bot())
            upd._test = Mock()
            upd._test.side_effect = test_event.set

            upd.start()
            if test_event.wait(10):
                EXIT_EVENT.set()
                time.sleep(0.05)
            upd.stop()
            mock_sender.assert_called()


@patch('kaban.updater.log')
class Note(Fixtures):
    def test_notifications(self, mock_log):
        notes = 'note-1 >>> note-2 >>> note-3'
        uids = []
        for entry in TEST_DB:
            uid = entry['uid']
            if uid not in uids:
                uids.append(uid)
        expect_calls = len(uids) * 3  # notes
        mock_file = mock_open(read_data=notes)

        with patch('builtins.open', mock_file) as mock_file_handler, \
                patch('kaban.updater.SQLSession') as mock_session, \
                patch('kaban.helpers.send_message') as mock_sender, \
                patch('kaban.updater.info') as mock_info:
            mock_session.return_value = self.SQLSession()
            upd = updater.UpdaterThread(Mock())

            upd._notifications()
            mock_file_handler.assert_called()
            self.assertEqual(mock_sender.call_count, expect_calls)
            mock_info.assert_called_once()


class Loader(Fixtures):
    def test_normal_case(self):
        post = Mock()
        post.title = self.post_data['title']
        post.published_parsed = tuple(self.post_data['published_parsed'])
        feed = Mock()
        feed.entries = [post]

        uids = []
        for entry in TEST_DB:
            uid = entry['uid']
            if uid not in uids:
                uids.append(uid)

        with patch('kaban.updater.log') as mock_log, \
                patch('kaban.updater.SQLSession') as mock_session, \
                patch('kaban.updater.feedparser') as mock_feedparser:
            mock_session.return_value = self.SQLSession()
            mock_feedparser.parse.return_value = feed

            upd = updater.UpdaterThread(Mock())
            new_posts = {}
            upd._load(new_posts)

            self.assertEqual(len(new_posts), len(uids))
            title = hashlib.md5(
                post.title.strip().encode()
            ).hexdigest()
            for uid in new_posts:
                for feed in new_posts[uid]:
                    posts = new_posts[uid][feed]
                    self.assertEqual(posts[0]['title'], title)
                    self.assertEqual(posts[0]['post'], post)

    def test_exception_case(self):
        feed = Mock()
        with patch('kaban.updater.log') as mock_log, \
                patch('kaban.updater.SQLSession') as mock_session, \
                patch('kaban.updater.feedparser') as mock_feedparser:
            mock_session.return_value = self.SQLSession()
            upd = updater.UpdaterThread(Mock())
            upd._populate_list_of_posts = Mock()

            feed.entries = None
            mock_feedparser.parse.return_value = feed
            upd._load({})
            upd._populate_list_of_posts.assert_not_called()
            mock_log.warning.assert_called()
            self.assertEqual(mock_log.warning.call_count, len(TEST_DB))
            result = mock_log.warning.call_args_list[0].args[0]
            self.assertIn('failed to load feed', result)

            mock_feedparser.parse.side_effect = Exception
            upd._load({})
            upd._populate_list_of_posts.assert_not_called()
            result = mock_log.warning.call_args_list[-1].args[0]
            self.assertIn('feedparser fail', result)


class Sender(Fixtures):
    def test_normal_case(self):
        post = Mock()
        post.published_parsed = tuple(self.post_data['published_parsed'])
        post_published = datetime.fromtimestamp(
            time.mktime(post.published_parsed)
        )
        upd_post = {'title': 'test-title', 'post': post}

        with patch('kaban.updater.SQLSession') as mock_session, \
                patch('kaban.helpers.send_a_post') as mock_sender:
            mock_session.return_value = self.SQLSession()
            upd = updater.UpdaterThread(Mock())

            upd._updater(TEST_DB[0]['uid'], TEST_DB[0]['feed'], upd_post)
            mock_sender.assert_called_once()
            mock_sender.assert_called_with(ANY, post, ANY, TEST_DB[0]['feed'])

        with self.SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == TEST_DB[0]['uid'],
                FeedsDB.feed == TEST_DB[0]['feed']
            ).first()
            self.assertIn('test-title', db_entry.last_posts)
            self.assertEqual(post_published, db_entry.last_check)
