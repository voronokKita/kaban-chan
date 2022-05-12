#!/usr/bin/env python
"""
v1 April of 2022
v2 May

Thanks to
    https://habr.com/ru/post/350648/
    https://habr.com/ru/post/495036/
    https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/webhook_examples/webhook_flask_echo_bot.py
    https://stackoverflow.com/a/45017691
    https://stackoverflow.com/a/70345496
    https://github.com/TelegramBotAPI/errors
    https://stackoverflow.com/a/54800683
"""
# TODO feed nickname
import helpers
import bot_config
from variables import *
from webhook import WebhookThread
from updater import UpdaterThread
from receiver import ReceiverThread


def main():
    print("I woke up (*・ω・)ﾉ")
    time.sleep(0.2)

    try:
        bot = bot_config.get_bot()
    except Exception:
        log.exception()
        print("failed to process a bot.")
        sys.exit(1)
    else:
        server = WebhookThread()
        receiver = ReceiverThread(bot)
        updater = UpdaterThread(bot)

    print("starting a webhook")
    server.start()
    if READY_TO_WORK.wait(20):
        print("starting receiver & updater")
        receiver.start()
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
            thread.join()
            print(f"{thread} stopped")
        except Exception:
            log.exception(thread)
            print(f"error in {thread}")
            errors = True

    print("Go to sleep (´-ω-｀)…zZZ")
    info("---   stopping   ---\n")
    sys.exit(3) if errors else sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, helpers.exit_signal)
    signal.signal(signal.SIGTSTP, helpers.exit_signal)
    if not DB_URI.exists():
        SQLAlchemyBase.metadata.create_all(db)
    main()
