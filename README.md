# kaban-chan

One telegram bot to learn them all.

0. get ngrok https://dashboard.ngrok.com/get-started/setup
1. ./ngrok http 5000
2. $ curl --location --request POST \ <br>
'https://api.telegram.org/bot{TELGRAM-API-TOKEN}/setWebhook' \ <br>
--header 'Content-Type: application/json' \ <br>
--data-raw '{"url": "{NGROK-HTTPS-URL}"}'
3. pipenv install
4. pipenv shell
5. FLASK_APP=kaban.py flask run
