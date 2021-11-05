# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
The cache object API for implementing caches. The default is a thread
safe in-memory dictionary.
"""
from threading import Lock
from typing import Optional
from pathlib import Path
from abc import ABC
from .compat import HTTPResponse
from .serialize import Serializer


class LegacyCache(object):
    """Legacy cache interface."""

    def get(self, key):
        raise NotImplementedError()

    def set(self, key, value, expires=None):
        raise NotImplementedError()

    def delete(self, key):
        raise NotImplementedError()

    def close(self):
        pass


BaseCache = LegacyCache  # backwards compatibility


class CacheInterface(ABC):
    """New interface for caches.

    The metadata is stored separately from the body data, in order to make it
    easy to directly stream large amounts of data to disk.

    This is deliberately compatible with the old interface, so implementations
    can support both.
    """

    def get_as_file(self, key: str, serializer: Serializer) -> HTTPResponse:
        """
        Return tuple of (encoded-metadata file-like, body file-like).
        """

    def set_from_file(
        self,
        key: str,
        metadata_value: bytes,
        body_path: Path,
        expires: Optional[int] = None,
    ):
        """
        Store a cache entry, with metadata and body being passed in separately,
        the latter as a path to a file.  The metadata is encoded.  Expiration
        time is a duration (from the present moment) in seconds.
        """

    def delete(self, key: str):
        """
        Delete an entry.
        """

    def close(self):
        """
        Close the cache.
        """


class DictCache(BaseCache):
    def __init__(self, init_dict=None):
        self.lock = Lock()
        self.data = init_dict or {}

    def get(self, key):
        return self.data.get(key, None)

    def set(self, key, value, expires=None):
        with self.lock:
            self.data.update({key: value})

    def delete(self, key):
        with self.lock:
            if key in self.data:
                self.data.pop(key)


class _OldCacheToNew(CacheInterface):
    """Adapt an old-style cache to the new interface."""

    def __init__(self, cache):
        self._cache = cache

    def __getattr__(self, attr):
        return getattr(self._cache, attr)

    def get_as_file(self, key: str, request, serializer: Serializer) -> HTTPResponse:
        """
        Return tuple of (encoded-metadata file-like, body file-like).
        """
        combined_data = self.get(key)
        # This is old-school format where metadata and body are combined...
        return serializer.loads(request, combined_data)

    def set_from_file(
        self,
        key: str,
        metadata_value: bytes,
        body_path: Path,
        expires: Optional[int] = None,
    ):
        """
        Store a cache entry, with metadata and body being passed in separately,
        the latter as a path to a file.  The metadata is encoded.  Expiration
        time is a duration (from the present moment) in seconds.
        """
