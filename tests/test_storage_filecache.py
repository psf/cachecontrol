"""
Unit tests that verify FileCache storage works correctly.
"""
import os
import string

from random import randint, sample, shuffle

import pytest
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from cachecontrol.caches.file_cache import url_to_file_path
from lockfile import LockFile
from lockfile.mkdirlockfile import MkdirLockFile


def randomdata():
    """Plain random http data generator:"""
    key = ''.join(sample(string.ascii_lowercase, randint(2, 4)))
    val = ''.join(sample(string.ascii_lowercase + string.digits,
                         randint(2, 10)))
    return '&{0}={1}'.format(key, val)


class TestStorageFileCache(object):

    @pytest.fixture()
    def sess(self, url, tmpdir):
        self.url = url
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

    def test_cant_use_dir_and_lock_class(self, tmpdir):
        with pytest.raises(ValueError):
            FileCache(str(tmpdir), use_dir_lock=True, lock_class=object())

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, LockFile),
            (True, MkdirLockFile),
            (False, LockFile),
        ],
    )
    def test_simple_lockfile_arg(self, tmpdir, value, expected):
        if value is not None:
            cache = FileCache(str(tmpdir), use_dir_lock=value)
        else:
            cache = FileCache(str(tmpdir))

        assert issubclass(cache.lock_class, expected)

    def test_lock_class(self, tmpdir):
        lock_class = object()
        cache = FileCache(str(tmpdir), lock_class=lock_class)
        assert cache.lock_class is lock_class

    def test_url_to_file_path(self, tmpdir):
        cache = FileCache(str(tmpdir))
        # We'll add a long sorted suffix so that unsorted queries have a low
        # collision probability (about 3.8e-23 for each sorted/unsorted
        # comparison).
        letter_n_numbers = list(enumerate(string.ascii_lowercase[3:], start=4))
        suff = '&' + '&'.join('%s=%s' % (k, v) for v, k in letter_n_numbers)

        def get_param(url):
            """Mock losing order when processing params"""
            shuffle(letter_n_numbers)
            params = {k: v for v, k in letter_n_numbers}
            url = url.replace(suff, '')
            query = '&' + '&'.join('%s=%s' % item for item in params.items())
            return url + query

        urls = {
            'no_query': 'http://example.com',
            'unsorted_query': 'http://example.com?b=2&c=3&a=1' + suff,
            'sorted_query': 'http://example.com?a=1&b=2&c=3' + suff,
            'unsorted_empty_value': 'http://example.com?b=&c=&a=1' + suff,
            'sorted_empty_value': 'http://example.com?a=1&b=&c=3' + suff,
            'unsorted_repeated_key': 'http://example.com?b=2&c=3&b=0'
                                     '&c=5&a=1' + suff,
            'sorted_repeated_key': 'http://example.com?a=1&b=0&b=2&c=3&'
                                   'c=5' + suff}

        unoquery = url_to_file_path(urls['no_query'], cache, sort_query=False)
        snoquery = url_to_file_path(urls['no_query'], cache, sort_query=True)
        assert unoquery == snoquery
        urls.pop('no_query')

        sortedpaths = {urlname: url_to_file_path(urlvalue, cache, True) for
                       urlname, urlvalue in urls.items()}

        for key, value in urls.items():
            if key.startswith('sorted'):
                assert url_to_file_path(value, cache, True) == sortedpaths[key]

        unsortedpaths = {urlname: url_to_file_path(urlvalue, cache, False) for
                         urlname, urlvalue in urls.items()}

        for key, url in urls.items():
            if key.startswith('unsorted'):
                assert sortedpaths[key] != unsortedpaths[key]
            else:
                assert sortedpaths[key] == unsortedpaths[key]

            # Randomize and sort params
            sort_param = url_to_file_path(get_param(url), cache, True)
            assert sort_param == sortedpaths[key]

            # Randomize but don't sort params
            unsort_param = url_to_file_path(get_param(url), cache, False)
            assert unsort_param != unsortedpaths[key]
