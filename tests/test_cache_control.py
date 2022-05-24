# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests that verify our caching methods work correctly.
"""
import pytest
from mock import ANY, Mock
import time
from tempfile import mkdtemp

from cachecontrol import CacheController
from cachecontrol.cache import DictCache
from cachecontrol.caches import SeparateBodyFileCache
from .utils import NullSerializer, DummyResponse, DummyRequest

TIME_FMT = "%a, %d %b %Y %H:%M:%S GMT"



class TestCacheControllerResponse(object):
    url = "http://url.com/"

    def req(self, headers=None):
        headers = headers or {}
        return Mock(full_url=self.url, url=self.url, headers=headers)  # < 1.x support

    def resp(self, headers=None):
        headers = headers or {}
        return Mock(
            status=200, headers=headers, request=self.req(), read=lambda **k: b"testing"
        )

    @pytest.fixture()
    def cc(self):
        # Cache controller fixture
        return CacheController(Mock(), serializer=Mock())

    def test_no_cache_non_20x_response(self, cc):
        # No caching without some extra headers, so we add them
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = self.resp({"cache-control": "max-age=3600", "date": now})

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
        resp = self.resp({"cache-control": "max-age=3600"})
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_no_cache_with_wrong_sized_body(self, cc):
        # When the body is the wrong size, then we don't want to cache it
        # because it is obviously broken.
        resp = self.resp({"cache-control": "max-age=3600", "Content-Length": "5"})
        cc.cache_response(self.req(), resp, b"0" * 10)

        assert not cc.cache.set.called

    def test_cache_response_no_cache_control(self, cc):
        resp = self.resp()
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_cache_response_cache_max_age(self, cc):
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = self.resp({"cache-control": "max-age=3600", "date": now})
        req = self.req()
        cc.cache_response(req, resp)
        cc.serializer.dumps.assert_called_with(req, resp, None)
        cc.cache.set.assert_called_with(self.url, ANY, expires=3600)

    def test_cache_response_cache_max_age_with_invalid_value_not_cached(self, cc):
        now = time.strftime(TIME_FMT, time.gmtime())
        # Not a valid header; this would be from a misconfigured server
        resp = self.resp({"cache-control": "max-age=3600; public", "date": now})
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_cache_response_no_store(self):
        resp = Mock()
        cache = DictCache({self.url: resp})
        cc = CacheController(cache)

        cache_url = cc.cache_url(self.url)

        resp = self.resp({"cache-control": "no-store"})
        assert cc.cache.get(cache_url)

        cc.cache_response(self.req(), resp)
        assert not cc.cache.get(cache_url)

    def test_cache_response_no_store_with_etag(self, cc):
        resp = self.resp({"cache-control": "no-store", "ETag": "jfd9094r808"})
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_no_cache_with_vary_star(self, cc):
        # Vary: * indicates that the response can never be served
        # from the cache, so storing it can be avoided.
        resp = self.resp({"vary": "*"})
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_update_cached_response_no_local_cache(self):
        """
        If the local cache doesn't have the given URL, just reuse the response
        passed to ``update_cached_response()``
        """
        cache = DictCache({})
        cc = CacheController(cache)
        req = DummyRequest(url="http://localhost/", headers={"if-match": "xyz"})
        resp = DummyResponse(status=304, headers={
            "ETag": "xyz",
            "x-value": "b",
            "Date": time.strftime(TIME_FMT, time.gmtime()),
            "Cache-Control": "max-age=60",
            "Content-Length": "200"
        })
        # First, ensure the response from update_cached_response() matches the
        # cached one:
        result = cc.update_cached_response(req, resp)
        assert result is resp

    def test_update_cached_response_with_valid_headers_separate_body(self):
        """
        If the local cache has the given URL ``update_cached_response()`` will:

        1. Load the body from the cache.
        2. Update the stored headers to match the returned response.

        This is the version for a cache that stores a separate body.
        """
        cache = SeparateBodyFileCache(mkdtemp())
        self.update_cached_response_with_valid_headers_test(cache)

    def test_update_cached_response_with_valid_headers(self):
        """
        If the local cache has the given URL ``update_cached_response()`` will:

        1. Load the body from the cache.
        2. Update the stored headers to match the returned response.

        This is the version for non-separate body.
        """
        cache = DictCache({})
        self.update_cached_response_with_valid_headers_test(cache)

    def update_cached_response_with_valid_headers_test(self, cache):
        """
        If the local cache has the given URL ``update_cached_response()`` will:

        1. Load the body from the cache.
        2. Update the stored headers to match the returned response.

        This is the shared utility for any cache object.
        """
        # Cache starts out prepopulated wih an entry:
        etag = "jfd9094r808"
        cc = CacheController(cache)
        url = "http://localhost:123/x"
        req = DummyRequest(url=url, headers={})
        cached_resp = DummyResponse(status=200, headers={
            "ETag": etag,
            "x-value:": "a",
            "Content-Length": "100",
            "Cache-Control": "max-age=60",
            "Date": time.strftime(TIME_FMT, time.gmtime()),
        })
        cc._cache_set(url, req, cached_resp, b"my body")

        # Now we get another request, and it's a 304, with new value for
        # `x-value` header.

        # Set our content length to 200. That would be a mistake in
        # the server, but we'll handle it gracefully... for now.
        req = DummyRequest(url=url, headers={"if-match": etag})
        resp = DummyResponse(status=304, headers={
            "ETag": etag,
            "x-value": "b",
            "Date": time.strftime(TIME_FMT, time.gmtime()),
            "Cache-Control": "max-age=60",
            "Content-Length": "200"
        })
        # First, ensure the response from update_cached_response() matches the
        # cached one:
        result = cc.update_cached_response(req, resp)
        # Second, ensure that the cache was updated:
        result2 = cc.cached_request(req)

        for r in [result, result2]:
            assert r.headers["ETag"] == etag
            assert r.headers["x-value"] == "b"
            assert r.headers["Content-Length"] == "100"
            assert r.read() == b"my body"


class TestCacheControlRequest(object):
    url = "http://foo.com/bar"

    def setup(self):
        self.c = CacheController(DictCache(), serializer=NullSerializer())

    def req(self, headers):
        mock_request = Mock(url=self.url, headers=headers)
        return self.c.cached_request(mock_request)

    def test_cache_request_no_headers(self):
        cached_resp = Mock(headers={"ETag": "jfd9094r808", "Content-Length": 100}, status=200)
        self.c.cache = DictCache({self.url: cached_resp})
        resp = self.req({})
        assert not resp

    def test_cache_request_no_cache(self):
        resp = self.req({"cache-control": "no-cache"})
        assert not resp

    def test_cache_request_pragma_no_cache(self):
        resp = self.req({"pragma": "no-cache"})
        assert not resp

    def test_cache_request_no_store(self):
        resp = self.req({"cache-control": "no-store"})
        assert not resp

    def test_cache_request_max_age_0(self):
        resp = self.req({"cache-control": "max-age=0"})
        assert not resp

    def test_cache_request_not_in_cache(self):
        resp = self.req({})
        assert not resp

    def test_cache_request_fresh_max_age(self):
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={"cache-control": "max-age=3600", "date": now}, status=200)

        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert r == resp

    def test_cache_request_unfresh_max_age(self):
        earlier = time.time() - 3700  # epoch - 1h01m40s
        now = time.strftime(TIME_FMT, time.gmtime(earlier))
        resp = Mock(headers={"cache-control": "max-age=3600", "date": now}, status=200)
        self.c.cache = DictCache({self.url: resp})
        r = self.req({})
        assert not r

    def test_cache_request_fresh_expires(self):
        later = time.time() + 86400  # GMT + 1 day
        expires = time.strftime(TIME_FMT, time.gmtime(later))
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={"expires": expires, "date": now}, status=200)
        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert r == resp

    def test_cache_request_unfresh_expires(self):
        sooner = time.time() - 86400  # GMT - 1 day
        expires = time.strftime(TIME_FMT, time.gmtime(sooner))
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={"expires": expires, "date": now}, status=200)
        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert not r

    def test_cached_request_with_bad_max_age_headers_not_returned(self):
        now = time.strftime(TIME_FMT, time.gmtime())
        # Not a valid header; this would be from a misconfigured server
        resp = Mock(headers={"cache-control": "max-age=xxx", "date": now}, status=200)

        self.c.cache = DictCache({self.url: resp})

        assert not self.req({})
