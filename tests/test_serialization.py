import requests

from mock import Mock

from cachecontrol.compat import pickle
from cachecontrol.serialize import Serializer


class TestSerializer(object):

    def setup(self):
        self.serializer = Serializer()
        self.response_data = {
            'response': {
                'body': 'Hello World',
                'headers': {
                    'Content-Type': 'text/plain',
                    'Expires': '87654',
                    'Cache-Control': 'public',
                },
                'status': 200,
                'version': '2',
                'reason': '',
                'strict': '',
                'decode_content': True,
            },
        }

    def test_load_by_version_one(self):
        data = 'cc=0,somedata'
        req = Mock()
        assert not self.serializer.loads(req, data)

    def test_read_version_two(self):
        data = 'cc=1,%s' % pickle.dumps(self.response_data)
        req = Mock()
        resp = self.serializer.loads(req, data)
        assert resp.data == 'Hello World'

    def test_read_version_three_streamable(self, url):
        original_resp = requests.get(url, stream=True)
        # data = original_resp.content
        req = original_resp.request

        resp = self.serializer.loads(
            req, self.serializer.dumps(
                req,
                original_resp.raw
            )
        )

        assert resp.read()

    def test_read_version_three(self, url):
        original_resp = requests.get(url)
        data = original_resp.content
        req = original_resp.request

        resp = self.serializer.loads(
            req, self.serializer.dumps(
                req,
                original_resp.raw,
                body=data
            )
        )

        assert resp.read()
