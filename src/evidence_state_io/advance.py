"""Bounded, evidence-driven continuation for the repository project state.

This module is operational tooling. It is deliberately outside the
deterministic gateway decision path and may observe Git state and wall time.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from fnmatch import fnmatch
from hashlib import sha256
from pathlib import Path
from typing import Any, Sequence

PROJECT_STATE_SCHEMA = "esio-project-state/1.0"
TASK_LEDGER_SCHEMA = "esio-task-ledger/1.0"
ACCEPTANCE_LEDGER_SCHEMA = "esio-acceptance-ledger/1.0"
ACCEPTANCE_STATUSES = {"PASS", "FAIL", "BLOCKED", "UNVERIFIED", "STALE"}
TASK_STATUSES = {"pending", "in_progress", "verified", "blocked"}
MAX_ITERATIONS = 10
CONTROL_RECORDS = {
    "project/acceptance.json",
    "project/progress.jsonl",
    "project/state.json",
    "project/tasks.json",
}


class AdvanceError(RuntimeError):
    """Raised for a safe operational stop."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdvanceError(f"cannot read valid JSON from {path}") from exc
    if type(value) is not dict:
        raise AdvanceError(f"{path} must contain one JSON object")
    return value


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary.write_text(data, encoding="utf-8")
    os.replace(temporary, path)


