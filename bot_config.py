from variables import *
import helpers


def get_bot():
    """ Main telebot requests processor. """
    bot = telebot.TeleBot(API)


    @bot.message_handler(commands=['start', 'restart'])
    def hello(message):
        """ Will also delete any old data in order to work as a restart function. """
        uid = message.chat.id
        global USERS
        if USERS.get(uid):
            USERS.pop(uid)
        helpers.delete_user(uid)

        helpers.send_message(bot, uid, f"Hello, @{message.chat.username}!")
        time.sleep(1)
        text = f"Use {COMMAND_ADD} command. I will check your web feed from time to time " \
                "and notify when something new comes up~\n\n" \
                "ⓘ The server may be slow so don't rush to use commands again " \
                "if there is no immediate response. (´･ᴗ･ ` )"
        helpers.send_message(bot, uid, text)


    @bot.message_handler(commands=['help'])
    def help(message):
        helpers.send_message(bot, message.chat.id, HELP)


    @bot.message_handler(commands=[KEY_ADD, KEY_INSERT, KEY_CANCEL])
    def add_new_feed(message, check_out=False):
        """ Handles the insertion of new entries into the feeds db. """
        text = ""
        uid = message.chat.id
        global USERS
        USERS.setdefault(uid, {'AWAITING_FEED': False, 'POTENTIAL_FEED': None})

        if not USERS[uid]['AWAITING_FEED'] and message.text == COMMAND_ADD:
            text = "Send me a URI of your web feed. I'll check it out."
            USERS[uid]['AWAITING_FEED'] = True

        elif message.text == COMMAND_CANCEL:
            text = "Cancelled~"
            USERS.pop(uid)

        elif check_out:
            feed = message.text.strip()
            try:
                helpers.check_out_feed(feed, uid)
            except DataAlreadyExists:
                text = "I already watch this feed for you!"
            except Exception:
                text = "Can't read the feed. Check for errors or try again later."
            else:
                text = f"All is fine — I managed to read the feed! " \
                       f"Use the {COMMAND_INSERT} command to complete."
                USERS[uid]['POTENTIAL_FEED'] = feed

        elif USERS[uid]['AWAITING_FEED'] and \
                USERS[uid]['POTENTIAL_FEED'] and \
                message.text == COMMAND_INSERT:

            feed = USERS[uid]['POTENTIAL_FEED']
            text = helpers.add_new_feed(bot, uid, feed)
            time.sleep(1)
            USERS.pop(uid)

        elif message.text == COMMAND_INSERT:
            text = f"Use {COMMAND_ADD} command first."

        else:
            text = f"You can use {COMMAND_CANCEL} to go back."

        helpers.send_message(bot, uid, text)


    @bot.message_handler(commands=[KEY_LIST, KEY_DELETE])
    def list_user_feeds(message):
        """ Sends the list of feeds associated with the id.
            Handles the deletion of feeds. """
        text = ""
        message_text = message.text.strip()
        uid = message.chat.id
        global USERS

        if USERS.get(uid):
            add_new_feed(message)

        elif message_text == COMMAND_LIST:
            text = helpers.list_user_feeds(uid)

        elif PATTERN_DELETE.fullmatch(message_text):
            feed = PATTERN_DELETE.findall(message_text)[0][1]
            text = helpers.delete_a_feed(feed, uid)

        else:
            help(message)

        if text:
            helpers.send_message(bot, uid, text)


    @bot.message_handler(commands=[KEY_SW_SUMMARY, KEY_SW_DATE, KEY_SW_LINK])
    def switch(message):
        """ Posts style options. """
        text = ""
        message_text = message.text.strip()
        uid = message.chat.id
        global USERS

        if USERS.get(uid):
            add_new_feed(message)

        elif PATTERN_SUMMARY.fullmatch(message_text) or \
                PATTERN_DATE.fullmatch(message_text) or \
                PATTERN_LINK.fullmatch(message_text):

            parts = PATTERN_COMMAND.findall(message_text)
            feed = parts[0][1]
            command = parts[0][0].strip()
            try:
                helpers.check_out_feed(feed, uid, first_time=False)
            except DataAlreadyExists:
                helpers.feed_switcher(uid, command, feed)
                text = "Done."
            else:
                text = "No such web feed found. Check for errors."

        else:
            help(message)

        if text:
            helpers.send_message(bot, uid, text)


    @bot.message_handler(content_types=['text'])
    def get_text_data(message):
        """ Process text messages. """
        uid = message.chat.id
        global USERS
        if USERS.get(uid) and USERS[uid]['AWAITING_FEED']:
            add_new_feed(message, check_out=True)
        else:
            help(message)


    return bot
