import requests

from cachecontrol.controller import CacheController
from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.cache import DictCache


def CacheControl(sess, cache=None):
    cache = cache or DictCache()
    sess.mount('http://', CacheControlAdapter(cache))
    return sess


class _CacheControl(object):

    def __init__(self, session, cache=None):
        self.session = session
        self.cache = cache or DictCache()
        self.controller = CacheController(self.cache)

    def __getattr__(self, key):
        if hasattr(self.session, key):
            return getattr(self.session, key)
        raise AttributeError('%s not found' % key)

    def cached_request(self, *args, **kw):
        """
        See if we should use a cached response. We are looking for
        client conditions such as no-cache and testing our cached
        value to see if we should use it or not.

        This is taken almost directly from httplib2._entry_disposition
        """
        req = requests.Request(*args, **kw)
        return self.controller.cached_request(req.url, req.headers)

    def from_cache(f):
        """
        A decorator that allows using a cached response.
        """
        def cached_handler(self, *args, **kw):
            # If we have a cached response use it
            cached_response = self.cached_request(*args, **kw)
            if cached_response:
                return cached_response

            # Else return original function's response
            return f(self, *args, **kw)
        return cached_handler

    def invalidates_cache(f):
        """
        A decorator for marking methods that can invalidate the cache.
        """

        def invalidating_handler(self, *args, **kw):
            resp = f(self, *args, **kw)
            if resp.ok:
                cache_url = self.controller.cache_url(resp.request.url)
                self.cache.delete(cache_url)
            return resp
        return invalidating_handler

    # Handler wrappers
    # NOTE: We create a _verb method b/c we need the verb in order to
    #       create the Request object and handle the caching
    #       correctly.
    def get(self, url, headers=None, *args, **kw):
        return self._get('GET', url, headers, *args, **kw)

    def put(self, url, headers=None, *args, **kw):
        return self._put('PUT', url, headers, *args, **kw)

    def delete(self, url, headers=None, *args, **kw):
        return self._delete('DELETE', url, headers, *args, **kw)

    @from_cache
    def _get(self, verb, url, headers=None, *args, **kw):
        resp = self.session.request(verb, url, headers=headers, *args, **kw)
        # We set this primarily for testing
        resp.from_cache = False

        # See if we need to cache the response
        self.controller.cache_response(resp)

        # actually return the repsonse
        return resp

    @invalidates_cache
    def _put(self, *args, **kw):
        return self.session.put(*args, **kw)

    @invalidates_cache
    def _delete(self, *args, **kw):
        return self.session.delete(*args, **kw)
