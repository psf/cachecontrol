..
  SPDX-FileCopyrightText: SPDX-FileCopyrightText: 2015 Eric Larson

  SPDX-License-Identifier: Apache-2.0

===============
 Release Notes
===============

0.14.0
======

* Explicitly allow ``pathlib.Path`` as a type for ``FileCache.directory``.
* Don't use the cache to return a full response if a request has a Range header.

0.13.1
======

* Support for old serialization formats has been removed.
* Move the serialization implementation into own method.
* Drop support for Python older than 3.7.

0.13.0
======

**YANKED**

The project has been moved to the `PSF <https://github.com/psf>`_ organization.

* Discard the ``strict`` attribute when serializing and deserializing responses.
* Fix the ``IncompleteRead`` error thrown by ``urllib3 2.0``.
* Remove usage of ``utcnow`` in favor of timezone-aware datetimes.
* Remove the ``compat`` module.
* Use Python's ``unittest.mock`` library instead of ``mock``.
* Add type annotations.
* Exclude the ``tests`` directory from the wheel.

0.12.14
=======

* Revert the change "switch lockfile to filelock" to fix the compatibility issue.

0.12.13
=======

* Discard the ``strict`` attribute when serializing and deserializing responses.
* Fix the IncompleteRead error thrown by ``urllib3`` 2.0.
* Exclude the tests directory from the wheel.

0.12.11
=======

* Added new variant of ``FileCache``, ``SeparateBodyFileCache``, which uses less memory by storing the body in a separate file than metadata, and streaming data in and out directly to/from that file. Implemented by [Itamar Turner-Trauring](https://pythonspeed.com), work sponsored by [G-Research](https://www.gresearch.co.uk/technology-innovation-and-open-source/).

0.12.7
======

* Dropped support for Python 2.7, 3.4, 3.5.
* Reduced memory usage when caching large files.

0.12.0
======

Rather than using compressed JSON for caching values, we are now using
MessagePack (http://msgpack.org/). MessagePack has the advantage that
that serialization and deserialization is faster, especially for
caching large binary payloads.


0.11.2
======

This release introduces the `cachecontrol.heuristics.LastModified`
heuristic. This uses the same behaviour as many browsers to base expiry on the
`Last-Modified` header when no explicit expiry is provided.


0.11.0
======

The biggest change is the introduction of using compressed JSON rather
than pickle for storing cached values. This allows Python 3.4 and
Python 2.7 to use the same cache store. Previously, if a cache was
created on 3.4, a 2.7 client would fail loading it, causing an invalid
cache miss. Using JSON also avoids the exec call used in pickle,
making the cache more secure by avoiding a potential code injection
point. Finally, the compressed JSON is a smaller payload, saving a bit
of space.

In order to support arbitrary binary data in the JSON format, base64
encoding is used to turn the data into strings. It has to do some encoding dances
to make sure that the bytes/str types are correct, so **please** open
a new issue if you notice any issues.

This release also introduces the
`cachecontrol.heuristics.ExpiresAfter` heuristic. This allows passing
in arguments like a `datetime.timedelta` in order to configure that
all responses are cached for the specific period of time.


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
