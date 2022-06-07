from datetime import datetime
import logging
import os
import pathlib
import re
import threading

from typing import Dict, Union, List, Callable, Any, TypeVar

import telebot
import feedparser
import sqlalchemy as sql
from sqlalchemy.orm import declarative_base


# Annotations
class Logger(logging.RootLogger): pass

class Event(threading.Event): pass

class Path(pathlib.Path): pass

class UsersInMemory(Dict[int, Dict[str, Union[bool, str]]]): pass

class BannedIp(List[str]): pass

class Feed(feedparser.util.FeedParserDict): pass

class UpdPost(Dict[str, Union[str, Feed]]):
    """ {'str-title-md5': Feed} """

class UpdPostList(List[UpdPost]):
    """ [UpdPost,] """

class UpdFeeds(Dict[str, UpdPostList]):
    """ {'str-feed': UpdPostList[UpdPost,]} """

class UpdPosts(Dict[int, UpdFeeds]):
    """ {int-uid: UpdFeeds} """

class Key(str): pass

class Command(str): pass


# Main data
MASTER = "@simple_complexity"

REPLIT = False

BASE_DIR: Path = pathlib.Path(__file__).resolve().parent.parent

FEEDS_UPDATE_TIMEOUT = 3600

TIME_FORMAT = 'on %A, in %-d day of %B %Y, at %-H:%M %z'

NOTIFICATIONS: Path = BASE_DIR / "resources" / "notifications.txt"

FEED_SUMMARY_LEN = 400
SHORTCUT_LEN = 30

USERS: UsersInMemory = {}
BANNED: BannedIp = []

HOOK_READY_TO_WORK: Event = threading.Event()
EXIT_EVENT: Event = threading.Event()
NEW_MESSAGES_EVENT: Event = threading.Event()


# Exceptions
class DataAlreadyExists(Exception): pass

class WebhookRequestError(Exception): pass
class FeedLoadError(Exception): pass
class FeedFormatError(Exception): pass
class FeedPreprocessError(Exception): pass


# Telebot commands
ADD_FEED = Key("add")
INSERT_FEED = Key("confirm")
GO_BACK = Key("cancel")
LIST_FEEDS = Key("list")
DELETE_FEED = Key("delete")
ADD_SHORTCUT = Key("short")
SWITCH_SUMMARY = Key("summary")
SWITCH_DATE = Key("date")
SWITCH_LINK = Key("link")

CMD_ADD = Command(f"/{ADD_FEED}")
CMD_INSERT = Command(f"/{INSERT_FEED}")
CMD_CANCEL = Command(f"/{GO_BACK}")
CMD_LIST = Command(f"/{LIST_FEEDS}")
CMD_DELETE = Command(f"/{DELETE_FEED}")
CMD_SHORTCUT = Command(f"/{ADD_SHORTCUT}")
CMD_SUMMARY = Command(f"/{SWITCH_SUMMARY}")
CMD_DATE = Command(f"/{SWITCH_DATE}")
CMD_LINK = Command(f"/{SWITCH_LINK}")

PATTERN_DELETE = re.compile(rf'({CMD_DELETE}\s+)(\S+)')
PATTERN_SHORTCUT = re.compile(rf'({CMD_SHORTCUT}\s+)(\S+\s*)(\S+)?')
PATTERN_SUMMARY = re.compile(rf'({CMD_SUMMARY}\s+)(\S+)')
PATTERN_DATE = re.compile(rf'({CMD_DATE}\s+)(\S+)')
PATTERN_LINK = re.compile(rf'({CMD_LINK}\s+)(\S+)')
PATTERN_COMMAND = re.compile(r'(/\w+\s+)(\S+)')

HELP = """
{add} - add a new web feed
{confirm} - start tracking the feed
{cancel} - go to the beginning
{list} - show list of your feeds
{delete} - use it with argument ( {delete} [feed] ), it'll delete a feed from your list
{date} - ( {date} [feed] ), switch display of publication date in all posts from some feed
{summary} - ( {summary} [feed] ), switch display of summary
{link} - ( {link} [feed] ), switch display of a URL of feed's posts
{short} - ( {short} [feed] [shortcut] ), make a {s_len} character shortcut for a feed, or empty to clear it
/help - this message
/start - restart the bot
master: {master}
""".format(add=CMD_ADD, confirm=CMD_INSERT, cancel=CMD_CANCEL,
           list=CMD_LIST, delete=CMD_DELETE, date=CMD_DATE,
           summary=CMD_SUMMARY, link=CMD_LINK, short=CMD_SHORTCUT,
           s_len=SHORTCUT_LEN, master=MASTER)

