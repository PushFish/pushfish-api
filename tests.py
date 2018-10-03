# coding=utf-8
from __future__ import unicode_literals

import os
from uuid import uuid4
import unittest
import string
import random
import json
import logging
from time import sleep
from ast import literal_eval
import paho.mqtt.client as mqtt_api

from config import Config

_LOGGER = logging.getLogger("pushrocket-api-TESTS")


def _random_str(length=10, unicode=True):
    # A random string with the "cupcake" in Japanese appended to it
    # Always make sure that there is some unicode in there
    random_str = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))

    if unicode:
        random_str = random_str[:-7] + 'カップケーキ'
        # It's important that the following is a 4+-byte Unicode character.
        random_str = '😉' + random_str

    return random_str


def _failing_loader(s):
    data = json.loads(s)
    if 'error' in data:
        err = data['error']
        raise AssertionError("Got an unexpected error, [{}] {}".format(err['id'], err['message']))

    return data


_messages_received = []


def _message_callback(client, userdata, message):
    """
    mqtt subscribe callback function
    puts received messages in _messages_received
    """
    message = {"data": literal_eval(message.payload.decode("utf-8")), "topic": message.topic, "qos": message.qos,
               "retain": message.retain}
    _messages_received.append(message)


# NOTE: don't inherit these from unittest.TestCase, inherit the specialized
# database classes that way, then they both get run
class PushRocketTestCase(unittest.TestCase):
    def setUp(self):
        self.uuid = str(uuid4())
        from application import app
        cfg = Config.get_global_instance()

        app.config['TESTING'] = True
        app.config['TESTING_GCM'] = []
        self.gcm_enable = True
        if not cfg.google_api_key:
            _LOGGER.warning("GCM API key is not provided, won't test GCM")
            self.gcm_enable = False
        self.mqtt_enable = True
        self.mqtt_address = cfg.mqtt_broker_address
        if not cfg.mqtt_broker_address:
            _LOGGER.warning("MQTT broker address is not provided, won't test MQTT")
            self.mqtt_enable = False

        self.gcm = app.config['TESTING_GCM']
        self.app = app.test_client()
        self.app_real = app

    def test_service_create(self):
        name = "Hello test! {}".format(_random_str(5))
        data = {
            "name": name,
            "icon": "http://i.imgur.com/{}.png".format(_random_str(7, False))
        }
        rv = json.loads(self.app.post('/service', data=data).data)
        assert 'service' in rv
        return rv['service']['public'], rv['service']['secret'], name

    def test_subscription_new(self):
        public, secret, _ = self.test_service_create()
        data = dict(uuid=self.uuid, service=public)
        rv = self.app.post('/subscription', data=data)
        _failing_loader(rv.data)
        return public, secret

    def test_subscription_double(self):
        public, _ = self.test_subscription_new()
        data = dict(uuid=self.uuid, service=public)
        rv = self.app.post('/subscription', data=data)
        assert rv.status_code == 409
        data = json.loads(rv.data)
        assert 'error' in data
        assert data['error']['id'] == 4

    def test_subscription_delete(self):
        public, secret = self.test_subscription_new()
        rv = self.app.delete('/subscription?uuid={}&service={}'.format(self.uuid, public))
        _failing_loader(rv.data)
        return public, secret

    def test_subscription_invalid_delete(self):
        # Without a just-deleted service there's a chance to get an existing
        # one, as a test database isn't created when running tests.
        public, _ = self.test_subscription_delete()
        rv = self.app.delete('/subscription?uuid={}&service={}'.format(self.uuid, public))
        assert rv.status_code == 409
        data = json.loads(rv.data)
        assert 'error' in data
        assert data['error']['id'] == 11

    def test_subscription_list(self):
        public, _ = self.test_subscription_new()
        rv = self.app.get('/subscription?uuid={}'.format(self.uuid))
        resp = _failing_loader(rv.data)
        assert 'subscriptions' in resp
        assert len(resp['subscriptions']) == 1
        assert resp['subscriptions'][0]['service']['public'] == public

    def test_message_send(self, public='', secret=''):
        if not public or not secret:
            public, secret = self.test_subscription_new()
        data = {
            "level": random.randint(0, 5),
            "message": "Test message - {}".format(_random_str(20)),
            "title": "Test Title - {}".format(_random_str(5)),
            "secret": secret,
        }
        rv = self.app.post('/message', data=data)
        _failing_loader(rv.data)
        return public, secret, data

    def test_message_send_no_subscribers(self):
        # We just want to know if the server "accepts" it
        public, secret, _ = self.test_service_create()
        self.test_message_send(public, secret)

    def test_message_receive(self, amount=-1):
        if amount <= 0:
            self.test_message_send()
            amount = 1

        rv = self.app.get('/message?uuid={}'.format(self.uuid))
        resp = _failing_loader(rv.data)
        assert len(resp['messages']) is amount

        # Ensure it is marked as read
        rv = self.app.get('/message?uuid={}'.format(self.uuid))
        resp = _failing_loader(rv.data)
        assert len(resp['messages']) is 0

    def test_message_receive_no_subs(self):
        self.test_message_send()
        rv = self.app.get('/message?uuid={}'.format(uuid4()))
        resp = _failing_loader(rv.data)
        assert len(resp['messages']) is 0

    def test_message_receive_multi(self):
        self.test_message_mark_read()

        for _ in range(3):
            public, secret = self.test_subscription_new()
            for _ in range(5):
                self.test_message_send(public, secret)

        self.test_message_receive(15)

    def test_message_mark_read(self):
        self.test_message_send()
        self.app.delete('/message?uuid={}'.format(self.uuid))
        rv = self.app.get('/message?uuid={}'.format(self.uuid))
        resp = _failing_loader(rv.data)
        assert len(resp['messages']) == 0

    def test_message_mark_read_double(self):
        self.test_message_mark_read()

        # Read again without sending
        self.app.delete('/message?uuid={}'.format(self.uuid))
        rv = self.app.get('/message?uuid={}'.format(self.uuid))
        resp = _failing_loader(rv.data)
        assert not resp['messages']

    def test_message_mark_read_multi(self):
        # Stress test it a bit
        for _ in range(3):
            public, secret = self.test_subscription_new()
            for _ in range(5):
                self.test_message_send(public, secret)

        self.test_message_mark_read()

    def test_service_delete(self):
        public, secret = self.test_subscription_new()
        # Send a couple of messages, these should be deleted
        for _ in range(10):
            self.test_message_send(public, secret)

        rv = self.app.delete('/service?secret={}'.format(secret))
        _failing_loader(rv.data)

        # Does the service not exist anymore?
        rv = self.app.get('/service?service={}'.format(public))
        assert 'error' in json.loads(rv.data)

        # Has the subscriptioner been deleted?
        rv = self.app.get('/subscription?uuid={}'.format(self.uuid))
        resp = _failing_loader(rv.data)
        assert public not in [l['service']['public'] for l in resp['subscriptions']]

        # check we on't receive the message anymore
        rv = self.app.get('/message?uuid={}'.format(self.uuid))
        resp = _failing_loader(rv.data)
        assert not resp["messages"]

    def test_service_info(self):
        public, _, name = self.test_service_create()
        rv = self.app.get('/service?service={}'.format(public))
        data = _failing_loader(rv.data)
        assert 'service' in data
        srv = data['service']
        assert srv['name'] == name
        assert srv['public'] == public

    def test_service_info_secret(self):
        public, secret, name = self.test_service_create()
        rv = self.app.get('/service?secret={}'.format(secret))
        data = _failing_loader(rv.data)
        assert 'service' in data
        srv = data['service']
        assert srv['name'] == name
        assert srv['public'] == public

    def test_service_update(self):
        public, secret, _ = self.test_service_create()
        data = {
            "name": _random_str(10),
            "icon": "http://i.imgur.com/{}.png".format(_random_str(7, False))
        }
        rv = self.app.patch('/service?secret={}'.format(secret), data=data).data
        _failing_loader(rv)

        # Test if patched
        rv = self.app.get('/service?service={}'.format(public))
        rv = _failing_loader(rv.data)['service']
        for key in data.keys():
            assert data[key] == rv[key]

    def test_uuid_regex(self):
        rv = self.app.get('/service?service={}'.format(_random_str(20))).data
        assert 'error' in json.loads(rv)

    def test_service_regex(self):
        rv = self.app.get('/message?uuid={}'.format(_random_str(20))).data
        assert 'error' in json.loads(rv)

    def test_missing_arg(self):
        rv = json.loads(self.app.get('/message').data)
        assert 'error' in rv and rv['error']['id'] == 7
        rv = json.loads(self.app.get('/service').data)
        assert 'error' in rv and rv['error']['id'] == 7

    def test_gcm_register(self):
        if self.gcm_enable:
            reg_id = _random_str(40, unicode=False)
            data = {'uuid': self.uuid, 'regId': reg_id}
            rv = self.app.post('/gcm', data=data).data
            _failing_loader(rv)
            return reg_id
        else:
            _LOGGER.warning("GCM is disabled, not testing gcm_register")

    def test_gcm_unregister(self):
        if self.gcm_enable:
            self.test_gcm_register()
            rv = self.app.delete('/gcm', data={'uuid': self.uuid}).data
            _failing_loader(rv)
        else:
            _LOGGER.warning("GCM is disabled, not testing gcm_unregister")

    def test_gcm_register_double(self):
        if self.gcm_enable:
            self.test_gcm_register()
            self.test_gcm_register()
        else:
            _LOGGER.warning("GCM is disabled, not testing gcm_register_double")

    def test_gcm_send(self):
        if self.gcm_enable:
            reg_id = self.test_gcm_register()
            public, _, data = self.test_message_send()

            messages = [m['data'] for m in self.gcm
                        if reg_id in m['registration_ids']]

            assert len(messages) is 1
            assert messages[0]['encrypted'] is False

            message = messages[0]['message']
            assert message['service']['public'] == public
            assert message['message'] == data['message']
        else:
            _LOGGER.warning("GCM is disabled, not testing gcm_send")

    def test_mqtt_register(self):
        if self.mqtt_enable:
            data = {'uuid': self.uuid}
            rv = self.app.post('/mqtt', data=data).data
            _failing_loader(rv)
        else:
            _LOGGER.warning("MQTT is disabled, not testing mqtt_register")

    def test_mqtt_unregister(self):
        if self.mqtt_enable:
            self.test_mqtt_register()
            rv = self.app.delete('/mqtt', data={'uuid': self.uuid}).data
            _failing_loader(rv)
        else:
            _LOGGER.warning("MQTT is disabled, not testing mqtt_unregister")

    def test_mqtt_register_double(self):
        if self.mqtt_enable:
            self.test_mqtt_register()
            self.test_mqtt_unregister()
        else:
            _LOGGER.warning("MQTT is disabled, not testing MQTT_register_double")

    def test_mqtt_send(self):
        """
        test if message pushed to PushRocket can be received from the mqtt broker
        """
        if self.mqtt_enable:
            self.test_mqtt_register()

            url = self.mqtt_address
            if ":" in url:
                port = url.split(":")[1]
                url = url.split(":")[0]
            else:
                # default port
                port = 1883

            client = mqtt_api.Client()
            client.connect(url, port, 60)

            client.subscribe(self.uuid)
            client.on_message = _message_callback
            client.loop_start()
            public, _, data = self.test_message_send()
            sleep(2)
            client.loop_stop()
            client.disconnect()

            assert len(_messages_received) is 1

            mqtt_data = _messages_received[0]
            assert mqtt_data['topic'] == self.uuid
            message = mqtt_data['data']['message']
            assert message['service']['public'] == public
            assert message['message'] == data['message']
        else:
            _LOGGER.warning("MQTT is disabled, not testing mqtt_send")

    #    def test_get_version(self):
    #        version = self.app.get('/version').data
    #
    #        assert len(version) is 7
    #        with open('.git/refs/heads/master', 'r') as f:
    #            assert f.read()[:7] == version

    def test_get_static(self):
        files = ['robots.txt', 'favicon.ico']

        for f in files:
            path = os.path.join(self.app_real.root_path, 'static', f)
            with open(path, 'rb') as i:
                data = self.app.get('/{}'.format(f)).data
                assert data == i.read()


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    test_class = PushRocketTestCase
    tests = loader.loadTestsFromTestCase(test_class)
    suite.addTests(tests)
    return suite


if __name__ == "__main__":
    unittest.main()
