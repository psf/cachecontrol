import sys
import pytest


from cachecontrol import CacheControl
from cachecontrol.caches.file_cache import FileCache
from requests import Session


class Test39(object):

    @pytest.mark.skipif(sys.version.startswith('2'),
                        reason='Only run this for python 3.x')
    def test_file_cache_recognizes_consumed_file_handle(self):
        s = CacheControl(Session(), FileCache('web_cache'))
        s.get('http://httpbin.org/cache/60')
        r = s.get('http://httpbin.org/cache/60')
        assert r.from_cache
