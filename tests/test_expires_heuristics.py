from mock import Mock

from requests import Session
from cachecontrol import CacheControl
from cachecontrol.heuristics import OneDayCache


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
        hurl = url + '/optional_cacheable_request'
        r = self.sess.get(hurl)

        assert 'expires' in r.headers
        assert 'warning' in r.headers

        r = self.sess.get(hurl)
        assert r.from_cache
