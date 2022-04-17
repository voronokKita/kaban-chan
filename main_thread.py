from bot_config import bot, bot_types, BUTTON_CANCEL, BUTTON_ADD_NEW_FEED, BUTTON_INSERT_INTO_DB
from webhook import app
from variables import *


class MainThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.server = make_server('127.0.0.1', 5000, app)
        self.context = app.app_context()
        self.context.push()

    def run(self):
        print("starting a webhook")
        self.server.serve_forever()

    def shutdown(self):
        print("stopping a webhook")
        for uid in USERS:
            markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
            text = "Sorry, but I go to sleep~ See you later (´• ω •`)ﾉﾞ"
            markup.add(BUTTON_ADD_NEW_FEED)
            bot.send_message(uid, text, reply_markup=markup)
        self.server.shutdown()


@bot.message_handler(commands=['start'])
def hello(message):
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(BUTTON_ADD_NEW_FEED)
    bot.send_message(message.chat.id, f"Hello, @{message.chat.username}!")
    time.sleep(1)
    text = f"Use /{KEY_ADD_NEW_FEED} button. I will check your web feed from time to time and notify when something new comes up~"
    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, "One bot to learn them all.")


@bot.message_handler(commands=[KEY_ADD_NEW_FEED, KEY_INSERT_INTO_DB, KEY_CANCEL])
def add_rss(message):
    uid = message.chat.id
    USERS.setdefault(uid, {AWAITING_RSS: False, POTENTIAL_RSS: None})
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    text = ""

    if not USERS[uid][AWAITING_RSS] and message.text == f"/{KEY_ADD_NEW_FEED}":
        text = "Send me a URI of your web feed. I'll check it out."
        markup.add(BUTTON_CANCEL)
        USERS[uid][AWAITING_RSS] = True

    elif message.text == f"/{KEY_CANCEL}":
        text = "Cancelled~"
        markup.add(BUTTON_ADD_NEW_FEED)
        USERS.pop(uid)

    elif USERS[uid][AWAITING_RSS] and USERS[uid][POTENTIAL_RSS] and message.text == f"/{KEY_INSERT_INTO_DB}":
        try:
            add_new_rss(USERS[uid][POTENTIAL_RSS], str(uid))
        except Exception as error:
            text = f"Something went wrong :C Please notify the master {MASTER} about this. Error text:\n{error}"
            markup.add(BUTTON_CANCEL)
        else:
            text = "Web feed added!"
            markup.add(BUTTON_ADD_NEW_FEED)
            USERS.pop(uid)

    if text:
        bot.send_message(uid, text, reply_markup=markup)


@bot.message_handler(content_types=['text'])
def get_text_data(message):
    uid = message.chat.id
    markup = bot_types.ReplyKeyboardMarkup(resize_keyboard=True)
    text = ""
    if USERS.get(uid) and USERS[uid][AWAITING_RSS]:
        rss = message.text.strip()
        try:
            feedparser.parse(rss).feed.title
            check_out_rss(rss, str(uid))
        except DataAlreadyExistsError:
            text = "I already watch this feed for you!"
        except:
            text = "Can't read the feed. Check for errors or try again later."
        else:
            text = f"All is fine — I managed to read the feed! Press /{KEY_INSERT_INTO_DB} button to conform."
            markup.add(BUTTON_INSERT_INTO_DB)
            USERS[uid][POTENTIAL_RSS] = rss
        finally:
            markup.add(BUTTON_CANCEL)

    if text:
        bot.send_message(uid, text, reply_markup=markup)
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
