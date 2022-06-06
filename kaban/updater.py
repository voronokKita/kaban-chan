from kaban.settings import *
from kaban import helpers


class UpdaterThread(threading.Thread):
    """ Note:
    A web feed doesn't guarantee a strict sequence and order.
    Many of them update a post's publication date each time they update the post's text,
    causing all posts to reorder unpredictably.
    I tried to solve this problem by memorizing titles of N posts in md5.
    """
    def __init__(self, bot):
        threading.Thread.__init__(self)
        self.bot = bot
        self.exception = None

    @staticmethod
    def __repr__():
        return "updater thread"

    def run(self):
        """ Checks feeds for updates from time to time. """
        try:
            self._notifications()

            while True:
                dict_of_posts = {}
                self._load(dict_of_posts)
                if dict_of_posts:
                    self._updater(dict_of_posts)
                del dict_of_posts

                if EXIT_EVENT.wait(FEEDS_UPDATE_TIMEOUT):
                    break

        except Exception as error:
            self.exception = error
            helpers.exit_signal()

    def _notifications(self):
        """ Sends messages to users from a file.
            Messages must be separated by >>> """
        messages = []
        if NOTIFICATIONS.exists():
            with open(NOTIFICATIONS, 'r', encoding='utf-8') as file:
                text = file.read()
                messages = [m.strip() for m in text.split('>>>') if m.strip()]

        if not messages: return

        with SQLSession(db) as session:
            query = session.query(FeedsDB.uid).distinct()
            for uid in session.scalars(query):
                for m in messages:
                    helpers.send_message(self.bot, uid, m)

        with open(NOTIFICATIONS, 'w') as f: f.write('')
        info("notifications sent out")

    def _load(self, dict_of_posts):
        """ Loads the posts to be sent into memory. """
        self._populate_user_ids(dict_of_posts)
        self._populate_user_feeds(dict_of_posts)
        self._populate_feed_posts(dict_of_posts)

    @staticmethod
    def _populate_user_ids(dict_of_uids):
        """ Subfunction of _load() """
        with SQLSession(db) as session:
            for db_entry in session.scalars(session.query(FeedsDB)):
                dict_of_uids[db_entry.uid] = {}

    @staticmethod
    def _populate_user_feeds(dict_of_uids):
        """ Subfunction of _load() """
        for uid in dict_of_uids:
            dict_of_feeds = {}
            with SQLSession(db) as session:
                entries = session.query(FeedsDB).filter(FeedsDB.uid == uid)
                for db_entry in session.scalars(entries):
                    dict_of_feeds[db_entry.feed] = []
                dict_of_uids[uid] = dict_of_feeds

    def _populate_feed_posts(self, dict_of_uids):
        """ Subfunction of _load() """
        for uid in dict_of_uids:
            for feed in dict_of_uids[uid]:
                posts_to_send = []
                try:
                    parsed_feed = feedparser.parse(feed)
                    if not parsed_feed.entries or not parsed_feed.entries[0].title:
                        raise FeedLoadError(feed)

                    self._populate_list_of_posts(posts_to_send, parsed_feed, uid)

                except FeedLoadError:
                    log.warning(f'failed to load feed - {feed}')
                except Exception as error:
                    log.warning(f'feedparser fail - {error}')
                finally:
                    dict_of_uids[uid][feed] = posts_to_send

    @staticmethod
    def _populate_list_of_posts(posts_to_send, parsed_feed, uid):
        """ Subfunction of _load() """
        with SQLSession(db) as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == uid,
                FeedsDB.feed == parsed_feed.href
            ).first()

            old_posts = set(db_entry.last_posts.split(' /// '))
            feed_last_check = db_entry.last_check

        for post in parsed_feed.entries:
            published = datetime.fromtimestamp(
                time.mktime(post.published_parsed)
            )
            if published <= feed_last_check:
                break
            else:
                title = hashlib.md5(
                    post.title.strip().encode()
                ).hexdigest()

                if title in old_posts: continue
                else: posts_to_send.append({'title': title, 'post': post})

    def _updater(self, dict_of_posts):
        for uid in dict_of_posts:
            for feed in dict_of_posts[uid]:
                # The order of the posts should be reversed to keep the feed's original sequence.
                for post in reversed(dict_of_posts[uid][feed]):
                    self._sender(uid, feed, post)

    def _sender(self, uid:int, feed:str, post:dict):
        """ Subfunction of _updater() """
        with SQLSession(db) as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == uid,
                FeedsDB.feed == feed
            ).first()

            published = datetime.fromtimestamp(
                time.mktime(post['post'].published_parsed)
            )
            old_posts = db_entry.last_posts.split(' /// ')
            l = [post['title']] + old_posts
            new_posts = ' /// '.join(l[:POSTS_TO_STORE])

            helpers.send_a_post(self.bot, post['post'], db_entry, feed)

            db_entry.last_posts = new_posts
            db_entry.last_check = published
            session.commit()

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
