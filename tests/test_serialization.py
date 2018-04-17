import msgpack
import requests

from mock import Mock

from cachecontrol.compat import pickle
from cachecontrol.serialize import Serializer


class TestSerializer(object):

    def setup(self):
        self.serializer = Serializer()
        self.response_data = {
            u"response": {
                # Encode the body as bytes b/c it will eventually be
                # converted back into a BytesIO object.
                u"body": "Hello World".encode("utf-8"),
                u"headers": {
                    u"Content-Type": u"text/plain",
                    u"Expires": u"87654",
                    u"Cache-Control": u"public",
                },
                u"status": 200,
                u"version": 11,
                u"reason": u"",
                u"strict": True,
                u"decode_content": True,
            }
        }

    def test_load_by_version_v0(self):
        data = b"cc=0,somedata"
        req = Mock()
        resp = self.serializer.loads(req, data)
        assert resp is None

    def test_read_version_v1(self):
        req = Mock()
        resp = self.serializer._loads_v1(req, pickle.dumps(self.response_data))
        # We have to decode our urllib3 data back into a unicode string.
        assert resp.data == "Hello World".encode("utf-8")

    def test_read_version_v2(self):
        req = Mock()
        compressed_base64_json = b"x\x9c%O\xb9\n\x83@\x10\xfd\x97\xa9-\x92%E\x14R\xe4 +\x16\t\xe6\x10\xbb\xb0\xc7\xe0\x81\xb8\xb2\xbb*A\xfc\xf7\x8c\xa6|\xe7\xbc\x99\xc0\xa2\xebL\xeb\x10\xa2\t\xa4\xd1_\x88\xe0\xc93'\xf9\xbe\xc8X\xf8\x95<=@\x00\x1a\x95\xd1\xf8Q\xa6\xf5\xd8z\x88\xbc\xed1\x80\x12\x85F\xeb\x96h\xca\xc2^\xf3\xac\xd7\xe7\xed\x1b\xf3SC5\x04w\xfa\x1c\x8e\x92_;Y\x1c\x96\x9a\x94]k\xc1\xdf~u\xc7\xc9 \x8fDG\xa0\xe2\xac\x92\xbc\xa9\xc9\xf1\xc8\xcbQ\xe4I\xa3\xc6U\xb9_\x14\xbb\xbdh\xc2\x1c\xd0R\xe1LK$\xd9\x9c\x17\xbe\xa7\xc3l\xb3Y\x80\xad\x94\xff\x0b\x03\xed\xa9V\x17[2\x83\xb0\xf4\xd14\xcf?E\x03Im"
        resp = self.serializer._loads_v2(req, compressed_base64_json)
        # We have to decode our urllib3 data back into a unicode string.
        assert resp.data == "Hello World".encode("utf-8")

    def test_load_by_version_v3(self):
        data = b"cc=3,somedata"
        req = Mock()
        resp = self.serializer.loads(req, data)
        assert resp is None

    def test_read_version_v4(self):
        req = Mock()
        resp = self.serializer._loads_v4(req, msgpack.dumps(self.response_data))
        # We have to decode our urllib3 data back into a unicode string.
        assert resp.data == "Hello World".encode("utf-8")

    def test_read_v1_serialized_with_py2_TypeError(self):
        # This tests how the code handles in reading data that was pickled
        # with an old version of cachecontrol running under Python 2
        req = Mock()
        py2_pickled_data = b"".join(
            [
                b"(dp1\nS'response'\np2\n(dp3\nS'body'\np4\nS'Hello World'\n",
                b"p5\nsS'version'\np6\nS'2'\nsS'status'\np7\nI200\n",
                b"sS'reason'\np8\nS''\nsS'decode_content'\np9\nI01\n",
                b"sS'strict'\np10\nS''\nsS'headers'\np11\n(dp12\n",
                b"S'Content-Type'\np13\nS'text/plain'\np14\n",
                b"sS'Cache-Control'\np15\nS'public'\np16\n",
                b"sS'Expires'\np17\nS'87654'\np18\nsss.",
            ]
        )
        resp = self.serializer._loads_v1(req, py2_pickled_data)
        # We have to decode our urllib3 data back into a unicode
        # string.
        assert resp.data == "Hello World".encode("utf-8")

    def test_read_v2_corrupted_cache(self):
        # This should prevent a regression of bug #134
        req = Mock()
        assert self.serializer._loads_v2(req, b"") is None

    def test_read_latest_version_streamable(self, url):
        original_resp = requests.get(url, stream=True)
        req = original_resp.request

        resp = self.serializer.loads(req, self.serializer.dumps(req, original_resp.raw))

        assert resp.read()

    def test_read_latest_version(self, url):
        original_resp = requests.get(url)
        data = original_resp.content
        req = original_resp.request

        resp = self.serializer.loads(
            req, self.serializer.dumps(req, original_resp.raw, body=data)
        )

        assert resp.read() == data

    def test_no_vary_header(self, url):
        original_resp = requests.get(url)
        data = original_resp.content
        req = original_resp.request

        # We make sure our response has a Vary header and that the
        # request doesn't have the header.
        original_resp.raw.headers["vary"] = "Foo"

        assert self.serializer.loads(
            req, self.serializer.dumps(req, original_resp.raw, body=data)
        )
