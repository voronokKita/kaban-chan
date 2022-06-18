from datetime import datetime
import hashlib
import threading
import time

import feedparser

from kaban.settings import (
    EXIT_EVENT, FEEDS_UPDATE_TIMEOUT, NOTIFICATIONS, FeedLoadError,
    UpdPosts, UpdFeeds, UpdPostList, UpdPost, Feed
)
from kaban.helpers import exit_signal, send_message, send_a_post
from kaban.database import SQLSession, FeedsDB, POSTS_TO_STORE
from kaban.log import log, info


class UpdaterThread(threading.Thread):
    """ Note
    A web feed doesn't guarantee a strict sequence and order.
    Many of them update a post's publication date each time they update the post's text,
    causing all posts to reorder unpredictably.
    I tried to solve this problem by memorizing titles of N posts in md5.
    """
    def __init__(self, bot):
        threading.Thread.__init__(self)

        self.bot = bot
        self.exception = None

        self.exit = exit_signal
        self.send_message = send_message
        self.send_a_post = send_a_post

        self.exit_event = EXIT_EVENT
        self.timeout = FEEDS_UPDATE_TIMEOUT
        self.posts_to_store = POSTS_TO_STORE
        self.notifications = NOTIFICATIONS

    def __str__(self): return "updater thread"

    def run(self):
        """ Checks feeds for updates from time to time. """
        try:
            self._notifications()

            while True:
                new_posts: UpdPosts = {}
                self._load(new_posts)
                self._forward(new_posts)
                del new_posts
                self._test()

                if self.exit_event.wait(self.timeout):
                    break

        except Exception as error:
            self.exception = error
            self.exit()

    def _notifications(self):
        """ Sends messages to users from a file.
            Messages must be separated by >>> """
        messages = []
        if self.notifications.exists():
            with open(self.notifications, 'r', encoding='utf-8') as file:
                text = file.read()
                messages = [m.strip() for m in text.split('>>>') if m.strip()]

        if not messages: return

        with SQLSession() as session:
            uids = session.query(FeedsDB.uid).distinct()
            for uid in session.scalars(uids):
                for m in messages:
                    self.send_message(self.bot, uid, m)

        with open(self.notifications, 'w') as f: f.write('')
        info("notifications sent out")

    def _load(self, new_posts: UpdPosts):
        """ Loads new posts from all feeds into memory. """
        self._populate_user_ids(new_posts)
        self._populate_user_feeds(new_posts)
        self._populate_feed_posts(new_posts)

    def _populate_user_ids(self, new_posts: UpdPosts):
        """ Subfunction of _load(), loads all uids. """
        with SQLSession() as session:
            for db_entry in session.scalars(session.query(FeedsDB)):
                new_posts[db_entry.uid] = {}

    def _populate_user_feeds(self, new_posts: UpdPosts):
        """ Subfunction of _load(), loads all feeds. """
        for uid in new_posts:
            dict_of_feeds: UpdFeeds = {}
            with SQLSession() as session:
                entries = session.query(FeedsDB).filter(FeedsDB.uid == uid)
                for db_entry in session.scalars(entries):
                    dict_of_feeds[db_entry.feed] = []
            new_posts[uid] = dict_of_feeds

    def _populate_feed_posts(self, new_posts: UpdPosts):
        """ Subfunction of _load(), loads lists of new posts. """
        for uid in new_posts:
            for feed in new_posts[uid]:
                posts_to_send: UpdPostList = []
                try:
                    parsed_feed: Feed = feedparser.parse(feed)
                    if not parsed_feed.entries or not parsed_feed.entries[0].title:
                        raise FeedLoadError

                    self._populate_list_of_posts(
                        posts_to_send, parsed_feed.entries, uid, feed
                    )
                except (AttributeError, IndexError, FeedLoadError):
                    log.warning(f'failed to load feed - {feed}')
                except Exception as error:
                    log.warning(f'feedparser fail - {error}')
                finally:
                    new_posts[uid][feed] = posts_to_send

    def _populate_list_of_posts(self, posts_to_send: UpdPostList,
                                posts: list, uid: int, feed: str):
        """ Subfunction of _load(), loads new posts from a feed. """
        with SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == uid,
                FeedsDB.feed == feed
            ).first()

            old_posts = set(db_entry.last_posts.split(' /// '))
            feed_last_check = db_entry.last_check

        for post in posts:
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
                else:
                    new_post: UpdPost = {'title': title, 'post': post}
                    posts_to_send.append(new_post)

    def _forward(self, new_posts: UpdPosts):
        """ Organizes new posts mailing in order.
            The order of the posts should be reversed
            to keep feed's original sequence."""
        for uid in new_posts:
            for feed in new_posts[uid]:
                for post in reversed(new_posts[uid][feed]):
                    self._updater(uid, feed, post)

    def _updater(self, uid: int, feed: str, post: UpdPost):
        """ A bottom function.
            Forwards a post to the post sender function.
            Save changes to the database. """
        with SQLSession() as session:
            db_entry = session.query(FeedsDB).filter(
                FeedsDB.uid == uid,
                FeedsDB.feed == feed
            ).first()

            published = datetime.fromtimestamp(
                time.mktime(post['post'].published_parsed)
            )
            old_posts = db_entry.last_posts.split(' /// ')
            l = [post['title']] + old_posts
            new_last_posts = ' /// '.join(l[:self.posts_to_store])

            self.send_a_post(self.bot, post['post'], db_entry, feed)

            db_entry.last_posts = new_last_posts
            db_entry.last_check = published
            session.commit()

    def _test(self):
        """ Needed for testing. """

    def stop(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
