from datetime import datetime

from mock import Mock, MagicMock
from cachecontrol.caches import RedisCache


class TestRedisCache(object):

    def setup(self):
        self.conn = MagicMock()
        self.cache = RedisCache(self.conn)

    def test_set_expiration(self):
        self.cache.set('foo', 'bar', expires=datetime(2014, 2, 2))
        assert self.conn.setex.called
