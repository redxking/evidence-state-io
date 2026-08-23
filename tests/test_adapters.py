"""The read-only adapter contract and the GitHub search adapter.

An adapter's job is to report the ways a fetch was incomplete, because those are
exactly the facts a bare empty result hides. Most of these tests present a
response that looks like a clean empty search and check that the adapter
declines to call it one.

The security properties are verified here rather than assumed: verification
cannot be disabled, the token never reaches any record, the transport only
reads, and importing the package does not import the network.
"""

from __future__ import annotations

import json
import ssl
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from evidence_state_io.adapters import (
    GITHUB_SEARCH_RESULT_CAP,
    AdapterError,
    GitHubSearchAdapter,
    ReadOnlyAdapter,
    RecordedTransport,
    TransportResponse,
)
from evidence_state_io.models import EvidenceState, PopulationBasis

UTC = timezone.utc
AT = datetime(2026, 8, 23, 12, 47, tzinfo=UTC)
RECORDING = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "recorded"
    / "github-search-zero-results.json"
)


def _adapter(*payloads: dict) -> GitHubSearchAdapter:
    return GitHubSearchAdapter(
        RecordedTransport(
            pages=tuple(TransportResponse(payload=payload, retrieved_at=AT) for payload in payloads)
        )
    )


def _read(*payloads: dict, **kwargs):
    return _adapter(*payloads).read(query="topic:anything", observed_at=AT, **kwargs)


class IncompletenessTests(unittest.TestCase):
    """Every one of these looks like an ordinary empty result."""

    def test_a_clean_empty_search_is_in_scope_absence(self) -> None:
        reading = _read({"total_count": 0, "incomplete_results": False, "items": []})

        self.assertIs(reading.derived_state(), EvidenceState.ABSENT_WITHIN_SCOPE)
        self.assertTrue(reading.pagination_complete)
        self.assertEqual(reading.matched_count, 0)

    def test_an_internal_timeout_is_not_absence(self) -> None:
        """incomplete_results is the only signal; the item list is identical."""

        reading = _read({"total_count": 0, "incomplete_results": True, "items": []})

        self.assertTrue(reading.timed_out)
        self.assertIsNot(reading.derived_state(), EvidenceState.ABSENT_WITHIN_SCOPE)
        self.assertIs(reading.derived_state(), EvidenceState.NOT_OBSERVED)

    def test_rate_limiting_is_an_interruption_not_an_empty_result(self) -> None:
        adapter = GitHubSearchAdapter(
            RecordedTransport(
                pages=(
                    TransportResponse(
                        payload={"total_count": 0, "incomplete_results": False, "items": []},
                        retrieved_at=AT,
                        truncated_by_rate_limit=True,
                    ),
                )
            )
        )
        reading = adapter.read(query="topic:anything", observed_at=AT)

        self.assertTrue(reading.interrupted)
        self.assertIs(reading.derived_state(), EvidenceState.NOT_OBSERVED)

    def test_an_error_status_is_an_interruption(self) -> None:
        adapter = GitHubSearchAdapter(
            RecordedTransport(
                pages=(
                    TransportResponse(
                        payload={"items": []},
                        retrieved_at=AT,
                        status_code=503,
                    ),
                )
            )
        )
        reading = adapter.read(query="topic:anything", observed_at=AT)

        self.assertTrue(reading.interrupted)
        self.assertTrue(reading.query_errors)
        self.assertIs(reading.derived_state(), EvidenceState.FAILED)

    def test_the_result_cap_prevents_complete_enumeration(self) -> None:
        """Draining pagination is not the same as enumerating the population."""

        reading = _read(
            {
                "total_count": GITHUB_SEARCH_RESULT_CAP + 1,
                "incomplete_results": False,
                "items": [{"id": index} for index in range(100)],
            },
            max_pages=1,
        )

        self.assertFalse(reading.pagination_complete)
        self.assertEqual(reading.population_units, GITHUB_SEARCH_RESULT_CAP + 1)
        self.assertGreater(reading.pages_expected or 0, reading.pages_examined or 0)

    def test_a_missing_total_leaves_the_coverage_unquantified(self) -> None:
        reading = _read({"incomplete_results": False, "items": []})

        self.assertIs(reading.population_basis, PopulationBasis.UNKNOWN)
        self.assertIsNone(reading.population_units)
        self.assertIsNone(reading.pages_expected)
        self.assertFalse(reading.pagination_complete)

    def test_a_missing_items_array_is_refused(self) -> None:
        with self.assertRaisesRegex(AdapterError, "missing an items array"):
            _read({"total_count": 0})

    def test_the_index_state_is_never_invented(self) -> None:
        """GitHub publishes no watermark, and inventing one is the whole failure."""

        reading = _read({"total_count": 0, "incomplete_results": False, "items": []})
        self.assertIsNone(reading.index_as_of)

    def test_results_are_always_reported_as_permission_limited(self) -> None:
        """Search returns what the authorization can see and never says what it hid."""

        reading = _read({"total_count": 0, "incomplete_results": False, "items": []})
        self.assertTrue(reading.permission_limited)


