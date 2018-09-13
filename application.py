#!/usr/bin/env python2.7
# coding=utf-8
from __future__ import unicode_literals
from flask import Flask, redirect, send_from_directory, request
from sys import stderr
import logging
from sqlalchemy.exc import OperationalError
import sys

from config import Config
_LOGGER = logging.getLogger(name="pushrocket_API")


if __name__ == "__main__":
    _LOGGER.info("running application as main, creating Config object")
    cfg = Config(create=True)
else:
    _LOGGER.info("running application not as main (probably test mode), using existing global config")
    cfg = Config.get_global_instance()

import database



from shared import db
from controllers import subscription, message, service, gcm
from utils import Error

gcm_enabled = True
if cfg.google_api_key == '':
    stderr.write("WARNING: GCM disabled, please enter the google api key for gcm")
    gcm_enabled = False
if cfg.google_gcm_sender_id == 0:
    stderr.write('WARNING: GCM disabled, invalid sender id found')
    gcm_enabled = False


app = Flask(__name__)
app.debug = cfg.debug
app.config['SQLALCHEMY_DATABASE_URI'] = cfg.database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
db.app = app

try:
    database.init_db()
except Exception as err:
    _LOGGER.error("couldn't initialize database with URI: %s",cfg.database_uri)
    if cfg.GLOBAL_BACKTRACE_ENABLE:
        raise err
    else:
        sys.exit(1)

@app.route('/')
def index():
    return redirect('https://www.pushrocket.net')


@app.route('/robots.txt')
@app.route('/favicon.ico')
def robots_txt():
    return send_from_directory(app.static_folder, request.path[1:])


@app.route('/version')
def version():
    with open('.git/refs/heads/master', 'r') as f:
        return f.read(7)


@app.errorhandler(429)
def limit_rate(e):
    return Error.RATE_TOOFAST


app.register_blueprint(subscription)
app.register_blueprint(message)
app.register_blueprint(service)
if gcm_enabled:
    app.register_blueprint(gcm)

if __name__ == '__main__':
    app.run()
