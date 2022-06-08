#!/usr/bin/env python3
"""
v1 April 2022
v2 May

Thanks to
    https://habr.com/ru/post/350648/
    https://habr.com/ru/post/495036/
    https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/webhook_examples/webhook_flask_echo_bot.py
    https://stackoverflow.com/a/45017691
    https://stackoverflow.com/a/70345496
    https://github.com/TelegramBotAPI/errors
    https://stackoverflow.com/a/54800683
    https://github.com/eternnoir/pyTelegramBotAPI/issues/139
"""
import signal
import sys
import time

from kaban import helpers
from kaban import bot_config
from kaban import flask_config
from kaban.settings import *
from kaban.webhook import WebhookThread
from kaban.updater import UpdaterThread
from kaban.receiver import ReceiverThread


def main():
    print("I woke up (*・ω・)ﾉ")
    time.sleep(0.2)

    try:
        server = WebhookThread(flask_config.get_app())
        receiver = ReceiverThread(bot_config.get_bot())
        updater = UpdaterThread(bot_config.get_bot())
    except Exception as exc:
        log.exception(exc)
        print("failed to load telebot & flask.")
        sys.exit(1)

    print("starting a webhook")
    server.start()
    if HOOK_READY_TO_WORK.wait(20):
        time.sleep(0.5)

        print("starting a receiver")
        receiver.start()
        time.sleep(0.5)

        print("starting an updater")
        updater.start()
        time.sleep(1)

        info(">>> up & running >>>")
        print("All work has started (´｡• ω •｡`)")
    else:
        print("fail to start the webhook.")
        sys.exit(2)

    if EXIT_EVENT.wait():
        print("shutting down")
        server.shutdown()

    errors = False
    for thread in [server, receiver, updater]:
        try:
            thread.stop()
            print(f"{thread} stopped")
        except Exception as exc:
            log.exception(exc)
            print(f"error in {thread}")
            errors = True

    print("Go to sleep (´-ω-｀)…zZZ")
    info("---   stopping   ---\n")
    sys.exit(3) if errors else sys.exit(0)


if __name__ == '__main__':
    if __debug__ and not REPLIT:
        from tests import testsuite
        testsuite.execute()
        exit()

    signal.signal(signal.SIGINT, helpers.exit_signal)
    signal.signal(signal.SIGTSTP, helpers.exit_signal)
    main()
