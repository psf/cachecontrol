..
  SPDX-FileCopyrightText: SPDX-FileCopyrightText: 2015 Eric Larson

  SPDX-License-Identifier: Apache-2.0

.. CacheControl documentation master file, created by
   sphinx-quickstart on Mon Nov  4 15:01:23 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to CacheControl's documentation!
========================================

CacheControl is a port of the caching algorithms in httplib2_ for use with
the requests_ session object.

It was written because httplib2's better support for caching is often
mitigated by its lack of thread-safety. The same is true of requests in
terms of caching.


Install
=======

CacheControl is available from PyPI_. You can install it with pip_ ::

  $ pip install CacheControl

Some of the included cache storage classes have external
requirements. See :doc:`storage` for more info.



Quick Start
===========

For the impatient, here is how to get started using CacheControl:

.. code-block:: python

  import requests

  from cachecontrol import CacheControl


  sess = requests.session()
  cached_sess = CacheControl(sess)

  response = cached_sess.get('http://google.com')


This uses a thread-safe in-memory dictionary for storage.


Tests
=====

The tests are all in ``cachecontrol/tests`` and are runnable by ``py.test``.


Disclaimers
===========

CacheControl is relatively new and might have bugs. I have made an
effort to faithfully port the tests from httplib2 to CacheControl, but
there is a decent chance that I've missed something. Please file bugs
if you find any issues!

With that in mind, CacheControl has been used successfully in
production environments, replacing httplib2's usage.

If you give it a try, please let me know of any issues.


.. _httplib2: https://github.com/httplib2/httplib2
.. _requests: https://requests.readthedocs.io/en/latest/
.. _PyPI: https://pypi.org/project/CacheControl/
.. _pip: https://pip.pypa.io/en/stable/


Contents
========

.. toctree::
   :maxdepth: 2

   usage
   storage
   etags
   custom_heuristics
   tips

.. toctree::
   :hidden:
   :caption: Development
   :maxdepth: 2

   release_notes
   GitHub <https://github.com/psf/cachecontrol>
   PyPI <https://pypi.org/project/cachecontrol>


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
