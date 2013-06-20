"""
When resources are known to be updated via HTTP (ie PUT, DELETE), we
should invalidate them in our cache.
"""
import mock

from cachecontrol import CacheControl
from cachecontrol.cache import DictCache


class TestWrapperInvalidations(object):

    url = 'http://foo.com/bar/'

    def setup(self):
        req = mock.Mock(url=self.url)
        resp = mock.Mock(request=req)
        cache = DictCache({self.url: resp})
        session = mock.Mock(put=mock.Mock(return_value=resp),
                            delete=mock.Mock(return_value=resp))
        self.session = CacheControl(session, cache)

    def test_put_invalidates_cache(self):
        # Prep our cache
        self.session.put(self.url)
        assert not self.session.cache.get(self.url)

    def test_delete_invalidates_cache(self):
        # Prep our cache
        self.session.delete(self.url)
        assert not self.session.cache.get(self.url)
