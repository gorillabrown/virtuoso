"""Building a connector-backed register's snapshot (1.12.0).

A connector-backed register reaches the plugin only through a snapshot the host
builds. Hand-built snapshots went stale and flattened a card's decision subitems
into the work list, so ``next`` named an owner-decision row as the head card.
``snapshot --import`` is the builder: the host dumps the rows its connector read,
in the register's own column names, and the plugin maps them, keeps subitems out,
and stamps the read time.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance.providers import base, mapping as mapping_mod, snapshot_provider

REGISTRY_CLI = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_registry.py")
BOARD = "monday:board/1234567890"

#: A board as the connector reads it: the project's own columns, a decision
#: subitem flattened in beside its card, and the connector's value shapes.
ROWS = [
    {"Code": "PAY-RETRY", "Name": "Retry worker", "Seq": 12, "Status": "Ready",
     "Spec Status": "Specified", "Depends On": ["PAY-LOG"], "Parent": ""},
    {"Code": "PAY-LOG", "Name": "Payment telemetry", "Seq": 11,
     "Status": {"text": "Done"}, "Spec Status": "Specified", "Parent": None},
    {"Code": "PAY-REFUND", "Name": "Refund rule", "Seq": 13, "Status": "Ready",
     "Spec Status": "Specified", "Depends On": [], "Parent": ""},
    {"Code": "", "Name": "Owner decision: retry twice or thrice?", "Seq": 1,
     "Status": "Ready", "Parent": "PAY-RETRY"},
    {"Code": "DEC-7", "Name": "Owner decision: which lane?", "Seq": 2, "Status": "Ready",
     "Parent": "PAY-REFUND"},
    {"Code": "", "Name": "a blank row"},
]

POLICY = {"workRegister": {
    "snapshot": "workRegisterSnapshot",
    "fieldMappings": {"written_status": "Spec Status"},
    "statusMappings": {"queued": ["Ready"], "completed": ["Done"],
                       "written": {"full-spec": ["Specified"]}},
}}


def mapping():
    return mapping_mod.Mapping.from_policy(POLICY["workRegister"])


def run(*args):
    return subprocess.run([sys.executable, REGISTRY_CLI, *args], capture_output=True,
                          text=True, encoding="utf-8", env=dict(os.environ))


# --- the builder ---------------------------------------------------------------------


def test_rows_become_canonical_items_through_the_projects_mappings():
    snap, report = snapshot_provider.from_rows(ROWS, mapping(), source=BOARD,
                                               taken_at="2026-09-27T14:00:00Z")
    by_id = {item.id: item for item in snap.items}
    assert list(by_id) == ["PAY-RETRY", "PAY-LOG", "PAY-REFUND"]
    retry = by_id["PAY-RETRY"]
    assert (retry.title, retry.sequence, retry.status, retry.written_status) == \
        ("Retry worker", 12, base.QUEUED, base.FULL_SPEC)
    assert retry.prerequisites == ["PAY-LOG"]
    assert by_id["PAY-LOG"].status == base.COMPLETED      # {"text": "Done"}
    assert snap.source == BOARD and snap.taken_at == "2026-09-27T14:00:00Z"
    assert report.rows == 6 and report.items == 3 and report.without_id == 1


def test_a_subitem_never_enters_the_work_list():
    snap, report = snapshot_provider.from_rows(ROWS, mapping(), source=BOARD,
                                               taken_at="2026-09-27T14:00:00Z")
    assert report.parent_column == "Parent"
    assert [(s["id"], s["parent"]) for s in report.subitems] == \
        [("", "PAY-RETRY"), ("DEC-7", "PAY-REFUND")]
    assert "DEC-7" not in {item.id for item in snap.items}


def test_the_parent_column_can_be_named():
    rows = [dict(r) for r in ROWS]
    for row in rows:
        row["Belongs To"] = row.pop("Parent", "")
    _, report = snapshot_provider.from_rows(rows, mapping(), source=BOARD, taken_at="x",
                                            parent_column="Belongs To")
    assert report.parent_column == "Belongs To" and len(report.subitems) == 2
    _, unnamed = snapshot_provider.from_rows(rows, mapping(), source=BOARD, taken_at="x")
    assert unnamed.parent_column == "" and unnamed.subitems == []


def test_an_unreadable_status_is_reported():
    rows = ROWS + [{"Code": "ODD-1", "Name": "Odd", "Status": "Parked"}]
    _, report = snapshot_provider.from_rows(rows, mapping(), source=BOARD, taken_at="x")
    assert report.unknown_status == [{"id": "ODD-1", "status": "Parked"}]


def test_duplicate_identifiers_are_refused():
    with pytest.raises(ValueError, match="PAY-REFUND"):
        snapshot_provider.from_rows(ROWS + [{"Code": "PAY-REFUND", "Name": "again"}],
                                    mapping(), source=BOARD, taken_at="x")


def test_rows_with_no_identifier_column_are_refused():
    with pytest.raises(ValueError, match="fieldMappings.id"):
        snapshot_provider.from_rows([{"Label": "x"}], mapping(), source=BOARD, taken_at="x")


@pytest.mark.parametrize("value, expected", [
    ("2026-09-27T14:00:00Z", "2026-09-27T14:00:00Z"),
    ("2026-09-27T09:00:00-05:00", "2026-09-27T14:00:00Z"),
])
def test_the_read_time_is_stored_in_utc(value, expected):
    assert snapshot_provider.parse_taken_at(value) == expected


def test_a_read_time_without_an_offset_is_refused():
    with pytest.raises(ValueError, match="offset"):
        snapshot_provider.parse_taken_at("2026-09-27T14:00:00")


def test_a_snapshot_item_naming_a_parent_is_not_read_as_a_card(tmp_path):
    """A snapshot some other builder wrote is read the same way."""
    target = tmp_path / "snap.json"
    target.write_text(json.dumps({"takenAt": "2099-01-01T00:00:00Z", "items": [
        {"id": "CARD-1", "status": "queued", "sequence": 2},
        {"id": "DEC-1", "status": "queued", "sequence": 1, "parent": "CARD-1"},
        {"id": "DEC-2", "status": "queued", "sequence": 1, "extra": {"Parent Item": "CARD-1"}},
    ]}), encoding="utf-8")
    provider = snapshot_provider.SnapshotWorkRegister(source=str(target))
    assert [item.id for item in provider.snapshot().items] == ["CARD-1"]
    assert provider.next_eligible().id == "CARD-1"


# --- the command ----------------------------------------------------------------------


@pytest.fixture
def board(project):
    """A project whose live register is a board, read through a snapshot role."""
    (project / "Virtuoso").mkdir()
    manifest = {"schemaVersion": 2, "policy": POLICY, "roles": {
        "workRegister": {"external": BOARD, "provider": "connector", "authority": "live",
                         "mutability": "read-write", "allowedWriters": ["roadmap-review"],
                         "validation": "external", "classification": "active",
                         "origin": "authored"},
        "workRegisterSnapshot": {"path": "Virtuoso/board.snapshot.json",
                                 "provider": "snapshot", "authority": "report",
                                 "mutability": "generated", "validation": "exists",
                                 "classification": "active", "origin": "generated"},
    }}
    (project / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    (project / "rows.json").write_text(json.dumps({"takenAt": _now(), "rows": ROWS}),
                                       encoding="utf-8")
    return project


def _now(hours_ago=0):
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def test_import_writes_the_registered_snapshot_and_next_reads_the_real_head(board):
    imported = run("--root", str(board), "snapshot", "--import", "rows.json")
    assert imported.returncode == 0, imported.stderr
    assert "3 item(s) from 6 row(s)" in imported.stdout
    assert "2 subitem(s) kept out" in imported.stdout
    written = json.loads((board / "Virtuoso" / "board.snapshot.json").read_text(encoding="utf-8"))
    assert written["source"] == BOARD
    head = json.loads(run("--root", str(board), "next", "--json").stdout)
    assert head["item"]["id"] == "PAY-RETRY"
    assert head["provenance"]["stale"] is False


def test_import_reports_as_json(board):
    payload = json.loads(run("--root", str(board), "snapshot", "--import", "rows.json",
                             "--json").stdout)
    assert payload["snapshot"] == "Virtuoso/board.snapshot.json"
    assert payload["items"] == 3 and len(payload["subitemsExcluded"]) == 2


def test_the_taken_at_flag_wins_and_an_old_read_is_stale(board):
    old = _now(hours_ago=38)
    assert run("--root", str(board), "snapshot", "--import", "rows.json",
               "--taken-at", old).returncode == 0
    listing = run("--root", str(board), "next")
    assert "[STALE] snapshot is 38.0h old" in listing.stdout
    assert "snapshot --import" in listing.stdout


def test_import_never_writes_over_the_live_register(project):
    (project / "Virtuoso").mkdir()
    (project / "register.csv").write_text("id,title,status\nA,a,Queued\n", encoding="utf-8")
    manifest = {"schemaVersion": 2, "policy": {"workRegister": {"snapshot": "workRegister"}},
                "roles": {"workRegister": {
                    "path": "register.csv", "provider": "csv", "authority": "live",
                    "mutability": "read-write", "allowedWriters": [], "validation": "exists",
                    "classification": "active", "origin": "authored"}}}
    (project / "Virtuoso" / "workspace-layout.json").write_text(json.dumps(manifest),
                                                                encoding="utf-8")
    (project / "rows.json").write_text(json.dumps(ROWS), encoding="utf-8")
    before = snapshot_tree(str(project))
    refused = run("--root", str(project), "snapshot", "--import", "rows.json")
    assert refused.returncode == 3
    assert "is not a snapshot the import may replace" in refused.stderr
    assert snapshot_tree(str(project)) == before


def test_import_without_a_snapshot_role_needs_out(project):
    (project / "Virtuoso").mkdir()
    (project / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps({"schemaVersion": 2, "roles": {}}), encoding="utf-8")
    (project / "rows.json").write_text(json.dumps(ROWS), encoding="utf-8")
    refused = run("--root", str(project), "snapshot", "--import", "rows.json")
    assert refused.returncode == 3 and "Pass --out" in refused.stderr
    written = run("--root", str(project), "snapshot", "--import", "rows.json", "--out",
                  "snap.json")
    assert written.returncode == 0, written.stderr
    assert json.loads((project / "snap.json").read_text(encoding="utf-8"))["items"]


def test_a_malformed_rows_file_is_unanswerable(board):
    (board / "rows.json").write_text(json.dumps({"rows": "nope"}), encoding="utf-8")
    refused = run("--root", str(board), "snapshot", "--import", "rows.json")
    assert refused.returncode == 3 and "list of row objects" in refused.stderr
    assert not (board / "Virtuoso" / "board.snapshot.json").exists()
