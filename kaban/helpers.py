from datetime import datetime
import hashlib
import time

import feedparser
from bs4 import BeautifulSoup
from telebot.apihelper import ApiTelegramException

from kaban.settings import *


def exit_signal(signal_=None, frame=None):
    """ Gentle exiting. """
    if signal_: print()
    EXIT_EVENT.set()
    NEW_MESSAGES_EVENT.set()


def send_message(bot, uid: int, text: str):
    """ Final point. Handles errors in requests to Telegram. """
    retry = None
    while True:
        try:
            bot.send_message(uid, text)

        except ApiTelegramException as error:
            if WRONG_TOKEN.search(error.description):
                log.critical(f'wrong telegram token - {error}')
                exit_signal()

            elif UID_NOT_FOUND.search(error.description):
                retry = 1 if retry is None else retry - 1
                if resend_message(retry, sleep=5, delete_uid=uid): continue
                else: log.warning('user/chat not found; uid deleted')

            elif BOT_BLOCKED.search(error.description):
                retry = 3 if retry is None else retry - 1
                if resend_message(retry, sleep=10, delete_uid=uid): continue
                else: log.warning('bot blocked; uid deleted')

            elif BOT_TIMEOUT.search(error.description):
                retry = 1 if retry is None else retry - 1
                if resend_message(retry, sleep=10): continue
                else: log.warning('telegram timeout')

            else:
                retry = 3 if retry is None else retry - 1
                if resend_message(retry, sleep=2): continue
                else: log.exception('undefined telegram problem')

        except Exception as exc:
            retry = 1 if retry is None else retry - 1
            if resend_message(retry, sleep=5): continue
            else: log.exception(exc)

        time.sleep(0.1)
        break


def resend_message(attempt: int, sleep: int, delete_uid=None) -> bool:
    """ Will try to send message again [attempt] times after [sleep].
        Request to delete user if needed. """
    if attempt == 0:
        if delete_uid: delete_user(delete_uid)
        else: pass
        return False
    else:
        time.sleep(sleep)
        return True


def send_a_post(bot, post: Feed, db_entry, feed: str):
    """ Makes a post from some feed and sends it to a uid. """
    text = ""
    if db_entry.short:
        text += f"{db_entry.short}: "

    text += post.title + "\n"

    if db_entry.summary:
        try:
            summary_text = BeautifulSoup(post.summary, features='html.parser').text.strip()
            if not summary_text: raise AttributeError
        except (AttributeError, TypeError):
            feed_switcher(db_entry.uid, CMD_SUMMARY, feed)
        else:
            s = summary_text[:FEED_SUMMARY_LEN]
            s += "..." if len(summary_text) > FEED_SUMMARY_LEN else ""
            text += "\n" + s + "\n"

    if db_entry.date:
        published = datetime.fromtimestamp(
            time.mktime(post.published_parsed)
        ).strftime(TIME_FORMAT)
        text += "\n" + published + "\n"

    if db_entry.link:
        try:
            if not post.link: raise TypeError
        except (AttributeError, TypeError):
            feed_switcher(db_entry.uid, CMD_LINK, feed)
        else:
            text += post.link + "\n"

    send_message(bot, db_entry.uid, text)


def check_out_feed(feed: str, uid: int, first_time=True):
    """ Raises an exception if this user has already added this feed.
        Checks feed's availability and format correctness. """
    if first_time:
        try:
            parsed_feed = feedparser.parse(feed)
            post = parsed_feed.entries[0]
            if not parsed_feed.href or not post.published_parsed or not post.title:
                raise FeedFormatError
        except (AttributeError, IndexError, FeedFormatError):
            raise FeedFormatError
        except Exception as exc:
            raise Exception from exc

    with SQLSession() as session:
        db_entry = session.query(FeedsDB).filter(
            FeedsDB.uid == uid, FeedsDB.feed == feed
        ).first()
        if db_entry:
            raise DataAlreadyExists


def add_new_feed(bot, uid: int, feed: str) -> str:
    """ Inserts a new entry into the FeedsDB. """
    with SQLSession() as session:
        new_entry = FeedsDB(uid=uid, feed=feed)
        session.add(new_entry)
        session.commit()
        info('db - a new entry')
    try:
        new_feed_preprocess(bot, uid, feed)
    except FeedPreprocessError:
        return "A new web feed has been added, but some issues have arisen with reading it. " \
               "The feed will be automatically deleted if problems continue."
    else:
        return "New web feed added!"


def new_feed_preprocess(bot, uid: int, feed: str):
    """ Sends the top post from a newly added feed to the uid.
        Save changes to the database. """
    try:
        with SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == uid,
                FeedsDB.feed == feed,
            ).first()

            top_post = feedparser.parse(feed).entries[0]
            send_a_post(bot, top_post, db_entry, feed)

            title = hashlib.md5(
                top_post.title.strip().encode()
            ).hexdigest()
            top_post_date = datetime.fromtimestamp(
                time.mktime(top_post.published_parsed)
            )
            db_entry.last_posts = title
            db_entry.last_check = top_post_date
            session.commit()
    except Exception:
        log.exception("a new feed preprocess failed")
        raise FeedPreprocessError


def delete_a_feed(feed: str, uid: int, silent=False) -> str:
    """ Delete some entry from the feeds db. """
    with SQLSession() as session:
        db_entry = session.query(FeedsDB).filter(
            FeedsDB.uid == uid, FeedsDB.feed == feed
        ).first()
        if db_entry:
            session.delete(db_entry)
            session.commit()
            info('db - entry removed')
            text = "Done."
        else:
            text = "No such web feed found. Check for errors."

    if silent is False:
        return text


def list_user_feeds(uid: int) -> str:
    """ Loads & returns list of feeds associated with some uid. """
    list_of_feeds = ""
    with SQLSession() as session:
        feeds = session.query(FeedsDB).filter(FeedsDB.uid == uid)
        for i, entry in enumerate(session.scalars(feeds), 1):

            short = f"{entry.short}: " if entry.short else ""
            s = "on" if entry.summary else "off"
            d = "on" if entry.date else "off"
            l = "on" if entry.link else "off"

            list_of_feeds += f"{i}. {short}{entry.feed}\n"
            list_of_feeds += f"\tsummary: {s}, date: {d}, link: {l}\n\n"

    return list_of_feeds if list_of_feeds else "There is none!"


def feed_shortcut(uid: int, shortcut: str, feed: str) -> str:
    """ Assign shortcut to a feed. """
    if len(shortcut) > SHORTCUT_LEN:
        raise IndexError
    else:
        shortcut = None if len(shortcut) == 0 else shortcut

    with SQLSession() as session:
        db_entry = session.query(FeedsDB).filter(
            FeedsDB.uid == uid,
            FeedsDB.feed == feed,
        ).first()
        db_entry.short = shortcut
        session.commit()

    return "Done."


def feed_switcher(uid: int, command: Command, feed: str):
    """ Changes post style. """
    with SQLSession() as session:
        db_entry = session.query(FeedsDB).filter(
            FeedsDB.uid == uid,
            FeedsDB.feed == feed,
        ).first()
        if command == CMD_SUMMARY:
            db_entry.summary = not db_entry.summary
        elif command == CMD_DATE:
            db_entry.date = not db_entry.date
        elif command == CMD_LINK:
            db_entry.link = not db_entry.link
        session.commit()


def delete_user(uid: int):
    """ Takes all the feeds associated with some id and requests deletion. """
    with SQLSession() as session:
        result = session.query(FeedsDB).filter(FeedsDB.uid == uid)
        for entry in session.scalars(result):
            delete_a_feed(entry.feed, uid, silent=True)
