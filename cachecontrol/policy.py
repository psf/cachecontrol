# SPDX-FileCopyrightText: © 2019 The cachecontrol Authors
# SPDX-License-Identifier: Apache-2.0
"""Implement policy decision on caching requests and responses.

Providing the right decision on whether to cache or not cache a response, given a
request, is a complex matter that is governed by RFC 7234:
https://httpwg.org/specs/rfc7234.html

This module focuses on providing the answer to the following questions:
 - Can this request be answered from the cache?
 - Is this cached response still valid?
 - Can this new response be cached?
"""

import datetime
import http
import logging
from email.utils import parsedate_to_datetime

import pytz
from requests.structures import CaseInsensitiveDict
from six.moves import http_client

from .headers_parser import tokenize_cache_control, tokenize_pragma

logger = logging.getLogger(__name__)


# While RFC7234 allows caching methods other than GET, for now focus on caching the safe
# requests. There's a few other differences for methods such as HEAD, that can
# invalidate a cache, and can in some cases generate a new cache entry (e.g. permanent
# redirects), but not cache the whole content.
_CACHEABLE_METHODS = {
    "GET",
}

# We want to explicitly allow the safe methods, rather than disallow the invalidating
# one, as the RFC is clear that "A cache MUST invalidate ... when it receives a
# non-error response to a request with a method whose safety is unknown."
_SAFE_METHODS = {
    "GET",
    "HEAD",
}

_CACHEABLE_STATUS_CODES = {
    http_client.OK,
    http_client.NON_AUTHORITATIVE_INFORMATION,
    http_client.MULTIPLE_CHOICES,
    http_client.MOVED_PERMANENTLY,
    308,  # PERMANENT_REDIRECT
}

_PERMANENT_REDIRECT_CODES = {
    http_client.MOVED_PERMANENTLY,
    308,  # PERMANENT_REDIRECT
}


def use_cache_for_request(request, cacheable_methods=None):
    """Decide whether the provided request can be answered from cache.

    Args:
      request: The HTTPRequest object that is yet to be sent to the server.
      cacheable_methods: The list of methods to consider cacheable.

    Returns:
      False if the request is explicitly asking not to answer from a cached response,
      True otherwise.
    """

    if cacheable_methods is None:
        cacheable_methods = _CACHEABLE_METHODS

    if request.method not in cacheable_methods:
        logger.debug("Ignoring cache: method %r is not cacheable", request.method)
        return False

    request_headers = CaseInsensitiveDict(request.headers)
    req_cache_control_header = request_headers.get("cache-control", "")
    req_cache_control = tokenize_cache_control(req_cache_control_header)

    if "no-store" in req_cache_control:
        logger.debug(
            "Ignoring cache: request Cache-Control includes 'no-store' directive: %r",
            req_cache_control_header,
        )
        return False

    if "authorization" in request_headers:
        logger.debug("Ignoring cache: request includes 'Authorization'header")
        return False

    return True


def _response_expiration_datetime(
    response, request_datetime=None, shared_cache=False, max_age_override=None
):
    """Calculate the expiration datetime for a given response.

    Args:
      response: The HTTPResponse object to calculate the expiration of.
      request_datetime: Optional datetime object to assume the request was sent at.
        Only used if the response does not have a Date header.
      shared_cache: Whether to consider the cache a shared cache per RFC7234.
      max_age_override: If provided, this value in seconds will be used as the max age
        for the response.

    Returns:
      A datetime.datetime object representing the moment the request is considered
      expired.
    """
    response_headers = CaseInsensitiveDict(response.headers)
    resp_cache_control_header = response_headers.get("cache-control", "")
    resp_cache_control = tokenize_cache_control(resp_cache_control_header)

    if "date" in response_headers:
        response_datetime = parsedate_to_datetime(response_headers["date"])
    elif request_datetime:
        logger.debug("Missing Date header from request, assuming %s", request_datetime)
        response_datetime = request_datetime
    else:
        logger.debug("Missing response timestamp, no expiration assumed")
        return None

    # https://httpwg.org/specs/rfc7234.html#header.age
    if "age" in response_headers:
        response_datetime += datetime.timedelta(seconds=int(response_header["age"]))

    if max_age_override:
        max_age = max_age_override
    else:
        max_age = resp_cache_control.get("max-age", None)
        # https://httpwg.org/specs/rfc7234.html#cache-response-directive.s-maxage
        if shared_cache:
            max_age = resp_cache_control.get("s-maxage", max_age)

    # If any max_age directive or override is present, those control the expiration.
    if max_age is not None:
        expiration = response_datetime + datetime.timedelta(seconds=int(max_age))
        logger.debug("Expiration time: %s (max-age / s-maxage directives)", expiration)
    elif "expires" in response_headers:
        expiration = parsedate_to_datetime(response_headers["expires"])
        logger.debug("Expiration time: %s (Expires header)", expiration)
    elif "last-modified" in response_headers:
        # https://httpwg.org/specs/rfc7234.html#heuristic.freshness
        #
        #   There's no expiration defined as part of the response, we need to
        #   heuristically define an expiration for the request.
        last_modified_datetime = parsedate_to_datetime(
            response_headers["last-modified"]
        )
        modification_delta = response_datetime - last_modified_datetime
        expiration = response_datetime + modification_delta * 0.1  # 10%
        logger.debug("Expiration time: %s (heuristic)", expiration)
    else:
        logger.debug("Unable to identify a valid expiration time")
        return None

    return expiration


