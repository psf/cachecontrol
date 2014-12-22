import os

from requests import Session

from cachecontrol import CacheControl
from cachecontrol.caches.sqlite_cache import SQLiteCache


class TestSQLiteCache(object):

    def setup(self):
        self.dbpath = 'test_sqlite_cache.db'
        self.sess = CacheControl(
            Session(),
            cache=SQLiteCache(self.dbpath)
        )

    def teardown(self):
        os.remove(self.dbpath)

    def test_cache_request(self, url):
        r = self.sess.get(url)
        assert not r.from_cache

        r = self.sess.get(url)
        assert r.from_cache
