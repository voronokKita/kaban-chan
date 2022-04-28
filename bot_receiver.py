from variables import *
import helpers


class ReceiverThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.bot = None
        self.exception = None

    def __repr__(self):
        return "receiver thread"

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception

    def run(self):
        try:
            self.bot = receiver()
            while True:
                if NEW_MESSAGES_EVENT.wait():
                    if EXIT_EVENT.is_set():
                        self._receiver_stop()
                        break
                    else:
                        self._handler()
        except Exception as error:
            self.exception = error
            helpers.exit_signal()

    def _handler(self):
        data = None
        with SQLSession(db) as session:
            message = session.query(WebhookDB).first()
            if message:
                data = message.data
                session.query(WebhookDB).where(WebhookDB.id == message.id).delete()
                session.commit()
                if not session.query(WebhookDB).first():
                    NEW_MESSAGES_EVENT.clear()
        update = telebot.types.Update.de_json(data)
        self.bot.process_new_updates([update])

    def _receiver_stop(self):
        for uid in USERS:
            helpers.send_message(self.bot, uid, EXIT_NOTIFICATION)


def receiver():
    bot = telebot.TeleBot(API)


    @bot.message_handler(commands=['start'])
    def hello(message):
        uid = message.chat.id
        global USERS
        if USERS.get(uid):
            USERS.pop(uid)
        helpers.delete_user(uid)

        helpers.send_message(bot, uid, f"Hello, @{message.chat.username}!")
        time.sleep(1)
        text = f"Use {COMMAND_ADD} command. I will check your web feed from time to time " \
                "and notify when something new comes up~"
        helpers.send_message(bot, uid, text)


    @bot.message_handler(commands=['help'])
    def help(message):
        if USERS.get(uid):
            add_rss(message)
        helpers.send_message(bot, message.chat.id, HELP)


    @bot.message_handler(commands=[KEY_ADD_NEW_FEED, KEY_INSERT_INTO_DB, KEY_CANCEL])
    def add_rss(message, check_out=False):
        uid = message.chat.id
        global USERS
        USERS.setdefault(uid, {AWAITING_RSS: False, POTENTIAL_RSS: None})

        if not USERS[uid][AWAITING_RSS] and message.text == COMMAND_ADD:
            text = "Send me a URI of your web feed. I'll check it out."
            USERS[uid][AWAITING_RSS] = True

        elif message.text == COMMAND_CANCEL:
            text = "Cancelled~"
            USERS.pop(uid)

        elif check_out:
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

        elif USERS[uid][AWAITING_RSS] and USERS[uid][POTENTIAL_RSS] and message.text == COMMAND_INSERT:
            helpers.add_new_rss(USERS[uid][POTENTIAL_RSS], uid)
            text = "New web feed added!"
            USERS.pop(uid)

        elif message.text == COMMAND_INSERT:
            text = f"Use {COMMAND_ADD} command."

        else:
            text = f"You can use {COMMAND_CANCEL} to go back."

        helpers.send_message(bot, uid, text)


    @bot.message_handler(commands=[KEY_SHOW_USER_FEEDS, KEY_DELETE_FROM_DB])
    def list_rss(message):
        uid = message.chat.id
        global USERS

        if USERS.get(uid):
            add_rss(message)

        elif message.text == COMMAND_LIST:
            text = helpers.list_rss(uid)
            if not text:
                text = "There is none!"

        elif message.text == COMMAND_DELETE:
            text = f"To delete an entry from your list of feeds use: {COMMAND_DELETE} [feed]"

        elif DELETE_PATTERN.fullmatch(message.text.strip()):
            feed = DELETE_PATTERN.findall( message.text.strip() )[0][1]
            if helpers.delete_rss(feed, uid):
                text = "Done."
            else:
                text = "No such web feed found. Check for errors."

        else:
            help(message)

        helpers.send_message(bot, uid, text)


    @bot.message_handler(content_types=['text'])
    def get_text_data(message):
        uid = message.chat.id
        global USERS
        if USERS.get(uid) and USERS[uid][AWAITING_RSS]:
            add_rss(message, check_out=True)
        else:
            help(message)


    return bot
