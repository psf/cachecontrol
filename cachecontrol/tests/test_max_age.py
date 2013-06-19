from __future__ import print_function
from .. import CacheControl
import requests


class TestMaxAge(object):

    def setup(self):
        self.s = requests.Session()
        self.c = CacheControl(self.s, {})

    def test_client_max_age_0(self, server):
        """
        Making sure when the client uses max-age=0 we don't get a
        cached copy even though we're still fresh.
        """
        url = server.application_url + 'max_age'
        print('first request')
        r = self.c.get(url)
        cache_url = self.c.controller.cache_url(url)
        assert self.c.cache.get(cache_url) == r

        print('second request')
        r = self.c.get(url, headers={'Cache-Control': 'max-age=0'})

        # don't remove from the cache
        assert self.c.cache.get(cache_url)
        assert r.from_cache is False

    def test_client_max_age_3600(self, server):
        """
        Verify we get a cached value when the client has a
        reasonable max-age value.
        """
        # prep our cache
        url = server.application_url + 'max_age'
        r = self.c.get(url)
        cache_url = self.c.controller.cache_url(url)
        assert self.c.cache.get(cache_url) == r

        # request that we don't want a new one unless
        r = self.c.get(url, headers={'Cache-Control': 'max-age=3600'})
        assert r.from_cache is True

        # now lets grab one that forces a new request b/c the cache
        # has expired. To do that we'll inject a new time value.
        resp = self.c.cache.get(cache_url)
        resp.headers['date'] = 'Tue, 15 Nov 1994 08:12:31 GMT'
        r = self.c.get(url)
        assert r.from_cache is False
