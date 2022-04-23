import os
import re
import sys
import csv
import time
import signal
import pathlib
import datetime
import threading

import feedparser
from bs4 import BeautifulSoup

import telebot


MASTER = "@simple_complexity"

KEY_ADD_NEW_FEED = "add"
KEY_INSERT_INTO_DB = "confirm"
KEY_CANCEL = "cancel"
KEY_SHOW_USER_FEEDS = "list"
KEY_DELETE_FROM_DB = "delete"
COMMAND_ADD = f"/{KEY_ADD_NEW_FEED}"
COMMAND_INSERT = f"/{KEY_INSERT_INTO_DB}"
COMMAND_CANCEL = f"/{KEY_CANCEL}"
COMMAND_LIST = f"/{KEY_SHOW_USER_FEEDS}"
COMMAND_DELETE = f"/{KEY_DELETE_FROM_DB}"
DELETE_PATTERN = re.compile( r'{dell}\s\d+'.format(dell=COMMAND_DELETE) )
HELP = """
{add} - add a new web feed
{confirm} - start tracking the feed
{cancel} - go to the beginning
{list} - show list of your feeds
{delete} - use it with argument (delete n), it'll delete an n-th feed from your list
/help - this message
/start - restart the bot
""".format(add=COMMAND_ADD, confirm=COMMAND_INSERT, cancel=COMMAND_CANCEL,
           list=COMMAND_LIST, delete=COMMAND_DELETE)

READY_TO_WORK = threading.Event()
EXIT_EVENT = threading.Event()
NEW_MESSAGES_EVENT = threading.Event()
AWAITING_MESSAGES_EVENT = threading.Event()

USERS = {}
AWAITING_RSS = "AWAITING_FEED"
POTENTIAL_RSS = "POTENTIAL_FEED"

API = pathlib.Path.cwd() / "resources" / ".api"
if API.exists():
    with open(API) as f:
        API = f.read().strip()
else:
    API = None
    print("Enter the bot API key: ", end="")
    while not API:
        API = input().strip()

MESSAGES_SOCKET = pathlib.Path.cwd() / "resources" / "messages_socket"

DB = pathlib.Path.cwd() / "resources" / "database.db"
DB_HEADERS = ['feed', 'chat_id', 'last_update']
db = pathlib.Path.cwd() / "resources" / "database.csv"
if not db.exists():
    with open(db, 'w', encoding='utf8') as f:
        writer = csv.writer(f)
        writer.writerow(DB_HEADERS)

class DataAlreadyExistsError(Exception): pass
