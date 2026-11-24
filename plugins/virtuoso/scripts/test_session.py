"""Preserving a session before it is cleared.

The registry groundwork (the opt-in ``sessionRecords`` role and the ``preserve-session``
actor), and the ``session`` subcommand's spine: the gate that refuses while anything
still runs, the inventory that keeps this session's files apart from another's, and the
record check that says "safe to clear" only once every kept item is verified where it
went.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import schema

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")
MANIFEST = Path("Virtuoso") / "workspace-layout.json"


def run(script, *args, cwd=None):
    return subprocess.run([sys.executable, script, *args], capture_output=True,
                          text=True, encoding="utf-8", env=dict(os.environ), cwd=cwd)


@pytest.fixture
def workspace(project):
    assert run(PREFLIGHT, "--root", str(project), "--mode", "create",
               "--authorize").returncode == 0
    return project


def manifest(root: Path) -> dict:
    return json.loads((root / MANIFEST).read_text(encoding="utf-8"))


def write_manifest(root: Path, data: dict) -> None:
    (root / MANIFEST).write_text(json.dumps(data, indent=2), encoding="utf-8")


# =============================================================================
# The registry groundwork
# =============================================================================


def test_the_session_records_role_is_opt_in():
    assert "sessionRecords" not in schema.CREATE_ROLE_ORDER
    role = schema.DEFAULT_ROLES["sessionRecords"]
    assert role["allowedWriters"] == ["preserve-session", "governance-sweep"]
    assert role["mutability"] == "append-only"
    assert role["owner"] == "preserve-session"


def test_the_new_actor_writes_only_its_four_roles(workspace):
    writes = {name for name, role in schema.DEFAULT_ROLES.items()
              if "preserve-session" in role.get("allowedWriters", [])}
    assert writes == {"sessionRecords", "findings", "issues", "holdingBay"}

    # A layout that registered the holding bay before the actor existed keeps its own
    # writers: the actor is refused, and the refusal names the role and the field.
    data = manifest(workspace)
    data["roles"]["holdingBay"] = {
        "path": "Virtuoso/holding", "provider": "directory", "authority": "reference",
        "mutability": "read-write", "owner": "write-plan",
        "allowedWriters": ["storyboard", "write-plan", "virtuoso", "dispatch-closeout",
                           "roadmap-review"]}
    write_manifest(workspace, data)
    bay = workspace / "Virtuoso" / "holding"
    bay.mkdir(parents=True)
    entry = bay / "2026-09-24-export-retry.md"
    entry.write_text("# Held Plan — x\n\n<!-- virtuoso-held-plan v1 -->\n", encoding="utf-8")
    before = entry.read_bytes()
    refused = run(REGISTRY_CLI, "--root", str(workspace), "--actor", "preserve-session",
                  "holding", "--record", "2026-09-24-export-retry", "--state", "paused",
                  "--apply")
    assert refused.returncode == 3
    assert "may not write the holdingBay role" in refused.stderr
    assert "allowedWriters" in refused.stderr
    assert entry.read_bytes() == before


# =============================================================================
# Transcripts
# =============================================================================

MARKER = "preserve-session:0a1b2c3d"
SESSION = "s-1"


def _tool(i, name, args, at="2026-02-01T10:00:00.000Z"):
    return {"type": "assistant", "timestamp": at, "sessionId": SESSION, "message": {
        "id": "m%d" % i, "model": "claude-opus-5-5", "content": [
            {"type": "tool_use", "id": "t%d" % i, "name": name, "input": args}],
        "usage": {"input_tokens": 1, "output_tokens": 1}}}


def _said(text, at="2026-02-01T10:00:00.000Z"):
    return {"type": "assistant", "timestamp": at, "sessionId": SESSION, "message": {
        "id": "said-%d" % abs(hash(text)), "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": text}], "usage": {"input_tokens": 1,
                                                              "output_tokens": 1}}}


def _returned(i, result, text="ok"):
    return {"type": "user", "toolUseResult": result, "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t%d" % i, "content": text}]}}


def _notified(i):
    return {"type": "user", "message": {"content": (
        "<task-notification>\n<task-id>x%d</task-id>\n<tool-use-id>t%d</tool-use-id>\n"
        "<status>completed</status>\n</task-notification>" % (i, i))}}


def _filler(megabytes: float):
    chunk = "x" * 65536
    return [{"type": "user", "message": {"content": chunk}}
            for _ in range(int(megabytes * 16) + 1)]


def claude_transcript(home: Path, records, name=SESSION, folder="C--project") -> Path:
    path = home / "host-a" / "projects" / folder / ("%s.jsonl" % name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def gate(root, *extra):
    return run(REGISTRY_CLI, "--root", str(root), "--json", "session", "--gate",
               "--marker", MARKER, *extra)


LAUNCHES = [
    _said("Printing the marker: " + MARKER),
    _tool(1, "Bash", {"command": "pytest", "run_in_background": True,
                      "description": "suite"}),
    _returned(1, {"backgroundTaskId": "b1", "stdout": ""}),
    _tool(2, "Agent", {"description": "review", "prompt": "p", "run_in_background": True}),
    _returned(2, {"isAsync": True, "status": "async_launched", "agentId": "a2"}),
    _tool(3, "CronCreate", {"cron": "*/5 * * * *", "prompt": "check"}),
    _returned(3, {"id": "job42"}, "Scheduled job job42"),
]


def test_the_gate_names_what_is_still_running(workspace, isolated_home):
    # the launches sit more than 2 MiB before the end: a tail read would miss them
    claude_transcript(isolated_home, LAUNCHES + _filler(2.5) + [_said("later")])
    completed = gate(workspace)
    assert completed.returncode == 1, completed.stdout + completed.stderr
    running = json.loads(completed.stdout)["running"]
    assert sorted(h["id"] for h in running) == ["t1", "t2", "t3"]
    assert {h["kind"] for h in running} == {"background shell", "subagent",
                                             "scheduled check-in"}


def test_the_gate_passes_when_every_launch_finished(workspace, isolated_home):
    finished = LAUNCHES + [_notified(1), _notified(2), _tool(4, "CronDelete", {"id": "job42"}),
                           _returned(4, {"ok": True})]
    claude_transcript(isolated_home, finished)
    completed = gate(workspace)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout)["running"] == []

    # Two launches share a description and only one completes: pairing is by id.
    same = [_said(MARKER),
            _tool(5, "Agent", {"description": "review", "run_in_background": True}),
            _returned(5, {"isAsync": True}),
            _tool(6, "Agent", {"description": "review", "run_in_background": True}),
            _returned(6, {"isAsync": True}),
            _notified(6)]
    claude_transcript(isolated_home, same)
    completed = gate(workspace)
    assert completed.returncode == 1
    assert [h["id"] for h in json.loads(completed.stdout)["running"]] == ["t5"]


def test_a_shell_moved_to_the_background_is_still_running(workspace, isolated_home):
    """No run_in_background flag: the person or the host backgrounded it mid-run."""
    claude_transcript(isolated_home, [
        _said(MARKER), _tool(7, "Bash", {"command": "npm run dev", "description": "dev"}),
        _returned(7, {"backgroundTaskId": "b7", "stdout": ""})])
    completed = gate(workspace)
    assert completed.returncode == 1, completed.stdout
    assert [h["id"] for h in json.loads(completed.stdout)["running"]] == ["t7"]


def test_an_interim_notification_is_not_a_completion(workspace, isolated_home):
    interim = {"type": "user", "message": {"content": (
        "<task-notification>\n<tool-use-id>t2</tool-use-id>\n<status>completed</status>\n"
        "<note>This agent stopped with background work of its own still running.</note>\n"
        "</task-notification>")}}
    claude_transcript(isolated_home, [_said(MARKER)] + LAUNCHES[3:5] + [interim])
    completed = gate(workspace)
    assert completed.returncode == 1
    assert [h["id"] for h in json.loads(completed.stdout)["running"]] == ["t2"]


def _antigravity_transcript(home: Path, text: str) -> None:
    from tools.governance.hosts import antigravity
    path = home / ".gemini" / antigravity.APP_DATA_DIRS[0] / "brain" / "conv-1" / \
        antigravity.TRANSCRIPT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"type": "PLANNER_RESPONSE", "content": text}) + "\n",
                    encoding="utf-8")


@pytest.mark.parametrize("case", ["no-match", "two-matches", "unreadable", "no-reader"])
def test_the_gate_cannot_tell_without_one_transcript(workspace, isolated_home, monkeypatch,
                                                      case):
    from tools.governance import session as session_mod
    monkeypatch.setenv("USERPROFILE", str(isolated_home))
    monkeypatch.setenv("HOME", str(isolated_home))
    if case == "no-match":
        claude_transcript(isolated_home, [_said("no marker here")])
    elif case == "two-matches":
        claude_transcript(isolated_home, [_said(MARKER)], name="s-1")
        claude_transcript(isolated_home, [_said(MARKER)], name="s-2")
    elif case == "unreadable":
        claude_transcript(isolated_home, [_said(MARKER)])

        def refuse(path, needle):
            raise OSError("locked")
        monkeypatch.setattr(session_mod, "_contains", refuse)
    elif case == "no-reader":
        _antigravity_transcript(isolated_home, "printed " + MARKER)
    result = session_mod.gate(str(workspace), MARKER)
    assert result.code == 3
    assert result.case == case
    assert result.reason


def test_the_gate_writes_nothing(workspace, isolated_home):
    claude_transcript(isolated_home, LAUNCHES)
    before = (snapshot_tree(str(workspace)), snapshot_tree(str(isolated_home)))
    assert gate(workspace).returncode == 1
    assert run(REGISTRY_CLI, "--root", str(workspace), "session", "--inventory",
               "--marker", MARKER).returncode in (0, 3)
    assert (snapshot_tree(str(workspace)), snapshot_tree(str(isolated_home))) == before


# =============================================================================
# The inventory
# =============================================================================


def git(root, *args, date=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, env=env)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _edit(i, path):
    return [_tool(i, "Edit", {"file_path": str(path), "old_string": "a", "new_string": "b"}),
            _returned(i, {"filePath": str(path)})]


@pytest.fixture
def repo(workspace, isolated_home):
    """A repository whose base commit predates the session; the session edited a.py
    (left uncommitted) and b.md (committed after the base); c.py is dirty but never
    edited here — another session's."""
    for name in ("a.py", "c.py"):
        (workspace / name).write_text("a\n", encoding="utf-8")
    git(workspace, "init", "-q", "-b", "main")
    git(workspace, "add", "-A")
    git(workspace, "commit", "-q", "-m", "base", date="2026-01-01T00:00:00Z")
    (workspace / "b.md").write_text("b\n", encoding="utf-8")
    git(workspace, "add", "b.md")
    git(workspace, "commit", "-q", "-m", "b", date="2026-03-01T00:00:00Z")
    (workspace / "a.py").write_text("b\n", encoding="utf-8")
    (workspace / "c.py").write_text("b\n", encoding="utf-8")
    claude_transcript(isolated_home, [_said(MARKER)] + _edit(1, workspace / "a.py")
                      + _edit(2, workspace / "b.md"))
    return workspace


