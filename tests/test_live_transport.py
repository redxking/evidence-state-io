"""The live HTTPS transport, exercised without a network.

Every failure mode here returns something that looks like an ordinary empty
result to a caller who is not paying attention. These tests check that the
transport reports what actually happened instead.

The network is never touched: `urllib.request.urlopen` is replaced for the
duration of each test.
"""

from __future__ import annotations

import json
import ssl
import unittest
import urllib.error
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from evidence_state_io.adapters import AdapterError
from evidence_state_io.adapters import live as live_module
from evidence_state_io.adapters.live import GitHubHttpTransport, resolve_trust_store

UTC = timezone.utc
AT = datetime(2026, 8, 23, 12, 47, tzinfo=UTC)


class _Response:
    def __init__(self, body: str, *, status: int = 200, headers: dict[str, str] | None = None):
        self._body = body.encode("utf-8")
        self.status = status
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_: object) -> None:
        return None


@contextmanager
def _urlopen(replacement: Any) -> Iterator[None]:
    original = live_module.urllib.request.urlopen
    live_module.urllib.request.urlopen = replacement
    try:
        yield
    finally:
        live_module.urllib.request.urlopen = original


def _transport(**kwargs: Any) -> GitHubHttpTransport:
    return GitHubHttpTransport(retrieved_at=AT, **kwargs)


class ConstructionTests(unittest.TestCase):
    def test_the_endpoint_must_be_https(self) -> None:
        with self.assertRaisesRegex(AdapterError, "must be https"):
            _transport(endpoint="http://api.github.com/search/repositories")

    def test_retrieved_at_must_be_timezone_aware(self) -> None:
        with self.assertRaisesRegex(AdapterError, "timezone-aware"):
            GitHubHttpTransport(retrieved_at=datetime(2026, 8, 23, 12, 47))

    def test_a_missing_ca_bundle_is_refused_rather_than_ignored(self) -> None:
        with self.assertRaisesRegex(AdapterError, "does not exist"):
            _transport(ca_bundle="/nonexistent/ca-bundle.pem")

    def test_the_default_trust_store_verifies(self) -> None:
        context = resolve_trust_store()
        self.assertIs(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)


class FailureReportingTests(unittest.TestCase):
    def test_throttling_is_reported_rather_than_returned_as_empty(self) -> None:
        """A 403 with an exhausted budget is throttling, not absence."""

        def _raise(request, timeout=None, context=None):  # noqa: ANN001
            raise urllib.error.HTTPError(request.full_url, 403, "rate limited", {}, None)

        with _urlopen(_raise):
            response = _transport().fetch_page(query="x", page=1, per_page=10)

        self.assertTrue(response.truncated_by_rate_limit)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.errors)
        self.assertIs(response.payload["incomplete_results"], True)

    def test_a_server_error_is_reported_but_not_called_throttling(self) -> None:
        def _raise(request, timeout=None, context=None):  # noqa: ANN001
            raise urllib.error.HTTPError(request.full_url, 500, "boom", {}, None)

        with _urlopen(_raise):
            response = _transport().fetch_page(query="x", page=1, per_page=10)

        self.assertFalse(response.truncated_by_rate_limit)
        self.assertEqual(response.status_code, 500)

    def test_a_transport_failure_names_its_reason(self) -> None:
        def _raise(request, timeout=None, context=None):  # noqa: ANN001
            raise urllib.error.URLError("certificate verify failed")

        with _urlopen(_raise):
            with self.assertRaisesRegex(AdapterError, "certificate verify failed"):
                _transport().fetch_page(query="x", page=1, per_page=10)

    def test_a_non_json_body_is_refused(self) -> None:
        with _urlopen(lambda *a, **k: _Response("<html>not json</html>")):
            with self.assertRaisesRegex(AdapterError, "not valid JSON"):
                _transport().fetch_page(query="x", page=1, per_page=10)

    def test_a_non_object_body_is_refused(self) -> None:
        with _urlopen(lambda *a, **k: _Response("[1, 2, 3]")):
            with self.assertRaisesRegex(AdapterError, "not a JSON object"):
                _transport().fetch_page(query="x", page=1, per_page=10)

    def test_an_exhausted_rate_limit_header_marks_the_page_truncated(self) -> None:
        body = json.dumps({"total_count": 0, "incomplete_results": False, "items": []})
        with _urlopen(lambda *a, **k: _Response(body, headers={"X-RateLimit-Remaining": "0"})):
            response = _transport().fetch_page(query="x", page=1, per_page=10)

        self.assertTrue(response.truncated_by_rate_limit)

    def test_a_healthy_page_is_recorded_for_replay(self) -> None:
        body = json.dumps({"total_count": 0, "incomplete_results": False, "items": []})
        transport = _transport()
        with _urlopen(lambda *a, **k: _Response(body, headers={"X-RateLimit-Remaining": "29"})):
            response = transport.fetch_page(query="x", page=1, per_page=10)

        self.assertFalse(response.truncated_by_rate_limit)
        self.assertEqual(transport.recorded_pages, [json.loads(body)])


class RequestShapeTests(unittest.TestCase):
    def test_the_query_and_paging_reach_the_url_and_nothing_else_does(self) -> None:
        seen: dict[str, Any] = {}
        body = json.dumps({"total_count": 0, "incomplete_results": False, "items": []})

        def _capture(request, timeout=None, context=None):  # noqa: ANN001
            seen["url"] = request.full_url
            seen["method"] = request.get_method()
            seen["headers"] = dict(request.headers)
            return _Response(body)

        with _urlopen(_capture):
            _transport().fetch_page(query="topic:esio", page=2, per_page=50)

        self.assertEqual(seen["method"], "GET")
        self.assertIn("q=topic%3Aesio", seen["url"])
        self.assertIn("page=2", seen["url"])
        self.assertIn("per_page=50", seen["url"])
        self.assertNotIn("Authorization", seen["headers"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
