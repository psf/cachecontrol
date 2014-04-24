===============
 Release Notes
===============


0.10.0
======

This is an important release as it changes what is actually
cached. Rather than caching requests' Response objects, we are now
caching the underlying urllib3 response object. Also, the response
will not be cached unless the response is actually consumed by the user.

These changes allowed the reintroduction of .raw support.

Huge thanks goes out to @dstufft for these excellent patches and
putting so much work into CacheControl to allow cached responses to
behave exactly as a normal response.

 - FileCache Updates (via `@dstufft <https://github.com/dstufft>`_)

   - files are now hashed via sha-2

   - files are stored in a namespaced directory to avoid hitting os
     limits on the number of files in a directory.

   - use the io.BytesIO when reading / writing (via `@alex
     <https://github.com/alex>`_)

 - `#19 <https://github.com/ionrock/cachecontrol/pull/19>`_ Allow for
   a custom controller via `@cournape <https://github.com/cournape>`_

 - `#17 <https://github.com/ionrock/cachecontrol/pull/17>`_ use
   highest protocol version for pickling via `@farwayer <https://github.com/farwayer>`_

 - `#16 <https://github.com/ionrock/cachecontrol/pull/16>`_ FileCache:
   raw field serialization via `@farwayer <https://github.com/farwayer>`_


0.9.3
=====

 - `#16 <https://github.com/ionrock/cachecontrol/pull/16>`_: All
   cached responses get None for a raw attribute.

 - `#13 <https://github.com/ionrock/cachecontrol/pull/13>`_ Switched
   to md5 encoded keys in file cache (via `@mxjeff
   <http://github.com/mxjeff>`_)

 - `#11 <http://github.com/ionrock/cachecontrol/pull/11>`_ Fix
   timezones in tests (via `@kaliko <http://github.com/kaliko>`_)
