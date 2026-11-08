# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests that verify our caching methods work correctly.
"""

import os
import time
from pathlib import Path
from typing import IO
from unittest.mock import ANY, Mock

import pytest
from requests import PreparedRequest, Request
from urllib3 import HTTPResponse

from cachecontrol import CacheController
from cachecontrol.cache import DictCache
from cachecontrol.caches import SeparateBodyFileCache
from cachecontrol.serialize import Serializer

from .utils import DummyRequest, DummyResponse, NullSerializer

TIME_FMT = "%a, %d %b %Y %H:%M:%S GMT"


class TrackingSeparateBodyFileCache(SeparateBodyFileCache):
    def __init__(self, directory: str) -> None:
        super().__init__(directory)
        self.opened_bodies: list[IO[bytes]] = []

    def get_body(self, key: str) -> IO[bytes] | None:
        body = super().get_body(key)
        if body is not None:
            self.opened_bodies.append(body)
        return body

    def delete(self, key: str) -> None:
        assert all(body.closed for body in self.opened_bodies)
        super().delete(key)


class RetainingSerializer(Serializer):
    """Keep loaded responses alive so tests do not rely on refcounting."""

    def __init__(self) -> None:
        self.loaded_responses: list[HTTPResponse] = []

    def loads(
        self,
        request: PreparedRequest,
        data: bytes,
        body_file: IO[bytes] | None = None,
    ) -> HTTPResponse | None:
        response = super().loads(request, data, body_file)
        if response is not None:
            self.loaded_responses.append(response)
        return response


def make_separate_body_response(
    tmp_path: Path,
    *,
    response_headers: dict[str, str] | None = None,
    request_headers: dict[str, str] | None = None,
) -> tuple[CacheController, TrackingSeparateBodyFileCache, PreparedRequest]:
    cache = TrackingSeparateBodyFileCache(os.fsdecode(tmp_path))
    controller = CacheController(cache, serializer=RetainingSerializer())
    request = Request(
        "GET", "https://example.test/simple/project/", headers=request_headers
    ).prepare()
    response = HTTPResponse(
        body=b"old body",
        headers={
            "cache-control": "max-age=0",
            "date": time.strftime(TIME_FMT, time.gmtime()),
            **(response_headers or {}),
        },
        status=200,
    )
    assert request.url is not None
    controller._cache_set(request.url, request, response, b"old body")
    return controller, cache, request


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

    def test_cache_response_preserves_userinfo_case(self):
        cache = DictCache({})
        cc = CacheController(cache)
        url = "http://Alice:Secret@localhost/"
        req = DummyRequest(url=url, headers={})
        resp = DummyResponse(status=200, headers={"ETag": "xyz"})
        cc.cache_response(req, resp, b"")

        req = DummyRequest(
            url="http://alice:secret@localhost/", headers={"if-match": "xyz"}
        )
        result = cc.conditional_headers(req)

        assert not result

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


class TestSeparateBodyLifetime:
    @pytest.mark.parametrize(
        "response_headers",
        [
            {},
            {"etag": '"old"'},
            {"cache-control": "max-age=60", "date": "invalid", "etag": '"old"'},
        ],
        ids=["stale", "stale-etag", "invalid-date"],
    )
    def test_rejected_cached_response_closes_body(
        self, tmp_path: Path, response_headers: dict[str, str]
    ) -> None:
        controller, cache, request = make_separate_body_response(
            tmp_path, response_headers=response_headers
        )

        assert controller.cached_request(request) is False
        assert cache.opened_bodies[-1].closed

    def test_conditional_headers_close_body(self, tmp_path: Path) -> None:
        controller, cache, request = make_separate_body_response(
            tmp_path, response_headers={"etag": '"old"'}
        )

        assert controller.conditional_headers(request) == {"If-None-Match": '"old"'}
        assert cache.opened_bodies[-1].closed

    def test_invalid_serialization_closes_body(self, tmp_path: Path) -> None:
        controller, cache, request = make_separate_body_response(tmp_path)
        assert request.url is not None
        cache.set(request.url, b"invalid serialization")

        assert controller._load_from_cache(request) is None
        assert cache.opened_bodies[-1].closed

    def test_vary_mismatch_closes_body(self, tmp_path: Path) -> None:
        controller, cache, request = make_separate_body_response(
            tmp_path,
            request_headers={"Accept-Language": "en"},
            response_headers={"vary": "Accept-Language"},
        )
        request.headers["Accept-Language"] = "fr"

        assert controller._load_from_cache(request) is None
        assert cache.opened_bodies[-1].closed

    def test_returned_cached_response_owns_body(self, tmp_path: Path) -> None:
        controller, cache, request = make_separate_body_response(
            tmp_path, response_headers={"cache-control": "max-age=60"}
        )

        response = controller.cached_request(request)

        assert response is not False
        assert not cache.opened_bodies[-1].closed
        response.close()
        assert cache.opened_bodies[-1].closed


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
