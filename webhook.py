from variables import *


app = Flask(__name__)

try:
    WEBHOOK = ngrok.connect(5000, bind_tls=True)
    print(WEBHOOK)
    time.sleep(0.5)

    k = """curl --location --request POST \
    'https://api.telegram.org/bot{api}/setWebhook' \
    --header 'Content-Type: application/json' \
    --data-raw '{{"url": "{uri}"}}' \
    """.format(api=API, uri=WEBHOOK.public_url)

    os.system(k)  # TODO subprocess
    print()

except Exception as error:
    print("Failed to set an ngrok. Error code:", "-"*10, error, "-"*10, sep="\n")
    sys.exit(1)


class Webhook():
    def __init__(self):
        self.server = make_server('127.0.0.1', 5000, app)
        self.context = app.app_context()
        self.context.push()

    def run(self):
        print("starting a webhook")
        self.server.serve_forever()

    def shutdown(self):
        print("stopping a webhook")
        self.server.shutdown()


@app.route("/", methods=['POST'])
def receiver():
    global NEW_MASSAGES
    if request.headers.get('content-type') == 'application/json':
        data = request.get_data().decode('utf-8')
        #data['message']['from']['id']
        update = telebot.types.Update.de_json(data)
        NEW_MASSAGES.append(update)
        NEW_MASSAGES_EVENT.set()
    return ""
