from mock import Mock

from requests import Session, get
from cachecontrol import CacheControl
from cachecontrol.heuristics import OneDayCache, ExpiresAfter

from pprint import pprint


class TestUseExpiresHeuristic(object):

    def test_expires_heuristic_arg(self):
        sess = Session()
        cached_sess = CacheControl(sess, heuristic=Mock())
        assert cached_sess


class TestOneDayCache(object):

    def setup(self):
        self.sess = Session()
        self.cached_sess = CacheControl(
            self.sess, heuristic=OneDayCache()
        )

    def test_cache_for_one_day(self, url):
        the_url = url + 'optional_cacheable_request'
        r = self.sess.get(the_url)

        assert 'expires' in r.headers
        assert 'warning' in r.headers

        pprint(dict(r.headers))

        r = self.sess.get(the_url)
        pprint(dict(r.headers))
        assert r.from_cache


class TestExpiresAfter(object):

    def setup(self):
        self.sess = Session()
        self.cache_sess = CacheControl(
            self.sess, heuristic=ExpiresAfter(days=1)
        )

    def test_expires_after_one_day(self, url):
        the_url = url + 'no_cache'
        resp = get(the_url)
        assert resp.headers['cache-control'] == 'no-cache'

        r = self.sess.get(the_url)

        assert 'expires' in r.headers
        assert 'warning' in r.headers
        assert r.headers['cache-control'] == 'public'

        r = self.sess.get(the_url)
        assert r.from_cache
