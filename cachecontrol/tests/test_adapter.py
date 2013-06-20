import pytest

from requests import Session
from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.cache import DictCache


class TestCacheControlAdapter(object):

    @pytest.fixture()
    def url(self, server):
        """Use the url fixture to do setup for each test. We want to
        reuse the server fixture.

        Probably a better way to do this...
        """
        url = server.application_url + 'max_age'
        self.cache = DictCache()
        self.sess = Session()
        self.sess.mount('http://', CacheControlAdapter(self.cache))
        self.sess.get(url)
        return url

    def test_get_caches(self, url):
        r2 = self.sess.get(url)
        assert r2.from_cache is True

    def test_get_with_no_cache_does_not_cache(self, url):
        r2 = self.sess.get(url, headers={'Cache-Control': 'no-cache'})
        assert not hasattr(r2, 'from_cache')

    def test_put_invalidates_cache(self, url):
        r2 = self.sess.put(url, data={'foo': 'bar'})
        self.sess.get(url)
        assert not hasattr(r2, 'from_cache')

    def test_delete_invalidates_cache(self, url):
        r2 = self.sess.delete(url)
        self.sess.get(url)
        assert not hasattr(r2, 'from_cache')
        
        
