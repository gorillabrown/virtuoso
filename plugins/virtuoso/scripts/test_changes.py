"""The change ledger: when each change took effect, recorded by hand or automatically by the
operation that caused it, never rewritten."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from tools.governance import changes

REGISTRY_CLI = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_registry.py")
#: A lesson id under the default prefix, built so no shipped line names a real one.
LESSON = "SRL-%03d" % 1
PREFLIGHT = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_preflight.py")


def cli(root, *args, actor=None):
    command = [sys.executable, REGISTRY_CLI, "--root", str(root)]
    if actor:
        command += ["--actor", actor]
    return subprocess.run(command + list(args), capture_output=True, text=True,
                          encoding="utf-8", env=dict(os.environ))


@pytest.fixture
def created(project):
    made = subprocess.run([sys.executable, PREFLIGHT, "--root", str(project), "--mode", "create",
                           "--authorize"], capture_output=True, text=True, encoding="utf-8")
    assert made.returncode == 0, made.stdout + made.stderr
    return project


def ledger_path(root: Path) -> Path:
    layout = json.loads((root / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8"))
    return root.joinpath(*layout["roles"]["changeLedger"]["path"].split("/"))


def lines(root: Path) -> list[dict]:
    return changes.load(str(ledger_path(root)))


def test_a_new_workspace_has_an_empty_ledger_that_reads_ready(created):
    path = ledger_path(created)
    assert path.is_file() and path.read_text(encoding="utf-8") == ""
    layout = json.loads((created / "Virtuoso" / "workspace-layout.json").read_text(
        encoding="utf-8"))["roles"]["changeLedger"]
    assert (layout["provider"], layout["mutability"]) == ("jsonl", "append-only")
    checked = subprocess.run([sys.executable, PREFLIGHT, "--root", str(created), "--mode",
                              "check"], capture_output=True, text=True, encoding="utf-8")
    assert "virtuoso-status: ready" in checked.stdout


def test_a_policy_change_records_itself_in_the_same_operation(created):
    done = cli(created, "policy-set", "cost.units", "--value-json", '"tokens"', "--apply",
               "--json", actor="project-profile")
    assert done.returncode == 0, done.stderr
    [entry] = lines(created)
    assert (entry["id"], entry["kind"], entry["subject"], entry["from"], entry["to"]) == (
        "CH-001", "policy", "cost.units", "both", "tokens")
    assert entry["actor"] == "project-profile" and json.loads(done.stdout)["change"] == "CH-001"
    again = cli(created, "policy-set", "cost.units", "--value-json", '"tokens"', "--apply",
                actor="project-profile")
    assert again.returncode == 0 and len(lines(created)) == 1   # the same value: no change


def test_a_change_that_cannot_be_recorded_writes_nothing(created):
    path = ledger_path(created)
    path.unlink()
    path.parent.rename(path.parent.with_name(path.parent.name + "-gone"))
    manifest = created / "Virtuoso" / "workspace-layout.json"
    before = manifest.read_bytes()
    done = cli(created, "policy-set", "cost.units", "--value-json", '"tokens"', "--apply",
               actor="project-profile")
    assert done.returncode != 0 and "nothing was written" in done.stderr
    assert manifest.read_bytes() == before


def test_a_lesson_status_records_itself_with_its_date(created):
    lessons = created.joinpath(*json.loads((created / "Virtuoso" / "workspace-layout.json")
                               .read_text(encoding="utf-8"))["roles"]["lessons"]["path"]
                               .split("/"))
    lessons.write_text(lessons.read_text(encoding="utf-8")
                       + "\n### %s — A trap (X-1)\n**Status:** Live\n" % LESSON, encoding="utf-8")
    done = cli(created, "lessons", "--record-status", LESSON, "--status", "Retired — gone",
               "--date", "2026-10-20", "--apply", actor="roadmap-review")
    assert done.returncode == 0, done.stderr
    [entry] = lines(created)
    assert (entry["kind"], entry["subject"], entry["from"], entry["to"]) == (
        "lesson", LESSON, "Live", "Retired — gone")
    assert entry["effectiveFrom"] == "2026-10-20T00:00:00Z"
    from tools.governance import lessons as lessons_mod
    [lesson] = lessons_mod.parse(lessons.read_text(encoding="utf-8"), "SRL")
    assert lesson.status_dates == ["", "2026-10-20"]                # the record's date is kept


def test_a_change_by_hand_previews_then_writes_and_an_undo_is_its_own_line(created):
    preview = cli(created, "changes", "--record", "--kind", "standing-rule", "--subject", "rule-x",
                  "--to-json", '"promoted"', "--note", "by hand", actor="roadmap-review")
    assert preview.returncode == 0 and "preview" in preview.stdout and lines(created) == []
    cli(created, "changes", "--record", "--kind", "standing-rule", "--subject", "rule-x",
        "--to-json", '"promoted"', "--apply", actor="roadmap-review")
    listed = json.loads(cli(created, "changes", "--json").stdout)
    assert listed["inForce"] == ["CH-001"]
    undo = cli(created, "changes", "--undo", "CH-001", "--apply", actor="roadmap-review")
    assert undo.returncode == 0, undo.stderr
    first, second = lines(created)
    assert (second["action"], second["undoes"], second["to"]) == ("undo", "CH-001", None)
    assert first["action"] == "apply"                               # never rewritten
    assert json.loads(cli(created, "changes", "--json").stdout)["inForce"] == []
    again = cli(created, "changes", "--undo", "CH-001", "--apply", actor="roadmap-review")
    assert again.returncode != 0 and "not in force" in again.stderr


def test_only_an_allowed_ceremony_records_by_hand(created):
    refused = cli(created, "changes", "--record", "--subject", "x", "--apply",
                  actor="storyboard")
    assert refused.returncode != 0 and "may not write the changeLedger" in refused.stderr
    assert lines(created) == []


def test_without_the_role_the_command_offers_the_entry(project):
    made = subprocess.run([sys.executable, PREFLIGHT, "--root", str(project), "--mode", "create",
                           "--authorize"], capture_output=True, text=True, encoding="utf-8")
    assert made.returncode == 0
    manifest = project / "Virtuoso" / "workspace-layout.json"
    layout = json.loads(manifest.read_text(encoding="utf-8"))
    del layout["roles"]["changeLedger"]
    manifest.write_text(json.dumps(layout, indent=2), encoding="utf-8")
    done = cli(project, "changes")
    assert done.returncode != 0 and '"changeLedger": {"path": "<file>.jsonl"' in done.stderr
    ok = cli(project, "policy-set", "cost.units", "--value-json", '"tokens"', "--apply",
             actor="project-profile")
    assert ok.returncode == 0, ok.stderr                            # no ledger: nothing recorded


def test_the_next_ceremony_that_writes_notes_a_new_plugin_version_once(created):
    rows = created / "rows.json"
    rows.write_text(json.dumps([{"id": 1, "title": "a", "estimate": 5}]), encoding="utf-8")
    for dispatch in ("A-1", "A-2"):
        done = cli(created, "timing", "--dispatch", dispatch, "--open", "--rows-file", str(rows),
                   actor="virtuoso")
        assert done.returncode == 0, done.stderr
    versions = [l for l in lines(created) if l["kind"] == "plugin-version"]
    assert len(versions) == 1 and versions[0]["to"] == changes.plugin_version()
    checked = subprocess.run([sys.executable, PREFLIGHT, "--root", str(created), "--mode",
                              "check"], capture_output=True, text=True, encoding="utf-8")
    assert checked.returncode == 0 and len(lines(created)) == 1      # preflight never writes


def test_a_damaged_line_is_skipped_and_named_and_ids_keep_counting(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(b'{"id": "CH-004", "action": "apply", "subject": "a"}\n{broken\n\xff\n')
    skipped = []
    assert [l["id"] for l in changes.load(str(path), skipped)] == ["CH-004"]
    assert len(skipped) == 2
    written = changes.append(str(path), changes.line("manual", "b", None, 1, "x"))
    assert written["id"] == "CH-005"
    assert path.read_bytes().endswith(b"\n") and path.read_bytes().count(b"CH-005") == 1


def test_a_ledger_line_that_fails_after_the_write_puts_the_policy_back(created, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("virtuoso_registry_cli", REGISTRY_CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def refuse(*_args, **_kw):
        raise OSError("the disk is full")
    monkeypatch.setattr(changes, "append", refuse)     # fails after the policy is written
    manifest = created / "Virtuoso" / "workspace-layout.json"
    before = json.loads(manifest.read_text(encoding="utf-8"))
    from tools.governance.errors import GovernanceError
    with pytest.raises(GovernanceError, match="put back from .*nothing was written"):
        module._set_policy(str(created), "project-profile", "cost.units", "tokens", apply=True)
    assert json.loads(manifest.read_text(encoding="utf-8")).get("policy") == before.get("policy")


def test_a_mapping_records_one_line_per_leaf_it_changes(created):
    done = cli(created, "policy-set", "results", "--value-json",
               '{"minimum": {"activeDays": 5, "closedLogs": 3, "measuredRows": 30}, '
               '"noEffect": 0.1}', "--apply", actor="project-profile")
    assert done.returncode == 0, done.stderr
    assert [(l["subject"], l["from"], l["to"]) for l in lines(created)] == [
        ("results.minimum.activeDays", 3, 5)]


def test_a_status_date_must_be_a_day(created):
    done = cli(created, "lessons", "--record-status", LESSON, "--status", "Retired — x",
               "--date", "yesterday", "--apply", actor="roadmap-review")
    assert done.returncode != 0 and lines(created) == []


def test_two_writers_never_take_the_same_id(tmp_path):
    path = tmp_path / "ledger.jsonl"
    script = ("import sys; sys.path.insert(0, %r)\n"
              "from tools.governance import changes\n"
              "for n in range(15):\n"
              "    changes.append(%r, changes.line('manual', 's%%d' %% n, None, n, 'x'))\n"
              % (PLUGIN_ROOT, str(path)))
    runner = tmp_path / "writer.py"
    runner.write_text(script, encoding="utf-8")
    procs = [subprocess.Popen([sys.executable, str(runner)]) for _ in range(3)]
    assert [p.wait(timeout=120) for p in procs] == [0, 0, 0]
    ids = [l["id"] for l in changes.load(str(path))]
    assert len(ids) == 45 and len(set(ids)) == 45
    assert not (tmp_path / "ledger.jsonl.lock").exists()


def test_a_cut_short_last_line_never_has_its_id_reused(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(b'{"id": "CH-001", "action": "apply", "subject": "a"}\n'
                     b'{"id": "CH-002", "action": "apply", "subj')
    assert changes.append(str(path), changes.line("manual", "b", None, 1, "x"))["id"] == "CH-003"


@pytest.mark.parametrize("sequence, expected", [
    ([("CH-001", "apply", "a", None), ("CH-002", "apply", "a", None),
      ("CH-003", "undo", "a", "CH-002")], ["CH-001"]),           # undoing the latest restores
    ([("CH-001", "apply", "a", None)], ["CH-001"]),
    ([("CH-001", "apply", "a", None), ("CH-002", "apply", "a", None)], ["CH-002"]),
    ([("CH-001", "apply", "a", None), ("CH-002", "undo", "a", "CH-001")], []),
    ([("CH-001", "apply", "a", None), ("CH-002", "apply", "b", None),
      ("CH-003", "undo", "a", "CH-001")], ["CH-002"]),
])
def test_a_change_is_in_force_until_its_undo(sequence, expected):
    entries = [dict({"id": i, "action": a, "subject": s}, **({"undoes": u} if u else {}))
               for i, a, s, u in sequence]
    assert sorted(c["id"] for c in changes.in_force(entries).values()) == expected
