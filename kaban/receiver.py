from variables import *
import helpers


class ReceiverThread(threading.Thread):
    def __init__(self, bot):
        threading.Thread.__init__(self)
        self.bot = bot
        self.exception = None

    def __repr__(self):
        return "receiver thread"

    def run(self):
        """ Launches request's handler if event. """
        try:
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
        """ Loads messages from the WebhookDB and passes them to a telebot processor. """
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
            helpers.send_message(self.bot, uid, EXIT_NOTE)

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
