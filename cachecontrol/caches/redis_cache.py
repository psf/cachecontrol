from datetime import datetime

try:
    from cPickle import loads, dumps
except ImportError:  # Python 3.x
    from pickle import loads, dumps


class RedisCache(object):

    def __init__(self, conn):
        self.conn = conn

    def get(self, key):
        val = self.conn.get(key)
        if val:
            return loads(val)
        return None

    def set(self, key, value, expires=None):
        if not expires:
            self.conn.set(key, dumps(value))
        else:
            expires = expires - datetime.now()
            self.conn.setex(key, expires.total_seconds(), value)

    def delete(self, key):
        self.conn.delete(key)

    def clear(self):
        """Helper for clearing all the keys in a database. Use with
        caution!"""
        for key in self.conn.keys():
            self.conn.delete(key)