def is_response_fresh(request, cached_response, shared_cache=False):
    """Decide whether the cached response is still fresh enough for the request.

    Note that this depends on the request: a cached response might still not be expired,
    but not fresh enough for the provided request.

    Args:
      request: The HTTPRequest object that is yet to be sent to the server.
      cached_response: The HTTPResponse object stored in the cache to evaluate.
      shared_cache: Whether to consider the cache a shared cache per RFC7234.

    Returns:
      True if the cached response is still fresh enough for the request, False
      otherwise.
    """
    response_headers = CaseInsensitiveDict(cached_response.headers)
    resp_cache_control_header = response_headers.get("cache-control", "")
    resp_cache_control = tokenize_cache_control(resp_cache_control_header)

    request_headers = CaseInsensitiveDict(request.headers)
    req_cache_control_header = request_headers.get("cache-control", "")
    req_cache_control = tokenize_cache_control(req_cache_control_header)

    if "no-cache" in req_cache_control:
        logger.debug(
            "Cached response is not fresh: request Cache-Control includes 'no-cache' directive: %r",
            req_cache_control_header,
        )
        return False

    # https://httpwg.org/specs/rfc7234.html#header.pragma
    #
    #  The Pragma header is only specified for requests, not responses, and is ignored
    #  if Cache-Control is provided.
    if "cache-control" not in request_headers:
        pragma = tokenize_pragma(request_headers.get("pragma", ""))
        if "no-cache" in pragma:
            logger.debug(
                "Cached response is not fresh: request includes a 'Pragma: no-cache' header"
            )
            return False

    if "no-cache" in resp_cache_control:
        logger.debug(
            "Cached response is not fresh: response Cache-Control includes 'no-cache' directive: %r",
            resp_cache_control_header,
        )
        return False

    if "must-revalidate" in resp_cache_control:
        logger.debug(
            "Cached response is not fresh: response Cache-Control includes 'must-revalidate' directive: %r",
            resp_cache_control_header,
        )
        return False

    if req_cache_control.get("max-age", None) == "0":
        logger.debug(
            "Cache response is not fresh: request Cache-Control includes 'max-age=0' directive: %r",
            req_cache_control_header,
        )
        return False

    # If the cached response is a permanent redirect, consider it always fresh (minus
    # the Cache-Control directives above), since it does not require an explicit
    # expiration.
    if int(cached_response.status) in _PERMANENT_REDIRECT_CODES:
        logger.debug("Cached response is fresh: permanent redirect")
        return True

    if "max-age" in req_cache_control:
        max_age_override = int(req_cache_control["max-age"])
    else:
        max_age_override = None

    expiration = _response_expiration_datetime(
        cached_response, max_age_override=max_age_override, shared_cache=shared_cache
    )
    if not expiration:
        logger.debug(
            "Cached response is not fresh: unable to identify a valid expiration time."
        )
        return False

    # https://httpwg.org/specs/rfc7234.html#cache-request-directive.max-stale
    #
    #   If the request is allowing stale response, extend the expiration by how much it
    #   was required.
    expiration += datetime.timedelta(int(req_cache_control.get("max-stale", 0)))

    # https://httpwg.org/specs/rfc7234.html#cache-request-directive.min-fresh
    #
    #   If the request is asking for a response that is valid for longer, include that
    #   in the frehsness horizon.
    freshness_horizon = pytz.UTC.localize(datetime.datetime.utcnow())
    freshness_horizon += datetime.timedelta(int(req_cache_control.get("min-fresh", 0)))

    if freshness_horizon > expiration:
        logger.debug("Cached response is not fresh: expiration time already passed.")
        return False

    logger.debug("Cached response is fresh.")
    return True


