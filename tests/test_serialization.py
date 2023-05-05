# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

import msgpack
import requests

from mock import Mock

from cachecontrol.compat import pickle
from cachecontrol.serialize import Serializer


class TestSerializer(object):
    def setup_method(self):
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
        compressed_base64_json = b'x\x9c\x1d\x8fK\x0f\x820\x10\x84\xff\xcb\x9e9h\xe3A\x9ax\xf0\x11K8hPi\xb8\x99>6\n!\xd4\xd0\x02!\x84\xff\xee\xc2qg\xbe\x9d\x9d\x9d\xa0E\xffs\x8dG\xe0\x13hgG\xe0\xf0\x14\xd2k\xb1\xffH\x16\x8fZd\x07\x88\xc0\xa2q\x16\xdf\xc65\x01\x9b\x00<\xb4\x1dF\xf0Ee\xb1\xf5\xcbj\xc6\xe2\xce\n\xd9\xd9\xf36\xc7\xe2TS\x0c\x8d;{\x8e\x07-\xae?\xfd9,1\x19\xbbVJ\xe4a\xa5\x93\xb4\xd7G\x929\x98D\x96Z\xd4\x15\x11\x8f\xe2;\xa8"\xad\xcd\xb0:\xf7\x8ba\xb7\x17U\x98#j\xaa\xbckH$\xcc\x07\x15::\xcc6\x9b\x08z\xeaP\xae\x0e[\xb8^\xb5\xf4\xc54\xcf\x7f\xef\xc0E\xe6'
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
                b"sS'headers'\np11\n(dp12\n",
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

        resp = self.serializer.loads(
            req, self.serializer.dumps(req, original_resp.raw, original_resp.content)
        )

        assert resp.read()

    def test_read_latest_version(self, url):
        original_resp = requests.get(url)
        data = original_resp.content
        req = original_resp.request

        resp = self.serializer.loads(
            req, self.serializer.dumps(req, original_resp.raw, data)
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
            req, self.serializer.dumps(req, original_resp.raw, data)
        )

    def test_no_body_creates_response_file_handle_on_dumps(self, url):
        original_resp = requests.get(url, stream=True)
        data = None
        req = original_resp.request

        assert self.serializer.loads(
            req, self.serializer.dumps(req, original_resp.raw, data)
        )

        # By passing in data=None it will force a read of the file
        # handle. Reading it again proves we're resetting the internal
        # file handle with a buffer.
        assert original_resp.raw.read()
