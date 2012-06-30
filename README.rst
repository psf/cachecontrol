===========
 HTTPCache
===========

HTTPCache is a port of the caching algorithms in httplib2_ for use with
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

UPDATE: See: https://github.com/kennethreitz/requests/issues/304


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


Design
======

The CacheControl object's main task is to wrap the GET call of the
session object. The caching takes place by examining the request to
see if it should try to ue the cache. For example, if the request
includes a 'no-cache' or 'max-age=0' Cache-Control header, it will not
try to cache the request. If there is an cached value and its value
has been deemed fresh, the it will return the cached response.

If the request cannot be cached, the actual request is peformed. At
this point we then analyze the response and see if we should add it to
the cache. For example, if the request contains a 'max-age=3600' in
the 'Cache-Control' header, it will cache the response before
returning it to the caller. 


ETags and If-* Headers
======================

httplib2 handles etags and if-* headers according to `Editing the
Web`_. I made an effort to include this functionality in HTTPCache,
but decided against it. The use of ETags is primarily described in
terms of detecting a lost update. As such, even though it uses the
data store's cache, it does not impact when and what is stored.

For example, if you wanted to use the cache'd value when doing an
update (PUT), you could still use the storage object directly: ::

  import json
  import requests

  from mycache import CacheStore
  from httpcache import CacheControl


  sess = CacheControl(requests.session(), 
                      CacheStore())


  url = 'http://host.com/my/file/foo'

  # see if it exists
  resp = sess.head(url)

  # It exists so try to update it
  if resp.status == 200:

      do_update = True

      # See if we have an etag of the old content
      old_resp = sess.cache.get(url)
      if old_resp and 'etag' in old_resp.headers:
          headers = {'Content-Type': 'application/json', 
	             'expect': '100-continue',
                     'if-match': old_resp.headers['etag']}

          # see if we need to do the update            
    	  resp = sess.put(url, headers=headers)
	  if resp.status != 100:
              do_update = False

      if do_update:
          headers = {'Content-Type': 'application/json'}
	  data = json.dumps({'foo': 'bar'})
	  sess.put(url, headers=headers, data=data)


As you can see the actual decision to use PUT and perform an update is
most likely application specific and falls outside the
responsibilities of cache management, which is what HTTPCache is
designed to do.


Tests
=====

The tests are all in httpcache/tests and is runnable by py.test. 

TODO
====

 - Support the Vary header (only match when all headers are the same)


Disclaimers
===========

HTTPCache is brand new and maybe totally broken. I have some tests and
it is a pretty direct port of httplib2 caching, which I've found to be
very reliable. With that in mind, it hasn't been used in a production
environment just yet. If you check it out and find bugs, let me know.


.. _httplib2: http://code.google.com/p/httplib2/
.. _requests: http://docs.python-requests.org/ 
.. _Editing the Web: http://www.w3.org/1999/04/Editing/
