from variables import *
import helpers


class WebhookThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.server = None
        #self.context = app.app_context()
        #self.context.push()
        self.exception = None

    def __repr__(self):
        return "webhook thread"

    def run(self):
        try:
            self._make_tunnel()
            app = self._flask_app()
            self.server = make_server('127.0.0.1', 5000, app)
            READY_TO_WORK.set()
            self.server.serve_forever()
        except Exception as error:
            self.exception = error
            helpers.exit_signal()

    def _make_tunnel(self):
        tunnel = ngrok.connect(5000, bind_tls=True)
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

    def _flask_app(self):
        app = Flask(__name__)

        @app.route(WEBHOOK_ENDPOINT, methods=['POST'])
        def receiver():
            try:
                if not request.headers.get('content-type') == 'application/json':
                    raise
                data = request.get_data().decode('utf-8')
                telebot.types.Update.de_json(data)
                with SQLSession(db) as session:
                    new_message = WebhookDB(data=data)
                    session.add(new_message)
                    session.commit()
                NEW_MESSAGES_EVENT.set()
            except:
                print("-"*10, "Alien Invasion", request.get_data().decode('utf-8'), "-"*10, sep="\n")
                return "", 400
            else:
                return "", 200

        return app

    def shutdown(self):
        if self.server:
            self.server.shutdown()

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
