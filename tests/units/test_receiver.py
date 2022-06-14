import time
import sys
import pathlib
from unittest.mock import Mock, patch, ANY

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import kaban
from kaban import receiver
from kaban.settings import WebhookDB, EXIT_EVENT

from tests.fixtures.fixtures import Fixtures, TEST_DB


class SetReceiver(Fixtures):
    def test_normal_case(self):
        with open(BASE_DIR / 'tests' / 'fixtures' / 'tg_post') as f:
            data = f.read().strip()
        with self.SQLSession() as session:
            session.add(WebhookDB(data=data))
            session.add(WebhookDB(data=data))
            session.commit()

        with patch('kaban.receiver.SQLSession') as mock_session:
            mock_session.return_value = self.SQLSession()
            mock_bot = Mock()
            recv = receiver.ReceiverThread(mock_bot)
            recv.users_in_memory = {TEST_DB[0]['uid']: {'key-1': True, 'key-2': 'str'}}
            recv.send_message = Mock()

            recv.new_messages = Mock()
            recv.new_messages.wait.return_value = True
            recv.new_messages.clear.side_effect = EXIT_EVENT.set

            recv.start()
            if EXIT_EVENT.wait(10):
                time.sleep(0.1)
            recv.stop()

        self.assertEqual(mock_bot.process_new_updates.call_count, 2)
        recv.send_message.assert_called_once()
        recv.send_message.assert_called_with(mock_bot, TEST_DB[0]['uid'], ANY)

    def test_exception(self):
        recv = receiver.ReceiverThread(Mock())
        recv.new_messages = Mock()
        recv.new_messages.wait.side_effect = Exception
        recv.exit = Mock()
        recv.start()
        time.sleep(0.1)
        with self.assertRaises(Exception):
            recv.stop()
