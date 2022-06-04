from datetime import datetime
from collections import defaultdict
import csv
import hashlib
import logging
import os
import pathlib
import re
import secrets
import signal
import subprocess
import sys
import threading
import time

import telebot
from telebot.apihelper import ApiTelegramException

import feedparser
from bs4 import BeautifulSoup

from pyngrok import ngrok
import flask
from flask import Flask, request
from werkzeug.serving import make_server

import sqlalchemy as sql
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session as SQLSession


MASTER = "@simple_complexity"

FEEDS_UPDATE_TIMEOUT = 3600

TIME_FORMAT = 'on %A, in %-d day of %B %Y, at %-H:%M %z'

NOTIFICATIONS = pathlib.Path.cwd() / "resources" / "notifications.txt"
UPDATER_BACKUP = pathlib.Path.cwd() / "resources" / "updater_backup.csv"

SUMMARY = 400
SHORTCUT = 30

USERS = {}
BANNED = []

class DataAlreadyExists(Exception): pass
class WrongWebhookRequestError(Exception): pass
class FeedLoadError(Exception): pass


READY_TO_WORK = threading.Event()
EXIT_EVENT = threading.Event()
NEW_MESSAGES_EVENT = threading.Event()


# Telebot commands
KEY_ADD = "add"
KEY_INSERT = "confirm"
KEY_CANCEL = "cancel"
KEY_LIST = "list"
KEY_DELETE = "delete"
KEY_SHORTCUT = "short"
KEY_SW_SUMMARY = "summary"
KEY_SW_DATE = "date"
KEY_SW_LINK = "link"

COMMAND_ADD = f"/{KEY_ADD}"
COMMAND_INSERT = f"/{KEY_INSERT}"
COMMAND_CANCEL = f"/{KEY_CANCEL}"
COMMAND_LIST = f"/{KEY_LIST}"
COMMAND_DELETE = f"/{KEY_DELETE}"
COMMAND_SHORTCUT = f"/{KEY_SHORTCUT}"
COMMAND_SW_SUMMARY = f"/{KEY_SW_SUMMARY}"
COMMAND_SW_DATE = f"/{KEY_SW_DATE}"
COMMAND_SW_LINK = f"/{KEY_SW_LINK}"

PATTERN_DELETE = re.compile(rf'({COMMAND_DELETE}\s+)(\S+)')
PATTERN_SHORTCUT = re.compile(rf'({COMMAND_SHORTCUT}\s+)(\S+\s*)(\S+)?')
PATTERN_SUMMARY = re.compile(rf'({COMMAND_SW_SUMMARY}\s+)(\S+)')
PATTERN_DATE = re.compile(rf'({COMMAND_SW_DATE}\s+)(\S+)')
PATTERN_LINK = re.compile(rf'({COMMAND_SW_LINK}\s+)(\S+)')
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
""".format(add=COMMAND_ADD, confirm=COMMAND_INSERT, cancel=COMMAND_CANCEL,
           list=COMMAND_LIST, delete=COMMAND_DELETE, date=COMMAND_SW_DATE,
           summary=COMMAND_SW_SUMMARY, link=COMMAND_SW_LINK, short=COMMAND_SHORTCUT,
           s_len=SHORTCUT, master=MASTER)

EXIT_NOTE = "Sorry, but I go to sleep~ See you later (´• ω •`)ﾉﾞ"


# Web settings
ADDRESS = '127.0.0.1'
PORT = 5000
WEBHOOK_ENDPOINT = "/kaban-chan"
WEBHOOK_WAS_SET = re.compile(r'was set|already set')

API = pathlib.Path.cwd() / "resources" / ".api"
if API.exists():
    with open(API) as f:
        API = f.read().strip()
else:
    API = input("Enter the bot's API key: ").strip()


# Database
POSTS_TO_STORE = 50

DB_URI = pathlib.Path.cwd() / "resources" / "database.db"
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
    short = sql.Column(sql.String(SHORTCUT), nullable=True, default=None)
    def __repr__(self):
        return f"<feed entry #{self.id!r}>"

class WebhookDB(SQLAlchemyBase):
    __tablename__ = "webhook"
    id = sql.Column(sql.Integer, primary_key=True)
    data = sql.Column(sql.Text, nullable=False)
    def __repr__(self):
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
LOG = pathlib.Path.cwd() / "resources" / "feedback.log"
LOG_FORMAT = '- %(asctime)s %(levelname)s: %(message)s'
LOG_DATEFMT = '%Y-%m-%d %H:%M'

werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel('ERROR')
werkzeug_log_handler = logging.FileHandler(filename=LOG, encoding='utf8')
werkzeug_log_handler.setFormatter( logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFMT) )
werkzeug_log.addHandler(werkzeug_log_handler)

telebot_log = telebot.logger
telebot_log.setLevel('ERROR')
telebot_log_handler = logging.FileHandler(filename=LOG, encoding='utf8')
telebot_log_handler.setFormatter( logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFMT) )
telebot_log.addHandler(telebot_log_handler)

log = telebot.logging.getLogger(__name__)
log.setLevel('WARNING')
log_handler = logging.FileHandler(filename=LOG, encoding='utf8')
log_handler.setFormatter( logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFMT) )
log.addHandler(log_handler)

def info(s):
    log.setLevel('INFO')
    log.info(s)
    log.setLevel('WARNING')

def debug(s):
    log.setLevel('DEBUG')
    log.debug(s)
    log.setLevel('WARNING')