def can_cache_response(response, cacheable_status_codes=None, shared_cache=False):
    """Decide whether the provided response can be stored in cache.

    Args:
      response: The *new* HTTPResponse object that was returned by the server.
      cacheable_status_codes: A container of integer status codes that are considered
        cacheable.
      shared_cache: Whether to consider the cache a shared cache per RFC7234.

    Returns:
      True if the received response is cacheable. False otherwise.
    """

    if cacheable_status_codes is None:
        cacheable_status_codes = _CACHEABLE_STATUS_CODES

    # Don't cache errors, temporary statuses, or non-OK return codes.
    if int(response.status) not in cacheable_status_codes:
        logger.debug("Not caching: status code %r is not cacheable", response.status)
        return False

    response_headers = CaseInsensitiveDict(response.headers)
    resp_cache_control_header = response_headers.get("cache-control", "")
    resp_cache_control = tokenize_cache_control(resp_cache_control_header)

    if "no-store" in resp_cache_control or "private" in resp_cache_control:
        logger.debug(
            "Not caching: response Cache-Control includes 'no-store' or 'private' directives: %r",
            resp_cache_control_header,
        )
        return False

    # https://httpwg.org/specs/rfc7234.html#caching.negotiated.responses
    #
    #   A Vary header field-value of "*" always fails to match.  Storing such a response
    #   leads to a deserialization warning during cache lookup and is not allowed to
    #   ever be served, so storing it can be avoided.
    if "*" in response_headers.get("vary", ""):
        logger.debug("Not caching: response contains 'Vary: *'")
        return False

    if int(response.status) in _PERMANENT_REDIRECT_CODES:
        logger.debug("Caching: permanent redirect")
        return True

    now = pytz.UTC.localize(datetime.datetime.utcnow())
    if "date" in response_headers:
        response_datetime = parsedate_to_datetime(response_headers["date"])
        # https://httpwg.org/specs/rfc7231.html#header.date
        #
        #   Date is supposed to always be in GMT, but it's not always returned
        #   correctly. If no timezone data was provided, assume GMT.
        if not response_datetime.tzinfo:
            pytz.UTC.localize(response_datetime)
    else:
        logger.debug("Missing Date header from request, assuming current.")
        response_datetime = now

    expiration = _response_expiration_datetime(
        response, request_datetime=now, shared_cache=shared_cache
    )

    if not expiration:
        logger.debug("Not caching: unable to identify a valid expiration time")
        return False

    if now > expiration:
        logger.debug("Not caching: expiration time already passed.")
        return False

    logger.debug("Caching: no reason not to")
    return True


def is_invalidating_cache(request, new_response):
    """Decide whether a given request/response pair invalidates the cached values.

    Args:
      request: The HTTPRequest sent to the server (does not need to have been sent
        through the cache.
      response: The HTTPResponse received from the server (not the one in cache.)

    Returns:
      True if the received response should invalidate the cached response, otherwise
      False.
    """

    response_status = int(new_response.status)
    # https://httpwg.org/specs/rfc7234.html#invalidation
    #
    #   Non-error response is defined as a 2xx or 3xx status, everything else can be
    #   considered an error and ignore it.
    if not 200 <= response_status <= 399:
        logger.debug(
            "Not invalidating: response contains an error status: %r",
            new_response.status,
        )
        return False

    if request.method not in _SAFE_METHODS:
        logger.debug("Invalidating: request method not known safe: %r", request.method)
        return True

    logger.debug("Not invalidating request.")
    return False
