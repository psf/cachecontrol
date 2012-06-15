import mock
from .. import CacheControl
import requests


class TestCachingConditions(object):

    def test_no_caching_directives(self):
        url = 'http://localhost:8080/'
        s = requests.Session()
        c = CacheControl(s, {})
        r = c.get(url)

        assert r
        assert r.content == 'foo'
        assert url not in c.cache

    def test_cache_max_age(self):
        url = 'http://localhost:8080/max_age/'
        s = requests.Session()
        c = CacheControl(s, {})
        r = c.get(url)
        assert url in c.cache
        assert c.cache[url]['response'] == r
        assert c.cache[url]['max-age']

    def test_cache_no_cache(self):
        url = 'http://localhost:8080/no_cache/'
        s = requests.Session()
        c = CacheControl(s, {})
        c.get(url)
        assert url not in c.cache

    def test_cache_must_revalidate(self):
        url = 'http://localhost:8080/must_revalidate/'
        s = requests.Session()
        c = CacheControl(s, {})
        c.get(url)
        assert url not in c.cache


class TestMaxAge(object):

    def test_client_max_age_0(self):
        url = 'http://localhost:8080/max_age/'
        s = requests.Session()
        c = CacheControl(s, {})
        r = c.get(url)
        assert url in c.cache
        assert c.cache[url]['response'] == r
        assert c.cache[url]['max-age']

        r = c.get(url, headers={'Cache-Control': 'max-age=0'})

        # don't remove from the cache
        assert url in c.cache
        assert not r.from_cache == False

    def test_client_max_age_3600(self):
        # prep our cache
        url = 'http://localhost:8080/max_age/'
        s = requests.Session()
        c = CacheControl(s, {})
        r = c.get(url)
        assert url in c.cache
        assert c.cache[url]['response'] == r
        assert c.cache[url]['max-age']

        r = c.get(url, headers={'Cache-Control': 'max-age=3600'})

        assert r.from_cache == True
