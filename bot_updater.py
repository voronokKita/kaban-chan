from variables import *


class UpdaterThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.timeout = 100
        self.exception = None

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception

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
        print("check for updates")

    """
    #  http://feeds.bbci.co.uk/news/rss.xml
    python_feed = feedparser.parse('https://feeds.feedburner.com/PythonInsider')
    print(python_feed.feed.title)
    print(python_feed.feed.link)
    print()
    for i in range(3):
        print(python_feed.entries[i].title)
        print(python_feed.entries[i].published)
        soup = BeautifulSoup(python_feed.entries[i].summary, features='html.parser')
        text = soup.text[:200]
        print(f"{text.strip()}...")
        print(python_feed.entries[i].link)
        print()
    """
