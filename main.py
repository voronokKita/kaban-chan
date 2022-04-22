#!/usr/bin/env python
# TODO read all:
    # https://core.telegram.org/bots/api#available-types
    # https://github.com/eternnoir/pyTelegramBotAPI
# TODO logging
# TODO testing
# TODO see/edit/delete feeds
# TODO delete buttons?
""" Thanks to
https://habr.com/ru/post/350648/
https://habr.com/ru/post/495036/
https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/webhook_examples/webhook_flask_echo_bot.py
https://stackoverflow.com/a/45017691
"""
from variables import *
from webhook import WebhookThread
from bot_updater import UpdaterThread
from bot_receiver import ReceiverThread


def main():
    print("I woke up (*・ω・)ﾉ")
    time.sleep(0.2)

    server = WebhookThread()
    receiver = ReceiverThread()
    updater = UpdaterThread()

    server.start()
    receiver.start()
    updater.start()

    time.sleep(3)
    print("All work has started (´｡• ω •｡`)")

    if EXIT_EVENT.wait():
        NEW_MESSAGES_EVENT.set()
        server.shutdown()

    errors = []
    for thread in [server, receiver, updater]:
        try:
            thread.join()
        except Exception as error:
            errors.append(error)

    print("Go to sleep (´-ω-｀)…zZZ")
    if errors:
        raise errors[0]
    else:
        sys.exit(0)


def signal_handler(signal, frame):
    print()
    EXIT_EVENT.set()
    NEW_MESSAGES_EVENT.set()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTSTP, signal_handler)
    main()
