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
            READY_TO_WORK.set()
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
        --data-raw '{{"url": "{url}/kaban-chan"}}' \
        """.format(api=API, url=tunnel.public_url)

        os.system(k)  # TODO subprocess
        print()

    def _flask_app(self):
        app = Flask(__name__)

        @app.route("/kaban-chan", methods=['POST'])
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
        print("stopping a webhook")
        self.server.shutdown()

    def join(self):
        threading.Thread.join(self)
        if self.exception:
            raise self.exception
