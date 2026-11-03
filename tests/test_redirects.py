# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
Test for supporting redirect caches as needed.
"""

from unittest.mock import patch

import pytest
import requests
from urllib3 import HTTPResponse

from cachecontrol import CacheControl
from cachecontrol.adapter import CacheControlAdapter


class TestPermanentRedirects:
    def setup_method(self):
        self.sess = CacheControl(requests.Session())

    def test_redirect_response_is_cached(self, url):
        self.sess.get(url + "permanent_redirect", allow_redirects=False)

        resp = self.sess.get(url + "permanent_redirect", allow_redirects=False)
        assert resp.from_cache

    def test_bust_cache_on_redirect(self, url):
        self.sess.get(url + "permanent_redirect", allow_redirects=False)

        resp = self.sess.get(
            url + "permanent_redirect",
            headers={"cache-control": "no-cache"},
            allow_redirects=False,
        )
        assert not resp.from_cache


class TestMultipleChoicesRedirects:
    def setup_method(self):
        self.sess = CacheControl(requests.Session())

    def test_multiple_choices_is_cacheable(self, url):
        self.sess.get(url + "multiple_choices_redirect", allow_redirects=False)

        resp = self.sess.get(url + "multiple_choices_redirect", allow_redirects=False)

        assert resp.from_cache

    def test_bust_cache_on_redirect(self, url):
        self.sess.get(url + "multiple_choices_redirect", allow_redirects=False)

        resp = self.sess.get(
            url + "multiple_choices_redirect",
            headers={"cache-control": "no-cache"},
            allow_redirects=False,
        )

        assert not resp.from_cache


@pytest.mark.parametrize("status", [301, 308])
def test_revalidated_redirect_keeps_status(status):
    session = CacheControl(requests.Session())
    url = "https://example.test/old"
    headers = {
        "ETag": '"redirect"',
        "Location": "/new",
        "Date": "Tue, 03 Nov 2026 12:00:00 GMT",
        "Cache-Control": "max-age=0",
    }
    adapter = session.get_adapter(url)
    adapter.controller.cache_response(
        requests.Request("GET", url).prepare(),
        HTTPResponse(status=status, headers=headers, body=b""),
        body=b"",
    )

    def revalidate(self, request, *args, **kwargs):
        assert request.headers["If-None-Match"] == '"redirect"'
        return CacheControlAdapter.build_response(
            self, request, HTTPResponse(status=304, headers=headers, body=b"")
        )

    with patch("requests.adapters.HTTPAdapter.send", revalidate):
        response = session.get(url, allow_redirects=False)

    assert response.from_cache
    assert response.status_code == status
    assert response.is_redirect
    assert response.headers["Location"] == "/new"
    assert response.content == b""
