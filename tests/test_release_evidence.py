from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class ReleaseEvidenceTests(unittest.TestCase):
    def test_generator_binds_tag_commit_artifact_and_spdx(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            repo = workspace / "repo"
            artifacts = workspace / "artifacts"
            output = workspace / "release"
            repo.mkdir()
            artifacts.mkdir()
            shutil.copy2(root / "pyproject.toml", repo / "pyproject.toml")
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True
            )
            subprocess.run(["git", "add", "pyproject.toml"], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "fixture"], cwd=repo, check=True, capture_output=True
            )
            subprocess.run(["git", "tag", "v0.6.0"], cwd=repo, check=True)
            artifact = artifacts / "evidence_state_io-0.6.0-py3-none-any.whl"
            artifact.write_bytes(b"synthetic-wheel")
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            ).stdout.strip()
            subprocess.run(
                [
                    "python3",
                    str(root / "scripts" / "generate_release_evidence.py"),
                    "--repo",
                    str(repo),
                    "--artifacts",
                    str(artifacts),
                    "--output",
                    str(output),
                    "--tag",
                    "v0.6.0",
                    "--commit",
                    commit,
                ],
                cwd=root,
                check=True,
            )

            manifest = json.loads((output / "EVIDENCE-MANIFEST.json").read_text())
            sbom = json.loads((output / "SBOM.spdx.json").read_text())
            self.assertEqual(manifest["commit"], commit)
            self.assertEqual(manifest["artifacts"][0]["name"], artifact.name)
            self.assertEqual(sbom["spdxVersion"], "SPDX-2.3")
            self.assertEqual(sbom["packages"][0]["licenseDeclared"], "Apache-2.0")

    def test_static_limitations_remain_explicit(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "release" / "LIMITATIONS.md").read_text(encoding="utf-8")
        for boundary in ("production", "source truth", "unsigned", "implementation-owned"):
            self.assertIn(boundary, text)


if __name__ == "__main__":
    unittest.main()
