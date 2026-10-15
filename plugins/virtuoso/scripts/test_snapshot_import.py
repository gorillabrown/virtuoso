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


def test_next_reports_in_flight_and_missing_prerequisites_apart(board):
    rows = [dict(row, Status="In Progress") if row["Code"] == "PAY-RETRY" else row
            for row in ROWS]
    rows.append({"Code": "PAY-AUDIT", "Name": "Audit trail", "Seq": 14, "Status": "Ready",
                 "Spec Status": "Specified", "Depends On": ["PAY-GONE"], "Parent": ""})
    (board / "rows.json").write_text(json.dumps({"takenAt": _now(), "rows": rows}),
                                     encoding="utf-8")
    imported = run("--root", str(board), "snapshot", "--import", "rows.json")
    assert imported.returncode == 0, imported.stderr
    head = json.loads(run("--root", str(board), "next", "--json").stdout)
    assert head["item"]["id"] == "PAY-REFUND"
    assert [i["id"] for i in head["inFlight"]] == ["PAY-RETRY"]
    assert head["missingPrerequisites"] == {"PAY-AUDIT": ["PAY-GONE"]}
    listing = run("--root", str(board), "next").stdout
    assert "in flight:     PAY-RETRY" in listing
    assert "PAY-GONE (named by PAY-AUDIT)" in listing


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


# --- a connector's raw page, keyed by column id (VIR-003) ------------------------------
#
# The fixtures are the connector's own responses for a real board, trimmed only by
# reading fewer whole items (and, in the column list, by dropping the owner's personal
# details, which nothing reads). Expected values are literals from that capture.

FIXTURES = Path(PLUGIN_ROOT) / "scripts" / "fixtures"
PAGE = str(FIXTURES / "monday_board_page.json")
COLUMNS = str(FIXTURES / "monday_board_columns.json")
MONDAY = "monday:board/18432510412"
MONDAY_POLICY = {"workRegister": {
    "snapshot": "workRegisterSnapshot",
    "fieldMappings": {"id": "Item ID", "title": "Name", "status": "Status",
                      "written_status": "Spec", "sequence": "Sequence", "effort": "Effort",
                      "prerequisites": "Depends On", "spec_link": "Spec Link",
                      "completed": "Completed", "group": "Group"},
    "statusMappings": {"queued": ["Queued"], "in-flight": ["Working on it"],
                       "blocked": ["Stuck"], "completed": ["Done"],
                       "dissolved": ["Dissolved"], "superseded": ["Superseded"],
                       "written": {"stub": ["Stub"], "full-spec": ["Full Spec"]}},
}}


