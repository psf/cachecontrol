# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime

from mock import Mock
from cachecontrol.caches import RedisCache


class TestRedisCache(object):

    def setup(self):
        self.conn = Mock()
        self.cache = RedisCache(self.conn)

    def test_set_expiration_datetime(self):
        self.cache.set("foo", "bar", expires=datetime(2014, 2, 2))
        assert self.conn.setex.called

    def test_set_expiration_int(self):
        self.cache.set("foo", "bar", expires=600)
        assert self.conn.setex.called
