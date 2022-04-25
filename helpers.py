from variables import *


def signal_handler(signal, frame):
    print()
    EXIT_EVENT.set()
    NEW_MESSAGES_EVENT.set()


def send_message(bot, uid, text):  #! TODO
    # https://core.telegram.org/api/errors
    try:
        bot.send_message(uid, text)
    except ApiTelegramException as error:
        print("AAA", error)
        print(error.description)
        print(error.error_code)
        print(error.result)
    except Exception:
        print("BBB")


def delete_user():
    pass


def check_out_rss(feed, uid):
    with SQLSession(db) as session:
        result = session.scalars(
            sql.select(WebFeedsDB)
            .where(WebFeedsDB.user_id == uid,
                    WebFeedsDB.web_feed == feed)
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
        result = sql.select(WebFeedsDB).where(WebFeedsDB.user_id == uid)
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
        result = session.scalars(
            sql.select(WebFeedsDB)
            .where(WebFeedsDB.user_id == uid,
                    WebFeedsDB.web_feed == feed)
        ).first()
        if result:
            session.delete(result)
            session.commit()
            return "Done."
        else:
            return "No such web feed found. Check for errors."
