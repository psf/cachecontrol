"""
The cache object API for implementing caches. The default is a thread
safe in-memory dictionary.
"""
from threading import Lock
import zlib

class BaseCache(object):

    def get(self, key):
        raise NotImplemented()

    def set(self, key, value):
        raise NotImplemented()

    def delete(self, key):
        raise NotImplemented()

    def close(self):
        pass


class DictCache(BaseCache):

    def __init__(self, init_dict=None):
        self.lock = Lock()
        self.data = init_dict or {}

    def get(self, key):
        value = self.data.get(key, None)

        if value is None:
            return None

        # to handle testing issues where a Mock object cannot be handled
        if type(value) is not 'str':
            return value

        value = zlib.decompress(value.encode('utf-8'))

        return value.decode('utf-8')

    def set(self, key, set_value):

        # mutability damage limiter
        value = set_value

        if value is None:
            with self.lock:
                self.data.update({key: None})
            return

        # to handle testing issues where a Mock object cannot be handled
        if type(value) is not 'str':
            self.data.update({key: value})
            return

        value = value.encode('utf-8')
        compressed_value = zlib.compress(value, zlib.Z_BEST_COMPRESSION)
        compressed_value = str(compressed_value)

        with self.lock:
            self.data.update({key: compressed_value})

    def delete(self, key):
        with self.lock:
            if key in self.data:
                self.data.pop(key)
