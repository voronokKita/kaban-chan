from variables import *
from bot_config import bot


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
    print("Failed to set a webhook. Error code:", "-"*10, error, "-"*10, sep="\n")
    sys.exit(1)
"""
try:
    # Block until CTRL-C or some other terminating event
    ngrok_process.proc.wait()
except KeyboardInterrupt:
    print(" Shutting down server.")
    ngrok.kill()
"""


@app.route("/", methods=['POST'])
def receiver():
    if request.headers.get('content-type') == 'application/json':
        json = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json)
        bot.process_new_updates([update])
    return ""
