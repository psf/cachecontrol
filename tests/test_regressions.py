# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

import pytest


from cachecontrol import CacheControl, CacheControlAdapter
from cachecontrol.caches import FileCache
from cachecontrol.filewrapper import CallbackFileWrapper
from requests import Session


class Test39:
    def test_file_cache_recognizes_consumed_file_handle(self, url):
        s = CacheControl(Session(), FileCache("web_cache"))
        the_url = url + "cache_60"
        s.get(the_url)
        r = s.get(the_url)
        assert r.from_cache
        s.close()


def test_getattr_during_gc():
    s = CallbackFileWrapper(None, None)
    # normal behavior:
    with pytest.raises(AttributeError):
        s.x

    # this previously had caused an infinite recursion
    vars(s).clear()  # gc does this.
    with pytest.raises(AttributeError):
        s.x


def test_handle_no_chunked_attr():

    class NoChunked(CacheControlAdapter):
        def build_response(self, request, response, from_cache=False,
                           cacheable_methods=None):
            if hasattr(response, 'chunked'):
                pytest.skip('Requests is new enough, test makes no sense.')
                # delattr(response, 'chunked')
            return super().build_response(request, response, from_cache,
                                          cacheable_methods)
    sess = Session()
    sess.mount('http://', NoChunked())
    sess.get('http://httpbin.org/cache/60')
