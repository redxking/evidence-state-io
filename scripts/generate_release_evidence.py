#!/usr/bin/env python3
"""Generate a deterministic release manifest and SPDX SBOM for built artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    artifacts_dir = args.artifacts.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    commit = args.commit or git(repo, "rev-parse", "HEAD")
    if git(repo, "rev-parse", f"{args.tag}^{{commit}}") != commit:
        raise SystemExit("release tag and supplied commit do not identify the same revision")

    metadata = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    project = metadata["project"]
    if args.tag != f"v{project['version']}":
        raise SystemExit("release tag does not match the package version")

    artifacts = sorted(
        path for path in artifacts_dir.iterdir() if path.is_file() and path.name != "SHA256SUMS"
    )
    if not artifacts:
        raise SystemExit("no release artifacts found")
    artifact_records = [
        {"name": path.name, "sha256": digest(path), "size": path.stat().st_size}
        for path in artifacts
    ]

    manifest = {
        "schema": "esio-release-evidence-manifest/1.0",
        "project": project["name"],
        "version": project["version"],
        "tag": args.tag,
        "commit": commit,
        "source_tree": git(repo, "rev-parse", f"{commit}^{{tree}}"),
        "tracked_worktree_dirty": bool(git(repo, "status", "--porcelain", "--untracked-files=no")),
        "artifacts": artifact_records,
        "acceptance_ledger": "project/acceptance.json",
        "limitations": "release/LIMITATIONS.md",
        "claims_boundary": "docs/CLAIMS_AND_BOUNDARIES.md",
        "runtime_dependencies": [],
        "environment": {
            "python": sys.version.split()[0],
            "platform": os.environ.get("RUNNER_OS", sys.platform),
        },
    }
    write_json(output / "EVIDENCE-MANIFEST.json", manifest)

    namespace = f"https://github.com/redxking/evidence-state-io/releases/{args.tag}/{commit}"
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{project['name']}-{project['version']}",
        "documentNamespace": namespace,
        "creationInfo": {
            "created": "1970-01-01T00:00:00Z",
            "creators": ["Tool: scripts/generate_release_evidence.py"],
        },
        "documentDescribes": ["SPDXRef-Package-evidence-state-io"],
        "packages": [
            {
                "name": project["name"],
                "SPDXID": "SPDXRef-Package-evidence-state-io",
                "versionInfo": project["version"],
                "downloadLocation": f"git+https://github.com/redxking/evidence-state-io.git@{commit}",
                "filesAnalyzed": False,
                "licenseConcluded": "Apache-2.0",
                "licenseDeclared": "Apache-2.0",
                "copyrightText": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:pypi/evidence-state-io@{project['version']}",
                    }
                ],
            }
        ],
        "relationships": [],
    }
    write_json(output / "SBOM.spdx.json", sbom)

    checksum_lines = [f"{record['sha256']}  {record['name']}" for record in artifact_records]
    (output / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
