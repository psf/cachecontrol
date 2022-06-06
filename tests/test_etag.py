# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from mock import Mock, patch

import requests

from cachecontrol import CacheControl
from cachecontrol.cache import DictCache
from cachecontrol.compat import urljoin
from .utils import NullSerializer


class TestETag(object):
    """Test our equal priority caching with ETags

    Equal Priority Caching is a term I've defined to describe when
    ETags are cached orthgonally from Time Based Caching.
    """

    @pytest.fixture()
    def sess(self, url):
        self.etag_url = urljoin(url, "/etag")
        self.update_etag_url = urljoin(url, "/update_etag")
        self.cache = DictCache()
        sess = CacheControl(
            requests.Session(), cache=self.cache, serializer=NullSerializer()
        )
        yield sess

        # closing session object
        sess.close()

    def test_etags_get_example(self, sess, server):
        """RFC 2616 14.26

        The If-None-Match request-header field is used with a method to make
        it conditional. A client that has one or more entities previously
        obtained from the resource can verify that none of those entities
        is current by including a list of their associated entity tags in
        the If-None-Match header field. The purpose of this feature is to
        allow efficient updates of cached information with a minimum amount
        of transaction overhead

        If any of the entity tags match the entity tag of the entity that
        would have been returned in the response to a similar GET request
        (without the If-None-Match header) on that resource, [...] then
        the server MUST NOT perform the requested method, [...]. Instead, if
        the request method was GET or HEAD, the server SHOULD respond with
        a 304 (Not Modified) response, including the cache-related header
        fields (particularly ETag) of one of the entities that matched.

        (Paraphrased) A server may provide an ETag header on a response. On
        subsequent queries, the client may reference the value of this Etag
        header in an If-None-Match header; on receiving such a header, the
        server can check whether the entity at that URL has changed from the
        clients last version, and if not, it can return a 304 to indicate
        the client can use it's current representation.
        """
        r = sess.get(self.etag_url)

        # make sure we cached it
        assert self.cache.get(self.etag_url) == r.raw

        # make the same request
        resp = sess.get(self.etag_url)
        assert resp.raw == r.raw
        assert resp.from_cache

        # tell the server to change the etags of the response
        sess.get(self.update_etag_url)

        resp = sess.get(self.etag_url)
        assert resp != r
        assert not resp.from_cache

        # Make sure we updated our cache with the new etag'd response.
        assert self.cache.get(self.etag_url) == resp.raw


class TestDisabledETags(object):
    """Test our use of ETags when the response is stale and the
    response has an ETag.
    """

    @pytest.fixture()
    def sess(self, server, url):
        self.etag_url = urljoin(url, "/etag")
        self.update_etag_url = urljoin(url, "/update_etag")
        self.cache = DictCache()
        sess = CacheControl(
            requests.Session(),
            cache=self.cache,
            cache_etags=False,
            serializer=NullSerializer(),
        )
        return sess

    def test_expired_etags_if_none_match_response(self, sess):
        """Make sure an expired response that contains an ETag uses
        the If-None-Match header.
        """
        # get our response
        r = sess.get(self.etag_url)

        # expire our request by changing the date. Our test endpoint
        # doesn't provide time base caching headers, so we add them
        # here in order to expire the request.
        r.headers["Date"] = "Tue, 26 Nov 2012 00:50:49 GMT"
        self.cache.set(self.etag_url, r.raw)

        r = sess.get(self.etag_url)
        assert r.from_cache
        assert "if-none-match" in r.request.headers
        assert r.status_code == 200


class TestReleaseConnection(object):
    """
    On 304s we still make a request using our connection pool, yet
    we do not call the parent adapter, which releases the connection
    back to the pool. This test ensures that when the parent `get`
    method is not called we consume the response (which should be
    empty according to the HTTP spec) and release the connection.
    """

    def test_not_modified_releases_connection(self, server, url):
        sess = CacheControl(requests.Session())
        etag_url = urljoin(url, "/etag")
        sess.get(etag_url)

        resp = Mock(status=304, headers={})

        # This is how the urllib3 response is created in
        # requests.adapters
        response_mod = "requests.adapters.HTTPResponse.from_httplib"

        with patch(response_mod, Mock(return_value=resp)):
            sess.get(etag_url)
            assert resp.read.called
            assert resp.release_conn.called
