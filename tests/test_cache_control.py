"""
Unit tests that verify our caching methods work correctly.
"""
import pytest
from mock import ANY, Mock
import time
from random import shuffle
import string

from cachecontrol import CacheController
from cachecontrol.cache import DictCache


TIME_FMT = "%a, %d %b %Y %H:%M:%S GMT"


class NullSerializer(object):

    def dumps(self, request, response):
        return response

    def loads(self, request, data):
        return data


class TestCacheControllerResponse(object):
    url = 'http://url.com/'

    def req(self, headers=None):
        headers = headers or {}
        return Mock(full_url=self.url,  # < 1.x support
                    url=self.url,
                    headers=headers)

    def resp(self, headers=None):
        headers = headers or {}
        return Mock(status=200,
                    headers=headers,
                    request=self.req(),
                    read=lambda **k: b"testing")

    @pytest.fixture()
    def cc(self):
        # Cache controller fixture
        return CacheController(Mock(), serializer=Mock())

    def test_no_cache_non_20x_response(self, cc):
        # No caching without some extra headers, so we add them
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = self.resp({'cache-control': 'max-age=3600',
                          'date': now})

        no_cache_codes = [201, 400, 500]
        for code in no_cache_codes:
            resp.status = code
            cc.cache_response(Mock(), resp)
            assert not cc.cache.set.called

        # this should work b/c the resp is 20x
        resp.status = 203
        cc.cache_response(self.req(), resp)
        assert cc.serializer.dumps.called
        assert cc.cache.set.called

    def test_no_cache_with_no_date(self, cc):
        # No date header which makes our max-age pointless
        resp = self.resp({'cache-control': 'max-age=3600'})
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_no_cache_with_wrong_sized_body(self, cc):
        # When the body is the wrong size, then we don't want to cache it
        # because it is obviously broken.
        resp = self.resp({
            "cache-control": "max-age=3600",
            "Content-Length": "5",
        })
        cc.cache_response(self.req(), resp, body=b"0" * 10)

        assert not cc.cache.set.called

    def test_cache_response_no_cache_control(self, cc):
        resp = self.resp()
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_cache_response_cache_max_age(self, cc):
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = self.resp({'cache-control': 'max-age=3600',
                          'date': now})
        req = self.req()
        cc.cache_response(req, resp)
        cc.serializer.dumps.assert_called_with(req, resp, body=None)
        cc.cache.set.assert_called_with(self.url, ANY)

    def test_cache_response_cache_max_age_with_invalid_value_not_cached(self, cc):
        now = time.strftime(TIME_FMT, time.gmtime())
        # Not a valid header; this would be from a misconfigured server
        resp = self.resp({'cache-control': 'max-age=3600; public',
                          'date': now})
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_cache_response_no_store(self):
        resp = Mock()
        cache = DictCache({self.url: resp})
        cc = CacheController(cache)

        cache_url = cc.cache_url(self.url)

        resp = self.resp({'cache-control': 'no-store'})
        assert cc.cache.get(cache_url)

        cc.cache_response(self.req(), resp)
        assert not cc.cache.get(cache_url)

    def test_update_cached_response_with_valid_headers(self):
        cached_resp = Mock(headers={'ETag': 'jfd9094r808', 'Content-Length': 100})

        # Set our content length to 200. That would be a mistake in
        # the server, but we'll handle it gracefully... for now.
        resp = Mock(headers={'ETag': '28371947465', 'Content-Length': 200})
        cache = DictCache({self.url: cached_resp})

        cc = CacheController(cache)

        # skip our in/out processing
        cc.serializer = Mock()
        cc.serializer.loads.return_value = cached_resp
        cc.cache_url = Mock(return_value='http://foo.com')

        result = cc.update_cached_response(Mock(), resp)

        assert result.headers['ETag'] == resp.headers['ETag']
        assert result.headers['Content-Length'] == 100


class TestCacheControlRequest(object):
    url = 'http://foo.com/bar'

    def setup(self):
        self.c = CacheController(
            DictCache(),
            serializer=NullSerializer(),
        )

    def req(self, headers):
        mock_request = Mock(url=self.url, headers=headers)
        return self.c.cached_request(mock_request)

    def test_cache_request_no_headers(self):
        cached_resp = Mock(headers={'ETag': 'jfd9094r808', 'Content-Length': 100})
        self.c.cache = DictCache({self.url: cached_resp})
        resp = self.req({})
        assert not resp

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
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={'cache-control': 'max-age=3600',
                             'date': now})

        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert r == resp

    def test_cache_request_unfresh_max_age(self):
        earlier = time.time() - 3700  # epoch - 1h01m40s
        now = time.strftime(TIME_FMT, time.gmtime(earlier))
        resp = Mock(headers={'cache-control': 'max-age=3600',
                             'date': now})
        self.c.cache = DictCache({self.url: resp})
        r = self.req({})
        assert not r

    def test_cache_request_fresh_expires(self):
        later = time.time() + 86400  # GMT + 1 day
        expires = time.strftime(TIME_FMT, time.gmtime(later))
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={'expires': expires,
                             'date': now})
        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert r == resp

    def test_cache_request_unfresh_expires(self):
        sooner = time.time() - 86400  # GMT - 1 day
        expires = time.strftime(TIME_FMT, time.gmtime(sooner))
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={'expires': expires,
                             'date': now})
        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert not r

    def test_cached_request_with_bad_max_age_headers_not_returned(self):
        now = time.strftime(TIME_FMT, time.gmtime())
        # Not a valid header; this would be from a misconfigured server
        resp = Mock(headers={'cache-control': 'max-age=xxx',
                             'date': now})

        self.c.cache = DictCache({self.url: resp})

        assert not self.req({})

def test_cache_url_sorting():
    letter_n_numbers = list(enumerate(string.ascii_lowercase[3:], start=4))
    suff = '&' + '&'.join('%s=%s' % (k, v) for v, k in letter_n_numbers)

    def get_param(url):
        """Mock losing order when processing params"""
        shuffle(letter_n_numbers)
        params = {k: v for v, k in letter_n_numbers}
        url = url.replace(suff, '')
        query = '&' + '&'.join('%s=%s' % item for item in params.items())
        return url + query

    no_query = 'http://example.com'
    unsorted_query = 'http://example.com?b=2&c=3&a=1' + suff
    sorted_query = 'http://example.com?a=1&b=2&c=3' + suff

    cache_url = CacheController.cache_url
    assert cache_url(no_query, sort_query=True) == cache_url(no_query)
    assert cache_url(unsorted_query) != cache_url(sorted_query)
    assert cache_url(unsorted_query, True) == cache_url(sorted_query)
    randomized = get_param(unsorted_query)
    assert randomized != unsorted_query
    assert cache_url(randomized) != cache_url(sorted_query)
    assert cache_url(randomized, True) == cache_url(sorted_query)
    randomized_again = get_param(unsorted_query)
    assert cache_url(randomized, True) == cache_url(randomized_again, True)
