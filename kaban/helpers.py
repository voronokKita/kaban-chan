from kaban.settings import *


def exit_signal(signal=None, frame=None):
    """ Gentle exiting. """
    if signal: print()
    EXIT_EVENT.set()
    NEW_MESSAGES_EVENT.set()


def send_message(bot, uid, text):
    """ Handles errors in requests to Telegram. """
    def resend_message(retry, sleep, delete=False):
        if retry == 0:
            if delete: delete_user(args[1])
            else: pass
            return False
        else:
            time.sleep(sleep)
            return True

    while True:
        retry = None
        try:
            bot.send_message(uid, text)

        except ApiTelegramException as error:
            if WRONG_TOKEN.search(error.description):
                log.critical(f'wrong telegram token - {error}')
                exit_signal()

            elif UID_NOT_FOUND.search(error.description):
                retry = 1 if retry is None else retry - 1
                if resend_message(retry, sleep=5, delete=True): continue
                else: log.warning('user/chat not found; uid deleted')

            elif BOT_BLOCKED.search(error.description):
                retry = 3 if retry is None else retry - 1
                if resend_message(retry, sleep=10, delete=True): continue
                else: log.warning('bot blocked; uid deleted')

            elif BOT_TIMEOUT.search(error.description):
                retry = 1 if retry is None else retry - 1
                if resend_message(retry, sleep=10): continue
                else: log.warning('telegram timeout')

            else:
                retry = 3 if retry is None else retry - 1
                if resend_message(retry, sleep=2): continue
                else: log.exception('undefined telegram problem')

        except Exception as error:
            retry = 1 if retry is None else retry - 1
            if resend_message(retry, sleep=5): continue
            else: log.exception('request')

        time.sleep(0.1)
        break


def send_a_post(bot, post:Feed, db_entry, feed:str):
    """ Makes a post from some feed and sends it to a uid. """
    text = ""
    if db_entry.short: text += f"{db_entry.short}: "

    text += post.title + "\n"

    if db_entry.summary:
        try:
            soup = BeautifulSoup(post.summary, features='html.parser')
            s = soup.text[:SUMMARY].strip()
            s += "..." if len(soup.text) > SUMMARY else ""
            text += "\n" + s + "\n"
        except Exception:
            feed_switcher(db_entry.uid, COMMAND_SW_SUMMARY, feed)

    if db_entry.date:
        published = datetime.fromtimestamp(
            time.mktime(post.published_parsed)
        ).strftime(TIME_FORMAT)
        text += "\n" + published + "\n"

    if db_entry.link:
        try:
            text += post.link + "\n"
        except Exception:
            feed_switcher(db_entry.uid, COMMAND_SW_LINK, feed)

    send_message(bot, db_entry.uid, text)


def check_out_feed(feed, uid, first_time=True):
    """ Raises an exception if this uid has already added this feed. """
    if first_time:
        try:
            f = feedparser.parse(feed)
            p = f.entries[0]
            if not f.href or not p.published_parsed or not p.title:
                raise Exception
        except Exception:
            raise Exception

    with SQLSession(db) as session:
        db_entry = session.query(FeedsDB).filter(
            FeedsDB.uid == uid, FeedsDB.feed == feed
        ).first()
        if db_entry:
            raise DataAlreadyExists


def add_new_feed(bot, uid:int, feed:str) -> str:
    """ Inserts a new entry into the feeds db. """
    with SQLSession(db) as session:
        new_entry = FeedsDB(uid=uid, feed=feed)
        session.add(new_entry)
        session.commit()
    info('db - a new entry')
    try:
        new_feed_preprocess(bot, uid, feed)
    except Exception:
        return "A new web feed has been added, but some issues have arisen with reading it. " \
               "The feed will be automatically deleted if problems continue."
    else:
        return "New web feed added!"


def new_feed_preprocess(bot, uid, feed):
    """ Sends the top post from a newly added feed to the uid. """
    try:
        with SQLSession(db) as session:
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
    except Exception as error:
        log.exception("a new feed preprocess failed")
        raise error


def delete_a_feed(feed, uid, silent=False):
    """ Delete some entry from the feeds db. """
    with SQLSession(db) as session:
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


def list_user_feeds(uid):
    """ Loads & returns list of feeds associated with some id. """
    list_of_feeds = ""
    with SQLSession(db) as session:
        feeds = session.query(FeedsDB).filter(FeedsDB.uid == uid)
        for i, entry in enumerate(session.scalars(feeds), 1):

            short = f"{entry.short}: " if entry.short else ""
            s = "on" if entry.summary else "off"
            d = "on" if entry.date else "off"
            l = "on" if entry.link else "off"

            list_of_feeds += f"{i}. {short}{entry.feed}\n"
            list_of_feeds += f"\tsummary: {s}, date: {d}, link: {l}\n\n"

    return list_of_feeds if list_of_feeds else "There is none!"


def feed_shortcut(uid, shortcut, feed):
    """ Assign shortcut to a feed. """
    shortcut = None if len(shortcut) == 0 else shortcut
    try:
        with SQLSession(db) as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == uid,
                FeedsDB.feed == feed,
            ).first()
            db_entry.short = shortcut
            session.commit()
    except Exception:
        log.exception('def feed_shortcut')
        return "Undefined error."
    else:
        return "Done."


def feed_switcher(uid, command, feed):
    """ Changes post style. """
    with SQLSession(db) as session:
        db_entry = session.query(FeedsDB).filter(
            FeedsDB.uid == uid,
            FeedsDB.feed == feed,
        ).first()
        if command == COMMAND_SW_SUMMARY:
            db_entry.summary = not db_entry.summary
        elif command == COMMAND_SW_DATE:
            db_entry.date = not db_entry.date
        elif command == COMMAND_SW_LINK:
            db_entry.link = not db_entry.link
        session.commit()


def delete_user(uid):
    """ Takes all the feeds associated with some id and requests deletion. """
    with SQLSession(db) as session:
        result = session.query(FeedsDB).filter(FeedsDB.uid == uid)
        for entry in session.scalars(result):
            delete_a_feed(entry.feed, uid, silent=True)


def sum(arg):
    total = 0
    for val in arg: total += val
    return total
