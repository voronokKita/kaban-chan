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
                if EXIT_EVENT.wait(FEEDS_UPDATE_TIMEOUT):
                    break
        except Exception as error:
                    self.exception = error
                    helpers.exit_signal()

    def _updater(self):
        """ Loads the feeds database and goes through one by one, updates last_check. """
        with SQLSession(db) as session:
            for db_entry in session.scalars( session.query(WebFeedsDB) ):
                try:
                    feed = feedparser.parse(db_entry.web_feed)
                    uid = db_entry.user_id
                    last_check = db_entry.last_check
                    top_post_date = self._check_the_feed(feed, last_check, uid)

                    if last_check < top_post_date:
                        db_entry.last_check = published
                        session.commit()
                except Exception as error:
                    log.warning(f'feedparser fail - {error}')

    def _check_the_feed(self, feed, last_check, uid):
        """ Iterates through all posts in the feed until it reaches the previously loaded one.
            Returns the publication date of the newest post. """
        for post in feed.entries:
            published = datetime.fromtimestamp(
                time.mktime(post.published_parsed)
            )
            if last_check >= published:
                break
            else:
                soup = BeautifulSoup(post.summary, features='html.parser')
                summary = soup.text[:200]
                text = f"{post.title}\n" \
                       f"{published.strftime(TIME_FORMAT)}\n\n" \
                       f"{summary.strip()}...\n\n" \
                       f"{post.link}"
                helpers.send_message(self.bot, uid, text)

        top_post_date = datetime.fromtimestamp(
            time.mktime(feed.entries[0].published_parsed)
        )
        return top_post_date

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
