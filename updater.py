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
            if UPDATER_BACKUP.exists():
                self._unexpected_shutdown()
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

    @staticmethod
    def _unexpected_shutdown():
        feeds = defaultdict(list)
        with open(UPDATER_BACKUP, 'r') as f:
            for row in csv.DictReader(f):
                id_ = int(row['id'])
                feeds[id_].append(row['title'])

        with SQLSession(db) as session:
            for id_ in feeds:
                db_entry = session.query(FeedsDB).filter(FeedsDB.id == id_).first()
                old_posts = db_entry.last_posts.split(' /// ')
                l = feeds[id_][::-1] + old_posts
                new_posts = ' /// '.join(l[:POSTS_TO_STORE])
                db_entry.last_posts = new_posts
                session.commit()

        UPDATER_BACKUP.unlink()

    def _updater(self):
        """ Loads the feeds db and goes through one by one.
            Updates FeedsDB last_posts & last_check. """
        with SQLSession(db) as session:
            for db_entry in session.scalars(session.query(FeedsDB)):
                try:
                    feed = feedparser.parse(db_entry.feed)
                    if not feed.entries or not feed.entries[0].title:
                        raise FeedLoadError(feed)

                    new_posts = self._check_the_feed(feed, db_entry)

                    if new_posts:
                        top_post_date = datetime.fromtimestamp(
                            time.mktime(feed.entries[0].published_parsed)
                        )
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
        I tried to solve this problem by memorizing titles of N posts in md5.
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

        if not posts_to_send: new_posts = None
        else:
            with open(UPDATER_BACKUP, 'a+') as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'title'])
                writer.writeheader()
                for post in posts_to_send[::-1]:
                    helpers.send_a_post(self.bot, post['post'], db_entry, feed.href)
                    writer.writerow({'id': db_entry.id, 'title': post['title']})

        l = [post['title'] for post in posts_to_send] + old_posts
        new_posts = ' /// '.join(l[:POSTS_TO_STORE])

        return new_posts

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
