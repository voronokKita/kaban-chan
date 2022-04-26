from variables import *
import helpers


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
            self.bot = receiver()
            while True:
                if NEW_MESSAGES_EVENT.wait():
                    if not EXIT_EVENT.is_set():
                        self._handler()
                    else:
                        print("stopping a receiver")
                        self._receiver_stop()
                        break
        except Exception as error:
            print("error in a receiver:", error)
            self.exception = error
            helpers.exit_signal()

    def _handler(self):
        data = None
        with SQLSession(db) as session:
            message = session.query(WebhookDB).first()
            if message:
                data = message.data
                session.delete(message)
                session.commit()
                if not session.query(WebhookDB).first():
                    NEW_MESSAGES_EVENT.clear()
        update = telebot.types.Update.de_json(data)
        self.bot.process_new_updates([update])

    def _receiver_stop(self):
        for uid in USERS:
            text = "Sorry, but I go to sleep~ See you later (´• ω •`)ﾉﾞ"
            helpers.send_message(self.bot, uid, text)


def receiver():
    bot = telebot.TeleBot(API)


    @bot.message_handler(commands=['start'])
    def hello(message):
        global USERS
        uid = message.chat.id
        if USERS.get(uid):
            USERS.pop(uid)

        helpers.send_message(bot, message.chat.id, f"Hello, @{message.chat.username}!")
        time.sleep(1)
        text = f"Use {COMMAND_ADD} command. I will check your web feed from time to time " \
                "and notify when something new comes up~"
        helpers.send_message(bot, message.chat.id, text)


    @bot.message_handler(commands=['help'])
    def help(message):
        helpers.send_message(bot, message.chat.id, HELP)


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
            helpers.add_new_rss(USERS[uid][POTENTIAL_RSS], uid)
            text = "New web feed added!"
            USERS.pop(uid)  #! TODO load first

        else:
            text = f"You can use {COMMAND_CANCEL} to go back."

        helpers.send_message(bot, uid, text)


    @bot.message_handler(commands=[KEY_SHOW_USER_FEEDS, KEY_DELETE_FROM_DB])
    def list_rss(message):
        global USERS
        uid = message.chat.id
        text = ""

        if USERS.get(uid) and USERS[uid][AWAITING_RSS]:
            text = f"You can use {COMMAND_CANCEL} to go back."

        elif message.text == COMMAND_LIST:
            text = helpers.list_rss(uid)

        elif DELETE_PATTERN.fullmatch(message.text.strip()):
            feed = DELETE_PATTERN.findall( message.text.strip() )[0][1]
            text = helpers.delete_rss(feed, uid)

        else:
            text = f"To delete an entry from your list of feeds use: {COMMAND_DELETE} [feed]"

        helpers.send_message(bot, uid, text)


    @bot.message_handler(content_types=['text'])
    def get_text_data(message):
        global USERS
        uid = message.chat.id
        text = ""

        if USERS.get(uid) and USERS[uid][AWAITING_RSS]:
            rss = message.text.strip()
            try:
                feedparser.parse(rss).feed.title
                helpers.check_out_rss(rss, uid)
            except DataAlreadyExistsError:
                text = "I already watch this feed for you!"
            except:
                text = "Can't read the feed. Check for errors or try again later."
            else:
                text = f"All is fine — I managed to read the feed! Use the {COMMAND_INSERT} command to complete."
                USERS[uid][POTENTIAL_RSS] = rss

        if text:
            helpers.send_message(bot, uid, text)


    return bot
