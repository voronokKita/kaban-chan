#!/usr/bin/env python
# TODO read all:
    # https://core.telegram.org/bots/api#available-types
    # https://github.com/eternnoir/pyTelegramBotAPI
# TODO logging
# TODO testing
# TODO order
# TODO see/edit/delete feeds
# TODO cath exceptions
""" Thanks to
https://habr.com/ru/post/350648/
https://habr.com/ru/post/495036/
https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/webhook_examples/webhook_flask_echo_bot.py
https://stackoverflow.com/a/45017691
"""
from variables import *
from bot_config import bot
from webhook import WebhookThread
from bot_receiver import receiver_stop
from bot_updater import UpdaterThread


def main():
    print("I woke up (*・ω・)ﾉ")
    time.sleep(1)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTSTP, signal_handler)

    server = WebhookThread()
    try:  # TODO
        server.start()
    except Exception as error:
        print("Failed to set a webhook!\n", "-"*20)
        raise error

    updater = UpdaterThread()
    updater.start()

    time.sleep(2)
    print("All work has started (´｡• ω •｡`)")

    try:  # TODO
        receiver_start()
    except Exception as error:
        print("Failed to set a webhook!\n", "-"*20)
        raise error

    try:  # TODO
        updater.join()
    except Exception as error:
        print("Error in updater!\n", "-"*20)
        raise error
    finally:
        server.shutdown()
        server.join()

            massages = NEW_MASSAGES.copy()
            NEW_MASSAGES = []

            for massage in massages:  # TODO
                RECEIVER = ReceiverThread(massage)
                RECEIVER.start()
                RECEIVER.join()

def signal_handler(signal, frame):
    print()
    EXIT_EVENT.set()
    NEW_MESSAGES_EVENT.set()


if __name__ == '__main__':
    main()
