import logging

import telebot

from kaban.settings import BASE_DIR, Path, Logger


LOG: Path = BASE_DIR / "resources" / "feedback.log"
LOG_FORMAT = '- %(asctime)s %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M'

werkzeug_log: Logger = logging.getLogger('werkzeug')
werkzeug_log.setLevel('ERROR')
werkzeug_log_handler = logging.FileHandler(filename=LOG, encoding='utf8')
werkzeug_log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFORMAT)
werkzeug_log_handler.setFormatter(werkzeug_log_formatter)
werkzeug_log.addHandler(werkzeug_log_handler)

telebot_log: Logger = telebot.logger
telebot_log.setLevel('ERROR')
telebot_log_handler = logging.FileHandler(filename=LOG, encoding='utf8')
telebot_log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFORMAT)
telebot_log_handler.setFormatter(telebot_log_formatter)
telebot_log.addHandler(telebot_log_handler)

log: Logger = telebot.logging.getLogger(__name__)
log.setLevel('WARNING')
log_handler = logging.FileHandler(filename=LOG, encoding='utf8')
log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFORMAT)
log_handler.setFormatter(log_formatter)
log.addHandler(log_handler)

def info(s):
    log.setLevel('INFO')
    log.info(s)
    log.setLevel('WARNING')

def debug(s):
    log.setLevel('DEBUG')
    log.debug(s)
    log.setLevel('WARNING')
