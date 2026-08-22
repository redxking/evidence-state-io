from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from evidence_state_io.advance import (
    AdvanceError,
    ProjectController,
    ProjectLock,
    _validate_ledgers,
    fingerprint,
    main,
)


class AdvanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        subprocess.run(
            ["git", "init", "-b", "main"], cwd=self.repo, check=True, capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.invalid"], cwd=self.repo, check=True
        )
        (self.repo / "project").mkdir()
        (self.repo / "src").mkdir()
        (self.repo / "src" / "value.txt").write_text("one\n", encoding="utf-8")
        self.state = {
            "schema": "esio-project-state/1.0",
            "lifecycle": "MVP_NOT_ACCEPTED",
            "repository": {
                "local": {},
                "remote": {"name": "origin", "default_branch": "main"},
            },
            "updated_at": "2026-08-22T00:00:00Z",
        }
        self.acceptance = {
            "schema": "esio-acceptance-ledger/1.0",
            "criteria": [
                {
                    "id": "A-1",
                    "title": "example",
                    "status": "UNVERIFIED",
                    "watched_paths": ["src/**"],
                }
            ],
        }
        self.tasks = {
            "schema": "esio-task-ledger/1.0",
            "tasks": [
                {
                    "id": "T-1",
                    "title": "manual",
                    "priority": 1,
                    "status": "pending",
                    "dependencies": [],
                    "acceptance": ["A-1"],
                    "execution": {"mode": "external"},
                    "next_action": "inspect external state",
                }
            ],
        }
        self._write_ledgers()
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "fixture"], cwd=self.repo, check=True, capture_output=True
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_ledgers(self) -> None:
        for name, value in (
            ("state.json", self.state),
            ("acceptance.json", self.acceptance),
            ("tasks.json", self.tasks),
        ):
            (self.repo / "project" / name).write_text(json.dumps(value), encoding="utf-8")
        (self.repo / "project" / "progress.jsonl").write_text("", encoding="utf-8")

    def test_fingerprint_changes_with_watched_bytes(self) -> None:
        before = fingerprint(self.repo, ["src/**"])
        (self.repo / "src" / "value.txt").write_text("two\n", encoding="utf-8")
        self.assertNotEqual(before, fingerprint(self.repo, ["src/**"]))

    def test_control_records_do_not_create_self_referential_fingerprints(self) -> None:
        before = fingerprint(self.repo, ["**"])
        (self.repo / "project" / "progress.jsonl").write_text("event\n", encoding="utf-8")
        self.acceptance["criteria"][0]["status"] = "STALE"
        self._write_ledgers()
        self.assertEqual(before, fingerprint(self.repo, ["**"]))

    def test_reconcile_invalidates_stale_pass(self) -> None:
        controller = ProjectController(self.repo)
        criterion = controller.acceptance["criteria"][0]
        criterion["status"] = "PASS"
        criterion["evidence"] = {
            "fingerprint": fingerprint(self.repo, ["src/**"]),
        }
        controller.save()
        (self.repo / "src" / "value.txt").write_text("changed\n", encoding="utf-8")
        event = controller.reconcile()
        self.assertEqual(event["stale_criteria"], ["A-1"])
        self.assertEqual(controller.acceptance["criteria"][0]["status"], "STALE")

    def test_manual_task_stops_without_claiming_pass(self) -> None:
        controller = ProjectController(self.repo)
        result = controller.run_task(controller.next_task())
        self.assertEqual(result["status"], "needs_engineering_or_external_action")
        self.assertEqual(controller.acceptance["criteria"][0]["status"], "UNVERIFIED")

    def test_nonblocking_project_lock(self) -> None:
        with ProjectLock(self.repo):
            with self.assertRaisesRegex(AdvanceError, "holds the project lock"):
                with ProjectLock(self.repo):
                    self.fail("second lock should not be acquired")

    def test_unknown_acceptance_link_is_rejected(self) -> None:
        tasks = deepcopy(self.tasks)
        tasks["tasks"][0]["acceptance"] = ["missing"]
        with self.assertRaisesRegex(AdvanceError, "unknown acceptance link"):
            _validate_ledgers(self.state, tasks, self.acceptance)

    def test_iteration_limit_is_bounded(self) -> None:
        self.assertEqual(main(["--repo", str(self.repo), "--max-iterations", "11"]), 2)

    def test_verify_task_runs_against_clean_tree_then_records_evidence(self) -> None:
        self.tasks["tasks"][0].update(
            {
                "execution": {
                    "mode": "verify",
                    "commands": [
                        [
                            "git",
                            "diff-index",
                            "--quiet",
                            "HEAD",
                            "--",
                        ]
                    ],
                },
                "pass_criteria": ["A-1"],
            }
        )
        self._write_ledgers()
        subprocess.run(["git", "add", "project"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "verification task"],
            cwd=self.repo,
            check=True,
            capture_output=True,
        )
        controller = ProjectController(self.repo)
        result = controller.run_task(controller.next_task())
        self.assertEqual(result["status"], "verified")
        criterion = controller.acceptance["criteria"][0]
        self.assertEqual(criterion["status"], "PASS")
        self.assertFalse(criterion["evidence"]["dirty"])


if __name__ == "__main__":
    unittest.main()
