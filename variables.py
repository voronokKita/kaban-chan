import os
import re
import sys
import csv
import time
import signal
import pathlib
import datetime
import threading

import telebot

import feedparser
from bs4 import BeautifulSoup

from pyngrok import ngrok
from flask import Flask, request
from werkzeug.serving import make_server

import sqlalchemy as sql
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session as SQLSession


MASTER = "@simple_complexity"

class DataAlreadyExistsError(Exception): pass


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


DB_URI = pathlib.Path.cwd() / "resources" / "database.db"
db = sql.create_engine(f"sqlite:///{DB_URI}", future=True)
SQLAlchemyBase = declarative_base()

class WebFeedsDB(SQLAlchemyBase):
    __tablename__ = "feeds"
    id = sql.Column(sql.Integer, primary_key=True)
    user_id = sql.Column(sql.Integer, index=True, nullable=False)
    web_feed = sql.Column(sql.Text, nullable=False)
    last_check = sql.Column(sql.DateTime, nullable=True, default=None)
    def __repr__(self):
        return f"<feed #{self.id!r}>"

class WebhookDB(SQLAlchemyBase):
    __tablename__ = "webhook"
    id = sql.Column(sql.Integer, primary_key=True)
    time = sql.Column(sql.DateTime, nullable=False, default=datetime.datetime.now)
    data = sql.Column(sql.Text, nullable=False)
    def __repr__(self):
        return f"<message #{self.id!r}>"
