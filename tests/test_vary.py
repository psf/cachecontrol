from urlparse import urljoin

import pytest
import requests

from cachecontrol import CacheControl
from cachecontrol.cache import DictCache


class TestVary(object):

    @pytest.fixture()
    def sess(self, server):
        self.url = urljoin(server.application_url, '/vary_accept')
        self.cache = DictCache()
        sess = CacheControl(requests.Session(), cache=self.cache)
        return sess

    def test_vary_example(self, sess):
        """RFC 2616 13.6

        When the cache receives a subsequent request whose Request-URI
        specifies one or more cache entries including a Vary header field,
        the cache MUST NOT use such a cache entry to construct a response
        to the new request unless all of the selecting request-headers
        present in the new request match the corresponding stored
        request-headers in the original request.

        Or, in simpler terms, when you make a request and the server
        returns defines a Vary header, unless all the headers listed
        in the Vary header are the same, it won't use the cached
        value.
        """
        r = sess.get(self.url)

        # make sure we cached it
        assert self.cache.get(self.url) == r

        # make the same request
        resp = sess.get(self.url)
        assert resp == r
        assert resp.from_cache

        # make a similar request, changing the accept header
        resp = sess.get(self.url, headers={'Accept': 'text/plain, text/html'})
        assert resp != r
        assert not resp.from_cache

        # Just confirming two things here:
        #
        #   1) The server used the vary header
        #   2) We have more than one header we vary on
        #
        # The reason for this is that when we don't specify the header
        # in the request, it is considered the same in terms of
        # whether or not to use the cached value.
        assert 'vary' in r.headers
        assert len(r.headers['vary'].replace(' ', '').split(',')) == 2
