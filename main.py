# TODO read all:
    # https://core.telegram.org/bots/api#available-types
    # https://github.com/eternnoir/pyTelegramBotAPI
# TODO logging
# TODO testing
# TODO order
""" Thanks to
https://habr.com/ru/post/350648/
https://habr.com/ru/post/495036/
https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/webhook_examples/webhook_flask_echo_bot.py
https://stackoverflow.com/a/45017691
"""
from variables import *
from main_thread import MainThread
from side_thread import SideThread


def main():
    print("I woke up (*・ω・)ﾉ")
    time.sleep(1)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTSTP, signal_handler)

    SERVER = MainThread()
    SERVER.start()

    UPDATER = SideThread()
    UPDATER.start()

    time.sleep(1.5)
    print("All work has started (´｡• ω •｡`)")

    UPDATER.join()
    SERVER.shutdown()
    SERVER.join()

    print("Go to sleep (´-ω-｀)…zZZ")
    sys.exit(0)


def signal_handler(signal, frame):
    print()
    EXIT_EVENT.set()


if __name__ == '__main__':
    main()
