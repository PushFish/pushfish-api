from flask import Blueprint, jsonify
from utils import has_uuid, Error
from models import MQTT
from shared import db
from config import Config

cfg = Config.get_global_instance()

mqtt = Blueprint('mqtt', __name__)


@mqtt.route("/mqtt", methods=["POST"])
@has_uuid
def mqtt_register(client):
    """
    register by uuid to a service
    :param client: client uuid
    """
    regs = MQTT.query.filter_by(uuid=client).all()
    for u in regs:
        db.session.delete(u)
    reg = MQTT(client)
    db.session.add(reg)
    db.session.commit()
    return Error.NONE


@mqtt.route("/mqtt", methods=["DELETE"])
@has_uuid
def mqtt_unregister(client):
    """
    unregister by uuid to a service
    :param client: client uuid
    """
    regs = MQTT.query.filter_by(uuid=client).all()
    for u in regs:
        db.session.delete(u)
    db.session.commit()
    return Error.NONE


@mqtt.route("/mqtt", methods=["GET"])
def mqtt_broker_address():
    data = dict(broker_address=cfg.mqtt_broker_address)
    return jsonify(data)
