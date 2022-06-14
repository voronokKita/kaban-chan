import telebot

from kaban.settings import *
from kaban import helpers


class ReceiverThread(threading.Thread):
    def __init__(self, bot):
        threading.Thread.__init__(self)

        self.bot = bot
        self.users_in_memory = USERS
        self.exception = None

        self.exit = helpers.exit_signal
        self.send_message = helpers.send_message

        self.new_messages = NEW_MESSAGES_EVENT
        self.exit_event = EXIT_EVENT
        self.exit_note = EXIT_NOTE

    def __str__(self): return "receiver thread"

    def run(self):
        """ Launches request's handler on new-messages-event. """
        try:
            while True:
                if self.new_messages.wait():
                    if self.exit_event.is_set():
                        self._receiver_stop()
                        break
                    else:
                        self._handler()
        except Exception as error:
            self.exception = error
            self.exit()

    def _handler(self):
        """ Loads messages from the WebhookDB and
            passes them to the telebot processor. """
        data = None
        with SQLSession() as session:
            message = session.query(WebhookDB).first()
            if message:
                data = message.data

                session.query(WebhookDB).where(WebhookDB.id == message.id).delete()
                session.commit()

                update = telebot.types.Update.de_json(data)
                self.bot.process_new_updates([update])

            # ensure that this is the last message
            if not session.query(WebhookDB).first():
                self.new_messages.clear()

    def _receiver_stop(self):
        for uid in self.users_in_memory:
            self.send_message(self.bot, uid, self.exit_note)

    def stop(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
