from flask_sqlalchemy import SQLAlchemy
import zmq
# TODO: a better way of doing this
from config import Config, fatal_error_exit_or_backtrace

db = SQLAlchemy()

zmq_relay_socket = None
zeromq_context = None

cfg = Config.get_global_instance()

if cfg.zeromq_relay_uri:
    zeromq_context = zmq.Context()
    zmq_relay_socket = zeromq_context.socket(zmq.PUSH)
    try:
        zmq_relay_socket.connect(cfg.zeromq_relay_uri)
    except zmq.error.ZMQError as err:
        errstr = "coudn't connect to ZMQ relay, perhaps your option %s is wrong. current value:%s"
        fatal_error_exit_or_backtrace(err, errstr, None, "zeromq_relay_uri", cfg.zeromq_relay_uri)
