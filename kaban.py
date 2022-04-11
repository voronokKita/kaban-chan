#!python3
# TODO read all:
    # https://core.telegram.org/bots/api#available-types
    # https://github.com/eternnoir/pyTelegramBotAPI
# TODO logging
# TODO testing
import csv
import time
import pathlib
from datetime import datetime
from pprint import pprint

import telebot
from telebot import types as bot_types
import feedparser
from bs4 import BeautifulSoup


MASTER = "@simple_complexity"

api = pathlib.Path.cwd() / ".env"
with open(api) as f:
    api = f.read().strip()
bot = telebot.TeleBot(api)

DB_HEADERS = ['feed', 'chat_id']
db = pathlib.Path.cwd() / ".database.csv"
if not db.exists():
    with open(db, 'w', encoding='utf8') as f:
        writer = csv.writer(f)
        writer.writerow(DB_HEADERS)

KEY_CANCEL = "cancel"
BUTTON_CANCEL = bot_types.KeyboardButton(f"/{KEY_CANCEL}")
KEY_ADD_NEW_FEED = "add_rss_feed"
BUTTON_ADD_NEW_FEED = bot_types.KeyboardButton(f"/{KEY_ADD_NEW_FEED}")
KEY_INSERT_INTO_DB = "start_tracking_rss"
BUTTON_INSERT_INTO_DB = bot_types.KeyboardButton(f"/{KEY_INSERT_INTO_DB}")

FLAG_AWAITING_RSS = False
POTENTIAL_RSS = None

class DataAlreadyExistsError(Exception): pass


@bot.message_handler(commands=['start'])
def hello(message):
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(BUTTON_ADD_NEW_FEED)
    bot.send_message(message.chat.id, f"Hello, @{message.chat.username}!")
    time.sleep(1)
    text = f"Use /{KEY_ADD_NEW_FEED} button. I will check your RSS from time to time and notify when something new comes up~"
    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, "One bot to learn them all.")


@bot.message_handler(commands=[KEY_ADD_NEW_FEED, KEY_INSERT_INTO_DB, KEY_CANCEL])
def main_handler(message):
    global FLAG_AWAITING_RSS, POTENTIAL_RSS
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    text = ""
    if message.text == f"/{KEY_ADD_NEW_FEED}":
        text = "Send me a URI of your RSS. I'll check it out."
        markup.add(BUTTON_CANCEL)
        FLAG_AWAITING_RSS = True

    elif message.text == f"/{KEY_CANCEL}":
        text = "Cancelled~"
        markup.add(BUTTON_ADD_NEW_FEED)
        FLAG_AWAITING_RSS = False

    elif FLAG_AWAITING_RSS and POTENTIAL_RSS and message.text == f"/{KEY_INSERT_INTO_DB}":
        try:
            add_new_rss(POTENTIAL_RSS, str(message.chat.id))
        except Exception as error:
            text = f"Something went wrong :C Please notify the master {MASTER} about this. Error code:\n{error}"
            markup.add(BUTTON_CANCEL)
        else:
            text = "RSS added!"
            markup.add(BUTTON_ADD_NEW_FEED)
            FLAG_AWAITING_RSS = False
            POTENTIAL_RSS = None

    if text:
        bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(content_types=['text'])
def echo(message):
    global POTENTIAL_RSS
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    text = ""
    if FLAG_AWAITING_RSS:
        rss = message.text.strip()
        try:
            feedparser.parse(rss).feed.title
            check_out_rss(rss, str(message.chat.id))
        except DataAlreadyExistsError:
            text = "I already watch this feed for you!"
        except:
            text = "Can't read the feed. Check for errors or try again later."
        else:
            text = f"All is fine — I managed to read the RSS! Press /{KEY_INSERT_INTO_DB} button to conform."
            markup.add(BUTTON_INSERT_INTO_DB)
            POTENTIAL_RSS = rss
        finally:
            markup.add(BUTTON_CANCEL)

    if text:
        bot.send_message(message.chat.id, text, reply_markup=markup)
    else:
        bot.reply_to(message, message.text)


def check_out_rss(rss, chat_id):
    with open(db) as f:
        reader = csv.DictReader(f, DB_HEADERS)
        for line in reader:
            if line["chat_id"] == chat_id and line["feed"] == rss:
                raise DataAlreadyExistsError()


def add_new_rss(rss, chat_id):
    with open(db, 'a', encoding='utf8') as f:
        writer = csv.writer(f)
        writer.writerow([rss, chat_id])
    print("db: a new entry")


bot.infinity_polling()


"""
#  http://feeds.bbci.co.uk/news/rss.xml
python_feed = feedparser.parse('https://feeds.feedburner.com/PythonInsider')
print(python_feed.feed.title)
print(python_feed.feed.link)
print()
for i in range(3):
    print(python_feed.entries[i].title)
    print(python_feed.entries[i].published)
    soup = BeautifulSoup(python_feed.entries[i].summary, features='html.parser')
    text = soup.text[:200]
    print(f"{text.strip()}...")
    print(python_feed.entries[i].link)
    print()"""
