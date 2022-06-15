from datetime import datetime
import hashlib
import time
import sys
import requests
import pathlib
import threading
import json
import unittest
from unittest.mock import Mock, patch, mock_open, ANY

import telebot

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import kaban
from kaban import updater
from kaban import bot_config
from kaban.settings import (
    DataAlreadyExists, FeedFormatError,
    MASTER_UID, USERS, HELP, SHORTCUT_LEN,
    CMD_ADD, CMD_CANCEL, CMD_INSERT,
    CMD_LIST, CMD_DELETE, CMD_SHORTCUT,
    CMD_SUMMARY, CMD_DATE, CMD_LINK
)
from tests.fixtures.fixtures import Fixtures, TEST_DB


class Hello(unittest.TestCase):
    def test_help(self):
        with open(BASE_DIR / 'tests' / 'fixtures' / 'tg_request.json') as f:
            tg_request = json.load(f)

        with patch('kaban.helpers.send_message') as mock_sender, \
                patch('kaban.helpers.delete_user') as mock_delete, \
                patch('kaban.bot_config.time') as mock_time:
            bot = bot_config.get_bot()

            tg_request['message']['text'] = '/help'
            update = telebot.types.Update.de_json(
                json.dumps(tg_request)
            )
            bot.process_new_updates([update])
            mock_sender.assert_called_with(bot, MASTER_UID, HELP)

            tg_request['message']['text'] = 'some-random-text'
            update = telebot.types.Update.de_json(json.dumps(tg_request))
            bot.process_new_updates([update])
            mock_sender.assert_called_with(bot, MASTER_UID, HELP)

            mock_sender.reset_mock()
            tg_request['message']['text'] = '/start'
            update = telebot.types.Update.de_json(json.dumps(tg_request))
            USERS[TEST_DB[0]['uid']] = {'key-1': True, 'key-2': 'str'}
            bot.process_new_updates([update])
            mock_delete.assert_called_once()
            mock_sender.assert_called_with(bot, MASTER_UID, ANY)
            self.assertEqual(mock_sender.call_count, 2)


@patch('kaban.bot_config.info')
@patch('kaban.bot_config.time')
@patch('kaban.helpers.add_new_feed')
@patch('kaban.helpers.check_out_feed')
@patch('kaban.helpers.send_message')
class AddNewFeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BASE_DIR / 'tests' / 'fixtures' / 'tg_request.json') as f:
            cls.tg_request = json.load(f)
        cls.bot = bot_config.get_bot()

    def test_add(self, mock_sender, *args):
        self.tg_request['message']['text'] = CMD_ADD
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = "Send me a URI of your web feed. I'll check it out."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self.assertTrue(USERS[MASTER_UID]['AWAITING_FEED'])
        self._reset(mock_sender, users=True)

    def test_cancel(self, mock_sender, *args):
        self.tg_request['message']['text'] = CMD_CANCEL
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, "Cancelled~")
        self.assertNotIn(MASTER_UID, USERS)
        self._reset(mock_sender)

    def test_check_out(self, mock_sender, mock_feed_checker, *args):
        self.tg_request['message']['text'] = TEST_DB[0]['feed']
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = f"All is fine — I managed to read the feed! " \
               f"Use the {CMD_INSERT} command to complete."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        mock_feed_checker.assert_called_once()
        self.assertEqual(USERS[MASTER_UID]['POTENTIAL_FEED'], TEST_DB[0]['feed'])
        self._reset(mock_sender, mock_feed_checker, users=True)

    def test_insert(self, mock_sender, foo, mock_add_feed, *args):
        self.tg_request['message']['text'] = CMD_INSERT
        USERS.setdefault(
            MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': TEST_DB[0]['feed']}
        )
        mock_add_feed.return_value = "New web feed added!"
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = "New web feed added!"
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        mock_add_feed.assert_called_once()
        self.assertNotIn(MASTER_UID, USERS)
        self._reset(mock_sender, mock_add_feed=mock_add_feed)

    def test_insert_fail(self, mock_sender, *args):
        self.tg_request['message']['text'] = CMD_INSERT
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = f"Use {CMD_ADD} command first."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender)

    def test_add_fail(self, mock_sender, *args):
        self.tg_request['message']['text'] = CMD_ADD
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = f"You can use {CMD_CANCEL} to go back."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender)

    def test_check_out_exists(self, mock_sender, mock_feed_checker, *args):
        self.tg_request['message']['text'] = TEST_DB[0]['feed']
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})

        mock_feed_checker.side_effect = DataAlreadyExists
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = "I already watch this feed for you!"
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender, mock_feed_checker, users=True)

    def test_check_out_format(self, mock_sender, mock_feed_checker, *args):
        self.tg_request['message']['text'] = TEST_DB[0]['feed']
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})

        mock_feed_checker.side_effect = FeedFormatError
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = "Invalid feed's format, I can't add this feed."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender, mock_feed_checker, users=True)

    def test_check_out_exception(self, mock_sender, mock_feed_checker, *args):
        self.tg_request['message']['text'] = TEST_DB[0]['feed']
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})

        mock_feed_checker.side_effect = Exception
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = "Can't read the feed. Check for errors or try again later."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender, mock_feed_checker, users=True)

    @staticmethod
    def _reset(mock_sender, mock_feed_checker=None,
               mock_add_feed=None, users=False):
        mock_sender.reset_mock()
        if mock_feed_checker: mock_feed_checker.reset_mock()
        if mock_add_feed: mock_add_feed.reset_mock()
        if users: USERS.pop(MASTER_UID)


