"""The MCP stdio server.

The server is a transport, and the one property a transport must not break is
the one the whole project rests on: the same input produces the same decision,
and the decision is the library's, not the transport's. Most of these tests
exist to pin that.
"""

from __future__ import annotations

import io
import json
import unittest
from typing import Any

from evidence_state_io.gate import NegativeClaimRequest, evaluate_negative_claim
from evidence_state_io.mcp_server import (
    LATEST_PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    handle_message,
    serve,
)
from tests.helpers import request_dict, trusted_context


def _frame(method: str, params: Any = None, request_id: Any = 1) -> str:
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return json.dumps(message)


def _rpc(method: str, params: Any = None, request_id: Any = 1) -> dict[str, Any]:
    response = handle_message(_frame(method, params, request_id))
    assert response is not None
    return response


def _call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return _rpc("tools/call", {"name": name, "arguments": arguments})["result"]


def _context_arguments() -> dict[str, Any]:
    context = trusted_context().to_dict()
    return {
        "registry_snapshot": context["registry_snapshot"],
        "trust_selection": context["trust_selection"],
    }


class ProtocolTests(unittest.TestCase):
    def test_discover_advertises_versions_capabilities_and_identity(self) -> None:
        """The newest revision requires this and uses it as a compatibility probe."""

        result = _rpc("server/discover")["result"]

        self.assertEqual(result["protocolVersions"], list(SUPPORTED_PROTOCOL_VERSIONS))
        self.assertIn("tools", result["capabilities"])
        self.assertEqual(result["serverInfo"]["name"], "evidence-state-io")
        self.assertEqual(result["resultType"], "complete")

    def test_initialize_still_answers_older_clients(self) -> None:
        """A server that only spoke the newest revision would be unreachable."""

        for version in SUPPORTED_PROTOCOL_VERSIONS:
            with self.subTest(version=version):
                result = _rpc("initialize", {"protocolVersion": version})["result"]
                self.assertEqual(result["protocolVersion"], version)

    def test_an_unknown_requested_version_falls_back_to_the_newest(self) -> None:
        result = _rpc("initialize", {"protocolVersion": "1999-01-01"})["result"]
        self.assertEqual(result["protocolVersion"], LATEST_PROTOCOL_VERSION)

    def test_tools_are_listed_in_a_fixed_order_with_cache_fields(self) -> None:
        result = _rpc("tools/list")["result"]

        self.assertEqual(
            [tool["name"] for tool in result["tools"]],
            ["assess_negative_claim", "explain_rejection", "describe_evidence_requirements"],
        )
        self.assertEqual(result["cacheScope"], "public")
        self.assertGreater(result["ttlMs"], 0)
        self.assertEqual(result, _rpc("tools/list")["result"])

    def test_a_notification_draws_no_response(self) -> None:
        self.assertIsNone(
            handle_message(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        )

    def test_protocol_faults_are_json_rpc_errors(self) -> None:
        cases = {
            "not json": ("{", -32700),
            "not jsonrpc 2.0": (json.dumps({"id": 1, "method": "tools/list"}), -32600),
            "no method": (json.dumps({"jsonrpc": "2.0", "id": 1}), -32600),
            "unknown method": (_frame("resources/list"), -32601),
        }
        for label, (raw, code) in cases.items():
            with self.subTest(case=label):
                response = handle_message(raw)
                assert response is not None
                self.assertEqual(response["error"]["code"], code)

    def test_an_unknown_tool_is_an_invalid_parameter(self) -> None:
        response = _rpc("tools/call", {"name": "delete_everything", "arguments": {}})
        self.assertEqual(response["error"]["code"], -32602)


class DecisionFidelityTests(unittest.TestCase):
    """The transport must not become a second evaluator."""

    def test_the_server_returns_the_librarys_own_decision(self) -> None:
        data = request_dict()
        result = _call("assess_negative_claim", {"request": data, **_context_arguments()})

        expected = evaluate_negative_claim(
            NegativeClaimRequest.from_dict(data),
            trusted_context(),
        ).to_dict()
        self.assertEqual(result["structuredContent"], expected)
        self.assertFalse(result["isError"])

    def test_the_same_request_produces_byte_identical_output(self) -> None:
        arguments = {"request": request_dict(), **_context_arguments()}
        first = handle_message(
            _frame("tools/call", {"name": "assess_negative_claim", "arguments": arguments})
        )
        second = handle_message(
            _frame("tools/call", {"name": "assess_negative_claim", "arguments": arguments})
        )
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )

    def test_the_text_content_is_the_structured_content(self) -> None:
        """A model reading the text must not see something else than the record."""

        result = _call("assess_negative_claim", {"request": request_dict(), **_context_arguments()})
        self.assertEqual(
            json.loads(result["content"][0]["text"]),
            result["structuredContent"],
        )

    def test_the_server_never_supplies_an_evaluation_time(self) -> None:
        """A gate that reads a clock cannot be replayed."""

        data = request_dict()
        del data["evaluated_at"]
        result = _call("assess_negative_claim", {"request": data, **_context_arguments()})
        self.assertTrue(result["isError"])


