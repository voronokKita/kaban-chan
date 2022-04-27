from variables import *


def exit_signal(signal=None, frame=None):
    if signal:
        print()
    EXIT_EVENT.set()
    NEW_MESSAGES_EVENT.set()


def send_message(bot, uid, text):

    def resend_message(retry, sleep, delete=False, error=None):
        if retry == 0:
            if delete:
                delete_user(args[1])
            elif error:
                print(error)
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
                print("ERROR from telegram: ", error)
                exit_signal()

            elif UID_NOT_FOUND.search(error.description):
                retry = 1 if retry is None else retry - 1
                if resend_message(retry, sleep=5, delete=True):
                    continue

            elif BOT_BLOCKED.search(error.description):
                retry = 3 if retry is None else retry - 1
                if resend_message(retry, sleep=10, delete=True):
                    print("try")
                    continue

            elif BOT_TIMEOUT.search(error.description):
                retry = 1 if retry is None else retry - 1
                if resend_message(retry, sleep=10):
                    continue

            else:
                retry = 3 if retry is None else retry - 1
                if resend_message(retry, sleep=2):
                    continue

        except Exception as error:
            retry = 1 if retry is None else retry - 1
            if resend_message(retry, 5, error=f"ERROR sending request: {error}"):
                continue

        break


def delete_user(uid):
    with SQLSession(db) as session:
        result = session.query(WebFeedsDB).filter(WebFeedsDB.user_id == uid)
        for entry in session.scalars(result):
            delete_rss(entry.web_feed, uid)


def check_out_rss(feed, uid):
    with SQLSession(db) as session:
        result = session.query(WebFeedsDB).filter(
            WebFeedsDB.user_id == uid, WebFeedsDB.web_feed == feed
        ).first()
        if result:
            raise DataAlreadyExistsError()


def add_new_rss(feed, uid):
    with SQLSession(db) as session:
        new_entry = WebFeedsDB(user_id=uid, web_feed=feed)
        session.add(new_entry)
        session.commit()
    print("db: a new entry")


def list_rss(uid):
    list_of_feeds = ""
    with SQLSession(db) as session:
        result = session.query(WebFeedsDB).filter(WebFeedsDB.user_id == uid)
        for i, entry in enumerate( session.scalars(result), 1 ):
            list_of_feeds += f"{i}. {entry.web_feed}\n"
            date = entry.last_check.strftime(TIME_FORMAT)
            list_of_feeds += f"\tlast update: {date}\n\n"

    if not list_of_feeds:
        return "There is none!"
    else:
        list_of_feeds += f"To delete an entry use: {COMMAND_DELETE} [feed]"
        return list_of_feeds


def delete_rss(feed, uid):
    with SQLSession(db) as session:
        result = session.query(WebFeedsDB).filter(
            WebFeedsDB.user_id == uid, WebFeedsDB.web_feed == feed
        ).first()
        if result:
            session.delete(result)
            session.commit()
            return "Done."
        else:
            return "No such web feed found. Check for errors."
