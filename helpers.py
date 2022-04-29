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
            if delete:
                delete_user(args[1])
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


def delete_user(uid):
    """ Takes all the feeds associated with some id and requests deletion. """
    with SQLSession(db) as session:
        result = session.query(WebFeedsDB).filter(WebFeedsDB.user_id == uid)
        for entry in session.scalars(result):
            delete_rss(entry.web_feed, uid)


def check_out_rss(feed, uid):
    """ Raises an error if this id has already added this feed. """
    with SQLSession(db) as session:
        result = session.query(WebFeedsDB).filter(
            WebFeedsDB.user_id == uid, WebFeedsDB.web_feed == feed
        ).first()
        if result:
            raise DataAlreadyExistsError()


def add_new_rss(feed, uid):
    """ Inserts a new entry into the feeds db. """
    with SQLSession(db) as session:
        new_entry = WebFeedsDB(user_id=uid, web_feed=feed)
        session.add(new_entry)
        session.commit()
    info('db - a new entry')


def list_rss(uid):
    """ Loads & returns list of feeds associated with some id. """
    list_of_feeds = ""
    with SQLSession(db) as session:
        result = session.query(WebFeedsDB).filter(WebFeedsDB.user_id == uid)
        for i, entry in enumerate( session.scalars(result), 1 ):
            list_of_feeds += f"{i}. {entry.web_feed}\n"
            date = entry.last_check.strftime(TIME_FORMAT)
            list_of_feeds += f"\tlast update: {date}\n\n"

    if not list_of_feeds:
        return ""
    else:
        list_of_feeds += f"To delete an entry use: {COMMAND_DELETE} [feed]"
        return list_of_feeds


def delete_rss(feed, uid):
    """ Delete some entry from the feeds db. """
    with SQLSession(db) as session:
        result = session.query(WebFeedsDB).filter(
            WebFeedsDB.user_id == uid, WebFeedsDB.web_feed == feed
        ).first()
        if result:
            session.delete(result)
            session.commit()
            info('db - entry removed')
            return True
        else:
            return False


def send_a_post(post, published, bot, uid):
    """ Sends a post from some feed to a uid. """
    soup = BeautifulSoup(post.summary, features='html.parser')
    summary = soup.text[:300]
    text = f"{post.title}\n\n" \
           f"{summary.strip()}...\n\n" \
           f"{published.strftime(TIME_FORMAT)}\n" \
           f"{post.link}"
    send_message(bot, uid, text)


def new_feed_preprocess(bot, uid, rss):
    """ Sends the top post from a newly added feed to a uid. """
    feed = feedparser.parse(rss)
    top_post = feed.entries[0]
    published = datetime.fromtimestamp(
        time.mktime(top_post.published_parsed)
    )
    send_a_post(top_post, published, bot, uid)

    with SQLSession(db) as session:
        db_entry = session.query(WebFeedsDB).filter(
            WebFeedsDB.user_id == uid,
            WebFeedsDB.web_feed == rss,
        ).first()
        db_entry.last_check = published
        session.commit()
