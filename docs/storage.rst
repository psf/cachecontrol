====================
 Storing Cache Data
====================

CacheControl comes with a few storage backends for storing your
cache'd objects.


DictCache
=========

The `DictCache` is the default cache used when no other is
provided. It is a simple threadsafe dictionary. It doesn't try to do
anything smart about deadlocks or forcing a busted cache, but it
should be reasonably safe to use.

Also, the `DictCache` does not transform the request or response
objects in anyway. Therefore it is unlikely you could persist the
entire cache to disk. The converse is that it should be very fast.


FileCache
=========

The `FileCache` is similar to the caching mechanism provided by
httplib2_. It requires `lockfile`_ be installed as it prevents
multiple threads from writing to the same file at the same time.

Here is an example using the `FileCache`: ::

  import requests
  from cachecontrol import CacheControl
  from cachecontrol.caches import FileCache

  sess = CacheControl(requests.Session(),
                      cache=FileCache('.web_cache'))


The `FileCache` supports a `forever` flag that disables deleting from
the cache. This can be helpful in debugging applications that make
many web requests that you don't want to repeat. It also can be
helpful in testing. Here is an example of how to use it: ::

  forever_cache = FileCache('.web_cache', forever=True)
  sess = CacheControl(requests.Session(), forever_cache)


:A Note About Pickle:

  It should be noted that the `FileCache` uses pickle to store the
  cached response. Currently, `requests.Response` objects are not
  'pickleable' due to the use of `IOBase` base classes in `urllib3`
  `HTTPResponse` objects. In CacheControl we work around this by
  patching the Response objects with the appropriate `__getstate__` and
  `__setstate__` methods.



RedisCache
==========

The `RedisCache` uses a Redis database to store values. The values are
stored as strings in redis, which means the get, set and delete
actions are used.

The `RedisCache` also provides a clear method to delete all keys in a
database. Obviously, this should be used with caution as it is naive
and works iteratively, looping over each key and deleting it.

Here is an example using a `RedisCache`: ::

  import redis
  import requests
  from cachecontrol import CacheControl
  from cachecontrol.caches import RedisCache


  pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
  r = redis.Redis(connection_pool=pool)
  sess = CacheControl(requests.Session(), RedisCache(r))

This is primarily a proof of concept, so please file bugs if there is
a better method for utilizing redis as a cache.


.. _httplib2: http://code.google.com/p/httplib2/
