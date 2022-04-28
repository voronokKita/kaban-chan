#!/usr/bin/env python
# TODO option to disable links
# TODO possability that a web feed is offline
# TODO load the first feed entry after adding a feed
# TODO comments
""" Thanks to
https://habr.com/ru/post/350648/
https://habr.com/ru/post/495036/
https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/webhook_examples/webhook_flask_echo_bot.py
https://stackoverflow.com/a/45017691
https://stackoverflow.com/a/70345496
https://github.com/TelegramBotAPI/errors
"""
import helpers
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

    print("starting a webhook")
    server.start()
    if READY_TO_WORK.wait(10):
        print("starting receiver & updater")
        receiver.start()
        updater.start()
        time.sleep(1)
        info(">>> up & running >>>")
        print("All work has started (´｡• ω •｡`)")

    if EXIT_EVENT.wait():
        server.shutdown()

    errors = False
    for thread in [server, receiver, updater]:
        try:
            thread.join()
            print(f"stopping a {thread}")
        except Exception as error:
            print(f"error in a {thread}")
            log.exception(thread)
            errors = True

    print("Go to sleep (´-ω-｀)…zZZ")
    info("xxx   stopping   xxx\n")
    sys.exit(1) if errors else sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, helpers.exit_signal)
    signal.signal(signal.SIGTSTP, helpers.exit_signal)
    if not DB_URI.exists():
        SQLAlchemyBase.metadata.create_all(db)
    main()
