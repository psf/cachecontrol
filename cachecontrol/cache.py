"""
The cache object API for implementing caches. The default is a thread
safe in-memory dictionary.
"""
from threading import Lock


class BaseCache(object):

    def __init__(self, shared=False):
        self.shared = shared

    def get(self, key):
        raise NotImplementedError()

    def set(self, key, value):
        raise NotImplementedError()

    def delete(self, key):
        raise NotImplementedError()

    def close(self):
        pass


class DictCache(BaseCache):

    def __init__(self, init_dict=None, shared=False):
        super(DictCache, self).__init__(shared)
        self.lock = Lock()
        self.data = init_dict or {}

    def get(self, key):
        return self.data.get(key, None)

    def set(self, key, value):
        with self.lock:
            self.data.update({key: value})

    def delete(self, key):
        with self.lock:
            if key in self.data:
                self.data.pop(key)
