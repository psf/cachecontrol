from requests.adapters import HTTPAdapter
from cachecontrol import CacheController


class CacheControlAdapter(HTTPAdapter):
    invalidating_methods = set(['PUT', 'DELETE'])

    def __init__(self, cache, *args, **kw):
        super(CacheControlAdapter, self).__init__(*args, **kw)
        self.cache = cache
        self.controller = CacheController(self.cache)

    def send(self, request, **kw):
        """Send a request. Use the request information to see if it
        exists in the cache.
        """
        if request.method == 'GET':
            cached_response = self.controller.cached_request(
                request.url, request.headers
            )
            if cached_response:
                return cached_response

        return super(CacheControlAdapter, self).send(request, **kw)

    def build_response(self, request, response):
        resp = super(CacheControlAdapter, self).build_response(request,
                                                               response)

        # See if we should invalidate the cache.
        if request.method in self.invalidating_methods and resp.ok:
            cache_url = self.controller.cache_url(request.url)
            self.cache.delete(cache_url)

        # Try to store the response if it is a GET
        elif request.method == 'GET':
            self.controller.cache_response(resp)

        return resp
        
        
