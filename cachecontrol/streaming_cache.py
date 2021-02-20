# SPDX-License-Identifier: Apache-2.0

import io


class NotFound(Exception):
    '''Raised by Cache.open_read() and Cache.delete() when the key is missing'''


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
        '''Get data from the cache

        Throw NotFound if the key is missing
        '''
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


class ExampleCache:
    class WriteHandle:
        def __init__(self, put):
            self.put = put
            self.buf = io.BytesIO()

        def write(self, b):
            self.buf.write(b)

        def commit(self):
            self.put(self.buf.getvalue())

        def close(self):
            pass

    def __init__(self):
        self.data = {}

    def open_read(self, key):
        try:
            return io.BytesIO(self.data[key])
        except KeyError:
            raise NotFound(f'{key} not found in the cache')

    def open_write(self, key, expires=None):
        def put(b):
            self.data[key] = b
        return self.WriteHandle(put)

    def delete(self, key):
        del self.data[key]

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