def _append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _git(repo: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise AdvanceError(detail)
    return result


def _tracked_paths(repo: Path, patterns: Sequence[str]) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AdvanceError("cannot enumerate tracked project files")
    paths = tuple(item.decode("utf-8") for item in result.stdout.split(b"\0") if item)
    return tuple(
        path
        for path in paths
        if path not in CONTROL_RECORDS and any(fnmatch(path, pattern) for pattern in patterns)
    )


def fingerprint(repo: Path, patterns: Sequence[str]) -> str:
    """Return a deterministic digest of tracked paths and their current bytes."""

    digest = sha256()
    for relative in sorted(_tracked_paths(repo, patterns)):
        target = repo / relative
        if not target.is_file():
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(target.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _validate_ledgers(
    state: dict[str, Any], tasks: dict[str, Any], acceptance: dict[str, Any]
) -> None:
    if state.get("schema") != PROJECT_STATE_SCHEMA:
        raise AdvanceError("unsupported project-state schema")
    if tasks.get("schema") != TASK_LEDGER_SCHEMA or type(tasks.get("tasks")) is not list:
        raise AdvanceError("unsupported task-ledger schema")
    if (
        acceptance.get("schema") != ACCEPTANCE_LEDGER_SCHEMA
        or type(acceptance.get("criteria")) is not list
    ):
        raise AdvanceError("unsupported acceptance-ledger schema")
    criterion_ids: set[str] = set()
    for criterion in acceptance["criteria"]:
        if type(criterion) is not dict or type(criterion.get("id")) is not str:
            raise AdvanceError("each acceptance criterion must be an identified object")
        if criterion["id"] in criterion_ids:
            raise AdvanceError(f"duplicate acceptance criterion {criterion['id']}")
        criterion_ids.add(criterion["id"])
        if criterion.get("status") not in ACCEPTANCE_STATUSES:
            raise AdvanceError(f"invalid status for {criterion['id']}")
        if type(criterion.get("watched_paths")) is not list or not all(
            type(item) is str for item in criterion["watched_paths"]
        ):
            raise AdvanceError(f"invalid watched_paths for {criterion['id']}")
    task_ids: set[str] = set()
    for task in tasks["tasks"]:
        if type(task) is not dict or type(task.get("id")) is not str:
            raise AdvanceError("each task must be an identified object")
        if task["id"] in task_ids:
            raise AdvanceError(f"duplicate task {task['id']}")
        task_ids.add(task["id"])
        if task.get("status") not in TASK_STATUSES:
            raise AdvanceError(f"invalid status for task {task['id']}")
        linked = task.get("acceptance", [])
        if type(linked) is not list or not set(linked).issubset(criterion_ids):
            raise AdvanceError(f"task {task['id']} has an unknown acceptance link")


class ProjectLock(AbstractContextManager["ProjectLock"]):
    """Non-blocking project-local process lock."""

    def __init__(self, repo: Path):
        git_dir = _git(repo, "rev-parse", "--git-dir").stdout.strip()
        resolved = Path(git_dir)
        if not resolved.is_absolute():
            resolved = repo / resolved
        self.path = resolved / "evidence-state-advance.lock"
        self._stream: Any = None

    def __enter__(self) -> "ProjectLock":
        self._stream = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self._stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._stream.close()
            self._stream = None
            raise AdvanceError("another continuation run holds the project lock") from exc
        self._stream.seek(0)
        self._stream.truncate()
        self._stream.write(f"pid={os.getpid()}\n")
        self._stream.flush()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._stream is not None:
            fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
            self._stream.close()
            self._stream = None


class ProjectController:
    """Reconcile and advance the repository-owned project ledgers."""

    def __init__(self, repo: Path):
        self.repo = repo.resolve()
        self.project_dir = self.repo / "project"
        self.state_path = self.project_dir / "state.json"
        self.tasks_path = self.project_dir / "tasks.json"
        self.acceptance_path = self.project_dir / "acceptance.json"
        self.progress_path = self.project_dir / "progress.jsonl"
        self.state = _read_json(self.state_path)
        self.tasks = _read_json(self.tasks_path)
        self.acceptance = _read_json(self.acceptance_path)
        _validate_ledgers(self.state, self.tasks, self.acceptance)

    def save(self) -> None:
        _validate_ledgers(self.state, self.tasks, self.acceptance)
        _atomic_write_json(self.state_path, self.state)
        _atomic_write_json(self.tasks_path, self.tasks)
        _atomic_write_json(self.acceptance_path, self.acceptance)

    def reconcile(self, *, inspect_remote: bool = False) -> dict[str, Any]:
        now = _utc_now()
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        branch = _git(self.repo, "branch", "--show-current").stdout.strip()
        dirty = bool(_git(self.repo, "status", "--porcelain").stdout)
        local = self.state.setdefault("repository", {}).setdefault("local", {})
        local.update({"branch": branch, "commit": head, "dirty": dirty})

        stale: list[str] = []
        for criterion in self.acceptance["criteria"]:
            if criterion["status"] not in {"PASS", "STALE"}:
                continue
            evidence = criterion.get("evidence")
            if type(evidence) is not dict or type(evidence.get("fingerprint")) is not str:
                if criterion["status"] == "PASS":
                    criterion["status"] = "STALE"
                    stale.append(criterion["id"])
                continue
            observed = fingerprint(self.repo, criterion["watched_paths"])
            if observed != evidence["fingerprint"]:
                criterion["status"] = "STALE"
                criterion["stale_reason"] = "watched project inputs changed"
                criterion["stale_at"] = now
                stale.append(criterion["id"])

        remote_commit: str | None = None
        if inspect_remote:
            remote = self.state["repository"].setdefault("remote", {})
            remote_name = remote.get("name", "origin")
            default_branch = remote.get("default_branch", "main")
            query = _git(
                self.repo,
                "ls-remote",
                "--heads",
                remote_name,
                default_branch,
                check=False,
            )
            if query.returncode == 0 and query.stdout.strip():
                remote_commit = query.stdout.split()[0]
                remote.update(
                    {
                        "commit": remote_commit,
                        "observed_at": now,
                        "reachable": True,
                    }
                )
            else:
                remote.update({"observed_at": now, "reachable": False})

        self.state["updated_at"] = now
        self.state["lifecycle"] = (
            "MVP_ACCEPTED_AND_PUBLISHED"
            if all(row["status"] == "PASS" for row in self.acceptance["criteria"])
            else "MVP_NOT_ACCEPTED"
        )
        self.save()
        event = {
            "schema": "esio-progress-event/1.0",
            "at": now,
            "event": "reconciled",
            "commit": head,
            "dirty": dirty,
            "remote_commit": remote_commit,
            "stale_criteria": stale,
        }
        _append_event(self.progress_path, event)
        return event

    def next_task(self) -> dict[str, Any] | None:
        statuses = {task["id"]: task["status"] for task in self.tasks["tasks"]}
        candidates: list[dict[str, Any]] = []
        for task in self.tasks["tasks"]:
            if task["status"] in {"verified", "blocked"}:
                continue
            dependencies = task.get("dependencies", [])
            if any(statuses.get(item) != "verified" for item in dependencies):
                continue
            candidates.append(task)
        if not candidates:
            return None
        return min(candidates, key=lambda task: (int(task["priority"]), task["id"]))

    def _criterion(self, identifier: str) -> dict[str, Any]:
        for criterion in self.acceptance["criteria"]:
            if criterion["id"] == identifier:
                return criterion
        raise AdvanceError(f"unknown acceptance criterion {identifier}")

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        execution = task.get("execution", {})
        if execution.get("mode") != "verify":
            return {
                "status": "needs_engineering_or_external_action",
                "task": task["id"],
                "next_action": task.get("next_action"),
            }
        commands = execution.get("commands")
        if type(commands) is not list or not commands:
            raise AdvanceError(f"verification task {task['id']} has no commands")
        # The repository-local lock is the durable in-progress signal. Writing
        # the tracked ledgers before a clean-tree verification command would
        # invalidate that command's custody precondition.
        task["status"] = "in_progress"
        outputs: list[dict[str, Any]] = []
        for command in commands:
            if (
                type(command) is not list
                or not command
                or not all(type(part) is str for part in command)
            ):
                raise AdvanceError(f"task {task['id']} has an invalid command")
            result = subprocess.run(
                command,
                cwd=self.repo,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            combined = result.stdout + result.stderr
            outputs.append(
                {
                    "command": command,
                    "returncode": result.returncode,
                    "output_digest": "sha256:" + sha256(combined.encode("utf-8")).hexdigest(),
                }
            )
            if result.returncode != 0:
                task["status"] = "pending"
                task["last_failure"] = {
                    "at": _utc_now(),
                    "command": command,
                    "returncode": result.returncode,
                    "output_tail": combined[-4000:],
                }
                self.save()
                event = {
                    "schema": "esio-progress-event/1.0",
                    "at": _utc_now(),
                    "event": "verification_failed",
                    "task": task["id"],
                    "command": command,
                    "returncode": result.returncode,
                }
                _append_event(self.progress_path, event)
                return {"status": "failed", "task": task["id"], "outputs": outputs}

        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        dirty = bool(_git(self.repo, "status", "--porcelain").stdout)
        now = _utc_now()
        for identifier in task.get("pass_criteria", []):
            criterion = self._criterion(identifier)
            criterion["status"] = "PASS"
            criterion.pop("stale_reason", None)
            criterion.pop("stale_at", None)
            criterion["evidence"] = {
                "at": now,
                "commit": head,
                "dirty": dirty,
                "procedure": commands,
                "result": "PASS",
                "fingerprint": fingerprint(self.repo, criterion["watched_paths"]),
                "output_digests": [item["output_digest"] for item in outputs],
            }
        task["status"] = "verified"
        task["verified_at"] = now
        task["verified_commit"] = head
        self.state["updated_at"] = now
        self.save()
        event = {
            "schema": "esio-progress-event/1.0",
            "at": now,
            "event": "task_verified",
            "task": task["id"],
            "commit": head,
            "dirty": dirty,
            "criteria": task.get("pass_criteria", []),
            "outputs": outputs,
        }
        _append_event(self.progress_path, event)
        return {"status": "verified", "task": task["id"], "outputs": outputs}

    def status(self) -> dict[str, Any]:
        counts = {status: 0 for status in sorted(ACCEPTANCE_STATUSES)}
        for criterion in self.acceptance["criteria"]:
            counts[criterion["status"]] += 1
        task = self.next_task()
        return {
            "schema": "esio-advance-status/1.0",
            "lifecycle": self.state["lifecycle"],
            "repository": self.state["repository"],
            "acceptance": counts,
            "next_task": None if task is None else task["id"],
        }

    def commit_and_push_state(self) -> str | None:
        allowed = {
            "project/state.json",
            "project/tasks.json",
            "project/acceptance.json",
            "project/progress.jsonl",
        }
        changed = set(
            line[3:] for line in _git(self.repo, "status", "--porcelain").stdout.splitlines()
        )
        unrelated = changed - allowed
        if unrelated:
            raise AdvanceError(
                "refusing automated commit with unrelated changes: " + ", ".join(sorted(unrelated))
            )
        if not changed:
            return None
        _git(self.repo, "add", *sorted(changed))
        commit = _git(
            self.repo,
            "commit",
            "-s",
            "-m",
            "chore: reconcile project acceptance state",
        )
        if commit.returncode != 0:
            raise AdvanceError("could not commit reconciled project state")
        _git(self.repo, "push", "origin", "HEAD:main")
        return _git(self.repo, "rev-parse", "HEAD").stdout.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile and advance Evidence-State I/O from repository evidence."
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--status", action="store_true", help="Print current state only.")
    parser.add_argument("--reconcile", action="store_true", help="Invalidate stale evidence.")
    parser.add_argument("--remote", action="store_true", help="Inspect the configured remote.")
    parser.add_argument(
        "--until-blocked",
        action="store_true",
        help="Run bounded machine-verifiable tasks until one needs engineering or external action.",
    )
    parser.add_argument("--max-iterations", type=int, default=1)
    parser.add_argument("--commit-and-push", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.max_iterations < 1 or arguments.max_iterations > MAX_ITERATIONS:
        print(
            json.dumps(
                {
                    "error": "max_iterations must be between 1 and 10",
                    "schema": "esio-advance-error/1.0",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    try:
        controller = ProjectController(arguments.repo)
        if arguments.status and not (
            arguments.reconcile or arguments.until_blocked or arguments.commit_and_push
        ):
            print(json.dumps(controller.status(), indent=2, sort_keys=True))
            return 0
        with ProjectLock(controller.repo):
            if arguments.reconcile or arguments.until_blocked:
                controller.reconcile(inspect_remote=arguments.remote)
            results: list[dict[str, Any]] = []
            if arguments.until_blocked:
                for _ in range(arguments.max_iterations):
                    task = controller.next_task()
                    if task is None:
                        break
                    result = controller.run_task(task)
                    results.append(result)
                    if result["status"] != "verified":
                        break
            pushed = None
            if arguments.commit_and_push:
                pushed = controller.commit_and_push_state()
            print(
                json.dumps(
                    {
                        "schema": "esio-advance-run/1.0",
                        "results": results,
                        "pushed_commit": pushed,
                        "status": controller.status(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            if results and results[-1]["status"] == "failed":
                return 1
            if results and results[-1]["status"] == "needs_engineering_or_external_action":
                return 3
            return 0
    except AdvanceError as exc:
        print(
            json.dumps(
                {"error": str(exc), "schema": "esio-advance-error/1.0"},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
