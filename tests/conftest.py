# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

from pprint import pformat

import os
import socket

import pytest

import cherrypy


class SimpleApp(object):

    def __init__(self):
        self.etag_count = 0
        self.update_etag_string()

    def dispatch(self, env):
        path = env["PATH_INFO"][1:].split("/")
        segment = path.pop(0)
        if segment and hasattr(self, segment):
            return getattr(self, segment)

        return None

    def optional_cacheable_request(self, env, start_response):
        """A request with no hints as to whether it should be
        cached. Yet, we might still choose to cache it via a
        heuristic."""

        headers = [
            ("server", "nginx/1.2.6 (Ubuntu)"),
            ("last-modified", "Mon, 21 Jul 2014 17:45:39 GMT"),
            ("content-type", "text/html"),
        ]

        start_response("200 OK", headers)
        return [pformat(env).encode("utf8")]

    def vary_accept(self, env, start_response):
        response = pformat(env).encode("utf8")

        headers = [
            ("Cache-Control", "max-age=5000"),
            ("Content-Type", "text/plain"),
            ("Vary", "Accept-Encoding, Accept"),
        ]
        start_response("200 OK", headers)
        return [response]

    def update_etag_string(self):
        self.etag_count += 1
        self.etag_string = '"ETAG-{}"'.format(self.etag_count)

    def update_etag(self, env, start_response):
        self.update_etag_string()
        headers = [("Cache-Control", "max-age=5000"), ("Content-Type", "text/plain")]
        start_response("200 OK", headers)
        return [pformat(env).encode("utf8")]

    def conditional_get(self, env, start_response):
        return start_response("304 Not Modified", [])

    def etag(self, env, start_response):
        headers = [("Etag", self.etag_string)]
        if env.get("HTTP_IF_NONE_MATCH") == self.etag_string:
            start_response("304 Not Modified", headers)
            return []
        else:
            start_response("200 OK", headers)
        return [pformat(env).encode("utf8")]

    def cache_60(self, env, start_response):
        headers = [("Cache-Control", "public, max-age=60")]
        start_response("200 OK", headers)
        return [pformat(env).encode("utf8")]

    def no_cache(self, env, start_response):
        headers = [("Cache-Control", "no-cache")]
        start_response("200 OK", headers)
        return [pformat(env).encode("utf8")]

    def permanent_redirect(self, env, start_response):
        headers = [("Location", "/permalink")]
        start_response("301 Moved Permanently", headers)
        return ["See: /permalink".encode("utf-8")]

    def permalink(self, env, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return ["The permanent resource".encode("utf-8")]

    def multiple_choices(self, env, start_response):
        headers = [("Link", "/permalink")]
        start_response("300 Multiple Choices", headers)
        return ["See: /permalink".encode("utf-8")]

    def stream(self, env, start_response):
        headers = [("Content-Type", "text/plain"), ("Cache-Control", "max-age=5000")]
        start_response("200 OK", headers)

        for i in range(10):
            yield pformat(i).encode("utf8")

    def __call__(self, env, start_response):
        func = self.dispatch(env)

        if func:
            return func(env, start_response)

        headers = [("Cache-Control", "max-age=5000"), ("Content-Type", "text/plain")]
        start_response("200 OK", headers)
        return [pformat(env).encode("utf8")]


@pytest.fixture(scope="session")
def server():
    return cherrypy.server


@pytest.fixture()
def url(server):
    return "http://%s:%s/" % server.bind_addr


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    ip, port = s.getsockname()
    s.close()
    ip = os.environ.get("WEBTEST_SERVER_BIND", "127.0.0.1")
    return ip, port


def pytest_configure(config):
    cherrypy.tree.graft(SimpleApp(), "/")

    ip, port = get_free_port()

    cherrypy.config.update({"server.socket_host": ip, "server.socket_port": port})

    # turn off logging
    logger = cherrypy.log.access_log
    logger.removeHandler(logger.handlers[0])

    cherrypy.server.start()


def pytest_unconfigure(config):
    try:
        cherrypy.server.stop()
    except:
        pass
