"""The progress band's data: the opt-in ``progress`` role and ``virtuoso_registry progress``.

The plugin's hooks module (``hooks/progress-band.tsx``) draws the file above the prompt;
every skill that commits to a deliverable flags it here and every skill that finishes one
marks it, through the command, so ``updated`` always comes from the clock.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from tools.governance import progress as progress_mod
from tools.governance import schema

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")
MANIFEST = Path("Virtuoso") / "workspace-layout.json"
FILE = "Project Documentation/2 operational/Progress.json"

#: Every skill the contract's *Feeding the band* table names as a writer.
WRITERS = ("virtuoso", "next-dispatch", "dispatch-closeout", "epic", "roadmap-review",
           "mid-dispatch-decision", "adversarial-review", "3rd-party-audit",
           "governance-sweep")


def run(script, *args):
    return subprocess.run([sys.executable, script, *args], capture_output=True,
                          text=True, encoding="utf-8", env=dict(os.environ))


def cli(root, *args, actor=None):
    head = ["--root", str(root)] + (["--actor", actor] if actor else [])
    return run(REGISTRY_CLI, *head, "progress", *args)


@pytest.fixture
def workspace(project):
    assert run(PREFLIGHT, "--root", str(project), "--mode", "create",
               "--authorize").returncode == 0
    return project


def register(root: Path) -> Path:
    path = root / MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    role = dict(schema.DEFAULT_ROLES["progress"], path=FILE)
    data["roles"]["progress"] = role
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return root / FILE


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --- the role ------------------------------------------------------------------------------

def test_the_role_is_opt_in():
    assert "progress" in schema.DEFAULT_ROLES
    assert "progress" not in schema.CREATE_ROLE_ORDER


def test_every_skill_the_contract_names_may_write():
    assert set(schema.DEFAULT_ROLES["progress"]["allowedWriters"]) == set(WRITERS)


@pytest.mark.parametrize("skill", WRITERS)
def test_every_writer_skill_feeds_the_band(skill):
    body = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    assert re.search(r"--actor %s progress --(flag|set)" % re.escape(skill), body), skill


# --- the command ---------------------------------------------------------------------------

def test_unregistered_read_says_the_band_is_off(workspace):
    done = cli(workspace)
    assert done.returncode == 0
    assert "band is off" in done.stdout and '"progress":' in done.stdout


def test_unregistered_change_is_refused_naming_the_entry(workspace):
    done = cli(workspace, "--flag", "VIR-1", "--label", "one", actor="virtuoso")
    assert done.returncode != 0
    assert '"progress": {"path": "<file>.json"' in done.stderr + done.stdout


def test_a_writer_not_named_is_refused(workspace):
    register(workspace)
    done = cli(workspace, "--flag", "VIR-1", "--label", "one", actor="storyboard")
    assert done.returncode != 0
    assert not (workspace / FILE).exists()


def test_flag_set_and_read(workspace):
    path = register(workspace)
    assert cli(workspace, "--flag", "VIR-1", "--label", "one", actor="roadmap-review").returncode == 0
    assert cli(workspace, "--flag", "VIR-2", "--label", "two", actor="roadmap-review").returncode == 0
    assert cli(workspace, "--set", "VIR-1", "--state", "active", actor="next-dispatch").returncode == 0
    doc = read(path)
    assert [(i["id"], i["state"]) for i in doc["items"]] == [("VIR-1", "active"), ("VIR-2", "queued")]
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$", doc["updated"])
    assert cli(workspace, "--set", "VIR-1", "--state", "done", actor="dispatch-closeout").returncode == 0
    shown = json.loads(cli(workspace, "--json").stdout)
    assert (shown["done"], shown["total"], shown["percent"], shown["next"]) == (1, 2, 50, "two")


def test_flagging_again_never_moves_a_done_item_back(workspace):
    path = register(workspace)
    cli(workspace, "--flag", "VIR-1", "--label", "one", actor="roadmap-review")
    cli(workspace, "--set", "VIR-1", "--state", "done", actor="dispatch-closeout")
    assert cli(workspace, "--flag", "VIR-1", "--label", "one", actor="virtuoso").returncode == 0
    assert read(path)["items"][0]["state"] == "done"


def test_unknown_id_and_bad_state_are_refused(workspace):
    register(workspace)
    assert cli(workspace, "--set", "NOPE", "--state", "done", actor="virtuoso").returncode != 0
    cli(workspace, "--flag", "VIR-1", "--label", "one", actor="virtuoso")
    assert cli(workspace, "--set", "VIR-1", "--state", "finished", actor="virtuoso").returncode != 0


def test_after_drop_and_header(workspace):
    path = register(workspace)
    cli(workspace, "--flag", "VIR-1", "--label", "one", actor="roadmap-review")
    cli(workspace, "--flag", "VIR-3", "--label", "three", actor="roadmap-review")
    assert cli(workspace, "--flag", "HB-2", "--label", "held", "--after", "VIR-1",
               actor="virtuoso").returncode == 0
    assert cli(workspace, "--drop", "VIR-3", actor="roadmap-review").returncode == 0
    assert cli(workspace, "--deadline", "2027-01-01", actor="roadmap-review").returncode == 0
    assert cli(workspace, "--deadline", "soon", actor="roadmap-review").returncode != 0
    doc = read(path)
    assert [i["id"] for i in doc["items"]] == ["VIR-1", "HB-2"]
    assert doc["deadline"] == "2027-01-01"


def test_a_file_that_is_not_the_shape_is_reported(workspace):
    path = register(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"title": "x"}', encoding="utf-8")
    done = cli(workspace, "--flag", "VIR-1", "--label", "one", actor="virtuoso")
    assert done.returncode != 0
    assert read(path) == {"title": "x"}


def test_prune_done_and_now(workspace):
    path = register(workspace)
    cli(workspace, "--flag", "VIR-1", "--label", "one", actor="roadmap-review")
    cli(workspace, "--flag", "VIR-2", "--label", "two", actor="roadmap-review")
    cli(workspace, "--set", "VIR-1", "--state", "done", actor="dispatch-closeout")
    assert cli(workspace, "--prune-done", actor="roadmap-review").returncode == 0
    assert [i["id"] for i in read(path)["items"]] == ["VIR-2"]
    assert cli(workspace, "--now", "row 4 of 10", actor="virtuoso").returncode == 0
    assert read(path)["now"] == "row 4 of 10"
    assert cli(workspace, "--now", "", actor="virtuoso").returncode == 0
    assert "now" not in read(path)


def test_parallel_writers_lose_nothing(workspace):
    """Two processes flagging at once: every flag lands (the lock serializes them)."""
    path = register(workspace)
    head = [sys.executable, REGISTRY_CLI, "--root", str(workspace), "--actor", "virtuoso",
            "progress", "--flag"]
    procs = [subprocess.Popen(head + ["P-%d" % n, "--label", "p%d" % n],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
             for n in range(8)]
    assert all(p.wait(timeout=60) == 0 for p in procs)
    assert sorted(i["id"] for i in read(path)["items"]) == sorted("P-%d" % n for n in range(8))
    assert not Path(str(path) + ".lock").exists()


def test_a_stale_lock_is_taken_over(workspace):
    path = register(workspace)
    lock = Path(str(path) + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("999999", encoding="ascii")
    old = lock.stat().st_mtime - progress_mod.STALE_LOCK_SECONDS - 5
    os.utime(lock, (old, old))
    assert cli(workspace, "--flag", "VIR-1", "--label", "one", actor="virtuoso").returncode == 0


def test_a_held_lock_refuses_after_waiting(tmp_path):
    target = str(tmp_path / "p.json")
    with progress_mod.locked(target):
        with pytest.raises(progress_mod.ProgressError):
            with progress_mod.locked(target, wait_seconds=0.2):
                pass


# --- registering the role --------------------------------------------------------------------

def manifest(root: Path) -> dict:
    return json.loads((root / MANIFEST).read_text(encoding="utf-8"))


def test_register_previews_then_applies(workspace):
    before = (workspace / MANIFEST).read_text(encoding="utf-8")
    done = run(REGISTRY_CLI, "--root", str(workspace), "--actor", "project-profile",
               "progress", "--register")
    assert done.returncode == 0 and "preview" in done.stdout
    assert (workspace / MANIFEST).read_text(encoding="utf-8") == before
    done = run(REGISTRY_CLI, "--root", str(workspace), "--actor", "project-profile",
               "progress", "--register", "--apply")
    assert done.returncode == 0, done.stderr
    role = manifest(workspace)["roles"]["progress"]
    assert role["path"].endswith("/Progress.json")
    assert (workspace / role["path"]).is_file()
    assert cli(workspace, "--flag", "VIR-1", "--label", "one", actor="virtuoso").returncode == 0


def test_register_takes_a_path_and_refuses_escapes(workspace):
    base = [REGISTRY_CLI, "--root", str(workspace), "--actor", "virtuoso-init", "progress",
            "--register", "--apply", "--path"]
    assert run(*base, "../outside.json").returncode != 0
    assert "progress" not in manifest(workspace)["roles"]
    assert run(*base, "briefs/progress.json").returncode == 0
    assert manifest(workspace)["roles"]["progress"]["path"] == "briefs/progress.json"


def test_register_refuses_an_actor_that_may_not(workspace):
    done = run(REGISTRY_CLI, "--root", str(workspace), "--actor", "storyboard", "progress",
               "--register", "--apply")
    assert done.returncode != 0
    assert "progress" not in manifest(workspace)["roles"]


def test_register_rolls_back_a_manifest_that_fails_validation(workspace, monkeypatch):
    from tools.governance import registry as registry_mod
    from tools.governance import repair as repair_mod
    reg = registry_mod.load(str(workspace))
    before = (workspace / MANIFEST).read_text(encoding="utf-8")
    spec = schema.RoleSpec.from_manifest("progress", dict(
        schema.default_role("progress"), path="x.json", authority="not-an-authority"))
    plan = repair_mod.role_plan(reg, spec)
    with pytest.raises(Exception):
        repair_mod.apply_plan(reg, plan, label="progress-register", actor="virtuoso")
    assert (workspace / MANIFEST).read_text(encoding="utf-8") == before


def _item_in_register(workspace):
    made = run(REGISTRY_CLI, "--root", str(workspace), "--actor", "roadmap-review",
               "create-item", "--item", "ITEM-1", "--fields-json", '{"title": "First thing"}')
    assert made.returncode == 0, made.stdout + made.stderr


def test_prune_refuses_a_done_item_with_no_ledger_record(workspace):
    path = register(workspace)
    _item_in_register(workspace)
    cli(workspace, "--flag", "ITEM-1", "--label", "first", actor="virtuoso")
    cli(workspace, "--set", "ITEM-1", "--state", "done", actor="dispatch-closeout")
    cli(workspace, "--flag", "AUDIT-D1", "--label", "audit", actor="3rd-party-audit")
    cli(workspace, "--set", "AUDIT-D1", "--state", "done", actor="3rd-party-audit")
    before = path.read_text(encoding="utf-8")
    done = cli(workspace, "--prune-done", actor="roadmap-review")
    assert done.returncode != 0
    assert "ITEM-1" in done.stderr and "terminal ledger" in done.stderr
    assert "AUDIT-D1" not in done.stderr          # not a register item: exempt
    assert path.read_text(encoding="utf-8") == before


def test_prune_goes_ahead_once_the_item_is_closed_out(workspace):
    path = register(workspace)
    _item_in_register(workspace)
    cli(workspace, "--flag", "ITEM-1", "--label", "first", actor="virtuoso")
    cli(workspace, "--set", "ITEM-1", "--state", "done", actor="dispatch-closeout")
    closed = run(REGISTRY_CLI, "--root", str(workspace), "--actor", "dispatch-closeout",
                 "record-completion", "--item", "ITEM-1", "--date", "2026-01-01",
                 "--result", "shipped", "--evidence", "CloseOut.ITEM-1.2026-01-01.md", "--apply")
    assert closed.returncode == 0, closed.stdout + closed.stderr
    assert cli(workspace, "--prune-done", actor="roadmap-review").returncode == 0
    assert read(path)["items"] == []


def test_prune_refuses_when_the_ledger_cannot_be_read(workspace):
    path = register(workspace)
    _item_in_register(workspace)
    cli(workspace, "--flag", "ITEM-1", "--label", "first", actor="virtuoso")
    cli(workspace, "--set", "ITEM-1", "--state", "done", actor="dispatch-closeout")
    data = manifest(workspace)
    del data["roles"]["terminalLedger"]
    (workspace / MANIFEST).write_text(json.dumps(data, indent=2), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    done = cli(workspace, "--prune-done", actor="roadmap-review")
    assert done.returncode != 0 and "nothing was pruned" in done.stderr
    assert path.read_text(encoding="utf-8") == before


# --- drift against the register ----------------------------------------------------------------

def test_drift_names_both_directions_and_ignores_ids_the_register_lacks():
    doc = {"items": [
        {"id": "A", "state": "done"},      # in sync
        {"id": "B", "state": "active"},    # register closed it, the band has not
        {"id": "C", "state": "done"},      # the band closed it, the register has not
        {"id": "HB-1", "state": "queued"}, # a held plan: not in the register, not drift
    ]}
    found = progress_mod.drift(doc, {"A": True, "B": True, "C": False})
    assert found == {"registerDoneBandNot": ["B"], "bandDoneRegisterNot": ["C"],
                     "notInRegister": ["HB-1"], "inSync": 1}


def test_drift_reads_the_live_register(workspace):
    register(workspace)
    made = run(REGISTRY_CLI, "--root", str(workspace), "--actor", "roadmap-review",
               "create-item", "--item", "ITEM-1", "--fields-json", '{"title": "First thing"}')
    assert made.returncode == 0, made.stdout + made.stderr
    cli(workspace, "--flag", "ITEM-1", "--label", "first", actor="virtuoso")
    cli(workspace, "--set", "ITEM-1", "--state", "done", actor="dispatch-closeout")
    cli(workspace, "--flag", "HB-1", "--label", "held", actor="virtuoso")
    found = json.loads(cli(workspace, "--drift", "--json").stdout)
    assert found["computable"] is True
    assert found["bandDoneRegisterNot"] == ["ITEM-1"]
    assert found["notInRegister"] == ["HB-1"]


def test_the_ad_hoc_skills_do_not_write_the_band():
    for name in ("storyboard", "write-plan"):
        body = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert " progress --" not in body, name


# --- the module ----------------------------------------------------------------------------

def test_summary_counts_like_the_band():
    doc = {"title": "Q", "items": [
        {"id": "a", "label": "a", "state": "done"},
        {"id": "b", "label": "b", "state": "active"},
        {"id": "c", "label": "c", "state": "blocked"},
        {"id": "d", "label": "d", "state": "queued"}]}
    found = progress_mod.summary(doc)
    assert (found["done"], found["total"], found["percent"]) == (1, 4, 25)
    assert found["active"] == ["b"] and found["next"] == "c"


@pytest.mark.skipif(shutil.which("claude") is None,
                    reason="the claude CLI is not installed here (CI); release preflight runs it")
def test_the_band_module_passes_its_own_behaviour_tests():
    """`claude plugin test` runs hooks/progress-band.test.tsx against the engine itself."""
    done = subprocess.run(["claude", "plugin", "test", str(ROOT)], capture_output=True,
                          text=True, encoding="utf-8", timeout=300)
    assert done.returncode == 0, (done.stdout + done.stderr)[-1500:]
    assert " 0 fail" in done.stdout


def test_the_plugin_ships_the_band_module():
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert hooks["modules"] == ["./progress-band.tsx"]
    assert (ROOT / "hooks" / "progress-band.tsx").is_file()
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["types"] == "./types/index.d.ts"
    assert (ROOT / "types" / "index.d.ts").is_file()
