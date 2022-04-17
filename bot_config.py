from variables import *


bot = telebot.TeleBot(API)

BUTTON_CANCEL = bot_types.KeyboardButton(f"/{KEY_CANCEL}")
BUTTON_ADD_NEW_FEED = bot_types.KeyboardButton(f"/{KEY_ADD_NEW_FEED}")
BUTTON_INSERT_INTO_DB = bot_types.KeyboardButton(f"/{KEY_INSERT_INTO_DB}")
