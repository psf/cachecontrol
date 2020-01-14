from datetime import datetime

from mock import Mock
from cachecontrol.caches import RedisCache


class TestRedisCache(object):

    def setup(self):
        self.conn = Mock()
        self.cache = RedisCache(self.conn)

    def test_set_expiration(self):
        self.cache.set("foo", "bar", expires=3600)
        self.conn.set.assert_called_with("foo", "bar", ex=3600)

    def test_set_invalid_age(self):
        """
        Verify that expires=0 will not cause Redis to throw an error.   It must be passed
        as None or we receive: ResponseError: invalid expire time in set)
        """
        self.cache.set("foo", "bar", expires=0)
        self.conn.set.assert_called_with("foo", "bar", ex=None)