def inventory(root):
    completed = run(REGISTRY_CLI, "--root", str(root), "--json", "session", "--inventory",
                    "--marker", MARKER, cwd=str(root.parent))
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def test_the_inventory_keeps_this_sessions_files_apart(repo):
    found = inventory(repo)
    assert found["uncommitted"] == ["a.py"]
    assert found["committed"] == ["b.md"]
    assert "c.py" in found["others"] and "a.py" not in found["others"]


def test_another_sessions_dirty_file_is_never_offered(repo):
    from tools.governance import session as session_mod
    found = inventory(repo)
    assert found["stage"] == session_mod.stage_paths(found)
    assert not set(found["stage"]) & set(found["others"])
    assert "a.py" in found["stage"] and "c.py" not in found["stage"]


# =============================================================================
# The record
# =============================================================================


def register_records(root: Path) -> Path:
    data = manifest(root)
    data["roles"]["sessionRecords"] = dict(
        {"path": "Virtuoso/session-records"},
        **{k: schema.DEFAULT_ROLES["sessionRecords"][k]
           for k in ("provider", "authority", "mutability", "owner", "allowedWriters")})
    data["roles"]["holdingBay"] = dict(
        {"path": "Virtuoso/holding"},
        **{k: schema.DEFAULT_ROLES["holdingBay"][k]
           for k in ("provider", "authority", "mutability", "owner", "allowedWriters")})
    write_manifest(root, data)
    (root / "Virtuoso" / "holding").mkdir(parents=True, exist_ok=True)
    (root / "Virtuoso" / "session-records").mkdir(parents=True, exist_ok=True)
    return root / "Virtuoso" / "session-records"


