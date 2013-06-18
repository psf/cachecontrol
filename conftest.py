import pytest
from webtest.http import StopableWSGIServer

from cachecontrol.tests import SimpleApp


@pytest.fixture(scope='session')
def server():
    return pytest.server


def pytest_namespace():
    return dict(server=StopableWSGIServer.create(SimpleApp()))


def pytest_unconfigure(config):
    pytest.server.shutdown()
