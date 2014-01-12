"""
Unit tests that verify FileCache storage works correctly.
"""
import pytest
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

STORAGE_FOLDER = ".cache"


class TestStorageFileCache(object):

    @pytest.fixture()
    def sess(self, server):
        self.url = server.application_url
        self.cache = FileCache(STORAGE_FOLDER)
        sess = CacheControl(requests.Session(), cache=self.cache)
        return sess

    def test_filecache_from_cache(self, sess):
        response = sess.get(self.url)
        assert not response.from_cache
        response = sess.get(self.url)
        assert response.from_cache
