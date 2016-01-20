"""
ChunkingHTTPServer excerpted from `chunked_server_test.py` by Josiah Carlson.

ref: https://gist.github.com/josiahcarlson/3250376

"""
from __future__ import print_function, unicode_literals

import sys
import threading

PY3 = sys.version_info >= (3, 0)
if PY3:
    from http import server as httpserver
    import socketserver
else:
    import BaseHTTPServer as httpserver
    import SocketServer as socketserver

import pytest
from requests import Session
from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.cache import DictCache


@pytest.fixture
def chunking_server():
    server = ChunkingHTTPServer(('127.0.0.1', 0), ChunkingRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    return server


class NullSerializer(object):

    def dumps(self, request, response, body=None):
        return response

    def loads(self, request, data):
        return data


class TestChunkedResponse(object):

    @pytest.fixture()
    def sess(self, chunking_server):
        self.url = chunking_server.base_url
        self.cache = DictCache()
        sess = Session()
        sess.mount(
            'http://',
            CacheControlAdapter(self.cache, serializer=NullSerializer()),
        )
        return sess

    def test_cache_chunked_response(self, sess):
        """
        Verify that an otherwise cacheable response is cached when the response
        is chunked.
        """
        r = sess.get(self.url)
        assert self.cache.get(self.url) == r.raw

        r = sess.get(self.url, headers={'Cache-Control': 'max-age=3600'})
        assert r.from_cache is True


class ChunkingHTTPServer(socketserver.ThreadingMixIn, httpserver.HTTPServer):
    """
    This is just a proof of concept server that uses threads. You can make it
    fork, maybe hack up a worker thread model, or even use multiprocessing.
    That's your business. But as-is, it works reasonably well for streaming
    chunked data from a server.
    """
    daemon_threads = True

    @property
    def base_url(self):
        return 'http://{addr[0]}:{addr[1]}/'.format(addr=self.server_address)


class ChunkingRequestHandler(httpserver.BaseHTTPRequestHandler):
    """
    Nothing is terribly magical about this code, the only thing that you need
    to really do is tell the client that you're going to be using a chunked
    transfer encoding.

    """
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        self.send_response(200)
        self.send_header('Transfer-Encoding', 'chunked')
        self.send_header('Content-type', 'text/plain')
        self.send_header('Cache-Control', 'max-age=5000')
        self.end_headers()

        def write_chunk():
            tosend = '%X\r\n%s\r\n' % (len(chunk), chunk)
            self.wfile.write(tosend.encode())

        # get some chunks
        for chunk in chunk_generator():
            if not chunk:
                continue
            write_chunk()

        # send the chunked trailer
        self.wfile.write(b'0\r\n\r\n')


def chunk_generator():
    # generate some chunks
    for i in range(10):
        yield "this is chunk: %s\r\n"%i
