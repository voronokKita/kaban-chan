from copy import deepcopy
from datetime import datetime
import hashlib
import pathlib
import requests
import sys
import threading
import time
import unittest
from unittest.mock import Mock, patch, mock_open, ANY

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from kaban.updater import UpdaterThread
from kaban.database import FeedsDB
from kaban.settings import EXIT_EVENT

from tests.fixtures.fixtures import reset_mock, MockDB, TEST_DB, MOCK_FEED, MOCK_POST


@patch('kaban.updater.info')
@patch('kaban.updater.log')
@patch('kaban.updater.exit_signal')
@patch('kaban.updater.send_message')
@patch('kaban.updater.send_a_post')
@patch('kaban.updater.feedparser')
@patch('kaban.updater.SQLSession')
class SetUpdater(MockDB):
    def test_normal_case(self, mock_session, mock_feedparser, *args):
        mock_session.return_value = self.SQLSession()
        mock_feedparser.parse.return_value = deepcopy(MOCK_FEED)

        upd = UpdaterThread(Mock())
        upd.notifications = Mock()
        upd.notifications.exists.return_value = False
        upd._updater = Mock()

        upd.start()
        EXIT_EVENT.set()
        time.sleep(0.1)
        upd.stop()

        upd.notifications.exists.assert_called_once()
        upd._updater.assert_called()
        for i, call in enumerate(upd._updater.call_args_list):
            self.assertEqual(TEST_DB[i]['feed'], call.args[1])

        reset_mock(mock_session, mock_feedparser, *args)

    def test_exception(self, *args):
        upd = UpdaterThread(Mock())
        upd._load = Mock()
        upd._load.side_effect = Exception
        upd.start()
        time.sleep(0.1)
        with self.assertRaises(Exception):
            upd.stop()

        reset_mock(*args)

    def tearDown(self):
        if EXIT_EVENT.is_set():
            EXIT_EVENT.clear()


@patch('kaban.updater.info')
@patch('kaban.updater.log')
@patch('kaban.updater.exit_signal')
@patch('kaban.updater.send_message')
@patch('kaban.updater.send_a_post')
@patch('kaban.updater.SQLSession')
class WithInternet(MockDB):
    try: requests.get('https://core.telegram.org/')
    except Exception: no_internet = True
    else: no_internet = False

    @unittest.skipIf(no_internet, 'no internet')
    def test_with_internet(self, mock_session, mock_poster, *args):
        mock_session.return_value = self.SQLSession()
        upd = UpdaterThread(Mock())
        upd._test = Mock()
        test_event = threading.Event()
        upd._test.side_effect = test_event.set

        upd.start()
        if test_event.wait(10):
            EXIT_EVENT.set()
            time.sleep(0.1)
        upd.stop()
        mock_poster.assert_called()

        reset_mock(mock_session, mock_poster, *args)

    def tearDown(self):
        if EXIT_EVENT.is_set():
            EXIT_EVENT.clear()


@patch('kaban.updater.info')
@patch('kaban.updater.send_message')
@patch('kaban.updater.SQLSession')
class Note(MockDB):
    def test_notifications(self, mock_session, mock_sender, mock_info):
        notes = 'note-1 >>> note-2 >>> note-3'
        uids = []
        for entry in TEST_DB:
            uid = entry['uid']
            if uid not in uids:
                uids.append(uid)
        expect_calls = len(uids) * 3  # notes
        mock_file = mock_open(read_data=notes)

        with patch('builtins.open', mock_file) as mock_file_handler:
            mock_session.return_value = self.SQLSession()
            upd = UpdaterThread(Mock())
            upd._notifications()

            mock_file_handler.assert_called()
            self.assertEqual(mock_sender.call_count, expect_calls)
            mock_info.assert_called_once()

        reset_mock(mock_session, mock_sender, mock_info)


@patch('kaban.updater.log')
@patch('kaban.updater.feedparser')
@patch('kaban.updater.SQLSession')
class Loader(MockDB):
    def test_normal_case(self, mock_session, mock_feedparser, foo):
        uids = []
        for entry in TEST_DB:
            uid = entry['uid']
            if uid not in uids:
                uids.append(uid)

        mock_feed = deepcopy(MOCK_FEED)
        mock_post = mock_feed.entries[0]
        title_hash = hashlib.md5(
            mock_post.title.strip().encode()
        ).hexdigest()

        mock_feedparser.parse.return_value = mock_feed
        mock_session.return_value = self.SQLSession()

        new_posts = {}
        upd = UpdaterThread(Mock())
        upd._load(new_posts)

        self.assertEqual(len(new_posts), len(uids))
        for uid in new_posts:
            for feed in new_posts[uid]:
                post = new_posts[uid][feed][0]
                self.assertEqual(post['title'], title_hash)
                self.assertEqual(post['post'], mock_post)

        reset_mock(mock_session, mock_feedparser, foo)

    def test_exception_case(self, mock_session, mock_feedparser, mock_log):
        mock_session.return_value = self.SQLSession()
        mock_feed = deepcopy(MOCK_FEED)
        mock_feed.entries = None
        mock_feedparser.parse.return_value = mock_feed

        upd = UpdaterThread(Mock())
        upd._populate_list_of_posts = Mock()
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

        reset_mock(mock_session, mock_feedparser, mock_log)


@patch('kaban.updater.send_a_post')
@patch('kaban.updater.SQLSession')
class Sender(MockDB):
    def test_normal_case(self, mock_session, mock_poster):
        mock_session.return_value = self.SQLSession()
        mock_post = deepcopy(MOCK_POST)
        post_published = datetime.fromtimestamp(
            time.mktime(mock_post.published_parsed)
        )
        upd_post = {'title': 'test-title', 'post': mock_post}
        upd = UpdaterThread(Mock())

        upd._updater(TEST_DB[0]['uid'], TEST_DB[0]['feed'], upd_post)
        mock_poster.assert_called_once()
        mock_poster.assert_called_with(ANY, mock_post, ANY, TEST_DB[0]['feed'])

        with self.SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == TEST_DB[0]['uid'],
                FeedsDB.feed == TEST_DB[0]['feed']
            ).first()
            self.assertIn('test-title', db_entry.last_posts)
            self.assertEqual(post_published, db_entry.last_check)

        reset_mock(mock_session, mock_poster)


if __name__ == '__main__':
    unittest.main()
