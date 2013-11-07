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


Install
=======

CacheControl is available from PyPI_. You can install it with pip_ ::

  $ pip install CacheControl

Some of the included cache storage classes have external
requirements. See :doc:`storage` for more info.



Quick Start
===========

For the impatient, here is how to get started using CacheControl ::

  import requests

  from cachecontrol import CacheControl


  sess = requests.session()
  cached_sess = CacheControl(sess)

  response = cached_sess.get('http://google.com')


This uses a threadsafe in memory dictionary for storage.


ETags and If-* Headers
======================

httplib2 handles etags and if-* headers according to `Editing the
Web`_. I made an effort to include this functionality in CacheControl,
but decided against it for the time being. Hopefully this will change
relatively soon.

In the meant time, you can use the cache storage backend directly. The
use of ETags is primarily described in terms of detecting a lost
update. For example, if you wanted to use the cache'd value when doing
an update (PUT), you could still use the storage object directly: ::

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

      # See if we have an etag of the old content using the cache
      # store
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



Tests
=====

The tests are all in cachecontrol/tests and is runnable by py.test.

TODO
====

 - Support the Vary header (only match when all headers are the same)


Disclaimers
===========

CacheControl is relatively new and maybe totally broken. I have some
tests and it is a pretty direct port of httplib2 caching, which I've
found to be very reliable. With that in mind, it hasn't been used very
extensively in a production environment to my knowledge.

If you give it a try, please let me know of any issues.


.. _httplib2: http://code.google.com/p/httplib2/
.. _requests: http://docs.python-requests.org/
.. _Editing the Web: http://www.w3.org/1999/04/Editing/
.. _PyPI: https://pypi.python.org/pypi/CacheControl/
.. _pip: http://www.pip-installer.org/


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
