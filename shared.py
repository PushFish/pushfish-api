from flask_sqlalchemy import SQLAlchemy
#TODO: a better way of doing this
from config import Config
import zmq

db = SQLAlchemy()

zmq_relay_socket = None
zeromq_context = None

cfg = Config.get_global_instance()

if cfg.zeromq_relay_uri:
    zeromq_context = zmq.Context()
    zmq_relay_socket = zeromq_context.socket(zmq.PUSH)
    zmq_relay_socket.connect(cfg.zeromq_relay_id)
