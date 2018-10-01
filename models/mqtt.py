from shared import db
from sqlalchemy import Integer
from datetime import datetime
from config import Config
from models import Subscription, Message
import paho.mqtt.client as mqtt_api


cfg = Config.get_global_instance()


class MQTT(db.Model):
    id = db.Column(Integer, primary_key=True)
    uuid = db.Column(db.VARCHAR(40), nullable=False)
    timestamp_created = db.Column(db.TIMESTAMP, default=datetime.utcnow)

    def __init__(self, device):
        self.uuid = device

    def __repr__(self):
        return '<MQTT {}>'.format(self.uuid)

    def as_dict(self):
        data = {
            "uuid": self.service.as_dict(),
            "timestamp": int((self.timestamp_created - datetime.utcfromtimestamp(0)).total_seconds()),
        }
        return data

    @staticmethod
    def send_message(message):
        """

        :type message: Message to send to mqtt subscribers
        """
        subscriptions = Subscription.query.filter_by(service=message.service).all()
        if len(subscriptions) == 0:
            return 0
        mqtt_devices = MQTT.query.filter(MQTT.uuid.in_([l.device for l in subscriptions])).all()

        if len(mqtt_devices) > 0:
            data = dict(message=message.as_dict(), encrypted=False)
            MQTT.gcm_send([r.uuid for r in mqtt_devices], data)

        if len(mqtt_devices) > 0:
            uuids = [g.uuid for g in mqtt_devices]
            gcm_subscriptions = Subscription.query.filter_by(service=message.service).filter(
                Subscription.device.in_(uuids)).all()
            last_message = Message.query.order_by(Message.id.desc()).first()
            for l in gcm_subscriptions:
                l.timestamp_checked = datetime.utcnow()
                l.last_read = last_message.id if last_message else 0
            db.session.commit()
        return len(mqtt_devices)

    @staticmethod
    def gcm_send(uuids, data):
        url = cfg.mqtt_broker_address

        client = mqtt_api.Client()
        client.connect(url, 1883, 60)

        for uuid in uuids:
            client.publish(uuid, str(data))
