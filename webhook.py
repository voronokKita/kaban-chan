from variables import *


app = Flask(__name__)


class WebhookThread(threading.Thread):  # TODO exception
    def __init__(self):
        threading.Thread.__init__(self)
        self.server = make_server('127.0.0.1', 5000, app)
        self.context = app.app_context()
        self.context.push()

    def run(self):
        print("starting a webhook")
        try:
            tunnel = ngrok.connect(5000, bind_tls=True)
            print(tunnel)
            time.sleep(0.2)

            k = """curl --location --request POST \
            'https://api.telegram.org/bot{api}/setWebhook' \
            --header 'Content-Type: application/json' \
            --data-raw '{{"url": "{uri}"}}' \
            """.format(api=API, uri=tunnel.public_url)

            os.system(k)  # TODO subprocess
            print()
            self.server.serve_forever()
        except Exception as error:
            raise error

    def shutdown(self):
        print("stopping a webhook")
        self.server.shutdown()


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
    return ""
