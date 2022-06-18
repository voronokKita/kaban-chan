import json
import pathlib
import sys
import unittest
from unittest.mock import patch, ANY

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from kaban import bot_config
from kaban.settings import (
    DataAlreadyExists, FeedFormatError,
    MASTER_UID, USERS, HELP, SHORTCUT_LEN,
    CMD_ADD, CMD_CANCEL, CMD_INSERT,
    CMD_LIST, CMD_DELETE, CMD_SHORTCUT,
    CMD_SUMMARY, CMD_DATE, CMD_LINK
)
from tests.fixtures.fixtures import reset_mock, make_update, TEST_DB, TG_REQUEST


class Hello(unittest.TestCase):
    def test_help(self):
        tg_request = json.loads(TG_REQUEST)

        with patch('kaban.bot_config.send_message') as mock_sender, \
                patch('kaban.bot_config.delete_user') as mock_delete, \
                patch('kaban.bot_config.time') as mock_time:
            bot = bot_config.get_bot()

            update = make_update('/help')
            bot.process_new_updates([update])
            mock_sender.assert_called_with(bot, MASTER_UID, HELP)

            mock_sender.reset_mock()
            update = make_update('some-random-text')
            bot.process_new_updates([update])
            mock_sender.assert_called_with(bot, MASTER_UID, HELP)

            mock_sender.reset_mock()
            USERS[MASTER_UID] = {'key-1': True, 'key-2': 'str'}
            update = make_update('/start')
            bot.process_new_updates([update])

            mock_delete.assert_called_once()
            self.assertIsNone(USERS.get(MASTER_UID))
            mock_sender.assert_called_with(bot, MASTER_UID, ANY)
            self.assertEqual(mock_sender.call_count, 2)

    def tearDown(self):
        if USERS.get(MASTER_UID):
            USERS.pop(MASTER_UID)


@patch('kaban.bot_config.info')
@patch('kaban.bot_config.time')
@patch('kaban.bot_config.add_feed')
@patch('kaban.bot_config.check_out_feed')
@patch('kaban.bot_config.send_message')
class AddNewFeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bot = bot_config.get_bot()

    def test_add(self, mock_sender, *args):
        update = make_update(CMD_ADD)
        self.bot.process_new_updates([update])

        awaiting = "Send me a URI of your web feed. I'll check it out."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)
        self.assertTrue(USERS[MASTER_UID]['AWAITING_FEED'])

        reset_mock(mock_sender, *args)

    def test_cancel(self, mock_sender, *args):
        update = make_update(CMD_CANCEL)
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, "Cancelled~")
        self.assertNotIn(MASTER_UID, USERS)

        reset_mock(mock_sender, *args)

    def test_check_out(self, mock_sender, mock_feed_checker, *args):
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})
        update = make_update(TEST_DB[0]['feed'])
        self.bot.process_new_updates([update])

        awaiting = f"All is fine — I managed to read the feed! " \
                   f"Use the {CMD_INSERT} command to complete."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)
        mock_feed_checker.assert_called_once()
        self.assertEqual(USERS[MASTER_UID]['POTENTIAL_FEED'], TEST_DB[0]['feed'])

        reset_mock(mock_sender, mock_feed_checker, *args)

    def test_insert(self, mock_sender, foo, mock_add_feed, *args):
        USERS.setdefault(
            MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': TEST_DB[0]['feed']}
        )
        awaiting = "New web feed added!"
        mock_add_feed.return_value = awaiting

        update = make_update(CMD_INSERT)
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)
        mock_add_feed.assert_called_once()
        self.assertNotIn(MASTER_UID, USERS)

        reset_mock(mock_sender, foo, mock_add_feed, *args)

    def test_insert_fail(self, mock_sender, *args):
        update = make_update(CMD_INSERT)
        self.bot.process_new_updates([update])

        awaiting = f"Use {CMD_ADD} command first."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)

        reset_mock(mock_sender, *args)

    def test_add_fail(self, mock_sender, *args):
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})
        update = make_update(CMD_ADD)
        self.bot.process_new_updates([update])

        awaiting = f"You can use {CMD_CANCEL} to go back."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)

        reset_mock(mock_sender, *args)

    def test_check_out_exists(self, mock_sender, mock_feed_checker, *args):
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})
        mock_feed_checker.side_effect = DataAlreadyExists

        update = make_update(TEST_DB[0]['feed'])
        self.bot.process_new_updates([update])

        awaiting = "I already watch this feed for you!"
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)

        reset_mock(mock_sender, mock_feed_checker, *args)

    def test_check_out_format(self, mock_sender, mock_feed_checker, *args):
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})
        mock_feed_checker.side_effect = FeedFormatError

        update = make_update(TEST_DB[0]['feed'])
        self.bot.process_new_updates([update])

        awaiting = "Invalid feed's format, I can't add this feed."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)

        reset_mock(mock_sender, mock_feed_checker, *args)

    def test_check_out_exception(self, mock_sender, mock_feed_checker, *args):
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})
        mock_feed_checker.side_effect = Exception

        update = make_update(TEST_DB[0]['feed'])
        self.bot.process_new_updates([update])

        awaiting = "Can't read the feed. Check for errors or try again later."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)
        reset_mock(mock_sender, mock_feed_checker, *args)

    def tearDown(self):
        if USERS.get(MASTER_UID):
            USERS.pop(MASTER_UID)