def findings_path(root: Path) -> Path:
    data = manifest(root)
    return root / data["roles"]["findings"]["path"]


def record_text(rows, extra=""):
    table = "\n".join("| %s | %s | `%s` |  |" % row for row in rows)
    return ("# Session record — export retry work\n\n"
            "- **Date:** 2026-11-24\n- **Session:** s-1\n- **Host:** claude-code\n"
            "- **Marker:** %s\n\n## Items\n\n| Item | Kind | Destination | Verified |\n"
            "|---|---|---|---|\n%s\n\n## Not kept\n\n- a scratch probe — reproduced in "
            "the test\n\n## Uncommitted\n\n- none\n\n%s"
            "Provenance: transcript s-1.jsonl; git HEAD abc1234.\n" % (MARKER, table, extra))


@pytest.fixture
def kept(repo, tmp_path):
    """A repository with a finding, a held entry and a memory file to point at."""
    register_records(repo)
    with open(findings_path(repo), "a", encoding="utf-8") as handle:
        handle.write("\n### F-001 — Export retries are silent (preserve-session, "
                     "2026-11-24)\n\n**Disposition:** open\n")
    (repo / "Virtuoso" / "holding" / "2026-11-24-export-retry.md").write_text(
        "# Held Plan — x\n", encoding="utf-8")
    memory = tmp_path / "memory" / "feedback.md"
    memory.parent.mkdir()
    memory.write_text("prefers small commits\n", encoding="utf-8")
    sha = git(repo, "rev-parse", "HEAD")
    return [("the retry change", "code", "commit:%s" % sha),
            ("the probe notes", "file", "path:b.md"),
            ("why retries were silent", "finding", "finding:F-001"),
            ("the paused storyboard", "held", "held:2026-11-24-export-retry"),
            ("prefers small commits", "memory", "memory:%s" % memory)]


