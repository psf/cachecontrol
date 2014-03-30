import pytest

from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.wrapper import CacheControl
from cachecontrol.session import CacheControlSession

def use_wrapper():
    print('Using helper with Cache Session Handler')
    sess = CacheControl(CacheControlSession())
    return sess

def use_adapter():
    print('Using adapter with Cache Session Handler')
    sess = CacheControlSession()
    sess.mount('http://', CacheControlAdapter())
    return sess

@pytest.fixture(params=[use_adapter, use_wrapper])
def sess(url, request):
    sess = request.param()
    sess.get(url, cache_auto=True, cache_urls=['http://127.0.0.1'], cache_max_age=900)
    return sess

class TestSessionActions(object):

    def test_get_caches(self, url, sess):
        r2 = sess.get(url)
        assert r2.from_cache is True

    def test_get_with_no_cache_does_not_cache(self, url, sess):
        r2 = sess.get(url, headers={'Cache-Control': 'no-cache'})
        assert not r2.from_cache

    def test_put_invalidates_cache(self, url, sess):
        r2 = sess.put(url, data={'foo': 'bar'})
        sess.get(url)
        assert not r2.from_cache

    def test_delete_invalidates_cache(self, url, sess):
        r2 = sess.delete(url)
        sess.get(url)
        assert not r2.from_cache