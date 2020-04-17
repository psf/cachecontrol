# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

"""
The httplib2 algorithms ported for use with requests.
"""
import calendar
import logging
import re
import time

from requests.structures import CaseInsensitiveDict

from .cache import DictCache
from .policy import (
    can_cache_response,
    is_invalidating_cache,
    is_response_fresh,
    use_cache_for_request,
)
from .serialize import Serializer

logger = logging.getLogger(__name__)

URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")


def parse_uri(uri):
    """Parses a URI using the regex given in Appendix B of RFC 3986.

        (scheme, authority, path, query, fragment) = parse_uri(uri)
    """
    groups = URI.match(uri).groups()
    return (groups[1], groups[3], groups[4], groups[6], groups[8])


class CacheController(object):
    """An interface to see if request should cached or not.
    """

    def __init__(
        self, cache=None, serializer=None, status_codes=None, cacheable_methods=None,
    ):
        self.cache = DictCache() if cache is None else cache
        self.serializer = serializer or Serializer()
        self.cacheable_status_codes = status_codes
        self.cacheable_methods = cacheable_methods

    @classmethod
    def _urlnorm(cls, uri):
        """Normalize the URL to create a safe key for the cache"""
        (scheme, authority, path, query, fragment) = parse_uri(uri)
        if not scheme or not authority:
            raise Exception("Only absolute URIs are allowed. uri = %s" % uri)

        scheme = scheme.lower()
        authority = authority.lower()

        if not path:
            path = "/"

        # Could do syntax based normalization of the URI before
        # computing the digest. See Section 6.2.2 of Std 66.
        request_uri = query and "?".join([path, query]) or path
        defrag_uri = scheme + "://" + authority + request_uri

        return defrag_uri

    @classmethod
    def cache_url(cls, uri):
        return cls._urlnorm(uri)

    def cached_request(self, request, cacheable_methods=None):
        """
        Return a cached response if it exists in the cache, otherwise
        return False.
        """
        if not use_cache_for_request(request, cacheable_methods=cacheable_methods):
            return False

        cache_url = self.cache_url(request.url)
        logger.debug('Looking up "%s" in the cache', cache_url)

        # Request allows serving from the cache, let's see if we find something
        cache_data = self.cache.get(cache_url)
        if cache_data is None:
            logger.debug("No cache entry available")
            return False

        # Check whether it can be deserialized
        resp = self.serializer.loads(request, cache_data)
        if not resp:
            logger.warning("Cache entry deserialization failed, entry ignored")
            return False

        try:
            if is_response_fresh(request, resp):
                return resp
        except Exception:
            return False

        # return the original handler
        return False

    def add_conditional_headers(self, request):
        cache_url = self.cache_url(request.url)
        logger.debug("Applying conditional headers to request for %s", cache_url)
        resp = self.serializer.loads(request, self.cache.get(cache_url))

        if resp:
            cached_headers = CaseInsensitiveDict(resp.headers)
            etag = cached_headers.get("etag", None)
            last_modified = cached_headers.get("last-modified", None)

            if etag is not None:
                logger.debug("Adding If-None-Match: %s", etag)
                request.headers["if-none-match"] = etag

            if last_modified is not None:
                logger.debug("Adding If-Modified-Since: %s", last_modified)
                request.headers["if-modified-since"] = last_modified

    def cache_response(self, request, response, body=None, status_codes=None):
        """
        Algorithm for caching requests.

        This assumes a requests Response object.
        """
        # From httplib2: Don't cache 206's since we aren't going to
        #                handle byte range requests
        cacheable_status_codes = status_codes or self.cacheable_status_codes

        # If we've been given a body, our response has a Content-Length, that
        # Content-Length is valid then we can check to see if the body we've been given
        # matches the expected size, and if it doesn't we'll just skip trying to cache
        # it.
        if body is not None:
            response_headers = CaseInsensitiveDict(response.headers)
            content_length = response_headers.get("content-length", None)
            try:
                if int(content_length) != len(body):
                    logger.debug("Not caching response with invalid Content-Length")
                    return
            except (ValueError, TypeError):
                pass

        try:
            if not use_cache_for_request(request):
                logger.warning(
                    "Trying to cache the response to a request skipping cache."
                )
                return

            can_cache = can_cache_response(response)
        except Exception:
            logger.debug(
                "Exception occurred while verifying whether response can be cached, not caching."
            )
            return

        if can_cache:
            cache_url = self.cache_url(request.url)
            self.cache.set(cache_url, self.serializer.dumps(request, response, body))

    def update_cached_response(self, request, response):
        """On a 304 we will get a new set of headers that we want to
        update our cached value with, assuming we have one.

        This should only ever be called when we've sent an ETag and
        gotten a 304 as the response.
        """

        # Special case: we can cache a 304 code, but only because we're trying
        # to cache the new response.
        try:
            if not can_cache_response(response, cacheable_status_codes={200, 304}):
                logger.debug("Not updating cached response.")
                return response
        except Exception:
            logger.debug(
                "Exception occurred while verifying whether cached response can be updated, not updating."
            )
            return response

        cache_url = self.cache_url(request.url)

        cached_response = self.serializer.loads(request, self.cache.get(cache_url))

        if not cached_response:
            # we didn't have a cached response
            return response

        # Lets update our headers with the headers from the new request:
        # http://tools.ietf.org/html/draft-ietf-httpbis-p4-conditional-26#section-4.1
        #
        # The server isn't supposed to send headers that would make
        # the cached body invalid. But... just in case, we'll be sure
        # to strip out ones we know that might be problmatic due to
        # typical assumptions.
        excluded_headers = ["content-length"]

        cached_response.headers.update(
            dict(
                (k, v)
                for k, v in response.headers.items()
                if k.lower() not in excluded_headers
            )
        )

        # we want a 200 b/c we have content via the cache
        cached_response.status = 200

        # update our cache
        body = cached_response.read(decode_content=False)
        self.cache.set(cache_url, self.serializer.dumps(request, cached_response, body))

        return cached_response

    def maybe_invalidate_cache(self, request, response):
        try:
            invalidate_cache = is_invalidating_cache(request, response)
        except Exception:
            logger.debug(
                "Exception occurred while verifying whether cache should be invalidated. Invalidating for safety."
            )
            invalidate_cache = True

        if invalidate_cache:
            # TODO: https://httpwg.org/specs/rfc7234.html#invalidation says that the
            # cache MUST invalidate Location and Content-Location URLs if present, _if_
            # they are in the same host.
            cache_url = self.cache_url(request.url)
            logger.debug("Invalidating cache for %s", cache_url)
            self.cache.delete(cache_url)
