from copy import copy
from datetime import datetime
import hashlib
import json
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

from kaban import helpers
from kaban import bot_config
from kaban import flask_config
from kaban.webhook import WebhookThread
from kaban.updater import UpdaterThread
from kaban.receiver import ReceiverThread
from kaban.settings import (
    MASTER_UID, HOOK_READY_TO_WORK,
    HELP
)
from tests.fixtures.fixtures import MockDB, make_request


signal.signal(signal.SIGINT, helpers.exit_signal)
signal.signal(signal.SIGTSTP, helpers.exit_signal)

try: requests.get('https://core.telegram.org/')
except Exception: no_internet = True
else: no_internet = False


@patch('kaban.log.debug')
@patch('kaban.log.info')
@patch('kaban.log.log')
@patch('kaban.helpers.bot_sender')
@patch('kaban.settings.SQLSession')
@unittest.skipIf(no_internet, 'no internet')
class Integrity(MockDB):
    def test_integrity(self, mock_session, mock_sender, *args):
        mock_session = self.SQLSession
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
            raise Exception('fail to start a webhook')

        hook_url = server.url
        headers = {'content-type': 'application/json'}

        errors = []
        try:
            if test_event.wait(30):
                print(mock_sender.call_args_list)
                mock_sender.reset_mock()
            else:
                raise Exception('upd')

            request_data = make_request('/help')
            result = requests.post(url=hook_url, data=request_data, headers=headers)
            self.assertEqual(result.status_code, 200)
            time.sleep(0.5)
            mock_sender.assert_called_with(bot, MASTER_UID, HELP)

        except Exception as exc:
            errors.append(exc)
        else:
            pass
        finally:
            helpers.exit_signal()
            time.sleep(0.5)
            server.shutdown()

        for thread in [server, receiver, updater]:
            try:
                thread.stop()
            except Exception as exc:
                errors.append(exc)

        if errors:
            for exc in errors:
                raise Exception from exc
