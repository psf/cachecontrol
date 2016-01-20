import functools

from requests.adapters import HTTPAdapter
from requests.packages.urllib3 import HTTPResponse

from .controller import CacheController
from .cache import DictCache


class CacheControlAdapter(HTTPAdapter):
    invalidating_methods = set(['PUT', 'DELETE'])

    def __init__(self, cache=None,
                 cache_etags=True,
                 controller_class=None,
                 serializer=None,
                 heuristic=None,
                 *args, **kw):
        super(CacheControlAdapter, self).__init__(*args, **kw)
        self.cache = cache or DictCache()
        self.heuristic = heuristic
        self._hooks = {}

        controller_factory = controller_class or CacheController
        self.controller = controller_factory(
            self.cache,
            cache_etags=cache_etags,
            serializer=serializer,
        )

    def send(self, request, **kw):
        """
        Send a request. Use the request information to see if it
        exists in the cache and cache the response if we need to and can.
        """
        if request.method == 'GET':
            cached_response = self.controller.cached_request(request)
            if cached_response:
                return self.build_response(request, cached_response,
                                           from_cache=True)

            # check for etags and add headers if appropriate
            request.headers.update(
                self.controller.conditional_headers(request)
            )

        self._hooks[request] = functools.partial(self.cache_response, request)
        request.register_hook('response', self._hooks[request])
        return super(CacheControlAdapter, self).send(request, **kw)

    def cache_response(self, request, response, **kw):
        if request in self._hooks:
            request.deregister_hook('response', self._hooks.pop(request))
        self.controller.cache_response(request, response.raw, response.content)

    def build_response(self, request, response, from_cache=False):
        """
        Build a response by making a request or using the cache.

        This will end up calling send and returning a potentially
        cached response
        """
        if not from_cache and request.method == 'GET':

            # apply any expiration heuristics
            if response.status == 304:
                # We must have sent an ETag request. This could mean
                # that we've been expired already or that we simply
                # have an etag. In either case, we want to try and
                # update the cache if that is the case.
                cached_response = self.controller.update_cached_response(
                    request, response
                )

                if cached_response is not response:
                    from_cache = True

                # We are done with the server response, read a
                # possible response body (compliant servers will
                # not return one, but we cannot be 100% sure) and
                # release the connection back to the pool.
                response.read(decode_content=False)
                response.release_conn()

                response = cached_response

            # We always cache the 301 responses
            elif response.status == 301:
                self.controller.cache_response(request, response)
            else:
                # Check for any heuristics that might update headers
                # before trying to cache.
                if self.heuristic:
                    response = self.heuristic.apply(response)

        resp = super(CacheControlAdapter, self).build_response(
            request, response
        )

        if from_cache:
            self._remove_processed_encoding_headers(response)

        # See if we should invalidate the cache.
        if request.method in self.invalidating_methods and resp.ok:
            cache_url = self.controller.cache_url(request.url)
            self.cache.delete(cache_url)

        # Give the request a from_cache attr to let people use it
        resp.from_cache = from_cache

        return resp

    def _remove_processed_encoding_headers(self, response):
        self._remove_header(response, 'Transfer-Encoding', ['chunked'])
        self._remove_header(response, 'Content-Encoding',
                            HTTPResponse.CONTENT_DECODERS)

    def _remove_header(self, response, key, values):
        if key not in response.headers:
            return
        response.headers[key] = ', '.join(
            [enc for enc in response.headers.getlist(key) if enc not in values]
        )

    def close(self):
        self.cache.close()
        super(CacheControlAdapter, self).close()
