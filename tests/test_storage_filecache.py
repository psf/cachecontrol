# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests that verify FileCache storage works correctly.
"""
import os
import string

from random import randint, sample

import pytest
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache, SeparateBodyFileCache
from filelock import FileLock


def randomdata():
    """Plain random http data generator:"""
    key = "".join(sample(string.ascii_lowercase, randint(2, 4)))
    val = "".join(sample(string.ascii_lowercase + string.digits, randint(2, 10)))
    return "&{}={}".format(key, val)


class FileCacheTestsMixin(object):

    FileCacheClass = None  # Either FileCache or SeparateBodyFileCache

    @pytest.fixture()
    def sess(self, url, tmpdir):
        self.url = url
        self.cache = self.FileCacheClass(str(tmpdir))
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

    def test_simple_lockfile_arg(self, tmpdir):
        cache = self.FileCacheClass(str(tmpdir))

        assert issubclass(cache.lock_class, FileLock)
        cache.close()

    def test_lock_class(self, tmpdir):
        lock_class = object()
        cache = self.FileCacheClass(str(tmpdir), lock_class=lock_class)
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


class TestFileCache(FileCacheTestsMixin):
    """
    Tests for ``FileCache``.
    """

    FileCacheClass = FileCache

    def test_body_stored_inline(self, sess):
        """The body is stored together with the metadata."""
        url = self.url + "cache_60"
        response = sess.get(url)
        body = response.content
        response2 = sess.get(url)
        assert response2.from_cache
        assert response2.content == body

        # OK now let's violate some abstraction boundaries to make sure body
        # was stored in metadata file.
        with open(self.cache._fn(url), "rb") as f:
            assert body in f.read()
        assert not os.path.exists(self.cache._fn(url) + ".body")


class TestSeparateBodyFileCache(FileCacheTestsMixin):
    """
    Tests for ``SeparateBodyFileCache``
    """

    FileCacheClass = SeparateBodyFileCache

    def test_body_actually_stored_separately(self, sess):
        """
        Body is stored and can be retrieved from the SeparateBodyFileCache, with assurances
        it's actually being loaded from separate file than metadata.
        """
        url = self.url + "cache_60"
        response = sess.get(url)
        body = response.content
        response2 = sess.get(url)
        assert response2.from_cache
        assert response2.content == body

        # OK now let's violate some abstraction boundaries to make sure body
        # actually came from separate file.
        with open(self.cache._fn(url), "rb") as f:
            assert body not in f.read()
        with open(self.cache._fn(url) + ".body", "rb") as f:
            assert body == f.read()
        with open(self.cache._fn(url) + ".body", "wb") as f:
            f.write(b"CORRUPTED")
        response2 = sess.get(url)
        assert response2.from_cache
        assert response2.content == b"CORRUPTED"
