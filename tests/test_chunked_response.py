# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0
"""
Test for supporting streamed responses (Transfer-Encoding: chunked)
"""
from __future__ import print_function, unicode_literals

import pytest
import requests

from cachecontrol import CacheControl


@pytest.fixture()
def sess():
    sess = CacheControl(requests.Session())
    yield sess

    # closing session object
    sess.close()


class TestChunkedResponses(object):

    def test_cache_chunked_response(self, url, sess):
        """
        Verify that an otherwise cacheable response is cached when the
        response is chunked.
        """
        url = url + "stream"
        r = sess.get(url)
        from pprint import pprint

        pprint(dict(r.headers))
        pprint(dict(r.request.headers))
        print(r.content)
        assert r.headers.get("transfer-encoding") == "chunked"

        r = sess.get(url, headers={"Cache-Control": "max-age=3600"})
        assert r.from_cache is True

    def test_stream_is_cached(self, url, sess):
        resp_1 = sess.get(url + "stream")
        content_1 = resp_1.content

        resp_2 = sess.get(url + "stream")
        content_2 = resp_1.content

        assert not resp_1.from_cache
        assert resp_2.from_cache
        assert content_1 == content_2

    def test_stream_is_not_cached_when_content_is_not_read(self, url, sess):
        sess.get(url + "stream", stream=True)
        resp = sess.get(url + "stream", stream=True)

        assert not resp.from_cache
