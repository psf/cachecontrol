"""
Test for supporting redirect caches as needed.
"""
import requests

from cachecontrol import CacheControl


class TestPermanentRedirects(object):

    def setup(self):
        self.sess = CacheControl(requests.Session())

    def test_redirect_response_is_cached(self, url):
        self.sess.get(url + 'permanent_redirect', allow_redirects=False)

        resp = self.sess.get(url + 'permanent_redirect',
                             allow_redirects=False)
        assert resp.from_cache

    def test_bust_cache_on_redirect(self, url):
        self.sess.get(url + 'permanent_redirect', allow_redirects=False)

        resp = self.sess.get(url + 'permanent_redirect',
                             headers={'cache-control': 'no-cache'},
                             allow_redirects=False)
        assert not resp.from_cache
