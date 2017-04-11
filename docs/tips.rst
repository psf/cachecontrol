=========================
 Tips and Best Practices
=========================

Caching is hard! It is considered one of the great challenges of
computer science. Fortunatley, the HTTP spec helps to navigate some
pitfalls of invalidation using stale responses. Below are some
suggestions and best practices to help avoid the more subtle issues
that can crop up using CacheControl and HTTP caching.

If you have a suggetions please create a new issue in `github
<https://github.com/ionrock/cachecontrol/issues/>`_ and let folks know
what you ran into and how you fixed it.


Timezones
=========

It is important to remember that the times reported by a server may or
may not be timezone aware. If you are using CacheControl with a
service you control, make sure any timestamps are used consistently,
especially if requests might cross timezones.


Cached Responses
================

We've done our best to make sure cached responses act like a normal
response, but there are aspects that are different for somewhat
obvious reasons.

 - Cached responses are never streaming
 - Cached responses have `None` for the `raw` attribute

Obviously, when you cache a response, you have downloaded the entire
body. Therefore, there is never a use case for streaming a cached
response.

With that in mind, you should be aware that if you try to cache a very
large response on a network store, you still might have some latency
tranferring the data from the network store to your
application. Another consideration is storing large responses in a
`FileCache`. If you are caching using ETags and the server is
extremely specific as to what constitutes an equivalent request, it
could provide many different responses for essentially the same data
within the context of your application.


Query String Params
===================

If you are caching requests that use a large number of query string
parameters, consider sorting them to ensure that the request is
properly cached.

.. note::

  Assuming random parameter order, a request with four parameters
  has a >95% chance of missing the cache on the second time, because
  it grows with the number of permutations (1/24 for four
  parameters, 1/125 for five, etc.). However, this problem doesn't
  arise while the order stays the same. So if the same dict is used
  as params many times it'll likely hit the cache. FileCache suffers
  more from this when used on different Python runs, as this makes
  order more random.

Requests supports passing both dictionaries and lists of tuples as the
param argument in a request. For example: ::

  requests.get(url, params=sorted([('foo', 'one'), ('bar', 'two')]))

By ordering your params, you can be sure the cache key will be
consistent across requests and you are caching effectively.

For convenience, the sorting of query parameters can be done in
cachecontrol itself. For example: ::

  # Unsorted
  sess = cachecontrol.CacheControl(requests.Session(), sort_query=False,
                                   heuristic=ExpiresAfter(days=1))
  params = [('a', 'b'), ('c', 'd')]
  resp = sess.get('http://www.reddit.com', params=params)
  print(resp.from_cache) # False (first fetch)
  resp = sess.get('http://www.reddit.com', params=reversed(params))
  print(resp.from_cache) # False (!)

  sess = cachecontrol.CacheControl(requests.Session(), sort_query=True,
                                   heuristic=ExpiresAfter(days=1))
  params = [('a', 'b'), ('c', 'd')]
  resp = sess.get('http://www.reddit.com', params=params)
  print(resp.from_cache) # False (first fetch)
  resp = sess.get('http://www.reddit.com', params=reversed(params))
  print(resp.from_cache) # True :)

