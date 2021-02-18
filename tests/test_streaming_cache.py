from contextlib import closing
from cachecontrol.streaming_cache import ExampleCache
import pytest


# Helpers
def get(cache, key):
    with closing(cache.open_read(key)) as r:
        return r.read()


def put(cache, key, value):
    with closing(cache.open_write(key)) as w:
        w.write(value)
        w.commit()


@pytest.mark.parametrize('v', [b'fizz', b'buzz'])
def test_read_returns_what_you_wrote(v):
    with closing(ExampleCache()) as cache:
        put(cache, 'foo', v)
        assert get(cache, 'foo') == v


def test_cache_remembers_more_than_one_value():
    with closing(ExampleCache()) as cache:
        put(cache, 'foo', b'one')
        put(cache, 'bar', b'two')
        assert get(cache, 'foo') == b'one'
        assert get(cache, 'bar') == b'two'


@pytest.mark.parametrize('expect', [
    [('foo', b'one'), ('bar', b'two')],
    [('bar', b'two'), ('foo', b'one')],
])
def test_read_order_does_not_matter(expect):
    with closing(ExampleCache()) as cache:
        put(cache, 'foo', b'one')
        put(cache, 'bar', b'two')
        for k, v in expect:
            assert get(cache, k) == v
