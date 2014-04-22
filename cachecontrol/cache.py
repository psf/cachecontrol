"""
The cache object API for implementing caches. The default is just a
dictionary, which in turns means it is not threadsafe for writing.
"""
from threading import Lock

try:
    from pickle import loads, dumps, HIGHEST_PROTOCOL
except ImportError:
    from cPickle import loads, dumps, HIGHEST_PROTOCOL


class BaseCache(object):

    def get(self, key):
        raise NotImplemented()

    def set(self, key, value):
        raise NotImplemented()

    def delete(self, key):
        raise NotImplemented()


class DictCache(BaseCache):

    def __init__(self, init_dict=None):
        self.lock = Lock()
        self.data = init_dict or {}

    def get(self, key):
        data = self.data.get(key, None)
        if data is not None:
            try:
                data = loads(data)
            except ValueError:
                data = None
        return data

    def set(self, key, value):
        with self.lock:
            self.data.update({key: dumps(value, HIGHEST_PROTOCOL)})

    def delete(self, key):
        with self.lock:
            if key in self.data:
                self.data.pop(key)
