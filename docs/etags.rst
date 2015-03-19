==============
 ETag Support
==============

CacheControl's support of ETags is slightly different than
httplib2. In httplib2, an ETag is considered when using a cached
response when the cache is considered stale. When a cached response is
expired and it has an ETag header, it returns a response with the
appropriate `If-None-Match` header. We'll call this behavior a **Time
Priority** cache as the ETag support only takes effect when the time has
expired.

In CacheControl the default behavior when an ETag is sent by the
server is to cache the response. We'll refer to this pattern as a
**Equal Priority** cache as the decision to cache is either time base or
due to the presense of an ETag.

The spec is not explicit what takes priority when caching with both
ETags and time based headers. Therefore, CacheControl supports the
different mechanisms via configuration where possible.


Turning Off Equal Priority Caching
==================================

The danger in Equal Priority Caching is that a server that returns
ETag headers for every request may fill up your cache. You can disable
Equal Priority Caching and utilize a Time Priority algorithm like
httplib2. ::

  import requests
  from cachecontrol import CacheControl

  sess = CacheControl(requests.Session(), cache_etags=False)

This will only utilize ETags when they exist within the context of
time based caching headers. If a response has time base caching
headers that are valid along with an ETag, we will still attempt to
handle a 304 Not Modified even though the cached value as
expired. Here is a simple example. ::

  # Server response
  GET /foo.html
  Date: Tue, 26 Nov 2013 00:50:49 GMT
  Cache-Control: max-age=3000
  ETag: JAsUYM8K

On a subsequent request, if the cache has expired, the next request
will still include the `If-None-Match` header. The cached response
will remain in the cache awaiting the response. ::

  # Client request
  GET /foo.html
  If-None-Match: JAsUYM8K

If the server returns a `304 Not Modified`, it will use the stale
cached value, updating the headers from the most recent request. ::

  # Server response
  GET /foo.html
  Date: Tue, 26 Nov 2013 01:30:19 GMT
  Cache-Control: max-age=3000
  ETag: JAsUYM8K

If the server returns a `200 OK`, the cache will be updated
accordingly.


Equal Priority Caching Benefits
===============================

The benefits of equal priority caching is that you have two orthogonal
means of introducing a cache. The time based cache provides an
effective way to reduce the load on requests that can be eventually
consistent. Static resource are a great example of when time based
caching is effective.

The ETag based cache is effective for working with documents that are
larger and/or need to be correct immediately after changes. For
example, if you exported some data from a large database, the file
could be 10 GBs. Being able to send an ETag with this sort of request
an know the version you have locally is valid saves a ton of bandwidth
and time.

Likewise, if you have a resource that you want to update, you can be
confident there will not be a `lost update`_ because you have local
version that is stale.


Endpoint Specific Caching
=========================

It should be pointed out that there are times when an endpoint is
specifically tailored for different caching techniques. If you have a
RESTful service, there might be endpoints that are specifically meant
to be cached via time based caching techniques where as other
endpoints should focus on using ETags. In this situation it is
recommended that you use the `CacheControlAdapter` directly. ::

  import requests
  from cachecontrol import CacheControlAdapter
  from cachecontrol.caches import RedisCache

  # using django for an idea on where you might get a
  # username/password.
  from django.conf import settings

  # a function to return a redis connection all the instances of the
  # app may use. this allows updates to the API (ie PUT) to invalidate
  # the cache for other users.
  from myapp.db import redis_connection


  # create our session
  client = sess.Session(auth=(settings.user, settings.password))

  # we have a gettext like endpoint. this doesn't get updated very
  # often so a time based cache is a helpful way to reduce many small
  # requests.
  client.mount('http://myapi.foo.com/gettext/',
               CacheControlAdapter(cache_etags=False))


  # here we have user profile endpoint that lets us update information
  # about users. we need this to be consistent immediately after a user
  # updates some information because another node might handle the
  # request. It uses the global redis cache to coordinate the cache and
  # uses the equal priority caching to be sure etags are used by default.
  redis_cache = RedisCache(redis_connection())
  client.mount('http://myapi.foo.com/user_profiles/',
               CacheControlAdapter(cache=redis_cache))

Hopefully this more indepth example reveals how to configure a
`requests.Session` to better utilize ETag based caching vs. Time
Priority Caching.

.. _lost update: http://www.w3.org/1999/04/Editing/
