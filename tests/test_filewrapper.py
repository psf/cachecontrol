# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

import io
from http.client import HTTPResponse
from tempfile import NamedTemporaryFile
from unittest.mock import Mock

import pytest

from cachecontrol.filewrapper import CallbackFileWrapper


@pytest.mark.parametrize("body", [b"", b"response body"])
@pytest.mark.parametrize("error_type", [None, OSError, KeyboardInterrupt])
def test_close_buffer(monkeypatch, tmp_path, body, error_type):
    buffers = []

    def temporary_file(*args, **kwargs):
        buffer = NamedTemporaryFile(*args, dir=tmp_path, **kwargs)
        buffers.append(buffer)
        return buffer

    monkeypatch.setattr("cachecontrol.filewrapper.NamedTemporaryFile", temporary_file)
    wire = b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % len(body) + body
    response = HTTPResponse(Mock(makefile=Mock(return_value=io.BytesIO(wire))))
    response.begin()
    error = error_type("cache write failed") if error_type else None
    callback = Mock(side_effect=error)
    wrapper = CallbackFileWrapper(response, callback)

    if error_type is None:
        assert wrapper.read() == body
    else:
        with pytest.raises(error_type) as raised:
            wrapper.read()
        assert raised.value is error
    assert buffers[0].closed
    assert not list(tmp_path.iterdir())
    assert bytes(callback.call_args.args[0]) == body
    assert wrapper.read() == b""
    callback.assert_called_once()
