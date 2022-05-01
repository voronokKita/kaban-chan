from variables import *
import helpers


class UpdaterThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.bot = None
        self.exception = None

    def __repr__(self):
        return "updater thread"

    def run(self):
        """ Checks feeds for updates from time to time. """
        try:
            self.bot = telebot.TeleBot(API)
            while True:
                self._updater()
                if EXIT_EVENT.wait(FEEDS_UPDATE_TIMEOUT): break
        except Exception as error:
            self.exception = error
            helpers.exit_signal()

    def _updater(self):
        """ Loads the feeds db and goes through one by one, updates FeedsDB.last_check. """
        with SQLSession(db) as session:
            for db_entry in session.scalars( session.query(FeedsDB) ):
                try:
                    feed = feedparser.parse(db_entry.feed)
                    if not feed.entries:
                        raise FeedLoadError(feed)
                    uid = db_entry.uid
                    last_check = db_entry.last_check
                    style_args = (db_entry.summary, db_entry.date, db_entry.link)

                    top_post_date = self._check_the_feed(feed, last_check, uid, style_args)

                    if last_check < top_post_date:
                        db_entry.last_check = top_post_date
                        session.commit()

                except FeedLoadError as feed:
                    text = f"Failed to load {db_entry.feed} — not accessible. " \
                           f"Technical details: \n{feed}"
                    helpers.send_message(self.bot, db_entry.uid, text)
                    log.warning(f'failed to load feed - {feed}')

                except Exception as error:
                    log.warning(f'feedparser fail - {error}')

    def _check_the_feed(self, feed, last_check, uid, style_args):
        """ Iterates through all posts in a feed until it reaches the previously loaded one.
            Returns the publication date of the newest post. """
        for post in feed.entries:
            published = datetime.fromtimestamp(
                time.mktime(post.published_parsed)
            )
            if last_check >= published:
                break
            else:
                helpers.send_a_post(self.bot, uid, post, published, *style_args)

        top_post_date = datetime.fromtimestamp(
            time.mktime(feed.entries[0].published_parsed)
        )
        return top_post_date


    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
