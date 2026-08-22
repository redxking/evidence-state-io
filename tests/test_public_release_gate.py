from __future__ import annotations

import unittest

from scripts.public_release_gate import PATTERNS


class PublicReleaseGateTests(unittest.TestCase):
    def test_sensitive_patterns_detect_representative_hazards(self) -> None:
        cases = {
            "private_key": "-----BEGIN " + "PRIVATE KEY-----",
            "github_token": "ghp_" + "abcdefghijklmnopqrstuvwxyz123456",
            "aws_access_key": "AKIA" + "ABCDEFGHIJKLMNOP",
            "slack_token": "xoxb-" + "1234567890-abcdefghij",
            "credential_assignment": "api_key=" + "abcdefghijklmnop",
            "local_user_path": "/" + "Users/example/project",
            "sensitive_marking": "TOP " + "SECRET test",
        }
        for name, value in cases.items():
            with self.subTest(rule=name):
                self.assertRegex(value, PATTERNS[name])

    def test_placeholders_do_not_trigger_credential_assignment(self) -> None:
        for value in ("api_key=${API_KEY}", "password=<redacted>", "secret=example"):
            with self.subTest(value=value):
                self.assertNotRegex(value, PATTERNS["credential_assignment"])


if __name__ == "__main__":
    unittest.main()
