..
  SPDX-FileCopyrightText: SPDX-FileCopyrightText: 2026 William Woodruff

  SPDX-License-Identifier: Apache-2.0

=======================
Security Considerations
=======================

HTTP caching is a security-sensitive operation. Improper caching and use
of cached data can introduce security vulnerabilities into otherwise secure
applications.

This page will help you decide if you *can* use CacheControl securely
in your application, and if so, how to do so.

CacheControl's security model
=============================

CacheControl's security model is based on the following assumptions:

* CacheControl provides a **private** cache. This means that both shared
  *and* private responses are cached, and the cache is assumed to be accessible only
  to a single logical user. You **cannot** use CacheControl securely
  in a multi-user environment where cached data may be shared between
  different logical users. **Do not** use CacheControl for this;
  it **will** end badly for you.

* You **must** treat cached data as potentially sensitive. CacheControl
  does not natively encrypt or otherwise protect cached data. If an attacker
  can read your cache, they can read all cached responses. You must
  ensure that your cache storage is protected appropriately for the
  sensitivity of the data you are caching. Another framing of this is that
  CacheControl **assumes** the security of your cache storage, similar to
  how browsers assume the security of your local machine for the purpose
  of storing history, cookies, and cached data.

* You **must** trust the origins (i.e., servers)
  you are communicating with. A malicious origin can always send
  you malicious responses, which in the context of caching can mean
  sending you cacheable responses that you don't expect, spamming you
  with cache entries, and so on. In practice, this means that you must
  also trust your transport layer; if you use HTTP, any
  adversary on your network path can tamper with your connected
  origin's responses, and CacheControl has no way to protect you from that.

Conversely, here are some assumptions that CacheControl **does** attempt
to enforce; violating these assumptions would be a security vulnerability in
CacheControl itself:

* An attacker should not be able to trick CacheControl into caching across
  origins. For example, an attacker who controls ``evil.example.com``
  should not be able to trick CacheControl into caching responses for
  ``bank.example.com``.

* An attacker should not be able to trick CacheControl into serving cached
  responses to requests that would not normally receive those cached
  responses. For example, an attacker should not be able to trick
  CacheControl into serving a cached response to an unauthenticated
  request when the cached response was originally received in response
  to an authenticated request.

Reporting security issues
=========================

.. important::

    Please make sure to read the security model above before reporting
    issues. Reports that don't take the security model into account will
    be considered invalid.

We take security reports very seriously, and aim to address them as quickly
as possible.

Please use GitHub's `security advisory process`_ to report security issues.

.. _security advisory process: https://github.com/psf/cachecontrol/security/advisories/new
