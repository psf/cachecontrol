"""
Unit tests that verify FileCache storage works correctly.
"""

import string
import os
import getpass
import tempfile

from random import randint, sample

import pytest
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

def _getTempDir():
    """Returns the [system temp dir]/tvdb_api-u501 (or
    tvdb_api-myuser)
    """
    if hasattr(os, 'getuid'):
        uid = "u%d" % (os.getuid())
    else:
        # For Windows
        try:
            uid = getpass.getuser()
        except ImportError:
            return os.path.join(tempfile.gettempdir(), "cachecontrol")

    return os.path.join(tempfile.gettempdir(), "cachecontrol-%s" % (uid))

STORAGE_FOLDER = _getTempDir()

def randomdata():
    """Plain random http data generator:"""
    key = ''.join(sample(string.ascii_lowercase, randint(2, 4)))
    val = ''.join(sample(string.ascii_lowercase + string.digits,
                         randint(2, 10)))
    return '&{0}={1}'.format(key, val)


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

    def test_key_length(self, sess):
        """
        Hash table keys:
           Most file systems have a 255 characters path limitation.
              * Make sure hash method does not produce too long keys
              * Ideally hash method generate fixed length keys
        """
        url0 = url1 = 'http://example.org/res?a=1'
        while len(url0) < 255:
            url0 += randomdata()
            url1 += randomdata()
        assert len(self.cache.encode(url0)) < 200
        assert len(self.cache.encode(url0)) == len(self.cache.encode(url1))
