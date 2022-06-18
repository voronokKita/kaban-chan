import itertools
import pathlib
import requests
import signal
import sys
import threading
import time
import unittest
from unittest.mock import Mock, patch, ANY

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from kaban import bot_config
from kaban import flask_config
from kaban.helpers import exit_signal
from kaban.webhook import WebhookThread
from kaban.updater import UpdaterThread
from kaban.receiver import ReceiverThread
from kaban.settings import (
    MASTER_UID, HOOK_READY_TO_WORK,
    HELP,
    CMD_ADD, CMD_INSERT, CMD_CANCEL,
    CMD_LIST, CMD_DELETE, CMD_SHORTCUT,
    CMD_SUMMARY, CMD_DATE, CMD_LINK
)
from tests.fixtures.fixtures import MockDB, make_request, TEST_DB


TEST_FEED = 'https://www.wired.com/feed/tag/ai/latest/rss'
TEST_CASES = [
    {'message': '/help', 'result': HELP},
    {'message': CMD_ADD, 'result': "Send me a URI of your web feed. I'll check it out."},
    {'message': TEST_FEED,
     'result': f'All is fine — I managed to read the feed! '
               f'Use the {CMD_INSERT} command to complete.'},
    {'message': CMD_INSERT, 'result': 'New web feed added!'},

    {'message': CMD_LIST, 'result': ANY},
    {'message': f'{CMD_DELETE} {TEST_DB[-1]["feed"]}', 'result': 'Deleted.'},
    {'message': f'{CMD_SHORTCUT} {TEST_FEED} wired/ai', 'result': 'Appended.'},

    {'message': f'{CMD_SUMMARY} {TEST_FEED}', 'result': 'Summary switched.'},
    {'message': f'{CMD_DATE} {TEST_FEED}', 'result': 'Date switched.'},
    {'message': f'{CMD_LINK} {TEST_FEED}', 'result': 'Link switched.'},

    {'message': CMD_ADD, 'result': "Send me a URI of your web feed. I'll check it out."},
    {'message': CMD_ADD, 'result': f'You can use {CMD_CANCEL} to go back.'},
    {'message': CMD_LIST, 'result': f'You can use {CMD_CANCEL} to go back.'},
    {'message': f'{CMD_DATE} {TEST_FEED}', 'result': f'You can use {CMD_CANCEL} to go back.'},
    {'message': CMD_INSERT, 'result': 'You must add feed first.'},
    {'message': CMD_CANCEL, 'result': f'Cancelled~'},
    {'message': f'{CMD_DELETE} foo bar baz', 'result': HELP},
    {'message': f'{CMD_LINK} foo bar baz', 'result': HELP},
    {'message': 'foo bar baz', 'result': HELP},
]
WOKE_UP = threading.Event()

try: requests.get('https://core.telegram.org/')
except Exception: no_internet = True
else: no_internet = False


@patch('kaban.bot_config.info')
@patch('kaban.flask_config.log')
@patch('kaban.updater.info')
@patch('kaban.updater.log')
@patch('kaban.helpers.info')
@patch('kaban.helpers.log')
@patch('kaban.helpers.SQLSession')
@patch('kaban.flask_config.SQLSession')
@patch('kaban.receiver.SQLSession')
@patch('kaban.updater.SQLSession')
@patch('kaban.helpers.bot_sender')
@unittest.skipIf(no_internet, 'no internet')
class Integrity(MockDB):
    def test_integrity(self, mock_sender, upd_sql, rcv_sql,
                       hook_sql, helpers_sql, *args):
        for m in (upd_sql, rcv_sql, hook_sql, helpers_sql):
            m.return_value = self.SQLSession()

        self._start()

        bot = bot_config.get_bot()
        server = WebhookThread(flask_config.get_app())
        receiver = ReceiverThread(bot)

        updater = UpdaterThread(bot)
        updater._test = Mock()
        test_event = threading.Event()
        updater._test.side_effect = test_event.set

        server.start()
        if HOOK_READY_TO_WORK.wait(20):
            time.sleep(0.5)
            receiver.start()
            updater.start()
            time.sleep(0.5)
        else:
            self._stop()
            raise Exception('fail to start a webhook')

        hook_url = server.url
        headers = {'content-type': 'application/json'}

        errors = []
        try:
            if test_event.wait(30):
                mock_sender.assert_called()
                mock_sender.reset_mock()
            else:
                raise Exception('updater timeout')

            for case in TEST_CASES:
                request_data = make_request(case['message'])
                result = requests.post(url=hook_url, data=request_data, headers=headers)
                self.assertEqual(result.status_code, 200)
                time.sleep(1)
                mock_sender.assert_called_with(bot, MASTER_UID, case['result'])
                mock_sender.reset_mock()

        except Exception as exc:
            errors.append(exc)
        finally:
            exit_signal()
            time.sleep(0.5)
            server.shutdown()

        for thread in [server, receiver, updater]:
            try:
                thread.stop()
            except Exception as exc:
                errors.append(exc)

        self._stop()

        if errors:
            if len(errors) > 1:
                print(f'! all errors[{len(errors)}]:', errors, '!')
            for exc in errors:
                raise Exception from exc

    def _start(self):
        self.paint = threading.Thread(target=self._animation)
        self.paint.start()

    def _stop(self):
        WOKE_UP.set()
        time.sleep(1)
        self.paint.join()

    @staticmethod
    def _animation():
        l = ['*', '-', '—', '\\', '|', '/', '—', '-']
        sys.stdout.write('\n')
        for ell in itertools.cycle(l):
            if WOKE_UP.is_set():
                sys.stdout.write(f'\r...')
                sys.stdout.flush()
                break
            sys.stdout.write(f'\r{ell}')
            sys.stdout.flush()
            time.sleep(0.3)
        sys.stdout.write('\n')


if __name__ == '__main__':
    signal.signal(signal.SIGINT, exit_signal)
    signal.signal(signal.SIGTSTP, exit_signal)
    unittest.main()
