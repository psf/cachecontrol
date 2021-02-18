from contextlib import closing
from cachecontrol.streaming_cache import ExampleCache
import pytest


@pytest.mark.parametrize('v', [b'fizz', b'buzz'])
def test_read_returns_what_you_wrote(v):
    with closing(ExampleCache()) as cache:
        with closing(cache.open_write('foo')) as w:
            w.write(v)
            w.commit()
        with closing(cache.open_read('foo')) as r:
            got = r.read()
    assert got == v


def test_cache_remembers_more_than_one_value():
    with closing(ExampleCache()) as cache:
        with closing(cache.open_write('foo')) as w:
            w.write(b'one')
            w.commit()
        with closing(cache.open_write('bar')) as w:
            w.write(b'two')
            w.commit()
        with closing(cache.open_read('foo')) as r:
            got = r.read()
        assert got == b'one'
        with closing(cache.open_read('bar')) as r:
            got = r.read()
        assert got == b'two'