def monday_project(project, external=MONDAY, field_mappings=None):
    policy = json.loads(json.dumps(MONDAY_POLICY))
    policy["workRegister"]["fieldMappings"].update(field_mappings or {})
    (project / "Virtuoso").mkdir(exist_ok=True)
    manifest = {"schemaVersion": 2, "policy": policy, "roles": {
        "workRegister": {"external": external, "provider": "connector", "authority": "live",
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
    return project


def written_items(project):
    snap = json.loads((project / "Virtuoso" / "board.snapshot.json").read_text(encoding="utf-8"))
    return {i["id"]: i for i in snap["items"]}


def test_a_raw_monday_page_imports_without_hand_built_rows(project):
    monday_project(project)
    imported = run("--root", str(project), "snapshot", "--import", PAGE, "--columns", COLUMNS,
                   "--json")
    assert imported.returncode == 0, imported.stderr
    item = written_items(project)["ROADMAP-BOARD"]
    assert (item["sequence"], item["status"], item["written_status"], item["effort"],
            item["group"]) == (19, "queued", "stub", "L", "Up next")
    assert item["extra"] == {
        "providerId": "13122472255", "revision": "2026-10-09T04:15:32Z",
        "url": "https://estrattbrown.monday.com/boards/18432510412/pulses/13122472255"}


def test_drift_names_a_mapped_column_the_board_lacks(project):
    monday_project(project, field_mappings={"started": "Started"})
    payload = json.loads(run("--root", str(project), "snapshot", "--import", PAGE,
                             "--columns", COLUMNS, "--json").stdout)
    assert payload["missingColumns"] == [{"field": "started", "column": "Started"}]
    text = run("--root", str(project), "snapshot", "--import", PAGE, "--columns", COLUMNS)
    assert text.returncode == 0 and "[DRIFT]" in text.stdout


def test_drift_names_a_board_column_nothing_maps(project):
    monday_project(project)
    payload = json.loads(run("--root", str(project), "snapshot", "--import", PAGE,
                             "--columns", COLUMNS, "--json").stdout)
    assert {"id": "person", "title": "Person"} in payload["unmappedColumns"]
    assert not any("Person" in item["extra"] for item in written_items(project).values())


def _page():
    return json.loads(Path(PAGE).read_text(encoding="utf-8"))


def test_a_page_with_more_to_read_is_refused(project):
    monday_project(project)
    partial = _page()
    partial["pagination"]["has_more"] = True
    (project / "page.json").write_text(json.dumps(partial), encoding="utf-8")
    before = snapshot_tree(str(project))
    refused = run("--root", str(project), "snapshot", "--import", "page.json",
                  "--columns", COLUMNS)
    assert refused.returncode == 3 and "has_more" in refused.stderr
    assert snapshot_tree(str(project)) == before


def test_pages_are_read_together(project):
    monday_project(project)
    whole, first = _page(), _page()
    first["items"], first["pagination"]["has_more"] = whole["items"][:2], True
    last = dict(whole, items=whole["items"][2:])
    (project / "pages.json").write_text(json.dumps([first, last]), encoding="utf-8")
    assert run("--root", str(project), "snapshot", "--import", PAGE,
               "--columns", COLUMNS).returncode == 0
    single = set(written_items(project))
    assert run("--root", str(project), "snapshot", "--import", "pages.json",
               "--columns", COLUMNS).returncode == 0
    assert set(written_items(project)) == single and len(single) == 4


def test_a_page_from_another_board_is_refused(project):
    monday_project(project, external="monday:board/1234567890")
    refused = run("--root", str(project), "snapshot", "--import", PAGE, "--columns", COLUMNS)
    assert refused.returncode == 3
    assert "18432510412" in refused.stderr and "1234567890" in refused.stderr
    assert not (project / "Virtuoso" / "board.snapshot.json").exists()


def test_a_raw_page_without_columns_is_refused(project):
    monday_project(project)
    refused = run("--root", str(project), "snapshot", "--import", PAGE)
    assert refused.returncode == 3 and "--columns" in refused.stderr


@pytest.mark.parametrize("columns, mappings", [
    ([{"id": "a", "title": "Effort"}, {"id": "b", "title": "Effort"}], {}),
    ([{"id": "a", "title": "url"}], {"effort": "url"}),
])
def test_an_ambiguous_board_column_is_refused(columns, mappings):
    ambiguous = mapping_mod.Mapping.from_policy({"fieldMappings": mappings})
    with pytest.raises(ValueError, match="ambiguous"):
        snapshot_provider.page_to_rows([_page()], columns, ambiguous, mappings)


def test_a_page_naming_no_board_is_refused_where_a_board_is_registered(project):
    monday_project(project)
    anonymous = _page()
    del anonymous["board"]
    (project / "page.json").write_text(json.dumps(anonymous), encoding="utf-8")
    refused = run("--root", str(project), "snapshot", "--import", "page.json",
                  "--columns", COLUMNS)
    assert refused.returncode == 3 and "(none named)" in refused.stderr


def test_a_file_mixing_pages_and_rows_is_refused():
    with pytest.raises(ValueError, match="mixes"):
        snapshot_provider.parse_rows(json.dumps([_page(), {"Code": "A"}]))


def test_a_markdown_reads_autolinks_are_unwrapped():
    # Notion's rows mode and page fetch link any "<name>.md" (.md is a TLD) and any URL.
    rows = [{"Code": "PAY-1", "Name": "Write [done.md](http://done.md) and keep [x](y)",
             "Status": "Ready", "Spec Link": "[ROADMAP.md#a](http://ROADMAP.md#a)"},
            {"Code": "PAY-2", "Name": "Plain", "Status": "Ready",
             "Spec Link": {"text": "[https://e.com/s](https://e.com/s)"}}]
    snap, _ = snapshot_provider.from_rows(rows, mapping(), source=BOARD,
                                          taken_at="2026-10-09T00:00:00Z")
    by_id = {i.id: i for i in snap.items}
    assert by_id["PAY-1"].title == "Write done.md and keep [x](y)"
    assert by_id["PAY-1"].spec_link == "ROADMAP.md#a"
    assert by_id["PAY-2"].spec_link == "https://e.com/s"


@pytest.mark.parametrize("cell", ["None", "none", "-", "—", "n/a"])
def test_placeholder_prerequisites_mean_none(cell):
    rows = [{"Code": "PAY-1", "Status": "Ready", "Depends On": cell},
            {"Code": "PAY-2", "Status": "Ready", "Depends On": "VIR-001, -"}]
    snap, _ = snapshot_provider.from_rows(rows, mapping(), source=BOARD,
                                          taken_at="2026-10-09T00:00:00Z")
    by_id = {i.id: i for i in snap.items}
    assert by_id["PAY-1"].prerequisites == [] and by_id["PAY-2"].prerequisites == ["VIR-001"]


# --- one rows contract for every tool -------------------------------------------------

FIXTURES = Path(PLUGIN_ROOT) / "scripts" / "fixtures"
#: What every tool's rows must import to, whatever the tool called its columns.
EXPECTED = {"ABC-3": (base.COMPLETED, 1, "s", []),
            "ABC-7": (base.IN_FLIGHT, 2, "m", ["ABC-3"]),
            "ABC-9": (base.QUEUED, 3, "l", ["ABC-7"])}


def _import_tool_rows(name, field_mappings, status_mappings):
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    mapped = mapping_mod.Mapping.from_policy({"fieldMappings": field_mappings,
                                              "statusMappings": status_mappings})
    snap, _ = snapshot_provider.from_rows(data["rows"], mapped, source="example:register/1",
                                          taken_at=data["takenAt"])
    return {i.id: (i.status, i.sequence, i.effort, i.prerequisites) for i in snap.items}


def test_rows_written_from_a_database_read_import_through_the_mappings():
    got = _import_tool_rows(
        "rows_from_a_database_read.json",
        {"id": "Item ID", "title": "Name", "status": "Status", "sequence": "Sequence",
         "effort": "Effort", "prerequisites": "Depends On"},
        {"queued": ["Not started"], "in-flight": ["In progress"], "completed": ["Done"]})
    assert got == EXPECTED


def test_rows_written_from_an_issue_tracker_read_import_through_the_mappings():
    got = _import_tool_rows(
        "rows_from_an_issue_tracker_read.json",
        {"id": "Key", "title": "Title", "status": "State", "sequence": "Order",
         "effort": "Size", "prerequisites": "Blocked By"},
        {"queued": ["Todo"], "in-flight": ["In Progress"], "completed": ["Done"]})
    assert got == EXPECTED


def test_every_refresh_instruction_names_the_rows_form():
    """Each skill that names the snapshot import, and the contract, name the rows form."""
    root = Path(PLUGIN_ROOT)
    places = [root / "references" / "registry-contract.md"] + [
        root / "skills" / name / "SKILL.md"
        for name in ("dispatch-kickoff", "dispatch-closeout", "roadmap-review")]
    for path in places:
        text = " ".join(path.read_text(encoding="utf-8").split())
        assert "--import <rows.json>" in text, path
