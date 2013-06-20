"""
Unit tests that verify our caching methods work correctly.
"""
import pytest
import mock
import datetime
import time

from cachecontrol import CacheController
from cachecontrol.cache import DictCache


TIME_FMT = "%a, %d %b %Y %H:%M:%S"


class TestCacheControllerResponse(object):
    url = 'http://url.com/'

    def req(self, headers=None):
        headers = headers or {}
        return mock.Mock(full_url=self.url,  # < 1.x support
                         url=self.url,
                         headers=headers)

    def resp(self, headers=None):
        headers = headers or {}
        return mock.Mock(status_code=200,
                         headers=headers,
                         request=self.req())

    @pytest.fixture()
    def cc(self):
        # Cache controller fixture
        return CacheController(mock.Mock())

    def test_no_cache_non_20x_response(self, cc):
        # No caching without some extra headers, so we add them
        now = datetime.datetime.utcnow().strftime(TIME_FMT)
        resp = self.resp({'cache-control': 'max-age=3600',
                          'date': now})

        no_cache_codes = [201, 300, 400, 500]
        for code in no_cache_codes:
            resp.status_code = code
            cc.cache_response(resp)
            assert not cc.cache.set.called

        # this should work b/c the resp is 20x
        resp.status_code = 203
        cc.cache_response(resp)
        assert cc.cache.set.called

    def test_no_cache_with_no_date(self, cc):
        # No date header which makes our max-age pointless
        resp = self.resp({'cache-control': 'max-age=3600'})
        cc.cache_response(resp)

        assert not cc.cache.set.called

    def test_cache_response_no_cache_control(self, cc):
        resp = self.resp()
        cc.cache_response(resp)

        assert not cc.cache.set.called

    def test_cache_response_cache_max_age(self, cc):

        now = datetime.datetime.utcnow().strftime(TIME_FMT)
        resp = self.resp({'cache-control': 'max-age=3600',
                          'date': now})
        cc.cache_response(resp)
        cc.cache.set.assert_called_with(self.url, resp)

    def test_cache_repsonse_no_store(self):
        resp = mock.Mock()
        cache = DictCache({self.url: resp})
        cc = CacheController(cache)

        cache_url = cc.cache_url(self.url)

        resp = self.resp({'cache-control': 'no-store'})
        assert cc.cache.get(cache_url)

        cc.cache_response(resp)
        assert not cc.cache.get(cache_url)


class TestCacheControlRequest(object):
    url = 'http://foo.com/bar'

    def setup(self):
        self.c = CacheController(DictCache())

    def req(self, headers):
        return self.c.cached_request(self.url, headers=headers)

    def test_cache_request_no_cache(self):
        resp = self.req({'cache-control': 'no-cache'})
        assert not resp

    def test_cache_request_pragma_no_cache(self):
        resp = self.req({'pragma': 'no-cache'})
        assert not resp

    def test_cache_request_no_store(self):
        resp = self.req({'cache-control': 'no-store'})
        assert not resp

    def test_cache_request_max_age_0(self):
        resp = self.req({'cache-control': 'max-age=0'})
        assert not resp

    def test_cache_request_not_in_cache(self):
        resp = self.req({})
        assert not resp

    def test_cache_request_fresh_max_age(self):
        now = datetime.datetime.utcnow().strftime(TIME_FMT)
        resp = mock.Mock(headers={'cache-control': 'max-age=3600',
                                  'date': now})

        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert r == resp

    def test_cache_request_unfresh_max_age(self):
        earlier = time.time() - 3700
        now = datetime.datetime.fromtimestamp(earlier).strftime(TIME_FMT)

        resp = mock.Mock(headers={'cache-control': 'max-age=3600',
                                  'date': now})
        self.c.cache = DictCache({self.url: resp})
        r = self.req({})
        assert not r

    def test_cache_request_fresh_expires(self):
        later = datetime.timedelta(days=1)
        expires = (datetime.datetime.utcnow() + later).strftime(TIME_FMT)
        now = datetime.datetime.utcnow().strftime(TIME_FMT)
        resp = mock.Mock(headers={'expires': expires,
                                  'date': now})
        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert r == resp

    def test_cache_request_unfresh_expires(self):
        later = datetime.timedelta(days=-1)
        expires = (datetime.datetime.utcnow() + later).strftime(TIME_FMT)
        now = datetime.datetime.utcnow().strftime(TIME_FMT)
        resp = mock.Mock(headers={'expires': expires,
                                  'date': now})
        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert not r
