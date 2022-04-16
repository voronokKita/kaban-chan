# TODO read all:
    # https://core.telegram.org/bots/api#available-types
    # https://github.com/eternnoir/pyTelegramBotAPI
# TODO logging
# TODO testing
# TODO easy start
""" Thanks to
https://habr.com/ru/post/350648/
https://habr.com/ru/post/495036/
https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/webhook_examples/webhook_flask_echo_bot.py """
import os
import sys
import csv
import time
import signal
import pathlib
import threading
from datetime import datetime

import telebot
from telebot import types as bot_types
import feedparser
from bs4 import BeautifulSoup
from flask import Flask, request, json
from werkzeug.serving import make_server
from pyngrok import ngrok


MASTER = "@simple_complexity"

API = pathlib.Path.cwd() / ".api"
with open(API) as f:
    API = f.read().strip()
bot = telebot.TeleBot(API)

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

EXIT_EVENT = threading.Event()

WEBHOOK = None
try:
    WEBHOOK = ngrok.connect(5000, bind_tls=True)
    print(WEBHOOK)
    time.sleep(1)
    k = """curl --location --request POST \
    'https://api.telegram.org/bot{api}/setWebhook' \
    --header 'Content-Type: application/json' \
    --data-raw '{{"url": "{uri}"}}' \
    """.format(api=API, uri=WEBHOOK.public_url)
    os.system(k)  # TODO subprocess
    print()
except Exception as error:
    print("Failed to set a webhook. Error code:", "-"*10, error, "-"*10, sep="\n")
    sys.exit(1)
"""
try:
    # Block until CTRL-C or some other terminating event
    ngrok_process.proc.wait()
except KeyboardInterrupt:
    print(" Shutting down server.")
    ngrok.kill()
"""

app = Flask(__name__)
SERVER = None

class DataAlreadyExistsError(Exception): pass



def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTSTP, signal_handler)

    global SERVER
    SERVER = MainThread(app)
    SERVER.start()

    side_thread = threading.Thread(target=updater)
    side_thread.start()

    time.sleep(1)
    print("I woke up (*・ω・)ﾉ")

    side_thread.join()
    SERVER.shutdown()

    print("Go to sleep (´-ω-｀)…zZZ")
    sys.exit(0)


def signal_handler(signal, frame):
    print("signal")
    EXIT_EVENT.set()
    stop_server()


# <main>
class MainThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server('127.0.0.1', 5000, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        print("starting a webhook")
        self.server.serve_forever()

    def shutdown(self):
        print("stopping a webhook")
        self.server.shutdown()


@app.route("/", methods=['POST'])
def receiver():
    if request.headers.get('content-type') == 'application/json':
        json = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json)
        bot.process_new_updates([update])
    return ""


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
def add_rss(message):
    global FLAG_AWAITING_RSS, POTENTIAL_RSS
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    text = ""
    if not FLAG_AWAITING_RSS and message.text == f"/{KEY_ADD_NEW_FEED}":
        text = "Send me a URI of your RSS. I'll check it out."
        markup.add(BUTTON_CANCEL)
        FLAG_AWAITING_RSS = True

    elif FLAG_AWAITING_RSS and message.text == f"/{KEY_CANCEL}":
        text = "Cancelled~"
        markup.add(BUTTON_ADD_NEW_FEED)
        FLAG_AWAITING_RSS = False
        POTENTIAL_RSS = None

    elif FLAG_AWAITING_RSS and POTENTIAL_RSS and message.text == f"/{KEY_INSERT_INTO_DB}":
        try:
            add_new_rss(POTENTIAL_RSS, str(message.chat.id))
        except Exception as error:
            text = f"Something went wrong :C Please notify the master {MASTER} about this. Error text:\n{error}"
            markup.add(BUTTON_CANCEL)
        else:
            text = "RSS added!"
            markup.add(BUTTON_ADD_NEW_FEED)
            FLAG_AWAITING_RSS = False
            POTENTIAL_RSS = None

    if text:
        bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(content_types=['text'])
def get_text_data(message):
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
# </main>

# <updater>
def updater():
    while True:
        print("check for updates")
        if EXIT_EVENT.wait(timeout=3):
            break
    print("ending updates")
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
    print()
"""
# </updater>

if __name__ == '__main__':
    main()
