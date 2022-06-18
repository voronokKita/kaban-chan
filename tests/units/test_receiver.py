from copy import copy
import pathlib
import sys
import time
import unittest
from unittest.mock import Mock, patch, ANY

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from kaban.receiver import ReceiverThread
from kaban.database import WebhookDB
from kaban.settings import EXIT_EVENT, NEW_MESSAGES_EVENT, USERS, MASTER_UID

from tests.fixtures.fixtures import MockDB, reset_mock, TG_REQUEST


@patch('kaban.receiver.exit_signal')
@patch('kaban.receiver.SQLSession')
@patch('kaban.receiver.send_message')
class SetReceiver(MockDB):
    def test_normal_case(self, mock_sender, mock_session, foo):
        tg_request = copy(TG_REQUEST)
        with self.SQLSession() as session:
            session.add(WebhookDB(data=tg_request))
            session.add(WebhookDB(data=tg_request))
            session.commit()
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})

        mock_session.return_value = self.SQLSession()
        mock_bot = Mock()
        recv = ReceiverThread(mock_bot)

        recv.new_messages = Mock()
        recv.new_messages.wait.return_value = True
        recv.new_messages.clear.side_effect = EXIT_EVENT.set

        recv.start()
        if EXIT_EVENT.wait(10):
            time.sleep(0.1)
        recv.stop()

        self.assertEqual(mock_bot.process_new_updates.call_count, 2)
        mock_sender.assert_called_once()
        mock_sender.assert_called_with(mock_bot, MASTER_UID, ANY)

        reset_mock(mock_sender, mock_session, foo)

    def test_exception(self, *args):
        recv = ReceiverThread(Mock())
        recv.new_messages = Mock()
        recv.new_messages.wait.side_effect = Exception
        recv.exit = Mock()
        recv.start()
        time.sleep(0.1)
        with self.assertRaises(Exception):
            recv.stop()

        reset_mock(*args)

    def tearDown(self):
        if EXIT_EVENT.is_set():
            EXIT_EVENT.clear()
        if NEW_MESSAGES_EVENT.is_set():
            NEW_MESSAGES_EVENT.clear()
        if USERS.get(MASTER_UID):
            USERS.pop(MASTER_UID)


if __name__ == '__main__':
    unittest.main()
