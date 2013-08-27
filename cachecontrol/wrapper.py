from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.cache import DictCache


def CacheControl(sess, cache=None):
    cache = cache or DictCache()
    sess.mount('http://', CacheControlAdapter(cache))
    return sess
