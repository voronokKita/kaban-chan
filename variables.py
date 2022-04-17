import os
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
from telebot import types as bot_types

from flask import Flask, request, json
from werkzeug.serving import make_server
from pyngrok import ngrok


MASTER = "@simple_complexity"

KEY_CANCEL = "cancel"
KEY_ADD_NEW_FEED = "add_rss_feed"
KEY_INSERT_INTO_DB = "start_tracking_rss"

EXIT_EVENT = threading.Event()

USERS = {}
AWAITING_RSS = "AWAITING_RSS"
POTENTIAL_RSS = "POTENTIAL_RSS"

WEBHOOK = None
SERVER = None
UPDATER = None

API = pathlib.Path.cwd() / ".api"
with open(API) as f:
    API = f.read().strip()

DB_HEADERS = ['feed', 'chat_id', 'last_update']
db = pathlib.Path.cwd() / ".database.csv"
if not db.exists():
    with open(db, 'w', encoding='utf8') as f:
        writer = csv.writer(f)
        writer.writerow(DB_HEADERS)

class DataAlreadyExistsError(Exception): pass
