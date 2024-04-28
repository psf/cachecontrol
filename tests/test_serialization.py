# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock

import msgpack
import requests

from cachecontrol.serialize import Serializer


class TestSerializer:
    def setup_method(self):
        self.serializer = Serializer()
        self.response_data = {
            "response": {
                # Encode the body as bytes b/c it will eventually be
                # converted back into a BytesIO object.
                "body": b"Hello World",
                "headers": {
                    "Content-Type": "text/plain",
                    "Expires": "87654",
                    "Cache-Control": "public",
                },
                "status": 200,
                "version": 11,
                "reason": "",
                "strict": True,
                "decode_content": True,
            }
        }

    def test_load_by_version_v0(self):
        data = b"cc=0,somedata"
        req = Mock()
        resp = self.serializer.loads(req, data)
        assert resp is None

    def test_load_by_version_v1(self):
        data = b"cc=1,somedata"
        req = Mock()
        resp = self.serializer.loads(req, data)
        assert resp is None

    def test_load_by_version_v2(self):
        data = b"cc=2,somedata"
        req = Mock()
        resp = self.serializer.loads(req, data)
        assert resp is None

    def test_load_by_version_v3(self):
        data = b"cc=3,somedata"
        req = Mock()
        resp = self.serializer.loads(req, data)
        assert resp is None

    def test_read_version_v4(self):
        req = Mock()
        resp = self.serializer._loads_v4(req, msgpack.dumps(self.response_data))
        # We have to decode our urllib3 data back into a unicode string.
        assert resp.data == b"Hello World"

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

    def test_no_incomplete_read_on_dumps(self, url):
        resp = requests.get(url + "fixed_length", stream=True)
        self.serializer.dumps(resp.request, resp.raw)

        assert resp.content == b"0123456789"
