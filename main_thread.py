from telebot import bot, BUTTON_CANCEL, BUTTON_ADD_NEW_FEED, BUTTON_INSERT_INTO_DB
from webhook import app
from variables import *


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

    elif message.text == f"/{KEY_CANCEL}":
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