class RefusalTests(unittest.TestCase):
    def test_a_rejection_is_a_normal_result_not_an_error(self) -> None:
        data = request_dict()
        data["envelope"]["state"] = "PARTIAL"
        result = _call("assess_negative_claim", {"request": data, **_context_arguments()})

        self.assertFalse(result["isError"], "a rejection is the product working")
        self.assertEqual(result["structuredContent"]["decision"], "REJECT_NEGATIVE")

    def test_invalid_input_is_a_tool_error_not_a_transport_fault(self) -> None:
        response = _rpc(
            "tools/call",
            {"name": "assess_negative_claim", "arguments": {"request": {"not": "a request"}}},
        )
        self.assertNotIn("error", response)
        self.assertTrue(response["result"]["isError"])
        self.assertIn("error", response["result"]["structuredContent"])

    def test_half_a_trust_context_is_refused(self) -> None:
        """A snapshot with no trust selection pins nothing."""

        context = _context_arguments()
        for omitted in ("registry_snapshot", "trust_selection"):
            with self.subTest(omitted=omitted):
                arguments = {
                    "request": request_dict(),
                    **{k: v for k, v in context.items() if k != omitted},
                }
                result = _call("assess_negative_claim", arguments)
                self.assertTrue(result["isError"])


class ExplainTests(unittest.TestCase):
    def _rejected(self) -> dict[str, Any]:
        data = request_dict()
        data["envelope"]["state"] = "PARTIAL"
        return data

    def test_a_rejection_is_explained_as_conditions(self) -> None:
        result = _call(
            "explain_rejection",
            {"request": self._rejected(), **_context_arguments()},
        )
        remedy = result["structuredContent"]

        self.assertFalse(result["isError"])
        self.assertTrue(remedy["items"])
        for item in remedy["items"]:
            self.assertTrue(item["condition"].strip())
            self.assertIsNone(item["governed_value"], "CONSTRAINT_ONLY must disclose no value")

    def test_governed_values_are_disclosed_only_when_asked(self) -> None:
        arguments = {"request": self._rejected(), **_context_arguments()}
        closed = _call("explain_rejection", arguments)["structuredContent"]
        opened = _call(
            "explain_rejection",
            {**arguments, "disclosure": "WITH_GOVERNED_VALUES"},
        )["structuredContent"]

        self.assertEqual(closed["disclosure"], "CONSTRAINT_ONLY")
        self.assertEqual(opened["disclosure"], "WITH_GOVERNED_VALUES")
        self.assertEqual(
            [item["reason"] for item in closed["items"]],
            [item["reason"] for item in opened["items"]],
            "disclosure must not change which constraints are reported",
        )

    def test_a_permit_has_nothing_to_explain(self) -> None:
        result = _call("explain_rejection", {"request": request_dict(), **_context_arguments()})
        self.assertTrue(result["isError"])

    def test_neither_a_request_nor_a_certificate_is_refused(self) -> None:
        self.assertTrue(_call("explain_rejection", {})["isError"])


class DescribeTests(unittest.TestCase):
    def test_the_contract_is_described_without_input(self) -> None:
        result = _call("describe_evidence_requirements", {})
        payload = result["structuredContent"]

        self.assertFalse(result["isError"])
        self.assertIn("ABSENT_WITHIN_SCOPE", payload["evidence_states"])
        self.assertTrue(payload["an_assessable_request_must_declare"])
        self.assertTrue(payload["a_permit_does_not_establish"])
        self.assertEqual(
            payload["a_rejection_does_not_establish"],
            ["that the positive opposite is true"],
        )


class TransportTests(unittest.TestCase):
    def test_serve_reads_frames_and_writes_one_response_per_request(self) -> None:
        stdin = io.StringIO(
            "\n".join(
                [
                    _frame("server/discover", request_id="a"),
                    "",
                    json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                    _frame("tools/list", request_id="b"),
                ]
            )
            + "\n"
        )
        stdout = io.StringIO()

        self.assertEqual(serve(stdin, stdout), 0)
        lines = [line for line in stdout.getvalue().splitlines() if line]
        self.assertEqual([json.loads(line)["id"] for line in lines], ["a", "b"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
