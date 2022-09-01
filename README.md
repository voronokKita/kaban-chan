# kaban-chan

![picture](kaban.jpg "Kaban-chan")

One telegram bot to learn them all.
> https://t.me/KabanChan_bot

This bot can track web feeds. She tries to sort their content in order and send updates about once an hour. But, Replit’s web hosting sometimes goes offline. <br>
I had a lot of fun working on this project. Although it was written without knowledge of architectural patterns and suffers from design problems; maybe one day I'll fix it. <br>
The bot chassis uses pyTelegramBotAPI. The webhook made on Flask accepts commands from Telegram, and the database works through SQLAlchemy.

If you want to run a copy, you need to get a bot API from BotFather and install cURL. <br>
Work on Windows do not guaranteed.

###### Install the Pipenv and run in a terminal:

0. pipenv install
1. pipenv shell
2. python3 -O main.py

##### Demo:

<img src="scr1.jpg" width="400" alt="first-page">

<img src="scr2.jpg" width="400" alt="first-page">
