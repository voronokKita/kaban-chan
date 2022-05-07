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
        """ Loads the feeds db and goes through one by one. """
        with SQLSession(db) as session:
            for db_entry in session.scalars( session.query(FeedsDB) ):
                try:
                    feed = feedparser.parse(db_entry.feed)
                    if not feed.entries or not feed.entries[0].title:
                        raise FeedLoadError(feed)

                    new_top_posts = self._check_the_feed(feed, db_entry)

                    if db_entry.top_posts != new_top_posts:
                        db_entry.top_posts = new_top_posts
                        session.commit()

                except FeedLoadError as error:
                    text = f"Failed to load {db_entry.feed} — not accessible. " \
                           f"Technical details: \n{error}"
                    helpers.send_message(self.bot, db_entry.uid, text)
                    log.warning(f'failed to load feed - {feed}')

                except Exception as error:
                    log.warning(f'feedparser fail - {error}')

    def _check_the_feed(self, feed, db_entry):
        """ Iterates through top posts of a feed. Sends new posts.
            Returns hashes of the posts titles. """
        top_posts = []
        for i, post in enumerate(feed.entries):
            if i == POSTS_TO_CHECK: break
            else: top_posts.append(post)

        new_top_posts = []
        old_top_posts = db_entry.top_posts.split(' /// ')
        for post in top_posts[::-1]:

            title = hashlib.md5(
                post.title.strip().encode()
            ).hexdigest()
            new_top_posts.append(title)

            if title in old_top_posts: continue
            else: helpers.send_a_post(self.bot, post, db_entry)

        return ' /// '.join(new_top_posts)

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
