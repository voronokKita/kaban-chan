#!/usr/bin/env python
# TODO read all:
    # https://core.telegram.org/bots/api#available-types
    # https://github.com/eternnoir/pyTelegramBotAPI
# TODO logging
# TODO testing
# TODO bot blocked
""" Thanks to
https://habr.com/ru/post/350648/
https://habr.com/ru/post/495036/
https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/webhook_examples/webhook_flask_echo_bot.py
https://stackoverflow.com/a/45017691
https://stackoverflow.com/a/70345496
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
    if READY_TO_WORK.wait():
        receiver.start()
        updater.start()
        print("All work has started (´｡• ω •｡`)")

    if EXIT_EVENT.wait():
        server.shutdown()

    errors = []
    for thread in [server, receiver, updater]:
        try:
            thread.join()
        except Exception as error:
            errors.append(error)

    print("Go to sleep (´-ω-｀)…zZZ")
    if errors:
        print("-"*20)
        raise errors[0]
    else:
        sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, helpers.signal_handler)
    signal.signal(signal.SIGTSTP, helpers.signal_handler)
    if not DB_URI.exists():
        SQLAlchemyBase.metadata.create_all(db)
    main()
