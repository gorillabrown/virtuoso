"""Repair preview, transactionality, and backups (items 7, 8, 9, 93, 94).

A preview writes nothing and matches the subsequent approved apply exactly.
An apply that fails validation leaves the original registry and manifest intact.
Every backed-up target is recorded with its source, destination, byte count,
hash, timestamp, and operation, and the set verifies independently.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import backup as backup_mod, registry as registry_mod
from tools.governance import repair as repair_mod
from tools.governance.errors import BackupError, RepairError

PREFLIGHT = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_preflight.py")


def run(root, *args):
    return subprocess.run([sys.executable, PREFLIGHT, "--root", str(root), *args],
                          capture_output=True, text=True, env=dict(os.environ))


@pytest.fixture
def needs_repair(project):
    """A registered project whose readme generated region has drifted."""
    run(project, "--mode", "create", "--authorize")
    readme = project / "Virtuoso.Governance.Readme.md"
    text = readme.read_text(encoding="utf-8")
    readme.write_text(text.replace("| Roadmap / specification store |", "| WRONG |"),
                      encoding="utf-8")
    return project


# --- item 93: preview matches the apply ---------------------------------------


def test_preview_writes_nothing(needs_repair):
    before = snapshot_tree(needs_repair)
    result = run(needs_repair, "--mode", "repair", "--json")
    payload = json.loads(result.stdout[result.stdout.index("{"):])
    assert payload["writes"] == 0
    assert snapshot_tree(needs_repair) == before


def test_preview_output_matches_the_applied_change_exactly(needs_repair):
    raw = run(needs_repair, "--mode", "repair", "--json").stdout
    preview = json.loads(raw[raw.index("{"):])["plan"]

    raw = run(needs_repair, "--mode", "repair", "--apply", "--json").stdout
    applied = json.loads(raw[raw.index("{"):])

    assert applied["plan"] == preview, "the preview and the apply disagree"
    assert sorted(applied["filesWritten"]) == sorted(
        p for p in preview["filesAffected"]
    ), "the apply touched a different set of files than the preview promised"


def test_preview_names_paths_changes_files_and_backup_location(needs_repair):
    raw = run(needs_repair, "--mode", "repair").stdout
    assert "Files affected:" in raw
    assert "Backups will be written under:" in raw
    assert backup_mod.BACKUP_DIRNAME.replace(os.sep, "/") in raw
    assert any(kind in raw for kind in ("sync-readme-view", "sync-manifest",
                                        "append-generated-region", "adopt-readme-role"))


# --- item 8: transactional failure --------------------------------------------


def test_a_reconstruction_that_fails_validation_writes_nothing(project, monkeypatch):
    run(project, "--mode", "create", "--authorize")
    reg = registry_mod.load(str(project))
    plan = repair_mod.plan(reg)

    # Force the reconstruction to be invalid: a root-escaping path.
    data = json.loads(plan.manifest_text)
    data["roles"]["roadmap"]["path"] = "../../escape.md"
    plan.manifest_text = json.dumps(data, indent=2) + "\n"
    plan.files_affected = ["Virtuoso/workspace-layout.json"]

    before = snapshot_tree(project)
    with pytest.raises(RepairError) as excinfo:
        repair_mod.apply_plan(reg, plan)
    assert "untouched" in str(excinfo.value)
    assert snapshot_tree(project) == before


def test_a_failure_after_the_first_write_rolls_the_pair_back(project, monkeypatch):
    run(project, "--mode", "create", "--authorize")
    reg = registry_mod.load(str(project))
    readme = project / "Virtuoso.Governance.Readme.md"
    readme.write_text(readme.read_text(encoding="utf-8").replace(
        "| Roadmap / specification store |", "| WRONG |"), encoding="utf-8")

    reg = registry_mod.load(str(project))
    plan = repair_mod.plan(reg)
    plan.files_affected = ["Virtuoso/workspace-layout.json", "Virtuoso.Governance.Readme.md"]
    plan.manifest_text = reg.manifest_json().replace('"layout": "plugin-only"',
                                                     '"layout": "plugin-only" ')

    before = snapshot_tree(project)

    calls = {"n": 0}
    real_write = repair_mod.textio.write_if_changed

    def explode(path, content):
        calls["n"] += 1
        if calls["n"] == 2:                      # fail on the second write
            raise OSError("disk full")
        return real_write(path, content)

    monkeypatch.setattr(repair_mod.textio, "write_if_changed", explode)
    with pytest.raises(RepairError) as excinfo:
        repair_mod.apply_plan(reg, plan)
    assert "rolled back" in str(excinfo.value)

    after = snapshot_tree(project)
    for rel, raw in before.items():
        assert after[rel] == raw, "%s was left modified after a rollback" % rel


# --- item 9 / 55: backups ------------------------------------------------------


def test_backup_records_every_required_field(project):
    run(project, "--mode", "create", "--authorize")
    target = project / "Virtuoso" / "workspace-layout.json"
    backup_set = backup_mod.open_set(str(project), "test")
    entry = backup_set.add(str(target), "repair")
    backup_set.write_manifest()

    assert entry.source == "Virtuoso/workspace-layout.json"
    assert entry.destination
    assert entry.bytes == target.stat().st_size
    assert len(entry.sha256) == 64
    assert entry.timestamp.endswith("Z")
    assert entry.operation == "repair"

    payload = json.loads(Path(backup_set.manifest_path).read_text(encoding="utf-8"))
    assert payload["entries"][0]["sha256"] == entry.sha256


def test_backup_verifies_and_restores(project):
    run(project, "--mode", "create", "--authorize")
    target = project / "Virtuoso" / "workspace-layout.json"
    original = target.read_bytes()

    backup_set = backup_mod.open_set(str(project), "test")
    backup_set.add(str(target), "repair")
    backup_set.write_manifest()
    assert backup_mod.verify(backup_set) == []

    target.write_bytes(b"{}\n")
    backup_mod.restore(backup_set)
    assert target.read_bytes() == original


def test_a_corrupted_backup_refuses_to_restore(project):
    run(project, "--mode", "create", "--authorize")
    backup_set = backup_mod.open_set(str(project), "test")
    backup_set.add(str(project / "Virtuoso" / "workspace-layout.json"), "repair")
    backup_set.write_manifest()

    stored = Path(backup_set.directory) / backup_set.entries[0].destination
    stored.write_bytes(b"tampered")
    assert backup_mod.verify(backup_set)
    with pytest.raises(BackupError):
        backup_mod.restore(backup_set)


def test_backup_retention_prunes_old_sets(project):
    run(project, "--mode", "create", "--authorize")
    import datetime as dt
    base = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    for index in range(5):
        s = backup_mod.open_set(str(project), "test",
                                now=base + dt.timedelta(hours=index))
        s.add(str(project / "Virtuoso" / "workspace-layout.json"), "repair")
        s.write_manifest()
    removed = backup_mod.prune(str(project), keep=2)
    assert len(removed) == 3
    remaining = os.listdir(project / "Virtuoso" / ".backups")
    assert len(remaining) == 2


def test_backups_are_excluded_from_sweep_boundaries():
    """Item 56: backup and quarantine directories must be excluded by default."""
    from tools.governance import policy as policy_mod
    excludes = policy_mod.load({}).get("sweep.exclude")
    assert "Virtuoso/.backups/**" in excludes
    assert "Virtuoso/.quarantine/**" in excludes
