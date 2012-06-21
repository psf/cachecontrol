===========
 httpcache
===========

Httpcache is a port of the caching algorithms in httplib2_ for use with
requests_ session object. 

It was written because httplib2's better support for caching is often
mitigated by its lack of threadsafety. The same is true of requests in
terms of caching.


Usage
=====

NOTE: Eventually, my hope is that this module can be integrated directly
into requests. That said, I've had minimal exposure to requests, so I
expect the initial implementation to be rather un-requests-like in
terms of its API. Suggestions and patches welcome!

Here is the basic usage: ::

  import requests

  from httpcache import CacheControl


  sess = requests.session()
  cached_sess = CacheControl(sess)

  response = cached_sess.get('http://google.com')

If the URL contains any caching based headers, it will cache the
result in a simple dictionary. 

Below is the implementation of the DictCache, the default cache
backend. It is extremely simple and shows how you would implement some
other cache backend: ::

  from httpcache.cache import BaseCache


  class DictCache(BaseCache):
   
      def __init__(self, init_dict=None):
          self.data = init_dict or {}
   
      def get(self, key):
          return self.data.get(key, None)
   
      def set(self, key, value):
          self.data.update({key: value})
   
      def delete(self, key):
          self.data.pop(key)

  

See? Really simple.


Development
===========

The tests are all in httpcache/tests and is runnable by py.test. 


TODO
====

 - Better integration with requests
 - Support for HTTP 1.0 caching a response with Expires
 - Tests that run a server from the stdlib
