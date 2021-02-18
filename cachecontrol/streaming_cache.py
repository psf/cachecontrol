# SPDX-License-Identifier: Apache-2.0

import io


class ReadHandle:
    def read(self, size: int = -1) -> bytes:
        pass

    def close(self) -> None:
        pass


class WriteHandle:
    def write(self, b: bytes) -> int:
        pass

    def commit(self) -> None:
        '''Assign the value to the key and close the WriteHandle'''
        pass

    def close(self) -> None:
        '''Discard the value without assigning it to the key'''
        pass


class Cache:
    '''Cache API docs

    No need to inherit form this. This is just a documenation
    of the interface between CacheControl and a cache
    '''

    # TODO: are keys really str?
    def open_read(self, key: str) -> ReadHandle:
        pass

    def open_write(self, key: str, expires=None) -> WriteHandle:
        pass

    def delete(self, key):
        pass

    def close(self):
        '''Cleanup any temporary files, database connections etc.'''
        pass
    # Cache does not have __enter__ and __exit__ on purpose. Same for ReadHandle
    # and WriteHandle. The idea is to keep the interface small, simple and easy
    # to implement - it is the interface between CacheControl and storage
    # backends. Helpers can be written on top of this interface
    # to make it easier to use.


CACHE = {}


class ExampleCache:
    class WriteHandle:
        def __init__(self, key):
            self.key = key

        def write(self, b):
            global CACHE
            CACHE[self.key] = b

        def commit(self):
            pass

        def close(self):
            pass

    def open_read(self, key):
        return io.BytesIO(CACHE[key])

    def open_write(self, key, expires=None):
        return self.WriteHandle(key)

    def delete(self, key):
        pass

    def close(self):
        pass
'''
# An example to use while prototyping
class ExampleCache:
    # Why is ExampleCache.data not a dict[str, io.BytesIO]?
    # 1. I did not want the stream position to be shared by all readers and writers
    # 2. https://docs.python.org/3/library/io.html#io.BytesIO
    #    The buffer is discarded when the close() method is called.
    class WriteHandle:
        def __init__(self, commit):
            self._commit = commit
            self.fd = io.BytesIO()

        def write(self, b):
            return self.fd.write(b)

        def commit(self):
            self._commit(self.fd.getvalue())
            self.fd.close()

        def close(self):
            self.fd.close()

    def __init__(self):
        self.data = {}

    def open_read(self, key):
        return io.BytesIO(self.data[key])

    def open_write(self, key, expires=None):
        def commit(b):
            self.data[key] = b
        return WriteHandle(commit=commit)

    def delete(self, key):
        del self.data[key]

    def close(self):
        pass
'''