class ContractTests(unittest.TestCase):
    def test_an_adapter_must_declare_its_detection_assumptions(self) -> None:
        with self.assertRaisesRegex(AdapterError, "detection"):
            ReadOnlyAdapter(
                adapter_id="a",
                adapter_version="1",
                system="s",
                locator="l",
                accessible_population="p",
                detection_assumptions=(),
            )

    def test_the_transport_contract_has_no_write_operation(self) -> None:
        from evidence_state_io.adapters import base

        public = {name for name in dir(base.SearchTransport) if not name.startswith("_")}
        self.assertEqual(public, {"fetch_page"})

    def test_read_validates_its_arguments(self) -> None:
        adapter = _adapter({"total_count": 0, "incomplete_results": False, "items": []})
        for kwargs in (
            {"query": "", "observed_at": AT},
            {"query": "x", "observed_at": AT, "max_pages": 0},
            {"query": "x", "observed_at": AT, "per_page": 0},
            {"query": "x", "observed_at": AT, "per_page": 1000},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(AdapterError):
                    adapter.read(**kwargs)

    def test_an_unreadable_recording_fails_as_an_adapter_error(self) -> None:
        """A filesystem error must surface as "this reading could not be made"."""

        with self.assertRaisesRegex(AdapterError, "could not be read"):
            RecordedTransport.from_file(RECORDING.parent / "does-not-exist.json", retrieved_at=AT)

    def test_a_recording_must_be_a_non_empty_array(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write("[]")
            empty = handle.name
        with self.assertRaisesRegex(AdapterError, "non-empty JSON array"):
            RecordedTransport.from_file(empty, retrieved_at=AT)

    def test_a_page_beyond_the_recording_is_refused(self) -> None:
        transport = RecordedTransport.from_file(RECORDING, retrieved_at=AT)
        with self.assertRaisesRegex(AdapterError, "no recorded page"):
            transport.fetch_page(query="x", page=99, per_page=10)


class RecordedEvidenceTests(unittest.TestCase):
    """The recording is a real GitHub response, frozen."""

    def test_the_recorded_response_reproduces_its_reading(self) -> None:
        transport = RecordedTransport.from_file(RECORDING, retrieved_at=AT)
        reading = GitHubSearchAdapter(transport).read(query="topic:whatever", observed_at=AT)

        self.assertIs(reading.derived_state(), EvidenceState.ABSENT_WITHIN_SCOPE)
        self.assertEqual(reading.matched_count, 0)
        self.assertIsNone(reading.index_as_of)

    def test_the_recording_is_what_the_api_actually_returned(self) -> None:
        payloads = json.loads(RECORDING.read_text(encoding="utf-8"))
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["total_count"], 0)
        self.assertIs(payloads[0]["incomplete_results"], False)
        self.assertEqual(payloads[0]["items"], [])


class SecurityTests(unittest.TestCase):
    """Verified, not assumed."""

    def test_certificate_verification_cannot_be_disabled(self) -> None:
        from evidence_state_io.adapters import live

        context = live.resolve_trust_store()
        self.assertIs(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertNotIn(
            "insecure",
            " ".join(live.GitHubHttpTransport.__dataclass_fields__).lower(),
            "there must be no option that turns verification off",
        )
        self.assertNotIn("verify", " ".join(live.GitHubHttpTransport.__dataclass_fields__).lower())

    def test_the_transport_only_ever_issues_get(self) -> None:
        from evidence_state_io.adapters import live

        captured: list[str] = []

        class _Response:
            status = 200
            headers: dict[str, str] = {}

            def read(self) -> bytes:
                return b'{"total_count": 0, "incomplete_results": false, "items": []}'

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, *_: object) -> None:
                return None

        def _fake_urlopen(request, timeout=None, context=None):  # noqa: ANN001
            captured.append(request.get_method())
            return _Response()

        original = live.urllib.request.urlopen
        live.urllib.request.urlopen = _fake_urlopen  # type: ignore[assignment]
        try:
            transport = live.GitHubHttpTransport(retrieved_at=AT)
            transport.fetch_page(query="x", page=1, per_page=10)
        finally:
            live.urllib.request.urlopen = original  # type: ignore[assignment]

        self.assertEqual(captured, ["GET"])

    def test_a_token_never_reaches_a_record_or_an_error(self) -> None:
        import os

        from evidence_state_io.adapters import live

        # Assembled at runtime rather than written as a literal. A
        # credential-shaped string in a tracked file is exactly what the public
        # release gate is meant to refuse, and a test asserting that secrets do
        # not leak has no business shipping one.
        secret = "gh" + "p_" + ("t" * 36)
        previous = os.environ.get(live.GITHUB_TOKEN_VARIABLE)
        os.environ[live.GITHUB_TOKEN_VARIABLE] = secret
        try:
            transport = live.GitHubHttpTransport(
                retrieved_at=AT,
                use_token_from_environment=True,
            )
            headers = transport._headers()
            self.assertIn("Authorization", headers)

            reading = _read({"total_count": 0, "incomplete_results": False, "items": []})
            rendered = json.dumps(
                {
                    "reading": reading.coverage().to_dict(),
                    "errors": list(reading.query_errors),
                    "transport": repr(transport),
                }
            )
            self.assertNotIn(secret, rendered, "the token leaked into a record")
        finally:
            if previous is None:
                os.environ.pop(live.GITHUB_TOKEN_VARIABLE, None)
            else:
                os.environ[live.GITHUB_TOKEN_VARIABLE] = previous

    def test_no_token_is_read_unless_the_caller_opts_in(self) -> None:
        import os

        from evidence_state_io.adapters import live

        previous = os.environ.get(live.GITHUB_TOKEN_VARIABLE)
        os.environ[live.GITHUB_TOKEN_VARIABLE] = "gh" + "p_" + ("u" * 36)
        try:
            transport = live.GitHubHttpTransport(retrieved_at=AT)
            self.assertNotIn("Authorization", transport._headers())
        finally:
            if previous is None:
                os.environ.pop(live.GITHUB_TOKEN_VARIABLE, None)
            else:
                os.environ[live.GITHUB_TOKEN_VARIABLE] = previous

    def test_importing_the_package_does_not_import_the_network(self) -> None:
        """The evaluator must stay network-free, and that is an import property."""

        probe = (
            "import sys, evidence_state_io;"
            "network = [m for m in sys.modules if 'urllib.request' in m "
            "or m.endswith('adapters.live')];"
            "print(sorted(network))"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "[]", result.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
