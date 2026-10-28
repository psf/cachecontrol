# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from requests import Session
from cachecontrol import CacheControl
from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.cache import DictCache
from .utils import NullSerializer


class TestMaxAge:
    @pytest.fixture()
    def sess(self, url):
        self.url = url
        self.cache = DictCache()
        sess = Session()
        sess.mount(
            "http://", CacheControlAdapter(self.cache, serializer=NullSerializer())
        )
        return sess

    @pytest.mark.parametrize("value", ["0", '"0"'])
    def test_client_max_age_0(self, sess, value):
        """
        Making sure when the client uses max-age=0 we don't get a
        cached copy even though we're still fresh.
        """
        print("first request")
        r = sess.get(self.url)
        assert self.cache.get(self.url) == r.raw

        print("second request")
        r = sess.get(self.url, headers={"Cache-Control": f"max-age={value}"})

        # don't remove from the cache
        assert self.cache.get(self.url)
        assert not r.from_cache

    @pytest.mark.parametrize("path", ["cache_60", "cache_60_quoted"])
    def test_server_max_age(self, url, path):
        with CacheControl(Session()) as sess:
            response = sess.get(url + path)
            assert response.from_cache is False
            body = response.content

            response = sess.get(url + path)
            assert response.from_cache is True
            assert response.content == body

    def test_client_max_age_3600(self, sess):
        """
        Verify we get a cached value when the client has a
        reasonable max-age value.
        """
        r = sess.get(self.url)
        assert self.cache.get(self.url) == r.raw

        # request that we don't want a new one unless
        r = sess.get(self.url, headers={"Cache-Control": "max-age=3600"})
        assert r.from_cache is True

        # now lets grab one that forces a new request b/c the cache
        # has expired. To do that we'll inject a new time value.
        resp = self.cache.get(self.url)
        resp.headers["date"] = "Tue, 15 Nov 1994 08:12:31 GMT"
        r = sess.get(self.url)
        assert not r.from_cache
