import pytest
import requests

from cachecontrol import CacheControl
from cachecontrol.cache import DictCache
from cachecontrol.compat import urljoin

from pprint import pprint


class TestVary(object):

    @pytest.fixture()
    def sess(self, url):
        self.url = urljoin(url, "/vary_accept")
        self.cache = DictCache()
        sess = CacheControl(requests.Session(), cache=self.cache)
        return sess

    def cached_equal(self, cached, resp):
        # remove any transfer-encoding headers as they don't apply to
        # a cached value
        if "chunked" in resp.raw.headers.get("transfer-encoding", ""):
            resp.raw.headers.pop("transfer-encoding")

        checks = [
            cached._fp.getvalue() == resp.content,
            cached.headers == resp.raw.headers,
            cached.status == resp.raw.status,
            cached.version == resp.raw.version,
            cached.reason == resp.raw.reason,
            cached.strict == resp.raw.strict,
            cached.decode_content == resp.raw.decode_content,
        ]

        print(checks)
        pprint(dict(cached.headers))
        pprint(dict(resp.raw.headers))
        return all(checks)

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
        s = sess.adapters["http://"].controller.serializer
        r = sess.get(self.url)
        c = s.loads(r.request, self.cache.get(self.url))

        # make sure we cached it
        assert self.cached_equal(c, r)

        # make the same request
        resp = sess.get(self.url)
        assert self.cached_equal(c, resp)
        assert resp.from_cache

        # make a similar request, changing the accept header
        resp = sess.get(self.url, headers={"Accept": "text/plain, text/html"})
        assert not self.cached_equal(c, resp)
        assert not resp.from_cache

        # Just confirming two things here:
        #
        #   1) The server used the vary header
        #   2) We have more than one header we vary on
        #
        # The reason for this is that when we don't specify the header
        # in the request, it is considered the same in terms of
        # whether or not to use the cached value.
        assert "vary" in r.headers
        assert len(r.headers["vary"].replace(" ", "").split(",")) == 2
