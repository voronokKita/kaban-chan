from kaban.settings import *
from kaban import helpers


class WebhookThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app
        self.server = None
        self.exception = None

    def __repr__(self):
        return "webhook thread"

    def run(self):
        try:
            self._make_tunnel()
            self.server = make_server(ADDRESS, PORT, self.app)
            READY_TO_WORK.set()
            self.server.serve_forever()

        except Exception as error:
            self.exception = error
            helpers.exit_signal()

    @staticmethod
    def _make_tunnel():
        if REPLIT:
            url = REPLIT_URL + WEBHOOK_ENDPOINT
        else:
            tunnel = ngrok.connect(PORT, bind_tls=True)
            url = tunnel.public_url + WEBHOOK_ENDPOINT
        k = [
            'curl', '--location', '--request', 'POST',
            f'https://api.telegram.org/bot{API}/setWebhook',
            '--header', 'Content-Type: application/json',
            '--data-raw', f'{{"url": "{url}"}}'
        ]
        result = subprocess.check_output(k, stderr=subprocess.STDOUT).decode("utf-8")
        if not WEBHOOK_WAS_SET.search(result):
            raise Exception(result)

    def shutdown(self):
        if self.server:
            self.server.shutdown()

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
