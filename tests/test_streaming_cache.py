from contextlib import closing
from cachecontrol import streaming_cache
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


@pytest.mark.parametrize('expect', [
    [(0, b'one'), (1, b'two')],
    [(1, b'two'), (0, b'one')],
])
def test_caches_are_independent(expect):
    with closing(ExampleCache()) as c0, closing(ExampleCache()) as c1:
        put(c0, 'foo', b'one')
        put(c1, 'foo', b'two')
        for i, v in expect:
            c = [c0, c1][i]
            assert get(c, 'foo') == v


def test_open_read_throws_if_key_is_missing():
    with closing(ExampleCache()) as cache:
        put(cache, 'bar', b'bar')
        with pytest.raises(streaming_cache.NotFound):
            get(cache, 'foo')


def test_partial_read():
    with closing(ExampleCache()) as cache:
        put(cache, 'foo', b'123')
        with closing(cache.open_read('foo')) as r:
            assert r.read(2) == b'12'
            assert r.read(1) == b'3'


def test_read_handles_are_independant():
    with closing(ExampleCache()) as cache:
        put(cache, 'foo', b'123')
        with closing(cache.open_read('foo')) as r0,\
                closing(cache.open_read('foo')) as r1:
            assert r0.read(2) == b'12'
            assert r1.read(1) == b'1'
            assert r0.read(1) == b'3'
            assert r1.read(2) == b'23'


def test_key_is_not_added_until_commit_is_called():
    with closing(ExampleCache()) as cache:
        with closing(cache.open_write('foo')) as w:
            w.write(b'123')
            with pytest.raises(streaming_cache.NotFound):
                get(cache, 'foo')
            w.commit()
            get(cache, 'foo')


def test_partial_write():
    with closing(ExampleCache()) as cache:
        with closing(cache.open_write('foo')) as w:
            w.write(b'1')
            w.write(b'23')
            w.commit()
        assert get(cache, 'foo') == b'123'


def test_delete_removes_key():
    with closing(ExampleCache()) as cache:
        put(cache, 'foo', b'123')
        get(cache, 'foo')
        cache.delete('foo')
        with pytest.raises(streaming_cache.NotFound):
            get(cache, 'foo')


def test_delete_keeps_unrelated_key():
    with closing(ExampleCache()) as cache:
        put(cache, 'foo', b'123')
        put(cache, 'bar', b'456')
        cache.delete('foo')
        get(cache, 'bar')


def test_overwrite():
    with closing(ExampleCache()) as cache:
        put(cache, 'foo', b'123')
        assert get(cache, 'foo') == b'123'
        put(cache, 'foo', b'456')
        assert get(cache, 'foo') == b'456'
