#!/usr/bin/env python3
"""Fail closed on common public-release hazards in the tracked repository."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

TEXT_SUFFIXES = {
    "",
    ".cff",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
DENIED_SUFFIXES = {".key", ".p12", ".pfx", ".pem"}
REQUIRED_WIKI = {
    "ADR-Index.md",
    "Architecture.md",
    "Benchmark-Methodology.md",
    "Contributing-and-Development-Workflow.md",
    "Demo-Walkthrough.md",
    "Deployment-Models.md",
    "Evidence-State-Model.md",
    "Executive-Overview.md",
    "FAQ.md",
    "Gateway-Processing-Pipeline.md",
    "Governance-and-Assurance.md",
    "Home.md",
    "Integration-Guide.md",
    "Known-Limitations-and-Open-Questions.md",
    "Operations-and-Troubleshooting.md",
    "Problem-Definition.md",
    "Product-Scope-and-Non-Goals.md",
    "Quick-Start.md",
    "Release-History.md",
    "Roadmap.md",
    "Schemas-and-Interface-Contracts.md",
    "Security-and-Threat-Model.md",
    "Terminology-and-Glossary.md",
    "Test-and-Verification-Strategy.md",
}
PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "credential_assignment": re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*[\"']?[^\s\"'${}<]{12,}"
    ),
    "local_user_path": re.compile(r"/(?:Users|home)/[^/\s]+/"),
    "sensitive_marking": re.compile(r"\b(?:TOP " + r"SECRET|SECRET//|CONFIDENTIAL//)\b"),
}


def tracked_files(repo: Path) -> tuple[str, ...]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=repo, check=True, capture_output=True)
    return tuple(item.decode("utf-8") for item in result.stdout.split(b"\0") if item)


def inspect(repo: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = tracked_files(repo)
    for relative in paths:
        path = repo / relative
        if path.suffix.lower() in DENIED_SUFFIXES:
            findings.append({"path": relative, "rule": "denied_sensitive_suffix"})
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            findings.append({"path": relative, "rule": "unreviewed_non_utf8_content"})
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append({"path": relative, "line": line_number, "rule": name})

    required = {
        ".gitignore",
        "CITATION.cff",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "GOVERNANCE.md",
        "LICENSE",
        "NOTICE",
        "SECURITY.md",
        "SUPPORT.md",
        "docs/CLAIMS_AND_BOUNDARIES.md",
        "docs/SOURCE_REGISTER.md",
        "release/LIMITATIONS.md",
    }
    for missing in sorted(required - set(paths)):
        findings.append({"path": missing, "rule": "required_release_file_missing"})
    for missing in sorted(
        REQUIRED_WIKI - {Path(path).name for path in paths if path.startswith("wiki/")}
    ):
        findings.append({"path": f"wiki/{missing}", "rule": "required_wiki_page_missing"})

    license_text = (
        (repo / "LICENSE").read_text(encoding="utf-8") if (repo / "LICENSE").is_file() else ""
    )
    if "Apache License" not in license_text or "Version 2.0" not in license_text:
        findings.append({"path": "LICENSE", "rule": "license_not_apache_2_0"})

    return {
        "schema": "esio-public-release-gate/1.0",
        "status": "PASS" if not findings else "FAIL",
        "tracked_files": len(paths),
        "checks": [
            "secrets_and_credentials",
            "sensitive_markings_and_local_paths",
            "sensitive_file_types",
            "license_and_release_files",
            "canonical_wiki_inventory",
        ],
        "findings": findings,
        "limitations": [
            "Pattern scanning does not prove that no secret or sensitive information exists.",
            "GitHub secret scanning, dependency review, CodeQL, provenance review, and owner review remain separate gates.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = inspect(args.repo.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
