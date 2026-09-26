"""Loop hardening (v1.10.0): the gaps the loop's SWOT and gap analysis ranked.

Each section names the Definition-of-Done row of the loop-hardening epic it holds.
"""
from __future__ import annotations

import codecs
import importlib.util
import json
import os
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
    """Run a plugin script; the child writes UTF-8 and the output is read as UTF-8.

    Both halves matter: a piped child on Windows otherwise writes the console code
    page, where the plugin's em dash is byte 0x97 and no UTF-8 reader can decode it."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, script, *args], capture_output=True, text=True,
                          encoding="utf-8", cwd=cwd, env=env)


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


# --- D22, D11, D12, D15: hygiene, candidates, the anchored reason, loop health ---------

from tools.governance import learning as learning_mod, lessons as lessons_mod   # noqa: E402

CATALOG = """# Lessons

### LSN-001 — Read-side fallback before a row-shape migration (ADD-042, 2026-01-10)
**Verdict:** the reader crashed on rows written before the migration
**Evidence:** one crash, two hours
**Recommendation:** merge the reader fallback before the migration runs
**Applies to:** any item that changes a stored row shape
**Status:** Observation

### LSN-002 — Consumer fallback before an export-format change (ADD-051, 2026-02-01)
**Verdict:** consumers broke on the new export shape
**Evidence:** three consumers down for a day
**Recommendation:** merge the reader fallback before the migration runs
**Applies to:** any item that changes a stored row shape
**Status:** Observation

### LSN-003 — Name the fixture (ARCH-4, 2025-01-20)
**Verdict:** an unnamed fixture was shared across suites
**Evidence:** two flaky suites
**Recommendation:** name every shared fixture
**Applies to:** fixtures shared across suites
**Status:** Observation

### LSN-004 — Half-written lesson (ARCH-9, 2026-03-01)
**Verdict:** something happened
**Status:** Observation

### LSN-005 — Record the base's failing set first (ARCH-2, 2026-01-05)
**Verdict:** a red base hid a regression
**Evidence:** one day lost
**Recommendation:** record the failing set before the first change
**Applies to:** continuations on a red base
**Status:** Observation

