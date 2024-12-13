# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

import gc
import weakref
from unittest import mock

import pytest
from requests import Session

from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.cache import DictCache
from cachecontrol.wrapper import CacheControl


def use_wrapper():
    print("Using helper")
    sess = CacheControl(Session())
    return sess


def use_adapter():
    print("Using adapter")
    sess = Session()
    sess.mount("http://", CacheControlAdapter())
    return sess


@pytest.fixture(params=[use_adapter, use_wrapper])
def sess(url, request):
    sess = request.param()
    sess.get(url)
    yield sess

    # closing session object
    sess.close()


class TestSessionActions:
    def test_get_caches(self, url, sess):
        r2 = sess.get(url)
        assert r2.from_cache is True

    def test_get_with_no_cache_does_not_cache(self, url, sess):
        r2 = sess.get(url, headers={"Cache-Control": "no-cache"})
        assert not r2.from_cache

    def test_put_invalidates_cache(self, url, sess):
        r2 = sess.put(url, data={"foo": "bar"})
        sess.get(url)
        assert not r2.from_cache

    def test_patch_invalidates_cache(self, url, sess):
        r2 = sess.patch(url, data={"foo": "bar"})
        sess.get(url)
        assert not r2.from_cache

    def test_delete_invalidates_cache(self, url, sess):
        r2 = sess.delete(url)
        sess.get(url)
        assert not r2.from_cache

    def test_close(self):
        cache = mock.Mock(spec=DictCache)
        sess = Session()
        sess.mount("http://", CacheControlAdapter(cache))

        sess.close()
        assert cache.close.called

    def test_do_not_leak_response(self, url, sess):
        resp = sess.get(url + "stream", stream=True)
        resp.raise_for_status()
        r1_weak = weakref.ref(resp.raw)

        # This is a mis-use of requests, becase we should either consume
        # the body, or call .close().
        # But requests without cachecontrol handle this anyway, because
        # urllib3.response.HTTPResponse has a __del__ finalizer on it that closes it
        # once there are no more references to it.
        # We should not break this.

        resp = None
        # Below this point, it should be closed because there are no more references
        # to the session response.

        r1 = r1_weak()
        assert r1 is None or r1.closed
