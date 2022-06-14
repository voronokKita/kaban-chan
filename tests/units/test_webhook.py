import sys
import pathlib
import time
import requests
import unittest
from unittest.mock import Mock, patch

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import kaban
from kaban import webhook
from kaban import flask_config
from kaban.settings import HOOK_READY_TO_WORK, WEBHOOK_ENDPOINT, WebhookDB, BANNED

from tests.fixtures.fixtures import Fixtures


class SetHook(unittest.TestCase):
    def test_tunnel(self):
        with patch('kaban.webhook.ngrok') as mock_ngrok, \
                patch('kaban.webhook.telebot') as mock_telebot, \
                patch('kaban.webhook.subprocess') as mock_subprocess:
            mock_tunnel = Mock()
            mock_tunnel.public_url = 'https://example.com'
            mock_ngrok.connect.return_value = mock_tunnel
            mock_subprocess.check_output.return_value = 'Webhook was set.'.encode()

            server = webhook.WebhookThread(Mock())
            server._make_tunnel()
            server._set_webhook()

            mock_ngrok.connect.assert_called_once()
            mock_telebot.TeleBot().remove_webhook.assert_called_once()
            mock_subprocess.check_output.assert_called_once()
            result = mock_subprocess.check_output.call_args.args[0]
            self.assertTrue(type(result) is list and len(result) > 0)
            result_tunnel = result[8]
            self.assertIn('example.com' + WEBHOOK_ENDPOINT, result_tunnel)

    def test_normal_case(self):
        with patch('kaban.webhook.ngrok') as mock_ngrok, \
                patch('kaban.webhook.telebot') as mock_telebot, \
                patch('kaban.webhook.subprocess') as mock_subprocess:
            mock_tunnel = Mock()
            mock_tunnel.public_url = 'https://example.com'
            mock_ngrok.connect.return_value = mock_tunnel
            mock_subprocess.check_output.return_value = 'Webhook was set.'.encode()

            hook = webhook.WebhookThread(flask_config.get_app())
            hook.start()
            if HOOK_READY_TO_WORK.wait(5): time.sleep(0.05)
            hook.shutdown()
            hook.stop()

    def test_exception_case(self):
        with patch('kaban.webhook.ngrok') as mock_ngrok, \
                patch('kaban.webhook.telebot') as mock_telebot, \
                patch('kaban.webhook.subprocess') as mock_subprocess, \
                patch('kaban.helpers.exit_signal') as mock_exit:
            mock_subprocess.check_output.return_value = 'Raise me.'.encode()

            hook = webhook.WebhookThread(flask_config.get_app())
            hook.start()
            time.sleep(0.1)
            with self.assertRaises(Exception):
                hook.stop()


@patch('kaban.flask_config.SQLSession')
@patch('kaban.flask_config.log')
class FlaskConfig(Fixtures):
    """
    Due to the webhook connection timeout,
    it is very difficult to check the operation of
    different parts of code in separate tests.
    """
    try: requests.get('https://core.telegram.org/')
    except Exception: no_internet = True
    else: no_internet = False

    def setUp(self):
        self.hook = webhook.WebhookThread(flask_config.get_app())
        self.hook.start()
        if HOOK_READY_TO_WORK.wait(5): pass
        self.url = self.hook.url

    @unittest.skipIf(no_internet, 'no internet')
    def test_flask_app(self, mock_log, mock_session):
        mock_session.return_value = self.SQLSession()
        result = 0

        # normal case
        with open(BASE_DIR / 'tests' / 'fixtures' / 'tg_post') as f:
            tg_update = f.read().strip().encode()
        headers = {'content-type': 'application/json'}
        result = requests.post(url=self.url, data=tg_update, headers=headers).status_code
        self.assertEqual(result, 200)

        with self.SQLSession() as session:
            message = session.query(WebhookDB).first()
            self.assertIsNotNone(message)

        # exception
        tg_update = '{"some-kay": "some-value"}'.encode()
        result = requests.post(url=self.url, data=tg_update, headers=headers).status_code
        self.assertEqual(result, 403)
        self.assertTrue(len(BANNED) > 0)

    def tearDown(self):
        self.hook.shutdown()
        self.hook.stop()
