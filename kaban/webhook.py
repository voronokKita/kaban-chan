import subprocess
import threading

import telebot
from pyngrok import ngrok
from werkzeug.serving import make_server, BaseWSGIServer

from kaban.settings import (
    API, ADDRESS, PORT, WEBHOOK_ENDPOINT,
    WEBHOOK_WAS_SET, HOOK_READY_TO_WORK,
    REPLIT, REPLIT_URL
)
from kaban.helpers import exit_signal


class WebhookThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)

        self.app = app
        self.url = str
        self.exception = None

        self.exit = exit_signal
        self.webhook_was_set = WEBHOOK_WAS_SET

        self.tg_api = API
        self.server_ip = ADDRESS
        self.server_port = PORT
        self.endpoint = WEBHOOK_ENDPOINT
        self.ready = HOOK_READY_TO_WORK
        self.replit = REPLIT
        self.replit_url = REPLIT_URL

        try:
            self.server = make_server(
                host=self.server_ip,
                port=self.server_port,
                app=self.app
            )
            if type(self.server) is not BaseWSGIServer:
                raise TypeError
        except (OSError, TypeError, Exception) as exc:
            raise Exception from exc

    def __str__(self): return "webhook thread"

    def run(self):
        try:
            self._make_tunnel()
            self._set_webhook()
            self.ready.set()
            self.server.serve_forever()
        except Exception as error:
            self.exception = error
            self.exit()

    def _make_tunnel(self):
        if self.replit:
            self.url = self.replit_url + self.endpoint
        else:
            tunnel = ngrok.connect(self.server_port, bind_tls=True)
            self.url = tunnel.public_url + self.endpoint

    def _set_webhook(self):
        telebot.TeleBot(self.tg_api).remove_webhook()
        k = [
            'curl', '--location', '--request', 'POST',
            f'https://api.telegram.org/bot{self.tg_api}/setWebhook',
            '--header', 'Content-Type: application/json',
            '--data-raw', f'{{"url": "{self.url}"}}'
        ]
        result = subprocess.check_output(k, stderr=subprocess.STDOUT)
        if not self.webhook_was_set.search(result.decode("utf-8")):
            raise Exception(result)

    def shutdown(self):
        self.server.shutdown()

    def stop(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
