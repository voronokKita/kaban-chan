import secrets

import telebot
import flask
from flask import Flask, request

from kaban.database import SQLSession, WebhookDB
from kaban.settings import (
    NEW_MESSAGES_EVENT, BANNED,
    WEBHOOK_ENDPOINT, WebhookRequestError
)
from kaban.log import log


def get_app():
    """ Will return webhook application. """
    app = Flask('__main__')
    app.config.update(
        ENV='production',
        DEBUG=False,
        TESTING=False,
        PRESERVE_CONTEXT_ON_EXCEPTION=True,
        SECRET_KEY=secrets.token_hex(),
    )

    @app.route(WEBHOOK_ENDPOINT, methods=['POST'])
    def inbox():
        """ Checks requests and passes them into the WebhookDB.
            The db serves as a reliable request queue. """
        ip = request.environ.get('REMOTE_ADDR')
        if ip in BANNED:
            flask.abort(403)

        try:
            if not request.headers.get('content-type') == 'application/json':
                raise WebhookRequestError
            try:
                data = request.get_data().decode('utf-8')
                telebot.types.Update.de_json(data)
            except Exception:
                raise WebhookRequestError

        except WebhookRequestError:
            log.exception(f'Alien Invasion 👽 {request.get_data().decode("utf-8")}')
            BANNED.append(ip)
            flask.abort(403)

        else:
            with SQLSession() as session:
                new_message = WebhookDB(data=data)
                session.add(new_message)
                session.commit()
            NEW_MESSAGES_EVENT.set()
            return "", 200

    @app.route('/ping', methods=['GET'])
    def ping():
        return "pong", 200

    return app
