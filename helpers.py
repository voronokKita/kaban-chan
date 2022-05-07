from variables import *


def exit_signal(signal=None, frame=None):
    """ Gentle exiting. """
    if signal:
        print()
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
                if resend_message(retry, sleep=5, delete=True):
                    continue
                log.warning('user/chat not found == uid deleted')

            elif BOT_BLOCKED.search(error.description):
                retry = 3 if retry is None else retry - 1
                if resend_message(retry, sleep=10, delete=True):
                    continue
                log.warning('bot blocked == uid deleted')

            elif BOT_TIMEOUT.search(error.description):
                retry = 1 if retry is None else retry - 1
                if resend_message(retry, sleep=10):
                    continue
                log.warning('telgram timeout')

            else:
                retry = 3 if retry is None else retry - 1
                if resend_message(retry, sleep=2):
                    continue
                log.exception('undefined telegram problem')

        except Exception as error:
            retry = 1 if retry is None else retry - 1
            if resend_message(retry, sleep=5):
                continue
            log.exception('request')

        time.sleep(0.1)
        break


def send_a_post(bot, uid, post, published,
                summary=True, date=True, link=True, rss=None):
    """ Sends a post from some feed to a uid. """
    text = f"{post.title}"
    if summary:
        try:
            soup = BeautifulSoup(post.summary, features='html.parser')
            s = soup.text[:300].strip()
            s += "..." if len(soup.text) > 300 else ""
            text += f"\n\n{s}"
        except Exception:
            feed_switcher(uid, COMMAND_SW_SUMMARY, rss)

    if date:
        text += f"\n\n{published.strftime(TIME_FORMAT)}"

    if link:
        try:
            text += f"\n{post.link}"
        except Exception:
            feed_switcher(uid, COMMAND_SW_LINK, rss)

    send_message(bot, uid, text)


def new_feed_preprocess(bot, uid, rss):
    """ Sends the top post from a newly added feed to the uid. """
    feed = feedparser.parse(rss)
    top_post = feed.entries[0]
    published = datetime.fromtimestamp(
        time.mktime(top_post.published_parsed)
    )
    send_a_post(bot, uid, top_post, published, rss=rss)

    with SQLSession(db) as session:
        db_entry = session.query(FeedsDB).filter(
            FeedsDB.uid == uid,
            FeedsDB.feed == rss,
        ).first()
        title = hashlib.md5(
            top_post.title.strip().encode()
        ).hexdigest()
        db_entry.top_posts = title
        session.commit()


def check_out_rss(feed, uid):
    """ Raises an exception if this uid has already added this feed. """
    with SQLSession(db) as session:
        result = session.query(FeedsDB).filter(
            FeedsDB.uid == uid, FeedsDB.feed == feed
        ).first()
        if result:
            raise DataAlreadyExists


def add_new_rss(feed, uid):
    """ Inserts a new entry into the feeds db. """
    with SQLSession(db) as session:
        new_entry = FeedsDB(uid=uid, feed=feed)
        session.add(new_entry)
        session.commit()
    info('db - a new entry')


def delete_rss(feed, uid):
    """ Delete some entry from the feeds db. """
    with SQLSession(db) as session:
        result = session.query(FeedsDB).filter(
            FeedsDB.uid == uid, FeedsDB.feed == feed
        ).first()
        if result:
            session.delete(result)
            session.commit()
            info('db - entry removed')
            return True
        else:
            return False


def list_rss(uid):
    """ Loads & returns list of feeds associated with some id. """
    list_of_feeds = ""
    with SQLSession(db) as session:
        result = session.query(FeedsDB).filter(FeedsDB.uid == uid)
        for i, entry in enumerate( session.scalars(result), 1 ):
            list_of_feeds += f"{i}. {entry.feed}\n"
            s = "\tsummary: on, " if entry.summary else "\tsummary: off, "
            s += "date: on, " if entry.date else "date: off, "
            s += "link: on" if entry.link else "link: off"
            list_of_feeds += s + "\n\n"

    return list_of_feeds


def feed_switcher(uid, command, rss):
    """ Changes post style. """
    with SQLSession(db) as session:
        db_entry = session.query(FeedsDB).filter(
            FeedsDB.uid == uid,
            FeedsDB.feed == rss,
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
            delete_rss(entry.feed, uid)
