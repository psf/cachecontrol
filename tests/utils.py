"""
Shared utility classes.
"""

from requests.structures import CaseInsensitiveDict


class NullSerializer(object):

    def dumps(self, request, response, body=None):
        return response

    def loads(self, request, data, body_file=None):
        if data and getattr(data, "chunked", False):
            data.chunked = False
        return data


class DummyResponse:
    """Match a ``urllib3.response.HTTPResponse``."""
    version = "1.1"
    reason = b"Because"
    strict = 0
    decode_content = False

    def __init__(self, status, headers):
        self.status = status
        self.headers = CaseInsensitiveDict(headers)


class DummyRequest:
    """Match a Request."""

    def __init__(self, url, headers):
        self.url = url
        self.headers = CaseInsensitiveDict(headers)