EXIT_NOTE = "Sorry, but I go to sleep~ See you later (´• ω •`)ﾉﾞ"


# Web settings
PORT = 5000
ADDRESS = '0.0.0.0'
WEBHOOK_ENDPOINT = "/hook"
WEBHOOK_WAS_SET = re.compile(r'was set|already set')
REPLIT_URL = "https://kaban-chan.kitavoronok.repl.co"

if REPLIT:
    API = os.environ['API']
else:
    API = BASE_DIR / "resources" / ".api"
    if API.exists():
        with open(API) as f: API = f.read().strip()
    else:
        API = input("Enter the bot's API key: ").strip()


# Database
POSTS_TO_STORE = 50

DB_URI: Path = BASE_DIR / "resources" / "database.sqlite3"
db = sql.create_engine(f"sqlite:///{DB_URI}", future=True)
SQLAlchemyBase = declarative_base()

class FeedsDB(SQLAlchemyBase):
    __tablename__ = "feeds"
    id = sql.Column(sql.Integer, primary_key=True)
    uid = sql.Column(sql.Integer, index=True, nullable=False)
    feed = sql.Column(sql.Text, nullable=False)
    last_posts = sql.Column(sql.Text, nullable=False, default=' ')
    last_check = sql.Column(sql.DateTime, nullable=False, default=datetime.now)
    summary = sql.Column(sql.Boolean, nullable=False, default=True)
    date = sql.Column(sql.Boolean, nullable=False, default=True)
    link = sql.Column(sql.Boolean, nullable=False, default=True)
    short = sql.Column(sql.String(SHORTCUT_LEN), nullable=True, default=None)
    def __str__(self):
        return f"<feed entry #{self.id!r}>"

class WebhookDB(SQLAlchemyBase):
    __tablename__ = "webhook"
    id = sql.Column(sql.Integer, primary_key=True)
    data = sql.Column(sql.Text, nullable=False)
    def __str__(self):
        return f"<web message #{self.id!r}>"


# Requests errors
""" Telegram request error codes
400 - Bad Request: chat not found
400 - Bad request: user not found
400 - Bad request: Group migrated to supergroup
400 - Bad request: Invalid file id
400 - Bad request: Message not modified
400 - Bad request: Wrong parameter action in request
401 - Unauthorized
403 - Forbidden: user is deactivated
403 - Forbidden: bot was kicked
403 - Forbidden: bot blocked by user
403 - Forbidden: bot can't send messages to bots
409 - Conflict: Terminated by other long poll
429 - Too many requests
"""
WRONG_TOKEN = re.compile(r'Unauthorized')
UID_NOT_FOUND = re.compile(r'not found')
BOT_BLOCKED = re.compile(r'kicked|blocked|deactivated')
BOT_TIMEOUT = re.compile(r'Too many requests')


# Logging
LOG: Path = BASE_DIR / "resources" / "feedback.log"
LOG_FORMAT = '- %(asctime)s %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M'

werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel('ERROR')
werkzeug_log_handler = logging.FileHandler(filename=LOG, encoding='utf8')
werkzeug_log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFORMAT)
werkzeug_log_handler.setFormatter(werkzeug_log_formatter)
werkzeug_log.addHandler(werkzeug_log_handler)

telebot_log = telebot.logger
telebot_log.setLevel('ERROR')
telebot_log_handler = logging.FileHandler(filename=LOG, encoding='utf8')
telebot_log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFORMAT)
telebot_log_handler.setFormatter(telebot_log_formatter)
telebot_log.addHandler(telebot_log_handler)

log: Logger = telebot.logging.getLogger(__name__)
log.setLevel('WARNING')
log_handler = logging.FileHandler(filename=LOG, encoding='utf8')
log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFORMAT)
log_handler.setFormatter(log_formatter)
log.addHandler(log_handler)

def info(s):
    log.setLevel('INFO')
    log.info(s)
    log.setLevel('WARNING')

def debug(s):
    log.setLevel('DEBUG')
    log.debug(s)
    log.setLevel('WARNING')


# Cleaning
del LOG_FORMAT
del LOG_DATEFORMAT
del werkzeug_log_handler
del werkzeug_log_formatter
del telebot_log_handler
del telebot_log_formatter
del log_handler
del log_formatter
