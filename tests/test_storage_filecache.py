"""
Unit tests that verify FileCache storage works correctly.
"""
import os
import string

from random import randint, sample

import pytest
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache


def randomdata():
    """Plain random http data generator:"""
    key = ''.join(sample(string.ascii_lowercase, randint(2, 4)))
    val = ''.join(sample(string.ascii_lowercase + string.digits,
                         randint(2, 10)))
    return '&{0}={1}'.format(key, val)


class TestStorageFileCache(object):

    @pytest.fixture()
    def sess(self, server, tmpdir):
        self.url = server.application_url
        self.cache = FileCache(str(tmpdir))
        sess = CacheControl(requests.Session(), cache=self.cache)
        return sess

    def test_filecache_from_cache(self, sess):
        response = sess.get(self.url)
        assert not response.from_cache
        response = sess.get(self.url)
        assert response.from_cache

    def test_filecache_directory_not_exists(self, tmpdir, sess):
        url = self.url + ''.join(sample(string.ascii_lowercase, randint(2, 4)))

        # Make sure our cache dir doesn't exist
        tmp_cache = tmpdir.join('missing', 'folder', 'name').strpath
        assert not os.path.exists(tmp_cache)

        self.cache.directory = tmp_cache

        # trigger a cache save
        sess.get(url)

        # Now our cache dir does exist
        assert os.path.exists(tmp_cache)

    def test_filecache_directory_already_exists(self, tmpdir, sess):
        """
        Assert no errors are raised when using a cache directory
        that already exists on the filesystem.
        """
        url = self.url + ''.join(sample(string.ascii_lowercase, randint(2, 4)))

        # Make sure our cache dir DOES exist
        tmp_cache = tmpdir.join('missing', 'folder', 'name').strpath
        os.makedirs(tmp_cache, self.cache.dirmode)

        assert os.path.exists(tmp_cache)

        self.cache.directory = tmp_cache

        # trigger a cache save
        sess.get(url)

        assert True  # b/c no exceptions were raised

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

    def test_max_bytes(self, tmpdir, sess):
        """
        Test that caches the first url but not the second because
        the maximum bytes have been reached for the cache.
        """
        # use a cache with max_bytes set
        max_bytes = 1400
        self.cache = FileCache(str(tmpdir), max_bytes=max_bytes)
        sess = CacheControl(requests.Session(), cache=self.cache)

        url1 = self.url + ''.join(sample(string.ascii_lowercase, randint(2, 4)))
        url2 = self.url + ''.join(sample(string.ascii_lowercase, randint(2, 4)))
        assert url1 != url2

        # fill up the cache with url1
        response = sess.get(url1)
        assert not response.from_cache

        # make sure it got into the cache
        response = sess.get(url1)
        assert response.from_cache

        # do url2 now
        response = sess.get(url2)
        assert not response.from_cache

        # make sure url2 was NOT cached
        response = sess.get(url2)
        assert not response.from_cache

        # clear the cache
        response = sess.delete(url1)
        assert not response.from_cache

        # re-add to cache since bytes should be back to 0
        response = sess.get(url1)
        assert not response.from_cache

        # verify from cache again
        response = sess.get(url1)
        assert response.from_cache
