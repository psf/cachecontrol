.. CacheControl documentation master file, created by
   sphinx-quickstart on Mon Nov  4 15:01:23 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to CacheControl's documentation!
========================================

CacheControl is a port of the caching algorithms in httplib2_ for use with
requests_ session object.

It was written because httplib2's better support for caching is often
mitigated by its lack of threadsafety. The same is true of requests in
terms of caching.


Quick Start
===========

For the impatient, here is how to get started using CacheControl ::

  import requests

  from cachecontrol import CacheControl


  sess = requests.session()
  cached_sess = CacheControl(sess)

  response = cached_sess.get('http://google.com')


This uses a threadsafe in memory dictionary for storage.


Cache Implementations
=====================

CacheControl comes with a simple, threadsafe, in memory dictionary
like cache. Implementing a cache interface is simply a matter of
inheriting from the BaseCache or implementing the necessary methods.

To make it clear how simple this is, here is the base class: ::

  class BaseCache(object):

      def get(self, key):
          raise NotImplemented()

      def set(self, key, value):
          raise NotImplemented()

      def delete(self, key):
          raise NotImplemented()


See? Simple.


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
Web`_. I made an effort to include this functionality in CacheControl,
but decided against it. The use of ETags is primarily described in
terms of detecting a lost update. As such, even though it uses the
data store's cache, it does not impact when and what is stored.

For example, if you wanted to use the cache'd value when doing an
update (PUT), you could still use the storage object directly: ::

  import json
  import requests

  from mycache import CacheStore
  from cachecontrol import CacheControl


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
responsibilities of cache management, which is what CacheControl is
designed to do.


Tests
=====

The tests are all in cachecontrol/tests and is runnable by py.test.

TODO
====

 - Support the Vary header (only match when all headers are the same)


Disclaimers
===========

CacheControl is brand new and maybe totally broken. I have some tests and
it is a pretty direct port of httplib2 caching, which I've found to be
very reliable. With that in mind, it hasn't been used in a production
environment just yet. If you check it out and find bugs, let me know.


.. _httplib2: http://code.google.com/p/httplib2/
.. _requests: http://docs.python-requests.org/
.. _Editing the Web: http://www.w3.org/1999/04/Editing/


Contents:

.. toctree::
   :maxdepth: 2

   usage
   storage



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
