from logging import RootLogger
import os
import pathlib
import re
from threading import Event
from typing import Dict, Union, List

import sqlalchemy
from feedparser.util import FeedParserDict


# Annotations
class Logger(RootLogger): pass

class Path(pathlib.Path): pass

class UsersInMemory(Dict[int, Dict[str, Union[bool, str]]]): pass

class BannedIp(List[str]): pass

class Feed(FeedParserDict): pass

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

class Engine(sqlalchemy.engine.Engine): pass


# Main data
MASTER = "@simple_complexity"
MASTER_UID = 1266575762

REPLIT: bool = False

BASE_DIR: Path = pathlib.Path(__file__).resolve().parent.parent

FEEDS_UPDATE_TIMEOUT = 3600

TIME_FORMAT = 'on %A, in %-d day of %B %Y, at %-H:%M %z'

NOTIFICATIONS: Path = BASE_DIR / "resources" / "notifications.txt"

FEED_SUMMARY_LEN = 400
SHORTCUT_LEN = 30

USERS: UsersInMemory = {}
BANNED: BannedIp = []

HOOK_READY_TO_WORK: Event = Event()
EXIT_EVENT: Event = Event()
NEW_MESSAGES_EVENT: Event = Event()


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
        API = input("Enter the bot API key: ").strip()


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
