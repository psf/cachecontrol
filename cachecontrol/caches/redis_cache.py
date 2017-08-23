from __future__ import division

from datetime import datetime
from cachecontrol.cache import BaseCache
import zlib

def total_seconds(td):
    """Python 2.6 compatability"""
    if hasattr(td, 'total_seconds'):
        return int(td.total_seconds())

    ms = td.microseconds
    secs = (td.seconds + td.days * 24 * 3600)
    return int((ms + secs * 10**6) / 10**6)


class RedisCache(BaseCache):

    def __init__(self, conn):
        self.conn = conn

    def get(self, key):
        value = self.conn.get(key)

        if value is None:
            return None

        # to handle testing issues where a Mock object cannot be handled
        if type(value) is not 'str':
            return value

        value = zlib.decompress(value.encode('utf-8'))

        return value.decode('utf-8')

    def set(self, key, set_value, expires=None):

        # mutability damage limiter

        value = set_value

        # to handle testing issues where a Mock object cannot be handled

        if value is not None and type(value) is 'str':

            value = value.encode('utf-8')
            value = zlib.compress(value, zlib.Z_BEST_COMPRESSION)
            value = str(value)

        if not expires:
            self.conn.set(key, value)
        else:
            expires = expires - datetime.utcnow()
            self.conn.setex(key, total_seconds(expires), value)

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