### LSN-005 — a second lesson under the same id (ARCH-11, 2026-04-01)
**Verdict:** reused
**Recommendation:** something else
"""


def reports(*entries):
    return [("CloseOut.%s.%s.md" % (item, date),
             "---\ndate: %s\n---\n# Close-out\n\n## Lessons\n\n%s\n" % (date, body))
            for item, date, body in entries]


TODAY = __import__("datetime").date(2026, 9, 23)


def test_hygiene_proposes_merge_retire_tidy_and_repair():
    recorded = lessons_mod.parse(CATALOG, "LSN")
    outcomes = learning_mod.read_outcomes([], "LSN")
    report = learning_mod.hygiene(recorded, outcomes, today=TODAY, stale_after_days=180)
    assert report["duplicates"] == [{"keep": "LSN-001", "supersede": ["LSN-002"],
                                     "why": "the same Applies to (any item that changes a "
                                            "stored row shape) and the same recommendation"}]
    assert [s["id"] for s in report["stale"]] == ["LSN-001", "LSN-002", "LSN-003", "LSN-004",
                                                 "LSN-005"]
    assert report["incomplete"] == [{"id": "LSN-004",
                                     "missing": ["evidence", "recommendation", "applies to"]}]
    assert [m["id"] for m in report["malformed"]] == ["LSN-005"]


def test_a_lesson_applied_in_a_close_out_is_not_stale():
    recorded = lessons_mod.parse(CATALOG, "LSN")
    outcomes = learning_mod.read_outcomes(reports(
        ("ARCH-7", "2026-05-01", "- **Applied:** LSN-003 — held: both suites green")), "LSN")
    report = learning_mod.hygiene(recorded, outcomes, today=TODAY, stale_after_days=180)
    assert "LSN-003" not in [s["id"] for s in report["stale"]]
    assert learning_mod.hygiene(recorded, outcomes, today=TODAY,
                                stale_after_days=0)["stale"] == []


def test_candidates_promote_what_recurred_or_held_twice_and_revise_what_failed_twice():
    recorded = lessons_mod.parse(CATALOG, "LSN")
    outcomes = learning_mod.read_outcomes(reports(
        ("A-1", "2026-05-01", "- **Applied:** LSN-003 — held: suites green"),
        ("A-2", "2026-06-01", "- **Applied:** LSN-003 — held: green again"),
        ("A-3", "2026-06-02", "- **Applied:** LSN-005 — did not hold: base still hid it"),
        ("A-4", "2026-07-02", "- **Applied:** LSN-005 — did not hold: again"),
        ("A-5", "2026-07-03", "- **New:** No new lesson — covered by LSN-001")), "LSN")
    found = {c["id"]: c for c in learning_mod.candidates(recorded, outcomes)}
    assert found["LSN-001"]["action"] == "promote" and "LSN-002" in found["LSN-001"]["why"]
    assert found["LSN-003"] == {"id": "LSN-003", "action": "promote",
                                "why": "applied and held in 2 close-outs"}
    assert found["LSN-005"]["action"] == "revise or retire"
    assert outcomes.closeouts == 5 and outcomes.no_lesson == 1


def test_the_learning_metrics_are_computed_or_not_computable():
    empty = learning_mod.metrics([], learning_mod.Outcomes())
    assert [m.name for m in empty] == ["live-count", "lesson-yield", "held-rate",
                                       "promotion-rate", "time-to-apply", "repeated-trap-rate"]
    assert all(not m.computable and m.missing_inputs for m in empty)
    recorded = lessons_mod.parse(CATALOG, "LSN")
    outcomes = learning_mod.read_outcomes(reports(
        ("A-1", "2026-01-20", "- **Applied:** LSN-001 — held: no crash"),
        ("A-2", "2026-02-10", "- **Applied:** LSN-005 — did not hold: hidden again"),
        ("A-3", "2026-02-11", "No new lesson — covered by LSN-001")), "LSN")
    figures = {m.name: m for m in learning_mod.metrics(recorded, outcomes)}
    assert figures["live-count"].value == 5
    assert figures["lesson-yield"].value == round(5 / 3, 2)
    assert figures["held-rate"].value == 0.5
    assert figures["promotion-rate"].value == 0.0
    assert figures["time-to-apply"].value == 23             # LSN-001 10 days, LSN-005 36: median 23
    assert figures["repeated-trap-rate"].value == 0.4       # LSN-001 and LSN-002 of five


def closeout_text(line):
    return "# Close-out\n\n## Lessons\n\n- **New:** %s\n" % line


@pytest.mark.parametrize("line, standing, passes", [
    ("No new lesson — nothing new happened", (), False),
    ("No new lesson — both risks were covered by LSN-001 and LSN-003", (), True),
    ("No new lesson — the same change as ADD-042", (), True),
    ("No new lesson — standing rule WIDE-RULE covered it", ("WIDE-RULE",), True),
])
def test_a_no_lesson_reason_names_what_was_examined(line, standing, passes):
    recorded = lessons_mod.parse(CATALOG, "LSN")
    result = lessons_mod.check(closeout_text(line), recorded, "LSN", closeout=True,
                               item="ADD-099", standing_rules=standing)
    assert result.passed is passes, result.findings
    if not passes:
        assert result.findings[0]["code"] == "lesson-reason-unanchored"


def test_with_nothing_to_examine_any_real_reason_passes():
    result = lessons_mod.check(closeout_text("No new lesson — first dispatch of the project"),
                               [], "LSN", closeout=True, item="ADD-001")
    assert result.passed is True


@pytest.fixture
def catalog(workspace):
    data = manifest(workspace)
    data.setdefault("policy", {})["lessons"] = {"idPrefix": "LSN"}
    write_manifest(workspace, data)
    role_path(workspace, "lessons").write_text(CATALOG, encoding="utf-8", newline="\n")
    closeouts = role_path(workspace, "closeOuts")
    for name, text in reports(("A-1", "2026-05-01", "- **Applied:** LSN-003 — held: green"),
                              ("A-2", "2026-06-01", "- **Applied:** LSN-003 — held: green")):
        (closeouts / name).write_text(text, encoding="utf-8")
    return workspace


def lessons_cli(root, *args, actor=None):
    extra = ["--actor", actor] if actor else []
    return run(REGISTRY_CLI, "--root", str(root), *extra, "lessons", *args)


def test_the_hygiene_and_candidates_commands(catalog):
    completed = lessons_cli(catalog, "--hygiene", "--json")
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["duplicates"][0]["keep"] == "LSN-001" and report["closeOutsRead"] == 2
    text = lessons_cli(catalog, "--hygiene").stdout
    assert "merge    keep LSN-001; supersede LSN-002" in text and "tidy     LSN-004" in text
    found = json.loads(lessons_cli(catalog, "--candidates", "--json").stdout)["candidates"]
    assert {c["id"]: c["action"] for c in found} == {"LSN-001": "promote", "LSN-003": "promote"}


def test_record_status_previews_then_appends_and_reads_back(catalog):
    path = role_path(catalog, "lessons")
    before = path.read_bytes()
    preview = lessons_cli(catalog, "--record-status", "LSN-002", "--status",
                          "Superseded -> LSN-001", actor="governance-sweep")
    assert preview.returncode == 0 and "preview" in preview.stdout
    assert path.read_bytes() == before
    applied = lessons_cli(catalog, "--record-status", "LSN-002", "--status",
                          "Superseded -> LSN-001", "--item", "sweep", "--date", "2026-09-23",
                          "--apply", actor="governance-sweep")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    after = path.read_bytes()
    assert after.startswith(before), "an earlier entry was edited"
    assert after.endswith(b"### LSN-002 \xe2\x80\x94 status (sweep, 2026-09-23)\n"
                          b"**Status:** Superseded -> LSN-001\n")
    listing = json.loads(lessons_cli(catalog, "--json").stdout)
    assert {l["id"]: l["live"] for l in listing["lessons"]}["LSN-002"] is False


@pytest.mark.parametrize("lesson, status, actor, why", [
    ("LSN-002", "Superseded -> LSN-001", "next-pointer", "may not write"),
    ("LSN-042", "Retired — obsolete", "governance-sweep", "not a recorded lesson"),
    ("LSN-002", "Superseded -> LSN-002", "governance-sweep", "names the recorded lesson"),
    ("LSN-002", "Retired", "governance-sweep", "say where it went or why"),
    ("LSN-002", "Deleted", "governance-sweep", "a status begins with"),
])
def test_record_status_refuses(catalog, lesson, status, actor, why):
    before = role_path(catalog, "lessons").read_bytes()
    completed = lessons_cli(catalog, "--record-status", lesson, "--status", status, "--apply",
                            actor=actor)
    assert completed.returncode != 0
    assert why in completed.stdout + completed.stderr
    assert role_path(catalog, "lessons").read_bytes() == before


def test_kpis_carries_the_learning_group(catalog):
    completed = run(REGISTRY_CLI, "--root", str(catalog), "kpis", "--json")
    assert completed.returncode == 0, completed.stderr
    learning = json.loads(completed.stdout)["learning"]
    figures = {m["name"]: m for m in learning["metrics"]}
    assert figures["live-count"]["value"] == 5
    assert figures["held-rate"]["value"] == 1.0
    assert learning["provenance"]["closeOutsRead"] == 2
    text = run(REGISTRY_CLI, "--root", str(catalog), "kpis").stdout
    assert "learning" in text and "repeated-trap-rate" in text


def test_the_ceremonies_run_hygiene_and_candidates():
    sweep = (ROOT / "skills" / "governance-sweep" / "SKILL.md").read_text(encoding="utf-8")
    assert "lessons --hygiene" in sweep and "--actor governance-sweep" in sweep
    review = (ROOT / "skills" / "roadmap-review" / "SKILL.md").read_text(encoding="utf-8")
    assert "lessons --candidates" in review and "--record-status" in review


def test_the_stale_threshold_is_a_documented_policy_value():
    from tools.governance import policy as policy_mod
    assert policy_mod.documented_default("lessons.staleAfterDays") == 180
    assert policy_mod.lessons_problems({"staleAfterDays": -1})


# --- D10: standing rules are paired and have one source ---------------------------------

def declare_rules(root, ids, source=None):
    data = manifest(root)
    rules = {"ids": ids}
    if source:
        rules["source"] = source
    data.setdefault("policy", {})["standingRules"] = rules
    write_manifest(root, data)


def test_a_declared_rule_without_a_section_is_unpaired(workspace):
    role_path(workspace, "roadmap").write_text(
        "# Roadmap\n\n## Standing rules\n\n### SR-1 — Reader first\nText.\n\n"
        "```\n### SR-2 — only an example\n```\n", encoding="utf-8")
    declare_rules(workspace, ["SR-1", "SR-2"])
    completed, payload = preflight_json(workspace)
    assert completed.returncode == 0 and payload["status"] == "warning"
    unpaired = [f for f in payload["findings"] if f["code"] == "standing-rule-unpaired"]
    assert [f["identifier"] for f in unpaired] == ["SR-2"]
    assert unpaired[0]["severity"] == "warning"


def test_paired_rules_raise_nothing(workspace):
    role_path(workspace, "roadmap").write_text("# Roadmap\n\n### SR-1 — Reader first\n",
                                               encoding="utf-8")
    declare_rules(workspace, ["SR-1"])
    _, payload = preflight_json(workspace)
    assert payload["status"] == "ready"


def test_an_unregistered_source_is_named(workspace):
    declare_rules(workspace, ["SR-1"], source="rulebook")
    _, payload = preflight_json(workspace)
    [finding] = [f for f in payload["findings"]
                 if f["code"] == "standing-rules-source-unregistered"]
    assert "rulebook" in finding["message"]


def test_standing_rules_share_the_one_roadmap_read(workspace, monkeypatch):
    preflight = load_script("virtuoso_preflight")
    roadmap = role_path(workspace, "roadmap")
    roadmap.write_text("# Roadmap\n\n### SR-1 — Reader first\n", encoding="utf-8")
    declare_rules(workspace, ["SR-1", "SR-9"])
    reads = []
    real = textio.read_bytes
    monkeypatch.setattr(textio, "read_bytes",
                        lambda p: (reads.append(p) if Path(p) == roadmap else None) or real(p))
    outcome = preflight.preflight(str(workspace), "check")
    assert [f["identifier"] for f in outcome.findings
            if f["code"] == "standing-rule-unpaired"] == ["SR-9"]
    assert len(reads) == 1


def test_zeus_reads_standing_rules_from_the_registered_source():
    zeus = (ROOT / "skills" / "virtuoso" / "references" / "zeus.md").read_text(encoding="utf-8")
    assert "policy.standingRules.source" in zeus
    assert "(rules, current state, standing rules)" not in zeus


# --- D13: findings have a role and a reader ---------------------------------------------

def test_the_findings_role_is_a_default_with_its_writers():
    from tools.governance import schema
    role = schema.DEFAULT_ROLES["findings"]
    assert role["mutability"] == "append-only"
    for writer in ("governance-sweep", "adversarial-review", "virtuoso"):
        assert writer in role["allowedWriters"]
    assert "findings" in schema.CREATE_ROLE_ORDER


def test_create_scaffolds_the_findings_document(workspace):
    path = role_path(workspace, "findings")
    assert path.name == "Findings.md" and path.read_text(encoding="utf-8").startswith("# Findings")


def test_a_manifest_without_the_findings_role_stays_ready(workspace):
    data = manifest(workspace)
    del data["roles"]["findings"]
    write_manifest(workspace, data)
    run(PREFLIGHT, "--root", str(workspace), "--mode", "repair", "--apply")   # resync the readme view
    _, payload = preflight_json(workspace)
    assert payload["status"] in ("ready", "warning")
    assert not [f for f in payload["findings"] if f["severity"] == "error"], payload["findings"]


def test_the_findings_have_writers_and_a_reader_in_the_skills():
    review = (ROOT / "skills" / "roadmap-review" / "SKILL.md").read_text(encoding="utf-8")
    assert "registered `findings` role" in review and "lessons-applied.md" in review
    for skill in ("governance-sweep", "adversarial-review"):
        text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "`findings` role" in text and "F-NNN" in text, skill
    for agent in (ROOT / "agents").glob("*.md"):
        assert "findings document" not in agent.read_text(encoding="utf-8"), agent.name


# --- D14: effort calibration measured per project ----------------------------------------

@pytest.mark.parametrize("text, value", [
    ("90m", 1.5), ("1.5h", 1.5), ("2h30m", 2.5), ("3", 3.0), ("M", None), ("", None)])
def test_durations(text, value):
    assert learning_mod.hours(text) == value


def ledger_rows(pairs):
    from tools.governance.providers import ledger as ledger_mod
    return [ledger_mod.LedgerRecord("TR-%d" % i, "I-%d" % i, "2026-09-01", "shipped",
                                    effort_estimate=e, effort_actual=a)
            for i, (e, a) in enumerate(pairs)]


def test_calibration_is_not_computable_below_three_pairs():
    metric = learning_mod.effort_calibration(ledger_rows([("1h", "2h"), ("M", "3h"), ("", "")]))
    assert not metric.computable and "(1 have both)" in metric.missing_inputs[0]


def test_calibration_is_the_median_ratio():
    metric = learning_mod.effort_calibration(
        ledger_rows([("1h", "1.2h"), ("2h", "3h"), ("60m", "130m"), ("4h", "4h")]))
    assert metric.value == round((1.2 + 1.5) / 2, 2)


def test_a_markdown_ledger_with_effort_columns_round_trips(tmp_path):
    from tools.governance.providers import ledger as ledger_mod
    path = tmp_path / "ledger.md"
    path.write_text("# Ledger\n\n| Record | Item | Completed | Result | Evidence | Corrects "
                    "| Estimate | Actual |\n|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
    book = ledger_mod.TerminalLedger(str(path), writers=["pointer-closeout"])
    book.append(ledger_mod.LedgerRecord("TR-001", "I-1", "2026-09-23", "shipped",
                                        effort_estimate="2h", effort_actual="150m"),
                actor="pointer-closeout")
    [record] = book.records()
    assert (record.effort_estimate, record.effort_actual) == ("2h", "150m")
    assert "| TR-001 | I-1 | 2026-09-23 | shipped |  |  | 2h | 150m |" in path.read_text(encoding="utf-8")


def test_a_six_column_markdown_ledger_is_unchanged(tmp_path):
    from tools.governance.providers import ledger as ledger_mod
    path = tmp_path / "ledger.md"
    book = ledger_mod.TerminalLedger(str(path), writers=["pointer-closeout"])
    book.append(ledger_mod.LedgerRecord("TR-001", "I-1", "2026-09-23", "shipped",
                                        effort_estimate="2h", effort_actual="3h"),
                actor="pointer-closeout")
    assert "| TR-001 | I-1 | 2026-09-23 | shipped |  |  |" in path.read_text(encoding="utf-8")
    assert book.records()[0].effort_estimate == ""


def test_kpis_reports_effort_calibration(catalog):
    for item, estimate, actual in (("A", "1h", "1.5h"), ("B", "2h", "3h"), ("C", "1h", "1h")):
        path = role_path(catalog, "workRegister")
        with open(path, "a", encoding="utf-8", newline="") as handle:
            handle.write("%s,%s,1,Queued,Full Spec,,S,,,,,,,,,\n" % (item, item))
        completed = run(REGISTRY_CLI, "--root", str(catalog), "--actor", "pointer-closeout",
                        "record-completion", "--item", item, "--date", "2026-09-23",
                        "--result", "shipped", "--estimate", estimate, "--actual", actual,
                        "--apply")
        assert completed.returncode == 0, completed.stdout + completed.stderr
    learning = json.loads(run(REGISTRY_CLI, "--root", str(catalog), "kpis",
                              "--json").stdout)["learning"]
    figure = {m["name"]: m for m in learning["metrics"]}["effort-calibration"]
    assert figure["value"] == 1.5 and "ledger" in learning["provenance"]


def test_effort_levels_prefers_the_measured_figure():
    text = (ROOT / "skills" / "effort-levels" / "SKILL.md").read_text(encoding="utf-8")
    assert "effort-calibration" in text


# --- D16, D17: no project residue in shipped agents; one memory boundary -------------------

def test_the_validator_catches_a_projects_residue_in_a_shipped_file():
    validate = load_script("validate")
    hits = []
    for line in ("see 2 operational/Memo.x.md", "per the Session 116 refactor",
                 "- AR-3: display follows engine", "save to .claude/agents/feedback.log",
                 "git diff origin/main HEAD", "IMMEDIATE_BASE_PROB changed"):
        validate.scan("agents/Example.md", line, validate.SHIPPED_PROJECT_PATTERNS, "p", hits)
    assert len(hits) == 6, hits


def test_no_shipped_agent_carries_another_projects_residue():
    pattern = re.compile(r"2 operational|Session 116|\bAR-[1-7]\b|\bDC-4\b|origin/main"
                         r"|feedback\.log|\bLL-NNN\b|LL Promotion")
    for path in (ROOT / "agents").glob("*.md"):
        assert not pattern.search(path.read_text(encoding="utf-8")), path.name


def test_the_memory_boundary_is_stated_once_and_agents_defer_to_it():
    guide = (ROOT / "references" / "agent-memory-guide.md").read_text(encoding="utf-8")
    assert "## The boundary — memory, lessons, findings" in guide
    plato = (ROOT / "agents" / "Plato.md").read_text(encoding="utf-8")
    assert "references/agent-memory-guide.md" in plato and "memory.yaml" not in plato


# --- D18: anchors prove rule text; the buffer counts readiness -----------------------------

def test_a_changed_rule_fails_until_its_hash_is_updated(tmp_path):
    rules = load_script("skill_rules")
    skill = tmp_path / "skills" / "virtuoso"
    skill.mkdir(parents=True)
    marker = rules.anchor_comment("lane-declaration", "lane-concurrency")
    (skill / "SKILL.md").write_text("%s\n**Declare the lane** before any write.\n\nnext\n" % marker,
                                    encoding="utf-8")
    recorded = dict(rules.current_hashes(str(tmp_path / "skills")))
    assert rules.changed_rules(str(tmp_path / "skills"), recorded) == []
    (skill / "SKILL.md").write_text("%s\n**Declare the lane** when convenient.\n" % marker,
                                    encoding="utf-8")
    assert rules.changed_rules(str(tmp_path / "skills"), recorded) == ["lane-declaration"]


def test_every_registered_anchor_has_a_recorded_hash():
    rules = load_script("skill_rules")
    anchors = {a for pairs in rules.REQUIRED_RULE_ANCHORS.values() for a, _ in pairs}
    assert anchors == set(rules.RULE_TEXT_HASHES)


def test_dispatch_buffer_ready_counts_what_a_gate_would_pass(workspace):
    data = manifest(workspace)
    data.setdefault("policy", {})["lessons"] = {"idPrefix": "LSN"}
    write_manifest(workspace, data)
    role_path(workspace, "lessons").write_text(
        "### LSN-001 — Reader first (A-0, 2026-09-01)\n**Applies to:** row shapes\n"
        "**Status:** Observation\n", encoding="utf-8")
    role_path(workspace, "roadmap").write_text(
        "# Roadmap\n\n#### R-1 — Ready\n\n##### Lessons applied\n- LSN-001 applied\n\n"
        "#### R-2 — Written but not ready\n\n- **What:** something\n", encoding="utf-8")
    with open(role_path(workspace, "workRegister"), "a", encoding="utf-8", newline="") as handle:
        handle.write("R-1,Ready,1,Queued,Full Spec,,S,,,,,,,,,\n"
                     "R-2,Not ready,2,Queued,Full Spec,,S,,,,,,,,,\n")
    metrics = {m["name"]: m for m in json.loads(
        run(REGISTRY_CLI, "--root", str(workspace), "kpis", "--json").stdout)["metrics"]}
    assert metrics["dispatch-buffer-filled"]["value"] == 2
    assert metrics["dispatch-buffer-ready"]["value"] == 1


def test_dispatch_buffer_ready_names_what_it_cannot_judge(workspace):
    with open(role_path(workspace, "workRegister"), "a", encoding="utf-8", newline="") as handle:
        handle.write("R-9,Nowhere,1,Queued,Full Spec,,S,,,,,,,,,\n")
    metrics = {m["name"]: m for m in json.loads(
        run(REGISTRY_CLI, "--root", str(workspace), "kpis", "--json").stdout)["metrics"]}
    ready = metrics["dispatch-buffer-ready"]
    assert ready["computable"] is False and "R-9" in ready["missingInputs"][0]
