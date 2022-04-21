from variables import *


class WebhookThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.server = None
        #self.context = app.app_context()
        #self.context.push()
        self.exception = None

    def run(self):
        print("starting a webhook")
        try:
            self._make_tunnel()
            app = self._flask_app()
            self.server = make_server('127.0.0.1', 5000, app)
            self.server.serve_forever()
        except Exception as error:
            print("error in a webhook:", error)
            self.exception = error
            EXIT_EVENT.set()

    def _make_tunnel(self):
        tunnel = ngrok.connect(5000, bind_tls=True)
        print(tunnel)

        k = """curl --location --request POST \
        'https://api.telegram.org/bot{api}/setWebhook' \
        --header 'Content-Type: application/json' \
        --data-raw '{{"url": "{uri}"}}' \
        """.format(api=API, uri=tunnel.public_url)

        os.system(k)  # TODO subprocess
        print()

    def _flask_app(self):
        app = Flask(__name__)

        @app.route("/", methods=['POST'])
        def receiver():
            global NEW_MASSAGES
            if request.headers.get('content-type') == 'application/json':
                if AWAITING_MESSAGES_EVENT.wait():
                    data = request.get_data().decode('utf-8')
                    with open(MESSAGES_SOCKET, 'w', encoding='utf8') as f:
                        f.write(data)
                    AWAITING_MESSAGES_EVENT.clear()
                    NEW_MESSAGES_EVENT.set()
            else:
                print("POST: undefined request")
            return "", 200

        return app

    def shutdown(self):
        print("stopping a webhook")
        self.server.shutdown()

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
