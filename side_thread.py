from variables import *
from bot_config import bot, bot_types


class SideThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.updater = updater

    def run(self):
        print("starting an updater")
        self.updater()



def updater():
    while True:
        print("check for updates")
        if EXIT_EVENT.wait(timeout=100):
            break
    print("ending updates")
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