@patch('kaban.bot_config.feed_shortcut')
@patch('kaban.bot_config.check_out_feed')
@patch('kaban.bot_config.delete_a_feed')
@patch('kaban.bot_config.list_feeds')
@patch('kaban.bot_config.send_message')
class ListFeeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tg_request = json.loads(TG_REQUEST)
        cls.bot = bot_config.get_bot()

    def test_add_fail(self, mock_sender, *args):
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})

        update = make_update(CMD_LIST)
        self.bot.process_new_updates([update])

        awaiting = f"You can use {CMD_CANCEL} to go back."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)
        mock_sender.assert_called_once()

        reset_mock(mock_sender, *args)

    def test_list(self, mock_sender, mock_list, *args):
        awaiting = 'your-list'
        mock_list.return_value = awaiting

        update = make_update(CMD_LIST)
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)

        reset_mock(mock_sender, mock_list, *args)

    def test_delete(self, mock_sender, foo, mock_delete, *args):
        awaiting = "Done."
        mock_delete.return_value = awaiting

        update = make_update(CMD_DELETE + ' feed-to-dell')
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)

        reset_mock(mock_sender, foo, mock_delete, *args)

    def test_shortcut(self, mock_sender, foo, bar, mock_feed_checker, mock_shortcut):
        awaiting = "Done."
        mock_shortcut.return_value = awaiting
        mock_feed_checker.side_effect = DataAlreadyExists

        update = make_update(CMD_SHORTCUT + ' shortcut feed')
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)

        reset_mock(mock_sender, foo, bar, mock_feed_checker, mock_shortcut)

    def test_wrong_pattern(self, mock_sender, *args):
        update = make_update(CMD_DELETE)
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, HELP)
        mock_sender.assert_called_once()

        reset_mock(mock_sender, *args)

    def test_empty_short(self, mock_sender, *args):
        update = make_update(CMD_SHORTCUT + ' shortcut feed')
        self.bot.process_new_updates([update])

        awaiting = "No such web feed found. Check for errors."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)

        reset_mock(mock_sender, *args)

    def test_wrong_short(self, mock_sender, foo, bar, mock_feed_checker, mock_shortcut):
        mock_feed_checker.side_effect = DataAlreadyExists
        mock_shortcut.side_effect = IndexError

        update = make_update(CMD_SHORTCUT + ' shortcut feed')
        self.bot.process_new_updates([update])

        awaiting = f"The maximum length is {SHORTCUT_LEN} characters."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)

        reset_mock(mock_sender, foo, bar, mock_feed_checker, mock_shortcut)

    def tearDown(self):
        if USERS.get(MASTER_UID):
            USERS.pop(MASTER_UID)


@patch('kaban.bot_config.feed_switcher')
@patch('kaban.bot_config.check_out_feed')
@patch('kaban.bot_config.send_message')
class Switcher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tg_request = json.loads(TG_REQUEST)
        cls.bot = bot_config.get_bot()

    def test_add_fail(self, mock_sender, *args):
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})
        update = make_update(CMD_SUMMARY)
        self.bot.process_new_updates([update])

        awaiting = f"You can use {CMD_CANCEL} to go back."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)
        mock_sender.assert_called_once()

        reset_mock(mock_sender, *args)

    def test_switcher(self, mock_sender, mock_feed_checker, mock_switcher):
        mock_feed_checker.side_effect = DataAlreadyExists
        commands = [CMD_SUMMARY, CMD_DATE, CMD_LINK]
        for command in commands:
            update = make_update(command + ' dummy-feed')
            self.bot.process_new_updates([update])

            mock_switcher.assert_called_with(MASTER_UID, command, 'dummy-feed')
            mock_sender.assert_called_with(self.bot, MASTER_UID, "Done.")

            reset_mock(mock_sender, mock_feed_checker, mock_switcher)

    def test_wrong_feed(self, mock_sender, mock_feed_checker, foo):
        update = make_update(CMD_SUMMARY + ' dummy-feed')
        self.bot.process_new_updates([update])

        awaiting = "No such web feed found. Check for errors."
        mock_sender.assert_called_with(self.bot, MASTER_UID, awaiting)

        reset_mock(mock_sender, mock_feed_checker, foo)

    def test_wrong_pattern(self, mock_sender, *args):
        update = make_update(CMD_SUMMARY + 'wrong cmd')
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, HELP)
        mock_sender.assert_called_once()

        reset_mock(mock_sender, *args)

    def tearDown(self):
        if USERS.get(MASTER_UID):
            USERS.pop(MASTER_UID)


if __name__ == '__main__':
    unittest.main()
