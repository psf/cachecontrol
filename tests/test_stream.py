"""
Test for supporting streamed responses (Transfer-Encoding: chunked)
"""
import requests

from cachecontrol import CacheControl


class TestStream(object):

    def setup(self):
        self.sess = CacheControl(requests.Session())

    def test_stream_is_cached(self, url):
        resp_1 = self.sess.get(url + "stream")
        content_1 = resp_1.content

        resp_2 = self.sess.get(url + "stream")
        content_2 = resp_1.content

        assert not resp_1.from_cache
        assert resp_2.from_cache
        assert content_1 == content_2
