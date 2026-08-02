# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timedelta, timezone

import pytest
from redis.exceptions import ResponseError

from cachecontrol.caches import RedisCache


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}

    def set(self, key: str, value: bytes) -> None:
        self.values[key] = value
        self.ttls.pop(key, None)

    def setex(self, key: str, seconds: int, value: bytes) -> None:
        if seconds <= 0:
            raise ResponseError("invalid expire time in 'setex' command")
        self.values[key] = value
        self.ttls[key] = seconds

    def get(self, key: str) -> bytes | None:
        return self.values.get(key)

    def delete(self, key: str) -> None:
        self.values.pop(key, None)
        self.ttls.pop(key, None)


ONE_HOUR = timedelta(hours=1)


class TestRedisCache:
    def setup_method(self):
        self.conn = FakeRedis()
        self.cache = RedisCache(self.conn)

    @pytest.mark.parametrize("tzinfo", [None, timezone.utc], ids=["naive", "aware"])
    @pytest.mark.parametrize(
        "offset, expected",
        [(ONE_HOUR, b"bar"), (-ONE_HOUR, None)],
        ids=["future", "past"],
    )
    def test_set_expiration_datetime(self, tzinfo, offset, expected):
        """A deadline already in the past must not reach SETEX."""
        expires = datetime.now(timezone.utc).replace(tzinfo=tzinfo) + offset

        self.cache.set("foo", b"bar", expires=expires)

        assert self.conn.get("foo") == expected

    @pytest.mark.parametrize(
        "expires, expected", [(600, b"bar"), (-600, None)], ids=["positive", "negative"]
    )
    def test_set_expiration_int(self, expires, expected):
        """controller.py computes ``Expires - Date``, which can go negative."""
        self.cache.set("foo", b"bar", expires=expires)

        assert self.conn.get("foo") == expected
