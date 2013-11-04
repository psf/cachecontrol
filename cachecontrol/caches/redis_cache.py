from cPickle import loads, dumps


class RedisCache(object):

    def __init__(self, conn):
        self.conn = conn

    def get(self, key):
        val = self.conn.get(key)
        if val:
            return loads(val)
        return None

    def set(self, key, value):
        self.conn.set(key, dumps(value))

    def delete(self, key):
        self.conn.delete(key)

    def clear(self):
        """Helper for clearing all the keys in a database. Use with
        caution!"""
        for key in self.conn.keys():
            self.conn.delete(key)