def keep(root, path, *extra):
    return run(REGISTRY_CLI, "--root", str(root), "--actor", "preserve-session", "session",
               "--record", str(path), *extra, cwd=str(root.parent))


def test_a_verified_record_is_written_and_says_safe(kept, repo, tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(record_text(kept), encoding="utf-8")
    preview = keep(repo, draft)
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert "Safe to clear" not in preview.stdout
    records = repo / "Virtuoso" / "session-records"
    assert not records.exists() or not any(records.iterdir())
    applied = keep(repo, draft, "--apply")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert "Safe to clear: run /clear" in applied.stdout
    written = list(records.iterdir())
    assert len(written) == 1
    assert written[0].name.endswith("-export-retry-work.md")
    body = written[0].read_text(encoding="utf-8")
    assert body.count("| yes |") == len(kept)


def test_a_missing_destination_is_never_safe(kept, repo, tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(record_text(kept + [("a lost finding", "finding", "finding:F-999")]),
                     encoding="utf-8")
    refused = keep(repo, draft, "--apply")
    assert refused.returncode == 1
    assert "F-999" in refused.stdout
    assert "Safe to clear" not in refused.stdout
    records = repo / "Virtuoso" / "session-records"
    assert not records.exists() or not any(records.iterdir())


def test_no_record_without_the_role(repo, tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(record_text([("x", "file", "path:b.md")]), encoding="utf-8")
    before = snapshot_tree(str(repo))
    refused = keep(repo, draft, "--apply")
    assert refused.returncode == 3
    assert '"sessionRecords"' in refused.stdout
    assert '"allowedWriters": ["preserve-session", "governance-sweep"]' in refused.stdout
    assert "Safe to clear" not in refused.stdout
    assert snapshot_tree(str(repo)) == before


def test_a_credential_never_reaches_the_record(kept, repo, tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(record_text(kept, extra="Config used: api_key = sk-test-123\n\n"),
                     encoding="utf-8")
    refused = keep(repo, draft, "--apply")
    assert refused.returncode == 1
    assert "credential" in refused.stdout and "line " in refused.stdout
    assert "sk-test-123" not in refused.stdout
    records = repo / "Virtuoso" / "session-records"
    assert not records.exists() or not any(records.iterdir())


@pytest.mark.parametrize("line, refused", [
    ("api_key = sk-test-123", True),
    ('"api_key": "sk-live-abcdef"', True),
    ("| token: `ghp_abcdefghij` |", True),
    ("DATABASE_URL=postgres://u:hunter22@h/db", True),
    ("Tokens: 1234567", False),
    ("Author: gorillabrown", False),
    ("the key point is the export", False),
])
def test_the_credential_check_reads_assignments(line, refused):
    from tools.governance import session as session_mod
    assert bool(session_mod.credentials(line)) is refused


def test_a_launch_started_after_the_gate_is_never_safe(kept, repo, tmp_path, isolated_home):
    claude_transcript(isolated_home, [_said(MARKER)] + _edit(1, repo / "a.py") + [
        _tool(9, "Bash", {"command": "pytest", "run_in_background": True}),
        _returned(9, {"backgroundTaskId": "b9"})])
    draft = tmp_path / "draft.md"
    draft.write_text(record_text(kept), encoding="utf-8")
    refused = keep(repo, draft, "--apply")
    assert refused.returncode == 1
    assert "gate no longer passes" in refused.stdout and "Safe to clear" not in refused.stdout


def test_a_safe_record_drops_this_sessions_handoff_note(kept, repo, tmp_path):
    from tools.governance import guards
    from tools.governance.hosts import TranscriptFacts
    root = os.path.abspath(str(repo))
    note = Path(guards._path(os.path.join("handoffs", guards._project_key(root) + ".json")))

    guards.write_handoff({"session_id": "s-other"}, None, root, TranscriptFacts())
    draft = tmp_path / "draft.md"
    draft.write_text(record_text(kept), encoding="utf-8")
    assert keep(repo, draft, "--apply").returncode == 0
    assert note.exists()                    # another session's note stays

    guards.write_handoff({"session_id": "s-1"}, None, root, TranscriptFacts())
    draft.write_text(record_text(kept).replace("export retry work", "second pass"),
                     encoding="utf-8")
    assert keep(repo, draft, "--apply").returncode == 0
    assert not note.exists()                # this session's note is gone
