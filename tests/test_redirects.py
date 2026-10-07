# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
Test for supporting redirect caches as needed.
"""

import requests

from cachecontrol import CacheControl


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
        first = self.sess.get(url + "multiple_choices", allow_redirects=False)
        assert first.status_code == 300
        assert not first.from_cache

        resp = self.sess.get(url + "multiple_choices", allow_redirects=False)

        assert resp.status_code == 300
        assert resp.from_cache
        assert resp.content == first.content

    def test_bust_cache_on_redirect(self, url):
        self.sess.get(url + "multiple_choices", allow_redirects=False)

        cached = self.sess.get(url + "multiple_choices", allow_redirects=False)
        assert cached.status_code == 300
        assert cached.from_cache

        resp = self.sess.get(
            url + "multiple_choices",
            headers={"cache-control": "no-cache"},
            allow_redirects=False,
        )

        assert resp.status_code == 300
        assert not resp.from_cache
