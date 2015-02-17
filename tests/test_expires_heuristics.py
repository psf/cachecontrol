from mock import Mock

from requests import Session, get
from cachecontrol import CacheControl
from cachecontrol.heuristics import OneDayCache, ExpiresAfter, HeuristicFreshness

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

from requests.structures import CaseInsensitiveDict
from email.utils import parsedate
from datetime import datetime

class DummyResponse:
    def __init__(self, status_code, headers):
        self.status_code = status_code
        self.headers = CaseInsensitiveDict(headers)

class TestHeuristicFreshness(object):
    def setup(self):
        self.heuristic = HeuristicFreshness()

    def test_no_expiry_is_inferred_when_no_last_modified_is_present(self):
        assert self.heuristic.update_headers(DummyResponse(200, {})) == {}

    def test_expires_is_not_replaced_when_present(self):
        resp = DummyResponse(200, {'Expires': 'Mon, 21 Jul 2014 17:45:39 GMT'})
        assert self.heuristic.update_headers(resp) == {}

    def test_last_modified_is_used(self):
        resp = DummyResponse(200, {'Last-Modified': 'Mon, 21 Jul 2014 17:45:39 GMT'})
        modified = self.heuristic.update_headers(resp)
        assert ['expires'] == list(modified.keys())
        assert datetime(*parsedate(modified['expires'])[:6]) > datetime.now()
