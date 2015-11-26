"""
Test for supporting streamed responses (Transfer-Encoding: chunked)
"""
import requests

from cachecontrol import CacheControl


class TestStream(object):
    def test_stream_is_cached(self, url):
        sess = CacheControl(requests.Session())

        resp_1 = sess.get(url + 'stream')
        content_1 = resp_1.content

        resp_2 = sess.get(url + 'stream')
        content_2 = resp_1.content

        assert not resp_1.from_cache
        assert resp_2.from_cache
        assert content_1 == content_2

    def test_stream_is_not_cached_when_content_is_not_read(self, url):
        sess = CacheControl(requests.Session())
        sess.get(url + 'stream', stream=True)
        resp = sess.get(url + 'stream', stream=True)

        assert not resp.from_cache
