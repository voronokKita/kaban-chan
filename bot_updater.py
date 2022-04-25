from variables import *


class UpdaterThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.bot = telebot.TeleBot(API)
        self.timeout = FEEDS_UPDATE_TIMEOUT
        self.exception = None

    def run(self):
        print("starting an updater")
        while True:
            try:
                self._updater()
            except Exception as error:
                print("error in an updater:", error)
                self.exception = error
                EXIT_EVENT.set()
            if EXIT_EVENT.wait(timeout=self.timeout):
                print("stopping an updater")
                break

    def _updater(self):
        with SQLSession(db) as session:
            for entry in session.scalars( sql.select(WebFeedsDB) ):
                feed = feedparser.parse(entry.web_feed)
                self._check_the_feed(feed, entry)

    def _check_the_feed(self, feed, db_entry):
        for publication in feed.entries:
            published = datetime.fromtimestamp(
                time.mktime(publication.published_parsed)
            )
            if db_entry.last_check >= published:
                break
            else:
                soup = BeautifulSoup(publication.summary, features='html.parser')
                summary = soup.text[:200]
                text = f"{publication.title}\n" \
                       f"{published.strftime(TIME_FORMAT)}\n" \
                       f"{summary.strip()}...\n" \
                       f"{publication.link}"
                self.bot.send_message(db_entry.user_id, text)

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
