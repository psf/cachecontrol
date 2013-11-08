from pprint import pformat

import pytest

from webtest.http import StopableWSGIServer


class SimpleApp(object):

    def dispatch(self, env):
        path = env['PATH_INFO'][1:].split('/')
        segment = path.pop(0)
        if segment and hasattr(self, segment):
            return getattr(self, segment)
        return None

    def vary_accept(self, env, start_response):
        headers = [
            ('Cache-Control', 'max-age=5000'),
            ('Content-Type', 'text/plain'),
            ('Vary', 'Accept-Encoding, Accept'),
        ]
        start_response('200 OK', headers)
        return pformat(env)

    def __call__(self, env, start_response):
        func = self.dispatch(env)

        if func:
            return func(env, start_response)

        print('default handler')

        headers = [
            ('Cache-Control', 'max-age=5000'),
            ('Content-Type', 'text/plain'),
        ]
        start_response('200 OK', headers)
        return pformat(env)


@pytest.fixture(scope='session')
def server():
    return pytest.server


@pytest.fixture()
def url(server):
    return server.application_url


def pytest_namespace():
    return dict(server=StopableWSGIServer.create(SimpleApp()))


def pytest_unconfigure(config):
    pytest.server.shutdown()
