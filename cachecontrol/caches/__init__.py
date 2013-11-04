try:
    import lockfile
    from cachecontrol.caches.file_cache import FileCache
except ImportError:
    pass


try:
    import redis
    from cachecontrol.caches.redis_cache import RedisCache
except ImportError:
    pass
