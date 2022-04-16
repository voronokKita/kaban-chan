# TODO read all:
    # https://core.telegram.org/bots/api#available-types
    # https://github.com/eternnoir/pyTelegramBotAPI
# TODO logging
# TODO testing
# TODO easy start
# TODO order
""" Thanks to
https://habr.com/ru/post/350648/
https://habr.com/ru/post/495036/
https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/webhook_examples/webhook_flask_echo_bot.py
"""
from variables import *
from telebot import bot
from webhook import app
from main_thread import MainThread
from side_thread import updater


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTSTP, signal_handler)

    SERVER = MainThread(app)
    SERVER.start()

    side_thread = threading.Thread(target=updater)
    side_thread.start()

    time.sleep(1)
    print("I woke up (*・ω・)ﾉ")

    side_thread.join()
    SERVER.shutdown()

    print("Go to sleep (´-ω-｀)…zZZ")
    sys.exit(0)


def signal_handler(signal, frame):
    EXIT_EVENT.set()


if __name__ == '__main__':
    main()
