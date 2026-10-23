# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
The cache object API for implementing caches. The default is a thread
safe in-memory dictionary.
"""

from __future__ import annotations

from threading import Lock
from typing import IO, TYPE_CHECKING, MutableMapping

if TYPE_CHECKING:
    from datetime import datetime


class BaseCache:
    def get(self, key: str) -> bytes | None:
        raise NotImplementedError()

    def set(
        self, key: str, value: bytes, expires: int | datetime | None = None
    ) -> None:
        raise NotImplementedError()

    def delete(self, key: str) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        pass


class DictCache(BaseCache):
    def __init__(self, init_dict: MutableMapping[str, bytes] | None = None) -> None:
        self.lock = Lock()
        self.data = init_dict or {}

    def get(self, key: str) -> bytes | None:
        return self.data.get(key, None)

    def set(
        self, key: str, value: bytes, expires: int | datetime | None = None
    ) -> None:
        with self.lock:
            self.data.update({key: value})

    def delete(self, key: str) -> None:
        with self.lock:
            if key in self.data:
                self.data.pop(key)


class SeparateBodyBaseCache(BaseCache):
    """
    In this variant, the body is not stored mixed in with the metadata, but is
    passed in (as a bytes-like object) in a separate call to ``set_body()``.

    Cache implementations can override ``set_with_body()`` and
    ``get_with_body()`` when the two operations need to be synchronized. The
    default implementations retain the separate calls for compatibility.

    The low-level interaction pattern is::

        cache.set(key, serialized_metadata)
        cache.set_body(key)

    Similarly, the body should be loaded separately via ``get_body()``.
    """

    def get_with_body(self, key: str) -> tuple[bytes | None, IO[bytes] | None]:
        """Return an entry's metadata and body together."""
        metadata = self.get(key)
        if metadata is None:
            return None, None
        return metadata, self.get_body(key)

    def set_with_body(
        self,
        key: str,
        metadata: bytes,
        body: bytes | None,
        expires: int | datetime | None = None,
    ) -> None:
        """Store metadata and replace the body when one is provided."""
        self.set(key, metadata, expires)
        if body is not None:
            self.set_body(key, body)

    def set_body(self, key: str, body: bytes) -> None:
        raise NotImplementedError()

    def get_body(self, key: str) -> IO[bytes] | None:
        """
        Return the body as file-like object.
        """
        raise NotImplementedError()
