# coding=utf-8
from __future__ import unicode_literals

import os
from uuid import uuid4
import unittest
import string
import random
import json
import tempfile
import logging

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


#NOTE: don't inherit these from unittest.TestCase, inherit the specialized
#database classes that way, then they both get run
class PushRocketTestCase:
    @classmethod
    def setUpClass(cls):
        _LOGGER.info("running test cases with database URI: %s", cls.URI)
        _tempfd, cls._tempfilepath = tempfile.mkstemp(text=True)
        cls.config = Config(path=cls._tempfilepath, overwrite=True)
        cls.config.INJECT_CONFIG = True
        cls.config._cfg["database"]["uri"] = cls.URI
        #manually override google_api_key to force GCM enable for testing purposes

        if cls.config.google_api_key == "":
            _LOGGER.info("monkey patching google_api_key")
            cls.config._cfg["dispatch"]["google_api_key"] = "PLACEHOLDER"

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls._tempfilepath)


    def setUp(self):
        self.uuid = str(uuid4())
        from application import app

        app.config['TESTING'] = True
        app.config['TESTING_GCM'] = []

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

        #check we on't receive the message anymore
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
        reg_id = _random_str(40, unicode=False)
        data = {'uuid': self.uuid, 'regId': reg_id}
        rv = self.app.post('/gcm', data=data).data
        _failing_loader(rv)
        return reg_id

    def test_gcm_unregister(self):
        self.test_gcm_register()
        rv = self.app.delete('/gcm', data={'uuid': self.uuid}).data
        _failing_loader(rv)

    def test_gcm_register_double(self):
        self.test_gcm_register()
        self.test_gcm_register()

    def test_gcm_send(self):
        reg_id = self.test_gcm_register()
        public, _, data = self.test_message_send()

        messages = [m['data'] for m in self.gcm
                    if reg_id in m['registration_ids']]

        assert len(messages) is 1
        assert messages[0]['encrypted'] is False

        message = messages[0]['message']
        assert message['service']['public'] == public
        assert message['message'] == data['message']

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


class PushRocketSqliteTests(PushRocketTestCase, unittest.TestCase):
    URI = "sqlite:///pushrocket_api.db"

class PushRocketMysqlTests(PushRocketTestCase, unittest.TestCase):
    URI = "mysql+pymysql://pushrocket@localhost/pushrocket_api?charset=utf8mb4"


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    for test_class in [PushRocketSqliteTests, PushRocketMysqlTests]:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    return suite


if __name__ == "__main__":
    unittest.main()
