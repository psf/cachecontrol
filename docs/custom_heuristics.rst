===========================
 Custom Caching Strategies
===========================

There are times when a server provides responses that are logically
cacheable, but they lack the headers necessary to cause CacheControl
to cache the response. `The HTTP Caching Spec
<http://tools.ietf.org/html/rfc7234>`_ does allow for caching systems
to cache requests that lack caching headers. In these situations, the
caching system can use heuristics to determine an appropriate amount
of time to cache a response.

By default, in CacheControl the decision to cache must be explicit by
default via the cacheing headers. When there is a need to cache
responses that wouldn't normally be cached, a user can provide a
heuristic to adjust the response in order to make it cacheable.

For example when running a test suite against a service, caching all
responses might be helpful speeding things up while still making real
calls to the API.


Caching Heuristics
==================

A cache heuristic allows specifying a caching strategy by adjusting
response headers before the response is considered for caching.

For example, if we wanted to implement a caching strategy where every
request should be cached for a year, we can implement the strategy in
a `cachecontrol.heuristics.Heuristic`. ::

  import calendar
  from cachecontrol.heuristics import BaseHeuristic
  from email.utils import parsedate, formatdate


  class OneYearHeuristic(BaseHeuristic):

      def update_headers(self, response):
          date = parsedate(response.headers['date'])
          expires = datetime(*date[:6]) + timedelta(years=1)
          headers['expires'] = formatdate(calendar.timegm(expires.timetuple()))
          headers['cache-control'] = 'public'

      def warning(self, response):
          msg = 'Automatically cached! Response is Stale.'
          return '110 - "%s"' % msg


When a response is received and we are testing for whether it is
cacheable, the heuristic is applied before checking its headers. We
also set a `warning header
<http://tools.ietf.org/html/rfc7234#section-5.5>`_ to communicate why
the response might be stale. The original response is passed into the
warning header in order to use its values. For example, if the
response has been expired for more than 24 hours a `Warning 113
<http://tools.ietf.org/html/rfc7234#section-5.5.4>`_ should be used.

In order to use this heuristic, we pass it to our `CacheControl`
constructor. ::


  from requests import Session
  from cachecontrol import CacheControl


  sess = CacheControl(Session(), heuristic=OneYearHeuristic())
  sess.get('http://google.com')
  r = sess.get('http://google.com')
  assert r.from_cache

The google homepage specifically uses a negative expires header and
private cache control header to avoid caches. We've managed to work
around that aspect and cache the response using our heuristic.


Best Practices
==============

Cache heuristics are still a new feature, which means that the support
is somewhat rudimentary. There likely to be best practices and common
heuristics that can meet the needs of many use cases. For example, in
the above heuristic it is important to change both the `expires` and
`cache-control` headers in order to make the response cacheable.

If you do find a helpful best practice or create a helpful heuristic,
please consider sending a pull request or opening a issue.


Site Specific Heuristics
------------------------

If you have a specific domain that you want to apply a specific
heuristic to, use a separate adapter. ::

  import requests
  from cachecontrol import CacheControlAdapter
  from mypkg import MyHeuristic


  sess = requests.Session()
  sess.mount(
      'http://my.specific-domain.com',
      CacheControlAdapter(heuristic=MyHeuristic())
  )

In this way you can limit your heuristic to a specific site.


Warning!
========

Caching is hard and while HTTP does a reasonable job defining rules
for freshness, overriding those rules should be done with
caution. Many have been frustrated by over aggressive caches, so
please carefully consider your use case before utilizing a more
aggressive heuristic.
