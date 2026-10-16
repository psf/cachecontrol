# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests that verify our caching methods work correctly.
"""

import logging
import os
import time
from unittest.mock import ANY, Mock

import pytest
from urllib3 import HTTPResponse

from cachecontrol import CacheController
from cachecontrol.cache import DictCache
from cachecontrol.caches import SeparateBodyFileCache
from cachecontrol.serialize import Serializer

from .utils import DummyRequest, DummyResponse, NullSerializer

TIME_FMT = "%a, %d %b %Y %H:%M:%S GMT"


class TestCacheControllerResponse:
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

    def test_no_cache_with_malformed_date(self, cc):
        # An unparseable date must not crash; treat it like a missing date
        resp = self.resp({"cache-control": "max-age=3600", "date": "garbage"})
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

    def test_cache_control_directives_case_insensitive(self, cc):
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = self.resp({"cache-control": "No-Store, max-age=3600", "date": now})

        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_cache_response_no_store_with_etag(self, cc):
        resp = self.resp({"cache-control": "no-store", "ETag": "jfd9094r808"})
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_cache_response_expires_in_future(self, cc):
        now = time.time()
        resp = self.resp(
            {
                "date": time.strftime(TIME_FMT, time.gmtime(now)),
                "expires": time.strftime(TIME_FMT, time.gmtime(now + 3600)),
            }
        )
        cc.cache_response(self.req(), resp)

        cc.cache.set.assert_called_with(self.url, ANY, expires=3600)

    @pytest.mark.parametrize(
        "expires",
        [
            # RFC 9111 4.2.1: freshness lifetime is Expires - Date, which the
            # origin is free to make negative to force revalidation.
            "past",
            # RFC 9111 5.3: an invalid Expires means "already expired".
            "0",
            "garbage",
        ],
    )
    def test_cache_response_expires_in_past_not_cached(self, cc, expires):
        now = time.time()
        if expires == "past":
            expires = time.strftime(TIME_FMT, time.gmtime(now - 3600))
        resp = self.resp(
            {"date": time.strftime(TIME_FMT, time.gmtime(now)), "expires": expires}
        )
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_cache_response_expires_in_past_purges_existing_entry(self):
        now = time.time()
        cache = DictCache({self.url: b"stale"})
        cc = CacheController(cache, serializer=Mock())

        resp = self.resp(
            {
                "date": time.strftime(TIME_FMT, time.gmtime(now)),
                "expires": time.strftime(TIME_FMT, time.gmtime(now - 3600)),
            }
        )
        cc.cache_response(self.req(), resp)

        assert cc.cache.get(self.url) is None

    @pytest.mark.parametrize("expires_time", [0, -1, -3600])
    def test_cache_set_never_passes_non_positive_expires(self, cc, expires_time):
        """``_cache_set`` is the only chokepoint into ``BaseCache.set``.

        Backends may therefore assume ``expires`` is either None or strictly
        positive; a non-positive deadline must purge instead of store.
        """
        cc._cache_set(self.url, self.req(), self.resp(), b"testing", expires_time)

        assert not cc.cache.set.called
        cc.cache.delete.assert_called_with(self.url)

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
        resp = DummyResponse(
            status=304,
            headers={
                "ETag": "xyz",
                "x-value": "b",
                "Date": time.strftime(TIME_FMT, time.gmtime()),
                "Cache-Control": "max-age=60",
                "Content-Length": "200",
            },
        )
        # First, ensure the response from update_cached_response() matches the
        # cached one:
        result = cc.update_cached_response(req, resp)
        assert result is resp

    def test_update_cached_response_with_valid_headers_separate_body(self, tmp_path):
        """
        If the local cache has the given URL ``update_cached_response()`` will:

        1. Load the body from the cache.
        2. Update the stored headers to match the returned response.

        This is the version for a cache that stores a separate body.
        """
        cache = SeparateBodyFileCache(os.fsdecode(tmp_path))
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
        # Cache starts out prepopulated with an entry:
        etag = "jfd9094r808"
        cc = CacheController(cache)
        url = "http://localhost:123/x"
        req = DummyRequest(url=url, headers={})
        cached_resp = DummyResponse(
            status=200,
            headers={
                "ETag": etag,
                "x-value:": "a",
                "Content-Length": "100",
                "Cache-Control": "max-age=60",
                "Date": time.strftime(TIME_FMT, time.gmtime()),
            },
        )
        cc._cache_set(url, req, cached_resp, b"my body")

        # Now we get another request, and it's a 304, with new value for
        # `x-value` header.

        # Set our content length to 200. That would be a mistake in
        # the server, but we'll handle it gracefully... for now.
        req = DummyRequest(url=url, headers={"if-match": etag})
        resp = DummyResponse(
            status=304,
            headers={
                "ETag": etag,
                "x-value": "b",
                "Date": time.strftime(TIME_FMT, time.gmtime()),
                "Cache-Control": "max-age=60",
                "Content-Length": "200",
            },
        )
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


class TestCacheControlRequest:
    url = "http://foo.com/bar"

    def setup_method(self):
        self.c = CacheController(DictCache(), serializer=NullSerializer())

    def req(self, headers):
        mock_request = Mock(url=self.url, headers=headers)
        return self.c.cached_request(mock_request)

    def test_cache_request_no_headers(self):
        cached_resp = Mock(
            headers={"ETag": "jfd9094r808", "Content-Length": 100}, status=200
        )
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

    def test_cache_request_stale_age_header_not_returned(self, monkeypatch):
        now = 1_700_000_020
        monkeypatch.setattr(time, "time", lambda: now)
        date = time.strftime(TIME_FMT, time.gmtime(now - 5))
        # RFC 9111 section 4.2.3: corrected age must account for Age as well
        # as apparent age from Date when the two estimates differ.
        resp = Mock(
            headers={"cache-control": "max-age=60", "date": date, "age": "120"},
            status=200,
        )
        self.c.cache = DictCache({self.url: resp})

        assert self.req({}) is False

    def test_legacy_age_with_min_fresh_logs_without_integer_formatting(self, caplog):
        now = 1_700_000_020
        date = time.strftime(TIME_FMT, time.gmtime(now - 5))
        resp = Mock(
            headers={"cache-control": "max-age=60", "date": date, "age": "120"},
            status=200,
        )
        self.c.cache = DictCache({self.url: resp})

        with caplog.at_level(logging.DEBUG, logger="cachecontrol.controller"):
            assert not self.req({"cache-control": "min-fresh=1"})

        adjusted_age = next(
            record
            for record in caplog.records
            if record.msg == "Adjusted current age from min-fresh: %s"
        )
        assert adjusted_age.getMessage().endswith("inf")

    def test_cached_age_advances_after_storage_and_between_hits(self, monkeypatch):
        response_time = 1_700_000_000.0
        monkeypatch.setattr(time, "time", lambda: response_time)
        future_date = time.strftime(TIME_FMT, time.gmtime(response_time + 60))
        response = HTTPResponse(
            body=b"body",
            status=200,
            headers={
                "Cache-Control": "max-age=30",
                "Date": future_date,
                "Age": "10",
            },
        )
        response._cachecontrol_response_time = response_time
        response._cachecontrol_response_delay = 2.5
        request = DummyRequest(self.url, {})
        cache = DictCache()
        controller = CacheController(cache, serializer=Serializer())
        controller._cache_set(self.url, request, response, b"body")

        monkeypatch.setattr(time, "time", lambda: response_time + 7)
        first = controller.cached_request(request)
        assert first is not False
        assert first.headers["Age"] == "19"

        monkeypatch.setattr(time, "time", lambda: response_time + 12)
        second = controller.cached_request(request)
        assert second is not False
        assert second.headers["Age"] == "24"

    def test_min_fresh_does_not_change_emitted_age(self, monkeypatch):
        now = 1_700_000_020.0
        monkeypatch.setattr(time, "time", lambda: now)
        date = time.strftime(TIME_FMT, time.gmtime(now))
        request = DummyRequest(self.url, {"Cache-Control": "min-fresh=5"})
        response = HTTPResponse(
            body=b"body",
            status=200,
            headers={
                "Cache-Control": "max-age=20",
                "Date": date,
                "Age": "10",
            },
        )
        cache = DictCache()
        controller = CacheController(cache, serializer=Serializer())
        controller._cache_set(self.url, request, response, b"body")

        cached = controller.cached_request(request)

        assert cached is not False
        assert cached.headers["Age"] == "10"

    @pytest.mark.parametrize(
        ("age", "expected_age", "valid", "overflow"),
        [
            ("12, 99", 12, True, False),
            ("-1", 0, False, False),
            ("invalid", 0, False, False),
            (str(2**31 - 1), 2**31 - 1, True, False),
            (str(2**31), 2**31, True, True),
            (str(2**40), 2**31, True, True),
            ("0" * 5000, 0, True, False),
            ("0" * 5000 + "7", 7, True, False),
        ],
    )
    def test_parse_age_header(self, age, expected_age, valid, overflow):
        assert CacheController._parse_age({"Age": age}) == (
            expected_age,
            valid,
            overflow,
        )

    def test_oversized_age_cannot_be_fresh_against_larger_max_age(self, monkeypatch):
        now = 1_700_000_020.0
        monkeypatch.setattr(time, "time", lambda: now)
        date = time.strftime(TIME_FMT, time.gmtime(now))
        request = DummyRequest(self.url, {})
        response = HTTPResponse(
            body=b"body",
            status=200,
            headers={
                "Cache-Control": "max-age=4000000000",
                "Date": date,
                "Age": "6000000000",
                "ETag": '"v1"',
            },
        )
        cache = DictCache()
        controller = CacheController(cache, serializer=Serializer())
        controller._cache_set(self.url, request, response, b"body")

        assert controller.cached_request(request) is False

    def test_saturated_age_cannot_use_permanent_redirect_fallback(self, monkeypatch):
        now = 1_700_000_020.0
        monkeypatch.setattr(time, "time", lambda: now)
        date = time.strftime(TIME_FMT, time.gmtime(now))
        request = DummyRequest(self.url, {})
        response = HTTPResponse(
            body=b"body",
            status=301,
            headers={
                "Date": date,
                "Age": str(2**31),
                "ETag": '"v1"',
            },
        )
        cache = DictCache()
        controller = CacheController(cache, serializer=Serializer())
        controller._cache_set(self.url, request, response, b"body")

        assert controller.cached_request(request) is False

    def test_computed_age_saturates_to_infinity_marker(self):
        now = 1_700_000_020.0
        initial_age, overflow = CacheController._initial_age(
            {},
            now,
            1.0,
            age_headers={"Age": str(2**31 - 1)},
        )

        assert initial_age == 2**31
        assert overflow is True

    @pytest.mark.parametrize(
        ("validation_age", "validation_delay", "date_offset", "expected_age"),
        [(None, 3.0, 0, 3), ("20", 2.0, 3, 22)],
    )
    def test_304_refreshes_age_from_validation_response(
        self,
        monkeypatch,
        validation_age,
        validation_delay,
        date_offset,
        expected_age,
    ):
        now = 1_700_000_020.0
        monkeypatch.setattr(time, "time", lambda: now)
        date = time.strftime(TIME_FMT, time.gmtime(now))
        validation_date = time.strftime(TIME_FMT, time.gmtime(now - date_offset))
        request = DummyRequest(self.url, {"If-None-Match": '"v1"'})
        cache = DictCache()
        controller = CacheController(cache, serializer=Serializer())
        original = HTTPResponse(
            body=b"body",
            status=200,
            headers={
                "Cache-Control": "max-age=60",
                "Date": date,
                "ETag": '"v1"',
                "Age": "800",
            },
        )
        controller._cache_set(self.url, request, original, b"body")

        validation_headers = {
            "Cache-Control": "max-age=60",
            "Date": validation_date,
            "ETag": '"v1"',
        }
        if validation_age is not None:
            validation_headers["Age"] = validation_age
        not_modified = HTTPResponse(
            body=b"",
            status=304,
            headers=validation_headers,
        )
        not_modified._cachecontrol_response_time = now
        not_modified._cachecontrol_response_delay = validation_delay
        refreshed = controller.update_cached_response(request, not_modified)
        assert refreshed.headers["Age"] == str(expected_age)

        monkeypatch.setattr(time, "time", lambda: now + 4)
        cached = controller.cached_request(request)
        assert cached is not False
        assert cached.headers["Age"] == str(expected_age + 4)
        assert cached.read() == b"body"

    def test_304_saturated_age_is_emitted_and_remains_stale(self, monkeypatch):
        now = 1_700_000_020.0
        monkeypatch.setattr(time, "time", lambda: now)
        date = time.strftime(TIME_FMT, time.gmtime(now))
        request = DummyRequest(self.url, {"If-None-Match": '"v1"'})
        cache = DictCache()
        controller = CacheController(cache, serializer=Serializer())
        original = HTTPResponse(
            body=b"body",
            status=200,
            headers={
                "Cache-Control": "max-age=4000000000",
                "Date": date,
                "ETag": '"v1"',
            },
        )
        controller._cache_set(self.url, request, original, b"body")

        not_modified = HTTPResponse(
            body=b"",
            status=304,
            headers={
                "Cache-Control": "max-age=4000000000",
                "Date": date,
                "Age": "6000000000",
            },
        )
        not_modified._cachecontrol_response_time = now
        refreshed = controller.update_cached_response(request, not_modified)
        assert refreshed.headers["Age"] == str(2**31)

        monkeypatch.setattr(time, "time", lambda: now + 1)
        assert controller.cached_request(request) is False

    def test_cache_request_unfresh_max_age(self):
        earlier = time.time() - 3700  # epoch - 1h01m40s
        now = time.strftime(TIME_FMT, time.gmtime(earlier))
        resp = Mock(headers={"cache-control": "max-age=3600", "date": now}, status=200)
        self.c.cache = DictCache({self.url: resp})
        r = self.req({})
        assert not r

    def test_cache_request_unfresh_permanent_redirect(self):
        earlier = time.time() - 3600
        date = time.strftime(TIME_FMT, time.gmtime(earlier))
        resp = Mock(headers={"cache-control": "max-age=1", "date": date}, status=301)
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

    def test_cached_request_with_malformed_date_not_returned(self):
        # A cached entry with an unparseable date must not crash the lookup
        resp = Mock(
            headers={"cache-control": "max-age=3600", "date": "garbage"}, status=200
        )

        self.c.cache = DictCache({self.url: resp})

        assert not self.req({})
