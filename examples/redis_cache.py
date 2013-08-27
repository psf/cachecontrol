"""
A Redis cache example.
"""

from cachecontrol import BaseCache


class RedisCache(BaseCache):

    def __init__(self, conn):
        self.conn = conn

    def get(self, key):
        return self.conn.get(key)

    def set(self, key, value):
        self.conn.set(key, value)

    def delete(self, key):
        self.conn.delete(key)


if __name__ == '__main__':
    import redis
    import requests

    from cachecontrol import CacheControl

    pool = redis.ConnectionPool(host='localhost', port=6379, db=1)
    r = redis.Redis(connection_pool=pool)
    redis_cache = RedisCache(r)

    sess = CacheControl(requests.Session(), cache=redis_cache)
