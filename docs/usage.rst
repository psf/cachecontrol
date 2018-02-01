====================
 Using CacheControl
====================

CacheControl assumes you are using a `requests.Session` for your
requests. If you are making ad-hoc requests using `requests.get` then
you probably are not terribly concerned about caching.

There are two way to use CacheControl, via the wrapper and the
adapter.


Wrapper
=======

The easiest way to use CacheControl is to utilize the basic
wrapper. Here is an example: ::

  import requests
  import cachecontrol

  sess = cachecontrol.CacheControl(requests.Session())
  resp = sess.get('http://google.com')

This uses the default cache store, a thread safe in-memory dictionary.


Adapter
=======

The other way to use CacheControl is via a requests `Transport
Adapter`_.

Here is how the adapter works: ::

  import requests
  import cachecontrol

  sess = requests.Session()
  sess.mount('http://', cachecontrol.CacheControlAdapter())

  resp = sess.get('http://google.com')


Under the hood, the wrapper method of using CacheControl mentioned
above is the same as this example.


Use a Different Cache Store
===========================

Both the wrapper and adapter classes allow providing a custom cache
store object for storing your cached data. Here is an example using
the provided `FileCache` from CacheControl: ::

  import requests

  from cachecontrol import CacheControl

  # NOTE: This requires lockfile be installed
  from cachecontrol.caches import FileCache

  sess = CacheControl(requests.Session(),
                      cache=FileCache('.webcache'))


The `FileCache` will create a directory called `.webcache` and store a
file for each cached request.



.. _Transport Adapter: http://docs.python-requests.org/en/latest/user/advanced/#transport-adapters
