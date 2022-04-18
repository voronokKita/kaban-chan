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
from webhook import Webhook
from bot_receiver import ReceiverThread
from bot_updater import UpdaterThread


def signal_handler(signal, frame):
    print()
    print(NEW_MASSAGES)
    EXIT_EVENT.set()
    NEW_MASSAGES_EVENT.set()


def main():
    print("I woke up (*・ω・)ﾉ")
    time.sleep(1)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTSTP, signal_handler)

    SERVER = Webhook()
    SERVER.run()

    UPDATER = UpdaterThread()
    UPDATER.run()

    time.sleep(1.5)
    print("All work has started (´｡• ω •｡`)")

    global NEW_MASSAGES
    while True:
        if NEW_MASSAGES_EVENT.wait():
            if EXIT_EVENT.is_set():
                print("stopping a receiver")
                break

            massages = NEW_MASSAGES.copy()
            NEW_MASSAGES = []

            for massage in massages:  # TODO
                RECEIVER = ReceiverThread(massage)
                RECEIVER.start()
                RECEIVER.join()

            if not NEW_MASSAGES:
                NEW_MASSAGES_EVENT.clear()
            else:
                continue

    try:
        UPDATER.join()
        SERVER.shutdown()
    except Exception as error:
        SERVER.shutdown()
        raise error

    print("Go to sleep (´-ω-｀)…zZZ")
    sys.exit(0)


if __name__ == '__main__':
    main()
