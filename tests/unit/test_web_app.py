#!/usr/bin/env python3
"""Unit tests for avantfax.web.app WSGI routing."""

import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.web.app import create_app


class TestWebApp(unittest.TestCase):
    """Test suite for AvantFAX unified WSGI router."""

    def setUp(self):
        self.app = create_app()

    def _call_app(self, path="/", method="GET", headers=None, body=None):
        environ = {
            "PATH_INFO": path,
            "REQUEST_METHOD": method,
            "QUERY_STRING": "",
            "wsgi.input": io.BytesIO(body or b""),
            "CONTENT_LENGTH": str(len(body or b"")),
        }
        if headers:
            for k, v in headers.items():
                environ[k] = v

        response_status = []
        response_headers = []

        def start_response(status, hdrs):
            response_status.append(status)
            response_headers.extend(hdrs)

        body_chunks = self.app(environ, start_response)
        raw_output = b"".join(body_chunks)
        return response_status[0], dict(response_headers), raw_output

    def test_health_check(self):
        status, headers, body = self._call_app("/api/health")
        self.assertEqual(status, "200 OK")
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "ok")

    def test_root_index(self):
        status, headers, body = self._call_app("/")
        self.assertEqual(status, "200 OK")
        self.assertIn(b"AvantFAX Modern Web System Ready", body)

    def test_unauthenticated_api_access(self):
        status, headers, body = self._call_app("/api/inbox/list")
        self.assertEqual(status, "401 Unauthorized")


if __name__ == "__main__":
    unittest.main()
