# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
import math
from typing import IO, TYPE_CHECKING, Any, Mapping, cast

import msgpack
from requests.structures import CaseInsensitiveDict
from urllib3 import HTTPResponse

if TYPE_CHECKING:
    from requests import PreparedRequest


class Serializer:
    serde_version = "4"

    def dumps(
        self,
        request: PreparedRequest,
        response: HTTPResponse,
        body: bytes | None = None,
    ) -> bytes:
        response_headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            response.headers
        )

        if body is None:
            # When a body isn't passed in, we'll read the response. We
            # also update the response with a new file handler to be
            # sure it acts as though it was never read.
            body = response.read(decode_content=False)
            response._fp = io.BytesIO(body)  # type: ignore[assignment]
            response.length_remaining = len(body)

        data = {
            "response": {
                "body": body,  # Empty bytestring if body is stored separately
                "headers": {str(k): str(v) for k, v in response.headers.items()},
                "status": response.status,
                "version": response.version,
                "reason": str(response.reason),
                "decode_content": response.decode_content,
            }
        }

        initial_age = getattr(response, "_cachecontrol_initial_age", None)
        response_time = getattr(response, "_cachecontrol_response_time", None)
        if (
            isinstance(initial_age, (int, float))
            and not isinstance(initial_age, bool)
            and math.isfinite(initial_age)
            and initial_age >= 0
            and isinstance(response_time, (int, float))
            and not isinstance(response_time, bool)
            and math.isfinite(response_time)
            and response_time >= 0
        ):
            # This optional top-level field is additive to cc=4: existing
            # readers ignore unknown keys, and new readers accept old records
            # where timing metadata is absent.
            data["cachecontrol_age"] = {
                "initial_age": float(initial_age),
                "response_time": float(response_time),
            }
            if getattr(response, "_cachecontrol_age_overflow", False) is True:
                data["cachecontrol_age"]["overflow"] = True

        # Construct our vary headers
        data["vary"] = {}
        if "vary" in response_headers:
            varied_headers = response_headers["vary"].split(",")
            for header in varied_headers:
                header = str(header).strip()
                header_value = request.headers.get(header, None)
                if header_value is not None:
                    header_value = str(header_value)
                data["vary"][header] = header_value

        return b",".join([f"cc={self.serde_version}".encode(), self.serialize(data)])

    def serialize(self, data: dict[str, Any]) -> bytes:
        return cast(bytes, msgpack.dumps(data, use_bin_type=True))

    def loads(
        self,
        request: PreparedRequest,
        data: bytes,
        body_file: IO[bytes] | None = None,
    ) -> HTTPResponse | None:
        # Short circuit if we've been given an empty set of data
        if not data:
            return None

        # Previous versions of this library supported other serialization
        # formats, but these have all been removed.
        if not data.startswith(f"cc={self.serde_version},".encode()):
            return None

        data = data[5:]
        return self._loads_v4(request, data, body_file)

    def prepare_response(
        self,
        request: PreparedRequest,
        cached: Mapping[str, Any],
        body_file: IO[bytes] | None = None,
    ) -> HTTPResponse | None:
        """Verify our vary headers match and construct a real urllib3
        HTTPResponse object.
        """
        # Special case the '*' Vary value as it means we cannot actually
        # determine if the cached response is suitable for this request.
        # This case is also handled in the controller code when creating
        # a cache entry, but is left here for backwards compatibility.
        if "*" in cached.get("vary", {}):
            return None

        # Ensure that the Vary headers for the cached response match our
        # request
        for header, value in cached.get("vary", {}).items():
            if request.headers.get(header, None) != value:
                return None

        body_raw = cached["response"].pop("body")

        headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            data=cached["response"]["headers"]
        )
        if headers.get("transfer-encoding", "") == "chunked":
            headers.pop("transfer-encoding")

        cached["response"]["headers"] = headers

        try:
            body: IO[bytes]
            if body_file is None:
                body = io.BytesIO(body_raw)
            else:
                body = body_file
        except TypeError:
            # This can happen if cachecontrol serialized to v1 format (pickle)
            # using Python 2. A Python 2 str(byte string) will be unpickled as
            # a Python 3 str (unicode string), which will cause the above to
            # fail with:
            #
            #     TypeError: 'str' does not support the buffer interface
            body = io.BytesIO(body_raw.encode("utf8"))

        # Discard any `strict` parameter serialized by older version of cachecontrol.
        cached["response"].pop("strict", None)

        response = HTTPResponse(body=body, preload_content=False, **cached["response"])
        age_metadata = cached.get("cachecontrol_age")
        if isinstance(age_metadata, Mapping):
            initial_age = age_metadata.get("initial_age")
            response_time = age_metadata.get("response_time")
            age_overflow = age_metadata.get("overflow", False)
            if (
                isinstance(initial_age, (int, float))
                and not isinstance(initial_age, bool)
                and math.isfinite(initial_age)
                and initial_age >= 0
                and isinstance(response_time, (int, float))
                and not isinstance(response_time, bool)
                and math.isfinite(response_time)
                and response_time >= 0
                and isinstance(age_overflow, bool)
            ):
                setattr(response, "_cachecontrol_initial_age", float(initial_age))
                setattr(response, "_cachecontrol_response_time", float(response_time))
                if age_overflow:
                    setattr(response, "_cachecontrol_age_overflow", True)

        return response

    def _loads_v4(
        self,
        request: PreparedRequest,
        data: bytes,
        body_file: IO[bytes] | None = None,
    ) -> HTTPResponse | None:
        try:
            cached = msgpack.loads(data, raw=False)
        except ValueError:
            return None

        return self.prepare_response(request, cached, body_file)
