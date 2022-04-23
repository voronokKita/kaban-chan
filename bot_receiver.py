from variables import *


class ReceiverThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.bot = None
        self.exception = None


    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception


    def run(self):
        print("starting a receiver")
        try:
            self.bot = self._receiver()
            self._handler()
        except Exception as error:
            print("error in a receiver:", error)
            self.exception = error
            EXIT_EVENT.set()


    def _handler(self):
        while True:
            if NEW_MESSAGES_EVENT.wait():
                if EXIT_EVENT.is_set():
                    print("stopping a receiver")
                    self._receiver_stop()
                    break
                data = None
                with SQLSession(db) as session:
                    message = session.scalars( sql.select(WebhookDB) ).first()
                    if message:
                        data = message.data
                        session.delete(message)
                        session.commit()
                        if not session.scalars( sql.select(WebhookDB) ).first():
                            NEW_MESSAGES_EVENT.clear()
                update = telebot.types.Update.de_json(data)
                self.bot.process_new_updates([update])

    def _receiver_stop(self):
        for uid in USERS:
            text = "Sorry, but I go to sleep~ See you later (´• ω •`)ﾉﾞ"
            self.bot.send_message(uid, text)


    def _receiver(self):
        bot = telebot.TeleBot(API)


        @bot.message_handler(commands=['start'])
        def hello(message):
            global USERS
            uid = message.chat.id
            if USERS.get(uid):
                USERS.pop(uid)
            bot.send_message(message.chat.id, f"Hello, @{message.chat.username}!")
            time.sleep(1)
            text = f"Use {COMMAND_ADD} command. I will check your web feed from time to time and notify when something new comes up~"
            bot.send_message(message.chat.id, text)


        @bot.message_handler(commands=['help'])
        def help(message):
            bot.send_message(message.chat.id, HELP)


        @bot.message_handler(commands=[KEY_ADD_NEW_FEED, KEY_INSERT_INTO_DB, KEY_CANCEL])
        def add_rss(message):
            global USERS
            uid = message.chat.id
            USERS.setdefault(uid, {AWAITING_RSS: False, POTENTIAL_RSS: None})
            text = ""

            if not USERS[uid][AWAITING_RSS] and message.text == COMMAND_ADD:
                text = "Send me a URI of your web feed. I'll check it out."
                USERS[uid][AWAITING_RSS] = True

            elif message.text == COMMAND_CANCEL:
                text = "Cancelled~"
                USERS.pop(uid)

            elif USERS[uid][AWAITING_RSS] and USERS[uid][POTENTIAL_RSS] and message.text == COMMAND_INSERT:
                try:
                    add_new_rss(USERS[uid][POTENTIAL_RSS], uid)
                except Exception as error:
                    text = f"Something went wrong :C Please notify the master {MASTER} about this. Error text:\n{error}"
                else:
                    text = "New web feed added!"
                    USERS.pop(uid)

            else:
                text = f"You can use {COMMAND_CANCEL} to go back."

            bot.send_message(uid, text)


        @bot.message_handler(commands=[KEY_SHOW_USER_FEEDS, KEY_DELETE_FROM_DB])  #! TODO
        def list_rss(message):
            global USERS
            uid = message.chat.id
            text = ""

            if USERS.get(uid) and USERS[uid][AWAITING_RSS]:
                text = f"You can use {COMMAND_CANCEL} to go back."

            elif message.text == COMMAND_LIST:
                list_of_feeds = ""
                with open(db) as f:
                    reader = csv.DictReader(f, DB_HEADERS)
                    i = 1
                    for line in reader:
                        if line["chat_id"] == str(uid):
                            list_of_feeds += f"{i}. {line['feed']}\n"
                            i += 1
                if list_of_feeds:
                    text += list_of_feeds
                    text += f"\nTo delete an entry use: {COMMAND_DELETE} [number]"
                else:
                    text += "There is none!"

            elif DELETE_PATTERN.fullmatch(message.text.strip()):
                text = "Make love!"

            bot.send_message(uid, text)


        @bot.message_handler(content_types=['text'])
        def get_text_data(message):
            global USERS
            uid = message.chat.id
            text = ""

            if USERS.get(uid) and USERS[uid][AWAITING_RSS]:
                rss = message.text.strip()
                try:
                    feedparser.parse(rss).feed.title
                    check_out_rss(rss, uid)
                except DataAlreadyExistsError:
                    text = "I already watch this feed for you!"
                except:
                    text = "Can't read the feed. Check for errors or try again later."
                else:
                    text = f"All is fine — I managed to read the feed! Use the {COMMAND_INSERT} command to complete."
                    USERS[uid][POTENTIAL_RSS] = rss

            if text:
                bot.send_message(uid, text)
            else:
                bot.reply_to(message, message.text)


        def check_out_rss(rss, chat_id):
            with SQLSession(db) as session:
                result = session.scalars(
                    sql.select(WebFeedsDB)
                    .where(WebFeedsDB.user_id == chat_id,
                           WebFeedsDB.web_feed == rss)
                ).first()
                if result:
                    raise DataAlreadyExistsError()


        def add_new_rss(rss, chat_id):
            with SQLSession(db) as session:
                new_entry = WebFeedsDB(user_id=chat_id, web_feed=rss)
                session.add(new_entry)
                session.commit()
            print("db: a new entry")


        return bot
