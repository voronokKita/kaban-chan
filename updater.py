from variables import *
import helpers


class UpdaterThread(threading.Thread):
    def __init__(self, bot):
        threading.Thread.__init__(self)
        self.bot = bot
        self.exception = None

    def __repr__(self):
        return "updater thread"

    def run(self):
        """ Checks feeds for updates from time to time. """
        try:
            self._notifications()
            while True:
                self._updater()
                if EXIT_EVENT.wait(FEEDS_UPDATE_TIMEOUT): break
        except Exception as error:
            self.exception = error
            helpers.exit_signal()

    def _notifications(self):
        """ Sends messages to users from a file. """
        messages = []
        if NOTIFICATIONS.exists():
            with open(NOTIFICATIONS, 'r', encoding='utf-8') as file:
                text = file.read()
                messages = [m.strip() for m in text.split('>>>') if m.strip()]

        if messages:
            with SQLSession(db) as session:
                query = session.query(FeedsDB.uid).distinct()
                for uid in session.scalars(query):
                    for m in messages:
                        helpers.send_message(self.bot, uid, m)

            with open(NOTIFICATIONS, 'w') as f: f.write('')
            info("notifications sent out")

    def _updater(self):
        """ Loads the feeds db and goes through one by one.
            Updates FeedsDB last_posts & last_check. """
        with SQLSession(db) as session:
            for db_entry in session.scalars(session.query(FeedsDB)):
                try:
                    feed = feedparser.parse(db_entry.feed)
                    if not feed.entries or not feed.entries[0].title:
                        raise FeedLoadError(feed)

                    new_posts, top_post_date = self._check_the_feed(feed, db_entry)

                    if new_posts:
                        db_entry.last_posts = new_posts
                        db_entry.last_check = top_post_date
                        session.commit()

                except FeedLoadError as error:
                    text = f"Failed to load {db_entry.feed} — not accessible. " \
                           f"Technical details: \n{error}"
                    helpers.send_message(self.bot, db_entry.uid, text)
                    log.warning(f'failed to load feed - {feed}')

                except Exception as error:
                    log.warning(f'feedparser fail - {error}')

    def _check_the_feed(self, feed, db_entry):
        """ Process posts of a feed. Returns titles of last posts and the top post's date.
        Note:
        A web feed doesn't guarantee a strict sequence and order.
        Many of them update a post's publication date each time they update the post's text,
        causing all posts to reorder unpredictably.
        I tried to solve this problem by memorysing titles of N posts in md5.
        """
        old_posts = db_entry.last_posts.split(' /// ')
        old_set = set(old_posts)
        posts_to_send = []
        for post in feed.entries:
            published = datetime.fromtimestamp(
                time.mktime(post.published_parsed)
            )
            if published <= db_entry.last_check:
                break
            else:
                title = hashlib.md5(
                    post.title.strip().encode()
                ).hexdigest()

                if title in old_set: continue
                else: posts_to_send.append({'title': title, 'post': post})

        if posts_to_send:
            for post in posts_to_send[::-1]:
                helpers.send_a_post(self.bot, post['post'], db_entry, feed.href)

            l = [post['title'] for post in posts_to_send] + old_posts
            new_posts = ' /// '.join(l[:POSTS_TO_STORE])

            top_post_date = datetime.fromtimestamp(
                time.mktime(posts_to_send[0]['post'].published_parsed)
            )
        else:
            new_posts = None
            top_post_date = None

        return new_posts, top_post_date

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
