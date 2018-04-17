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
from lockfile import LockFile
from lockfile.mkdirlockfile import MkdirLockFile


def randomdata():
    """Plain random http data generator:"""
    key = "".join(sample(string.ascii_lowercase, randint(2, 4)))
    val = "".join(sample(string.ascii_lowercase + string.digits, randint(2, 10)))
    return "&{}={}".format(key, val)


class TestStorageFileCache(object):

    @pytest.fixture()
    def sess(self, url, tmpdir):
        self.url = url
        self.cache = FileCache(str(tmpdir))
        sess = CacheControl(requests.Session(), cache=self.cache)
        yield sess

        # closing session object
        sess.close()

    def test_filecache_from_cache(self, sess):
        response = sess.get(self.url)
        assert not response.from_cache
        response = sess.get(self.url)
        assert response.from_cache

    def test_filecache_directory_not_exists(self, tmpdir, sess):
        url = self.url + "".join(sample(string.ascii_lowercase, randint(2, 4)))

        # Make sure our cache dir doesn't exist
        tmp_cache = tmpdir.join("missing", "folder", "name").strpath
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
        url = self.url + "".join(sample(string.ascii_lowercase, randint(2, 4)))

        # Make sure our cache dir DOES exist
        tmp_cache = tmpdir.join("missing", "folder", "name").strpath
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
        url0 = url1 = "http://example.org/res?a=1"
        while len(url0) < 255:
            url0 += randomdata()
            url1 += randomdata()
        assert len(self.cache.encode(url0)) < 200
        assert len(self.cache.encode(url0)) == len(self.cache.encode(url1))

    def test_cant_use_dir_and_lock_class(self, tmpdir):
        with pytest.raises(ValueError):
            FileCache(str(tmpdir), use_dir_lock=True, lock_class=object())

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(None, LockFile), (True, MkdirLockFile), (False, LockFile)],
    )
    def test_simple_lockfile_arg(self, tmpdir, value, expected):
        if value is not None:
            cache = FileCache(str(tmpdir), use_dir_lock=value)
        else:
            cache = FileCache(str(tmpdir))

        assert issubclass(cache.lock_class, expected)
        cache.close()

    def test_lock_class(self, tmpdir):
        lock_class = object()
        cache = FileCache(str(tmpdir), lock_class=lock_class)
        assert cache.lock_class is lock_class
        cache.close()

    def test_filecache_with_delete_request(self, tmpdir, sess):
        # verifies issue #155
        url = self.url + "".join(sample(string.ascii_lowercase, randint(2, 4)))
        sess.delete(url)
        assert True  # test verifies no exceptions were raised

    def test_filecache_with_put_request(self, tmpdir, sess):
        # verifies issue #155
        url = self.url + "".join(sample(string.ascii_lowercase, randint(2, 4)))
        sess.put(url)
        assert True  # test verifies no exceptions were raised
