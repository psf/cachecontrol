from __future__ import division

from datetime import datetime
from cachecontrol.cache import BaseCache


class RedisCache(BaseCache):

    def __init__(self, conn):
        self.conn = conn

    def get(self, key):
        return self.conn.get(key)

    def set(self, key, value, expires=None):
        self.conn.set(key, value, ex=expires or None)

    def delete(self, key):
        self.conn.delete(key)

    def clear(self):
        """Helper for clearing all the keys in a database. Use with
        caution!"""
        for key in self.conn.keys():
            self.conn.delete(key)

    def close(self):
        """Redis uses connection pooling, no need to close the connection."""
        pass
