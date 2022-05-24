# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import print_function
import pytest

from requests import Session
from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.cache import DictCache
from .utils import NullSerializer


class TestMaxAge(object):

    @pytest.fixture()
    def sess(self, url):
        self.url = url
        self.cache = DictCache()
        sess = Session()
        sess.mount(
            "http://", CacheControlAdapter(self.cache, serializer=NullSerializer())
        )
        return sess

    def test_client_max_age_0(self, sess):
        """
        Making sure when the client uses max-age=0 we don't get a
        cached copy even though we're still fresh.
        """
        print("first request")
        r = sess.get(self.url)
        assert self.cache.get(self.url) == r.raw

        print("second request")
        r = sess.get(self.url, headers={"Cache-Control": "max-age=0"})

        # don't remove from the cache
        assert self.cache.get(self.url)
        assert not r.from_cache

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
