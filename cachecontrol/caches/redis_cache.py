# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from cachecontrol.cache import BaseCache  # Base class for all cache implementations

# Use TYPE_CHECKING to avoid import at runtime (improves performance, avoids circular import)
if TYPE_CHECKING:
    from redis import Redis


class RedisCache(BaseCache):
    """
    A cache implementation that stores cache data in a Redis backend.
    This class conforms to the CacheControl `BaseCache` interface.
    """

    def __init__(self, conn: Redis[bytes]) -> None:
        # Initialize the cache with a Redis connection instance
        self.conn = conn

    def get(self, key: str) -> bytes | None:
        # Retrieve a cached value from Redis by key
        return self.conn.get(key)

    def set(
        self, key: str, value: bytes, expires: int | datetime | None = None
    ) -> None:
        """
        Store a value in Redis.

        If `expires` is:
        - None: store the value indefinitely.
        - int: store the value with an expiry in seconds.
        - datetime: compute the difference from now and set expiry accordingly.
        """
        if not expires:
            # No expiration provided, set the value permanently
            self.conn.set(key, value)
        elif isinstance(expires, datetime):
            # Calculate the expiry in seconds if a datetime object is given
            now_utc = datetime.now(timezone.utc)
            if expires.tzinfo is None:
                # If datetime is naive (no timezone), make comparison fair
                now_utc = now_utc.replace(tzinfo=None)

            delta = expires - now_utc
            # Set value with expiration time in seconds
            self.conn.setex(key, int(delta.total_seconds()), value)
        else:
            # If expires is an integer, use it as TTL in seconds
            self.conn.setex(key, expires, value)

    def delete(self, key: str) -> None:
        # Remove the specified key from Redis cache
        self.conn.delete(key)

    def clear(self) -> None:
        """
        Clear all keys in the current Redis database.

        WARNING: This is potentially destructive and should be used with caution!
        """
        for key in self.conn.keys():
            self.conn.delete(key)

    def close(self) -> None:
        """
        Redis uses a connection pool, so explicit closing is not required.
        Provided to match the `BaseCache` interface.
        """
        pass