@patch('kaban.helpers.feed_shortcut')
@patch('kaban.helpers.check_out_feed')
@patch('kaban.helpers.delete_a_feed')
@patch('kaban.helpers.list_user_feeds')
@patch('kaban.helpers.send_message')
class ListFeeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BASE_DIR / 'tests' / 'fixtures' / 'tg_request.json') as f:
            cls.tg_request = json.load(f)
        cls.bot = bot_config.get_bot()

    def test_add_fail(self, mock_sender, *args):
        self.tg_request['message']['text'] = CMD_LIST
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = f"You can use {CMD_CANCEL} to go back."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        mock_sender.assert_called_once()

        self._reset(mock_sender)
        USERS.pop(MASTER_UID)

    def test_list(self, mock_sender, mock_list, *args):
        self.tg_request['message']['text'] = CMD_LIST
        text = 'your-list'
        mock_list.return_value = text

        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender, mock_list)

    def test_delete(self, mock_sender, foo, mock_delete, *args):
        self.tg_request['message']['text'] = CMD_DELETE + ' feed-to-dell'
        text = "Done."
        mock_delete.return_value = text

        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender, mock_delete=mock_delete)

    def test_shortcut(self, mock_sender, foo, bar, mock_feed_checker, mock_shortcut):
        self.tg_request['message']['text'] = CMD_SHORTCUT + ' shortcut feed'
        mock_feed_checker.side_effect = DataAlreadyExists
        text = "Done."
        mock_shortcut.return_value = text

        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender, mock_feed_checker=mock_feed_checker,
                    mock_shortcut=mock_shortcut)

    def test_wrong_pattern(self, mock_sender, *args):
        self.tg_request['message']['text'] = CMD_DELETE
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, HELP)
        mock_sender.assert_called_once()
        self._reset(mock_sender)

    def test_empty_short(self, mock_sender, foo, bar, mock_feed_checker, mock_shortcut):
        self.tg_request['message']['text'] = CMD_SHORTCUT + ' shortcut feed'

        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = "No such web feed found. Check for errors."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender, mock_feed_checker=mock_feed_checker,
                    mock_shortcut=mock_shortcut)

    def test_wrong_short(self, mock_sender, foo, bar, mock_feed_checker, mock_shortcut):
        self.tg_request['message']['text'] = CMD_SHORTCUT + ' shortcut feed'
        mock_feed_checker.side_effect = DataAlreadyExists
        mock_shortcut.side_effect = IndexError

        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = f"The maximum length is {SHORTCUT_LEN} characters."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender, mock_feed_checker=mock_feed_checker,
                    mock_shortcut=mock_shortcut)

    @staticmethod
    def _reset(mock_sender, mock_list=None, mock_delete=None,
               mock_feed_checker=None, mock_shortcut=None):
        mock_sender.reset_mock()
        if mock_list: mock_list.reset_mock()
        if mock_delete: mock_delete.reset_mock()
        if mock_feed_checker: mock_feed_checker.reset_mock()
        if mock_shortcut: mock_shortcut.reset_mock()


@patch('kaban.helpers.feed_switcher')
@patch('kaban.helpers.check_out_feed')
@patch('kaban.helpers.send_message')
class Switcher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BASE_DIR / 'tests' / 'fixtures' / 'tg_request.json') as f:
            cls.tg_request = json.load(f)
        cls.bot = bot_config.get_bot()

    def test_add_fail(self, mock_sender, *args):
        self.tg_request['message']['text'] = CMD_SUMMARY
        USERS.setdefault(MASTER_UID, {'AWAITING_FEED': True, 'POTENTIAL_FEED': None})
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = f"You can use {CMD_CANCEL} to go back."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        mock_sender.assert_called_once()

        self._reset(mock_sender)
        USERS.pop(MASTER_UID)

    def test_switcher(self, mock_sender, mock_feed_checker, mock_switcher):
        mock_feed_checker.side_effect = DataAlreadyExists
        commands = [CMD_SUMMARY, CMD_DATE, CMD_LINK]
        for command in commands:
            self.tg_request['message']['text'] = command + ' dummy-feed'
            update = telebot.types.Update.de_json(json.dumps(self.tg_request))
            self.bot.process_new_updates([update])

            mock_switcher.assert_called_with(MASTER_UID, command, 'dummy-feed')
            mock_sender.assert_called_with(self.bot, MASTER_UID, "Done.")
            self._reset(mock_sender, mock_feed_checker, mock_switcher)

    def test_wrong_feed(self, mock_sender, mock_feed_checker, foo):
        self.tg_request['message']['text'] = CMD_SUMMARY + ' dummy-feed'
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        text = "No such web feed found. Check for errors."
        mock_sender.assert_called_with(self.bot, MASTER_UID, text)
        self._reset(mock_sender, mock_feed_checker)

    def test_wrong_pattern(self, mock_sender, *args):
        self.tg_request['message']['text'] = CMD_SUMMARY + 'wrong cmd'
        update = telebot.types.Update.de_json(json.dumps(self.tg_request))
        self.bot.process_new_updates([update])

        mock_sender.assert_called_with(self.bot, MASTER_UID, HELP)
        mock_sender.assert_called_once()
        self._reset(mock_sender)

    @staticmethod
    def _reset(mock_sender, mock_feed_checker=None, mock_switcher=None):
        mock_sender.reset_mock()
        if mock_feed_checker: mock_feed_checker.reset_mock()
        if mock_switcher: mock_switcher.reset_mock()
