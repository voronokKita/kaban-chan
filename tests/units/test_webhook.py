from copy import copy
import pathlib
import requests
import sys
import time
import unittest
from unittest.mock import Mock, patch

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from kaban import flask_config
from kaban.webhook import WebhookThread
from kaban.database import WebhookDB
from kaban.settings import (
    HOOK_READY_TO_WORK, NEW_MESSAGES_EVENT,
    WEBHOOK_ENDPOINT, BANNED
)
from tests.fixtures.fixtures import MockDB, reset_mock, TG_REQUEST


@patch('kaban.webhook.exit_signal')
@patch('kaban.webhook.subprocess')
@patch('kaban.webhook.telebot')
@patch('kaban.webhook.ngrok')
class SetHook(unittest.TestCase):
    def test_tunnel_only(self, mock_ngrok, mock_telebot, mock_subprocess, foo):
        mock_tunnel = Mock()
        mock_tunnel.public_url = 'https://example.com'
        mock_ngrok.connect.return_value = mock_tunnel
        mock_subprocess.check_output.return_value = 'Webhook was set.'.encode()

        server = WebhookThread(Mock())
        server._make_tunnel()
        server._set_webhook()

        mock_ngrok.connect.assert_called_once()
        mock_telebot.TeleBot().remove_webhook.assert_called_once()
        mock_subprocess.check_output.assert_called_once()

        result = mock_subprocess.check_output.call_args.args[0]
        self.assertTrue(type(result) is list and len(result) > 0)
        result_tunnel = result[8]
        self.assertIn(f'example.com{WEBHOOK_ENDPOINT}', result_tunnel)

        reset_mock(mock_ngrok, mock_telebot, mock_subprocess, foo)

    def test_normal_case(self, mock_ngrok, foo, mock_subprocess, bar):
        mock_tunnel = Mock()
        mock_tunnel.public_url = 'https://example.com'
        mock_ngrok.connect.return_value = mock_tunnel
        mock_subprocess.check_output.return_value = 'Webhook was set.'.encode()

        hook = WebhookThread(flask_config.get_app())
        hook.start()
        if HOOK_READY_TO_WORK.wait(5):
            time.sleep(0.05)
            hook.shutdown()
        hook.stop()

        reset_mock(mock_ngrok, foo, mock_subprocess, bar)

    def test_exception_case(self, foo, bar, mock_subprocess, baz):
        mock_subprocess.check_output.return_value = 'Raise me.'.encode()
        hook = WebhookThread(flask_config.get_app())

        hook.start()
        time.sleep(0.1)
        with self.assertRaises(Exception):
            hook.stop()

        reset_mock(foo, bar, mock_subprocess, baz)

    def tearDown(self):
        if HOOK_READY_TO_WORK.is_set():
            HOOK_READY_TO_WORK.clear()


@patch('kaban.flask_config.log')
@patch('kaban.webhook.exit_signal')
@patch('kaban.flask_config.SQLSession')
class FlaskConfig(MockDB):
    """
    Due to the webhook connection timeout,
    it is very difficult to check the operation of
    different parts of code in separate tests.
    """
    try: requests.get('https://core.telegram.org/')
    except Exception: no_internet = True
    else: no_internet = False

    def setUp(self):
        self.hook = WebhookThread(flask_config.get_app())
        try: self.hook.start()
        except Exception: pass
        else:
            if HOOK_READY_TO_WORK.wait(5):
                self.url = self.hook.url

    @unittest.skipIf(no_internet, 'no internet')
    def test_flask_app(self, mock_session, foo, bar):
        mock_session.return_value = self.SQLSession()
        headers = {'content-type': 'application/json'}
        result = None

        # normal case
        tg_update = copy(TG_REQUEST).encode()
        result = requests.post(url=self.url, data=tg_update, headers=headers)
        self.assertEqual(result.status_code, 200)

        with self.SQLSession() as session:
            message = session.query(WebhookDB).first()
            self.assertIsNotNone(message)

        # exception
        tg_update = '{"some-kay": "some-value"}'.encode()
        result = requests.post(url=self.url, data=tg_update, headers=headers)
        self.assertEqual(result.status_code, 403)
        self.assertEqual(len(BANNED), 1)

        reset_mock(mock_session, foo, bar)

    def tearDown(self):
        try:
            self.hook.shutdown()
            self.hook.stop()
        except Exception: pass
        if HOOK_READY_TO_WORK.is_set():
            HOOK_READY_TO_WORK.clear()
        if NEW_MESSAGES_EVENT.is_set():
            NEW_MESSAGES_EVENT.clear()
        if BANNED:
            del BANNED[:]


if __name__ == '__main__':
    unittest.main()
