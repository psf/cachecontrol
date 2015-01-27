import json
import zlib

from mock import Mock
import cPickle as pickle

from cachecontrol.serialize import Serializer, _b64_encode_str


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

    def current_response_format(self):
        """The current format of the response by constructing a fake
        response and getting the dumped value from the serializer.
        """
        data = self.response_data['response']

        resp = Mock()
        resp.headers = data['headers']
        resp.status = data['status']
        resp.version = data['version']
        resp.reason = data['reason']
        resp.strict = data['strict']
        resp.decode_content = data['decode_content']

        return self.serializer.dumps(Mock(name='request'), resp, data['body'])

    def test_read_version_three(self):
        req = Mock()
        resp = self.serializer.loads(req, self.current_response_format())
        assert resp.data == 'Hello World'
