from urlparse import urljoin

import pytest
import requests

from cachecontrol import CacheControl
from cachecontrol.cache import DictCache


class TestEtag(object):

    @pytest.fixture()
    def sess(self, server):
        self.etag_url = urljoin(server.application_url, '/etag')
        self.update_etag_url = urljoin(server.application_url, '/update_etag')
        self.cache = DictCache()
        sess = CacheControl(requests.Session(), cache=self.cache)
        return sess

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
        assert self.cache.get(self.etag_url) == r

        # make the same request
        resp = sess.get(self.etag_url)
        assert resp == r
        assert resp.from_cache

        # tell the server to change the etags of the response
        sess.get(self.update_etag_url)

        resp = sess.get(self.etag_url)
        assert resp != r
        assert not resp.from_cache
