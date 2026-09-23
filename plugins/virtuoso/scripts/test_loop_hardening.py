"""Loop hardening (v1.10.0): the gaps the loop's SWOT and gap analysis ranked.

Each section names the Definition-of-Done row of the loop-hardening epic it holds.
"""
from __future__ import annotations

import codecs
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from tools.governance import registry as registry_mod, textio

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")
SPRINT_GUARDS = str(ROOT / "scripts" / "sprint_guards.py")


def run(script, *args, cwd=None):
    return subprocess.run([sys.executable, script, *args], capture_output=True, text=True,
                          encoding="utf-8", cwd=cwd)


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, str(ROOT / "scripts" / (name + ".py")))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest(root):
    return json.loads((root / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8"))


def write_manifest(root, data):
    (root / "Virtuoso" / "workspace-layout.json").write_text(json.dumps(data, indent=2),
                                                            encoding="utf-8")


def role_path(root, role):
    return root.joinpath(*manifest(root)["roles"][role]["path"].split("/"))


@pytest.fixture
def workspace(project):
    completed = run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return project


def preflight_json(root, *extra):
    completed = run(PREFLIGHT, "--root", str(root), "--mode", "check", "--json", *extra)
    return completed, json.loads(completed.stdout[completed.stdout.index("{"):])


# --- D2: the roadmap-integrity line ------------------------------------------------

def integrity_line(stdout):
    return [line for line in stdout.splitlines() if line.startswith("roadmap-integrity: ")]


@pytest.mark.parametrize("mode", ["check", "detect", "repair"])
@pytest.mark.parametrize("quiet", [True, False])
def test_the_integrity_line_is_printed_in_every_mode_and_survives_quiet(workspace, mode, quiet):
    args = ["--root", str(workspace), "--mode", mode] + (["--quiet"] if quiet else [])
    completed = run(PREFLIGHT, *args)
    [line] = integrity_line(completed.stdout)
    assert re.match(r"^roadmap-integrity: ok size=\d+$", line), line
    lines = completed.stdout.splitlines()
    deadlines = [i for i, l in enumerate(lines) if l.startswith("deadlines: ")][0]
    assert lines[deadlines + 1] == line


def test_an_unregistered_project_is_not_registered(project):
    completed = run(PREFLIGHT, "--root", str(project), "--mode", "check", "--quiet")
    assert integrity_line(completed.stdout) == ["roadmap-integrity: not registered"]


@pytest.mark.parametrize("content, state", [
    (b"", r"warn \(empty\) size=0"),
    (b"# Roadmap\n\x00\x00 trailing", r"fail \(null-bytes\) size=\d+"),
    (b"\x80\x81\xfa not text", r"fail \(not-text\) size=\d+"),
    (codecs.BOM_UTF16_LE + "# Roadmap\n".encode("utf-16-le"), r"ok size=\d+"),
])
def test_the_integrity_states(workspace, content, state):
    role_path(workspace, "roadmap").write_bytes(content)
    completed = run(PREFLIGHT, "--root", str(workspace), "--mode", "check", "--quiet")
    [line] = integrity_line(completed.stdout)
    assert re.match("^roadmap-integrity: %s$" % state, line), line
    assert completed.returncode == 0, "a side observation never fails preflight"


def test_a_missing_roadmap_fails_and_names_its_path(workspace):
    role_path(workspace, "roadmap").unlink()
    completed = run(PREFLIGHT, "--root", str(workspace), "--mode", "check", "--quiet")
    path = manifest(workspace)["roles"]["roadmap"]["path"]
    assert integrity_line(completed.stdout) == ["roadmap-integrity: fail (missing: %s)" % path]


def test_the_json_carries_the_integrity_state(workspace):
    _, payload = preflight_json(workspace)
    assert re.match(r"^ok size=\d+$", payload["roadmapIntegrity"]["state"])


def test_session_start_reads_the_roadmap_once(workspace, monkeypatch):
    """Charter assumption A3: the integrity line and the deadline check share one read."""
    preflight = load_script("virtuoso_preflight")
    roadmap = str(role_path(workspace, "roadmap"))
    data = manifest(workspace)
    data.setdefault("policy", {})["roadmap"] = {"deadlines": {"g": {
        "date": "2099-01-01", "owner": "o", "finishLine": "Nowhere", "recorded": "2026-09-23"}}}
    write_manifest(workspace, data)
    reads = []
    real_bytes, real_text = textio.read_bytes, textio.read_text

    def counting_bytes(path):
        if Path(path) == Path(roadmap):
            reads.append(path)
        return real_bytes(path)

    def counting_text(path):
        if Path(path) == Path(roadmap):
            reads.append(path)
        return real_text(path)

    monkeypatch.setattr(textio, "read_bytes", counting_bytes)
    monkeypatch.setattr(textio, "read_text", counting_text)
    outcome = preflight.preflight(str(workspace), "check")
    assert outcome.roadmap_integrity.startswith("ok")
    assert "; 1 finding" in outcome.deadlines          # the finish line was looked up
    assert len(reads) == 1, reads


def test_the_ceremonies_read_the_line_the_preflight_prints():
    for skill in ("next-pointer", "roadmap-status", "roadmap-review", "pointer-closeout"):
        text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "`roadmap-integrity:` line" in text, skill
        assert "exit 3" not in text and "exit 2" not in text, (
            "%s describes the line with --check-document's exit codes" % skill)


# --- D3: policy validated at every load ---------------------------------------------

def set_policy(root, policy):
    data = manifest(root)
    data["policy"] = policy
    write_manifest(root, data)


@pytest.mark.parametrize("policy, key", [
    ({"rubric": {"extensions": "coverage-gate"}}, "rubric.extensions"),
    ({"git": {"policy": "yolo"}}, "policy.git.policy"),
    ({"roadmap": {"dispatchBuffer": "five"}}, "roadmap.dispatchBuffer"),
])
def test_a_hand_edited_invalid_policy_is_a_warning_at_preflight(workspace, policy, key):
    set_policy(workspace, policy)
    completed, payload = preflight_json(workspace)
    assert completed.returncode == 0
    assert payload["status"] == "warning"
    [finding] = [f for f in payload["findings"] if f["code"] == "policy-invalid"]
    assert finding["severity"] == "warning" and finding["identifier"] == key


def test_a_valid_policy_raises_nothing(workspace):
    set_policy(workspace, {"rubric": {"extensions": ["coverage-gate"]}, "roadmap": {"dispatchBuffer": 3}})
    _, payload = preflight_json(workspace)
    assert not [f for f in payload["findings"] if f["code"] == "policy-invalid"]


def test_deadline_problems_stay_on_the_deadline_line(workspace):
    set_policy(workspace, {"roadmap": {"deadlines": {"g": {"date": "soon"}}}})
    completed, payload = preflight_json(workspace)
    assert payload["status"] == "ready"
    assert "deadlines: invalid (" in completed.stdout


def test_undocumented_keys_are_inert_not_invalid():
    assert registry_mod.policy_findings({"somethingNew": 1}) == []


# --- D4: default writers match the skill bodies ---------------------------------------

@pytest.mark.parametrize("role, writer", [
    ("issues", "virtuoso"), ("closeOuts", "virtuoso"), ("closeOuts", "mid-dispatch-decision"),
    ("lessons", "3rd-party-audit"), ("lessons", "governance-sweep"),
    ("roadmap", "3rd-party-audit"),
])
def test_default_writers_name_the_ceremonies_that_write(role, writer):
    from tools.governance import schema
    assert writer in schema.DEFAULT_ROLES[role]["allowedWriters"]


def test_a_new_workspace_carries_the_aligned_writers(workspace):
    roles = manifest(workspace)["roles"]
    assert "virtuoso" in roles["issues"]["allowedWriters"]
    assert "governance-sweep" in roles["lessons"]["allowedWriters"]


# --- D5: the Decision block has a step and a reader --------------------------------------

def test_the_decision_block_has_a_step_and_the_close_out_reads_it():
    decide = (ROOT / "skills" / "mid-dispatch-decision" / "SKILL.md").read_text(encoding="utf-8")
    assert "#### 6d. Record the Decision in the Issue File" in decide
    assert "## Decision — YYYY-MM-DD" in decide
    close = (ROOT / "skills" / "pointer-closeout" / "SKILL.md").read_text(encoding="utf-8")
    assert "`## Decision`" in close and "open decision" in close


# --- D6: nothing names a skill, agent or case that does not exist ------------------------

def test_the_reference_check_catches_a_ghost():
    validate = load_script("validate")
    skills, agents = ["roadmap-review", "next-pointer"], ["Aristotle", "Hermes"]
    assert validate.unresolved_references(
        "escalate to athena; (→ Hermes); run `/write-spec`; Invoke `write-spec`; "
        "`/virtuoso:next-pointer`", skills, agents) == ["/write-spec", "write-spec", "athena"]
    assert validate.unresolved_references(
        "escalate to the planner; (→ cross-cutting); □ 3. Aristotle: go", skills, agents) == []


def test_the_shipped_plugin_names_no_ghost():
    for ghost in ("athena", "solon", "herodotus", "write-spec", "Case C"):
        for path in list((ROOT / "skills").rglob("*.md")) + list((ROOT / "agents").glob("*.md")):
            assert ghost not in path.read_text(encoding="utf-8"), (ghost, path)


# --- D7: epics are a registered role, never a conventional path ------------------------

def test_the_epics_role_is_opt_in_and_written_by_the_epic_skill():
    from tools.governance import schema
    assert schema.DEFAULT_ROLES["epics"]["allowedWriters"] == ["epic"]
    assert "epics" not in schema.CREATE_ROLE_ORDER


def test_a_registered_epics_role_resolves(workspace):
    data = manifest(workspace)
    data["roles"]["epics"] = {"path": "Virtuoso/epics", "provider": "directory",
                              "authority": "reference", "mutability": "read-write",
                              "owner": "epic", "allowedWriters": ["epic"]}
    write_manifest(workspace, data)
    completed = run(REGISTRY_CLI, "--root", str(workspace), "resolve", "epics")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip().replace("\\", "/").endswith("Virtuoso/epics")


def test_the_epic_skill_names_no_conventional_path():
    text = (ROOT / "skills" / "epic" / "SKILL.md").read_text(encoding="utf-8")
    assert "resolve epics" in text
    assert "2 operational" not in text and "`epics/` at the project root" not in text


# --- D23: the close-out reviews every file the dispatch created -------------------------

def git(root, *args):
    completed = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


@pytest.fixture
def dispatch(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    (root / "Virtuoso").mkdir()
    (root / "Virtuoso" / "workspace-layout.json").write_text(json.dumps(
        {"schemaVersion": 2, "roles": {"temp": {"path": "Docs/temp", "provider": "directory"}}}))
    (root / "keep.py").write_text("x = 1\n")
    (root / ".gitignore").write_text("ignored.dat\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    git(root, "checkout", "-qb", "work")
    return root


def created(root, *extra):
    return run(SPRINT_GUARDS, "created-files", "--root", str(root), "--base", "main", *extra)


def test_created_files_is_clean_when_everything_is_committed(dispatch):
    (dispatch / "feature.py").write_text("y = 2\n")
    git(dispatch, "add", "feature.py")
    git(dispatch, "commit", "-qm", "feature")
    completed = created(dispatch)
    assert completed.returncode == 0, completed.stdout
    assert "1 committed, 0 temporary, 0 untracked, 0 uncommitted" in completed.stdout


def test_created_files_classifies_what_a_dispatch_leaves_behind(dispatch):
    (dispatch / "feature.py").write_text("y = 2\n")
    (dispatch / "notes.bak").write_text("old")
    git(dispatch, "add", "feature.py", "notes.bak")
    git(dispatch, "commit", "-qm", "feature and a backup")
    (dispatch / "Docs" / "temp").mkdir(parents=True)
    (dispatch / "Docs" / "temp" / "probe.md").write_text("scratch")    # the temp role
    (dispatch / "run.log").write_text("log")
    (dispatch / "report.md").write_text("a real deliverable nobody committed")
    (dispatch / "ignored.dat").write_text("deliberately ignored")
    (dispatch / "keep.py").write_text("x = 2\n")
    completed = created(dispatch, "--json")
    assert completed.returncode == 1
    found = json.loads(completed.stdout)
    assert found["temporary"] == ["Docs/temp/probe.md", "notes.bak", "run.log"]
    assert found["untracked"] == ["report.md"]
    assert found["uncommitted"] == ["keep.py"]
    assert found["committed"] == ["feature.py"]
    assert found["clean"] is False


def test_created_files_refuses_an_unknown_base(dispatch):
    completed = run(SPRINT_GUARDS, "created-files", "--root", str(dispatch), "--base", "nope")
    assert completed.returncode == 2 and "does not resolve" in completed.stdout


def test_the_close_out_runs_the_review_and_records_it():
    skill = (ROOT / "skills" / "pointer-closeout" / "SKILL.md").read_text(encoding="utf-8")
    assert skill.count("sprint_guards created-files") >= 1 and "created-files" in skill
    template = (ROOT / "skills" / "pointer-closeout" / "assets" /
                "CloseOut.template.md").read_text(encoding="utf-8")
    assert "## Files Created" in template


def test_the_virtuoso_skill_runs_the_guards_through_the_launcher():
    text = (ROOT / "skills" / "virtuoso" / "SKILL.md").read_text(encoding="utf-8")
    assert "registry:scripts" not in text
    assert text.count('"$HOME/.virtuoso/bin/virtuoso" sprint_guards') == 4
