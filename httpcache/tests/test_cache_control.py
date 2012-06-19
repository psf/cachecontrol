"""
Unit tests that verify our caching methods work correctly.
"""
import mock
import datetime
import time

from httpcache import CacheControl
from httpcache.cache import DictCache


TIME_FMT = "%a, %d %b %Y %H:%M:%S"


class TestCacheControlResponse(object):

    def test_cache_response_no_cache_control(self):
        c = CacheControl(mock.Mock(), mock.MagicMock())

        resp = mock.Mock(headers={})
        c.cache_response(resp)

        assert not c.cache.set.called

    def test_cache_response_cache_max_age(self):
        c = CacheControl(mock.Mock(), mock.MagicMock())

        now = datetime.datetime.utcnow().strftime(TIME_FMT)
        resp = mock.Mock(headers={'cache-control': 'max-age=3600',
                                  'date': now},
                         request=mock.Mock(full_url='http://url.com'))
        c.cache_response(resp)
        c.cache.set.assert_called_with('http://url.com/', resp)

    def test_cache_repsonse_no_store(self):
        url = 'http://foo.com/'
        resp = mock.Mock()
        cache = DictCache({url: resp})
        c = CacheControl(resp, cache)

        cache_url = c.cache_url(url)

        resp = mock.Mock(headers={'cache-control': 'no-store'},
                         request=mock.Mock(full_url=url))

        assert c.cache.get(cache_url)

        c.cache_response(resp)

        assert not c.cache.get(cache_url)


class TestCacheControlRequest(object):

    def test_cache_request_no_cache(self):
        url = 'http://foo.com'
        c = CacheControl(mock.Mock)
        resp = c.cached_request(url, headers={'cache-control': 'no-cache'})
        assert not resp

    def test_cache_request_max_age_0(self):
        url = 'http://foo.com'
        c = CacheControl(mock.Mock)
        resp = c.cached_request(url, headers={'cache-control': 'max-age=0'})
        assert not resp

    def test_cache_request_not_in_cache(self):
        url = 'http://foo.com'
        c = CacheControl(mock.Mock)
        resp = c.cached_request(url)
        assert not resp

    def test_cache_request_fresh_max_age(self):
        url = 'http://foo.com'
        now = datetime.datetime.utcnow().strftime(TIME_FMT)
        resp = mock.Mock(headers={'cache-control': 'max-age=3600',
                                  'date': now})
        cache = DictCache({'http://foo.com/': resp})
        c = CacheControl(mock.Mock, cache)
        r = c.cached_request(url)
        assert r == resp

    def test_cache_request_unfresh_max_age(self):
        url = 'http://foo.com'
        earlier = time.time() - 3700
        now = datetime.datetime.fromtimestamp(earlier).strftime(TIME_FMT)

        resp = mock.Mock(headers={'cache-control': 'max-age=3600',
                                  'date': now})
        cache = DictCache({'http://foo.com/': resp})
        c = CacheControl(mock.Mock, cache)
        r = c.cached_request(url)
        assert not r

    def test_cache_request_fresh_expires(self):
        url = 'http://foo.com'
        later = datetime.timedelta(days=1)
        expires = (datetime.datetime.utcnow() + later).strftime(TIME_FMT)
        now = datetime.datetime.utcnow().strftime(TIME_FMT)
        resp = mock.Mock(headers={'expires': expires,
                                  'date': now})
        cache = DictCache({'http://foo.com/': resp})
        c = CacheControl(mock.Mock, cache)
        r = c.cached_request(url)
        assert r == resp

    def test_cache_request_unfresh_expires(self):
        url = 'http://foo.com'
        later = datetime.timedelta(days=-1)
        expires = (datetime.datetime.utcnow() + later).strftime(TIME_FMT)
        now = datetime.datetime.utcnow().strftime(TIME_FMT)
        resp = mock.Mock(headers={'expires': expires,
                                  'date': now})
        cache = DictCache({'http://foo.com/': resp})
        c = CacheControl(mock.Mock, cache)
        r = c.cached_request(url)
        assert not r
