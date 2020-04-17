# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

import functools
import logging
import types
import zlib

from requests.adapters import HTTPAdapter

from .cache import DictCache
from .controller import CacheController
from .filewrapper import CallbackFileWrapper
from .policy import use_cache_for_request

logger = logging.getLogger(__name__)


class CacheControlAdapter(HTTPAdapter):
    def __init__(
        self,
        cache=None,
        controller_class=None,
        serializer=None,
        cacheable_methods=None,
        *args,
        **kw
    ):
        super(CacheControlAdapter, self).__init__(*args, **kw)
        self.cache = DictCache() if cache is None else cache
        self.cacheable_methods = cacheable_methods

        controller_factory = controller_class or CacheController
        self.controller = controller_factory(
            self.cache, serializer=serializer, cacheable_methods=cacheable_methods,
        )

    def send(self, request, cacheable_methods=None, **kw):
        """
        Send a request. Use the request information to see if it
        exists in the cache and cache the response if we need to and can.
        """
        try:
            cached_response = self.controller.cached_request(
                request, cacheable_methods=cacheable_methods
            )
        except zlib.error:
            cached_response = None
        if cached_response:
            return self.build_response(request, cached_response, from_cache=True)

        self.controller.add_conditional_headers(request)

        resp = super(CacheControlAdapter, self).send(request, **kw)

        return resp

    def build_response(
        self, request, response, from_cache=False, cacheable_methods=None
    ):
        """
        Build a response by making a request or using the cache.

        This will end up calling send and returning a potentially
        cached response
        """
        if not from_cache and use_cache_for_request(
            request, cacheable_methods=cacheable_methods
        ):
            if response.status == 304:
                logger.debug("Received a 'Not Modified' response.")

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

            else:
                # Wrap the response file with a wrapper that will cache the
                #   response when the stream has been consumed.
                response._fp = CallbackFileWrapper(
                    response._fp,
                    functools.partial(
                        self.controller.cache_response, request, response
                    ),
                )
                if response.chunked:
                    super_update_chunk_length = response._update_chunk_length

                    def _update_chunk_length(self):
                        super_update_chunk_length()
                        if self.chunk_left == 0:
                            self._fp._close()

                    response._update_chunk_length = types.MethodType(
                        _update_chunk_length, response
                    )

        resp = super(CacheControlAdapter, self).build_response(request, response)

        # See if we should invalidate the cache.
        self.controller.maybe_invalidate_cache(request, response)

        # Give the request a from_cache attr to let people use it
        resp.from_cache = from_cache

        return resp

    def close(self):
        self.cache.close()
        super(CacheControlAdapter, self).close()
