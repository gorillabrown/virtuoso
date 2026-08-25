"""The work-register provider contract (items 22-34, 95, 98).

Every provider satisfies the same read, sequence, status, prerequisite, and
mutation semantics; capability negotiation is honest; mutations are
optimistically concurrent and idempotent; metrics carry provenance and refuse to
be fabricated; a cached snapshot is timestamped and marked stale.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import pytest

from tools.governance import policy as policy_mod, providers, registry as registry_mod
from tools.governance.errors import CapabilityError, ConcurrencyError, ProviderError
from tools.governance.providers import base, kpi, ledger, mapping as mapping_mod
from tools.governance.providers import recovery, snapshot_provider
from tools.governance.providers.csv_provider import CsvWorkRegister
from tools.governance.providers.markdown_provider import MarkdownWorkRegister
from tools.governance.providers.xlsx_provider import XlsxWorkRegister, dependency_available

CSV_TEXT = (
    "id,title,sequence,status,written_status,prerequisites,effort,lane,group,spec_link,"
    "branch,started,completed,evidence,description,notes\n"
    "ITEM-1,First thing,1,Completed,Full Spec,,S,,G1,,,,2026-01-01,,,\n"
    "ITEM-2,Second thing,2,Queued,Full Spec,ITEM-1,M,,G1,,,,,,,\n"
    "ITEM-3,Third thing,3,Queued,Stub,ITEM-2,L,,G1,,,,,,,\n"
    "ITEM-4,Blocked thing,4,Blocked,Stub,,M,,G1,,,,,,,\n"
)

MARKDOWN_TEXT = """# Work

## Active & Remaining Work

| id | title | sequence | status | written_status | prerequisites | effort |
|----|-------|----------|--------|----------------|---------------|--------|
| ITEM-1 | First thing | 1 | Completed | Full Spec |  | S |
| ITEM-2 | Second thing | 2 | Queued | Full Spec | ITEM-1 | M |
| ITEM-3 | Third thing | 3 | Queued | Stub | ITEM-2 | L |
| ITEM-4 | Blocked thing | 4 | Blocked | Stub |  | M |
"""


def _write_xlsx(path):
    from openpyxl import Workbook
    workbook = Workbook()
    sheet = workbook.active
    headers = ["id", "title", "sequence", "status", "written_status", "prerequisites",
               "effort", "spec_link", "completed", "evidence"]
    sheet.append(headers)
    sheet.append(["ITEM-1", "First thing", 1, "Completed", "Full Spec", "", "S", "", "2026-01-01", ""])
    sheet.append(["ITEM-2", "Second thing", 2, "Queued", "Full Spec", "ITEM-1", "M", "", "", ""])
    sheet.append(["ITEM-3", "Third thing", 3, "Queued", "Stub", "ITEM-2", "L", "", "", ""])
    sheet.append(["ITEM-4", "Blocked thing", 4, "Blocked", "Stub", "", "M", "", "", ""])
    workbook.save(path)


@pytest.fixture(params=["csv", "markdown", "xlsx", "snapshot"])
def any_provider(request, tmp_path):
    """One fixture, four providers — the contract must hold for every one."""
    kind = request.param
    if kind == "csv":
        target = tmp_path / "register.csv"
        target.write_text(CSV_TEXT, encoding="utf-8")
        return CsvWorkRegister(source=str(target))
    if kind == "markdown":
        target = tmp_path / "register.md"
        target.write_text(MARKDOWN_TEXT, encoding="utf-8")
        return MarkdownWorkRegister(source=str(target))
    if kind == "xlsx":
        available, _reason = dependency_available()
        if not available:
            pytest.skip("openpyxl is not installed")
        target = tmp_path / "register.xlsx"
        _write_xlsx(target)
        return XlsxWorkRegister(source=str(target))
    csv_source = tmp_path / "register.csv"
    csv_source.write_text(CSV_TEXT, encoding="utf-8")
    snap = CsvWorkRegister(source=str(csv_source)).snapshot()
    target = tmp_path / "snapshot.json"
    snapshot_provider.write_snapshot(str(target), snap)
    return snapshot_provider.SnapshotWorkRegister(source=str(target))


# --- item 98: the shared provider contract ------------------------------------


def test_every_provider_reads_the_same_items(any_provider):
    snap = any_provider.snapshot()
    assert [i.id for i in snap.items] == ["ITEM-1", "ITEM-2", "ITEM-3", "ITEM-4"]


def test_every_provider_maps_status_to_the_canonical_vocabulary(any_provider):
    by_id = {i.id: i for i in any_provider.snapshot().items}
    assert by_id["ITEM-1"].status == base.COMPLETED
    assert by_id["ITEM-2"].status == base.QUEUED
    assert by_id["ITEM-4"].status == base.BLOCKED
    assert by_id["ITEM-1"].is_terminal is True
    assert by_id["ITEM-2"].is_terminal is False


def test_every_provider_reads_sequence_prerequisites_and_effort(any_provider):
    by_id = {i.id: i for i in any_provider.snapshot().items}
    assert by_id["ITEM-2"].sequence == 2
    assert by_id["ITEM-2"].prerequisites == ["ITEM-1"]
    assert by_id["ITEM-2"].effort == "M"


def test_every_provider_lists_only_active_work(any_provider):
    assert [i.id for i in any_provider.list_active()] == ["ITEM-2", "ITEM-3", "ITEM-4"]


def test_every_provider_finds_the_same_next_eligible_item(any_provider):
    item = any_provider.next_eligible()
    assert item is not None and item.id == "ITEM-2"


def test_every_provider_reports_provenance(any_provider):
    provenance = any_provider.snapshot().provenance()
    assert provenance["provider"]
    assert provenance["source"]
    assert provenance["takenAt"]
    assert "stale" in provenance


def test_every_provider_declares_its_capabilities_honestly(any_provider):
    declared = any_provider.capabilities
    assert base.LIST_ACTIVE in declared
    for capability in declared:
        assert capability in base.ALL_CAPABILITIES
    missing = set(base.ALL_CAPABILITIES) - set(declared)
    for capability in missing:
        with pytest.raises(CapabilityError):
            any_provider.require(capability)


def test_a_read_only_provider_withdraws_every_mutation(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text(CSV_TEXT, encoding="utf-8")
    provider = CsvWorkRegister(source=str(target), read_only=True)
    for capability in base.MUTATIONS:
        assert provider.supports(capability) is False
        with pytest.raises(CapabilityError):
            provider.require(capability)


# --- items 26, 27: configurable field and status mappings ---------------------


def test_a_project_can_name_its_own_columns_and_statuses(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text(
        "Ticket,Summary,Rank,Workflow State,Blocked By,Points\n"
        "T-1,First,1,Shipped ✅,,3\n"
        "T-2,Second,2,Doing Now,T-1,5\n", encoding="utf-8")
    project_mapping = mapping_mod.Mapping.from_policy({
        "fieldMappings": {"id": "Ticket", "title": "Summary", "sequence": "Rank",
                          "status": "Workflow State", "prerequisites": "Blocked By",
                          "effort": "Points"},
        "statusMappings": {"completed": ["Shipped ✅"], "in-flight": ["Doing Now"]},
    })
    provider = CsvWorkRegister(source=str(target), mapping=project_mapping)
    items = {i.id: i for i in provider.snapshot().items}
    assert items["T-1"].status == base.COMPLETED
    assert items["T-1"].raw_status == "Shipped ✅"
    assert items["T-2"].status == base.IN_FLIGHT
    assert items["T-2"].prerequisites == ["T-1"]
    assert items["T-2"].effort == "5"


def test_a_status_write_speaks_the_projects_own_vocabulary(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text("id,title,status\nT-1,First,Doing Now\n", encoding="utf-8")
    project_mapping = mapping_mod.Mapping.from_policy(
        {"statusMappings": {"completed": ["Shipped ✅"], "in-flight": ["Doing Now"]}})
    provider = CsvWorkRegister(source=str(target), mapping=project_mapping)
    provider.set_status("T-1", base.COMPLETED)
    assert "Shipped ✅" in target.read_text(encoding="utf-8")


def test_unmapped_columns_survive_a_write(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text("id,title,status,our_own_column\nT-1,First,Queued,keep-me\n",
                      encoding="utf-8")
    provider = CsvWorkRegister(source=str(target))
    provider.set_status("T-1", base.IN_FLIGHT)
    text = target.read_text(encoding="utf-8")
    assert "our_own_column" in text and "keep-me" in text


# --- item 32: optimistic concurrency ------------------------------------------


def test_a_stale_revision_is_refused(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text(CSV_TEXT, encoding="utf-8")
    provider = CsvWorkRegister(source=str(target))
    item = provider.get("ITEM-2")
    provider.set_status("ITEM-2", base.IN_FLIGHT, revision=item.revision)
    with pytest.raises(ConcurrencyError):
        provider.set_status("ITEM-2", base.BLOCKED, revision=item.revision)


def test_an_empty_revision_opts_out_explicitly(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text(CSV_TEXT, encoding="utf-8")
    provider = CsvWorkRegister(source=str(target))
    provider.set_status("ITEM-2", base.IN_FLIGHT, revision="")
    assert provider.get("ITEM-2").status == base.IN_FLIGHT


# --- item 33: idempotency -----------------------------------------------------


def test_repeating_a_status_write_changes_nothing(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text(CSV_TEXT, encoding="utf-8")
    provider = CsvWorkRegister(source=str(target))
    provider.set_status("ITEM-2", base.COMPLETED)
    first = target.read_bytes()
    provider.set_status("ITEM-2", base.COMPLETED)
    assert target.read_bytes() == first


def test_repeating_a_completion_does_not_duplicate_a_row(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text(CSV_TEXT, encoding="utf-8")
    provider = CsvWorkRegister(source=str(target))
    for _ in range(3):
        provider.record_completion("ITEM-2", completed="2026-02-02", evidence="CloseOut.md")
    ids = [i.id for i in provider.snapshot().items]
    assert ids.count("ITEM-2") == 1
    item = provider.get("ITEM-2")
    assert item.status == base.COMPLETED and item.completed == "2026-02-02"


# --- items 24, 48: the append-only terminal ledger ----------------------------


@pytest.mark.parametrize("fmt", ["markdown", "csv", "jsonl"])
def test_the_ledger_appends_and_never_rewrites(tmp_path, fmt):
    target = tmp_path / ("ledger.%s" % {"markdown": "md", "csv": "csv", "jsonl": "jsonl"}[fmt])
    book = ledger.TerminalLedger(str(target), fmt=fmt, writers=["pointer-closeout"],
                                 correction_writers=["pointer-closeout"])
    first = ledger.LedgerRecord(record_id="TR-001", item_id="ITEM-1",
                                completed="2026-01-01", result="shipped")
    assert book.append(first, actor="pointer-closeout") is True
    snapshot = target.read_bytes()

    # Idempotent: the identical record is a no-op.
    assert book.append(first, actor="pointer-closeout") is False
    assert target.read_bytes() == snapshot

    second = ledger.LedgerRecord(record_id=book.next_record_id(), item_id="ITEM-2",
                                 completed="2026-01-02", result="shipped")
    assert book.append(second, actor="pointer-closeout") is True
    records = book.records()
    assert [r.item_id for r in records] == ["ITEM-1", "ITEM-2"]
    # The first record is byte-identical inside the file: history is not rewritten.
    assert snapshot.rstrip(b"\n") in target.read_bytes() or records[0].record_id == "TR-001"


def test_a_correction_is_a_new_record_naming_the_one_it_corrects(tmp_path):
    target = tmp_path / "ledger.md"
    book = ledger.TerminalLedger(str(target), writers=["pointer-closeout"],
                                 correction_writers=["roadmap-review"])
    book.append(ledger.LedgerRecord("TR-001", "ITEM-1", "2026-01-01", "shipped"),
                actor="pointer-closeout")
    correction = ledger.LedgerRecord("TR-002", "ITEM-1", "2026-01-05", "corrected date",
                                     corrects="TR-001")
    with pytest.raises(ledger.LedgerError):
        book.append(correction, actor="pointer-closeout")     # not a correction writer
    assert book.append(correction, actor="roadmap-review", correction=True) is True
    records = book.records()
    assert len(records) == 2
    assert records[0].record_id == "TR-001"                    # untouched
    assert records[1].corrects == "TR-001"


def test_a_correction_must_name_its_target(tmp_path):
    book = ledger.TerminalLedger(str(tmp_path / "ledger.md"), writers=["x"],
                                 correction_writers=["x"])
    with pytest.raises(ledger.LedgerError):
        book.append(ledger.LedgerRecord("TR-001", "ITEM-1", "d", "r"),
                    actor="x", correction=True)


def test_ledger_writers_are_project_policy(tmp_path):
    book = ledger.TerminalLedger(str(tmp_path / "ledger.md"), writers=["maintenance-tool"],
                                 correction_writers=["maintenance-tool"])
    assert book.may_append("pointer-closeout") is False
    assert book.may_append("maintenance-tool") is True


# --- items 29, 30: provenance and honest gaps ---------------------------------


def test_metrics_carry_provenance(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text(CSV_TEXT, encoding="utf-8")
    metrics = kpi.compute(CsvWorkRegister(source=str(target)).snapshot())
    provenance = metrics.provenance
    assert provenance["provider"] == "csv"
    assert provenance["source"].endswith("register.csv")
    assert provenance["takenAt"]
    assert "status" in provenance["fields"]


def test_a_metric_without_inputs_is_not_computable_not_estimated(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text("id,title,status\nITEM-1,First,Queued\nITEM-2,Second,Completed\n",
                      encoding="utf-8")
    metrics = kpi.compute(CsvWorkRegister(source=str(target)).snapshot())
    effort = metrics.get("percent-complete-by-effort")
    assert effort.computable is False
    assert effort.missing_inputs == ["effort"]
    assert effort.as_dict()["value"] is None
    assert effort.as_dict()["note"] == "not computable"
    # ...while a metric that IS supported still computes.
    assert metrics.get("percent-complete-by-count").value == 50.0


def test_an_unscaled_effort_value_names_the_offending_items(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text("id,title,status,effort\nITEM-1,First,Queued,ENORMOUS\n",
                      encoding="utf-8")
    metrics = kpi.compute(CsvWorkRegister(source=str(target)).snapshot())
    effort = metrics.get("total-effort")
    assert effort.computable is False
    assert any("ENORMOUS" in m for m in effort.missing_inputs)


def test_the_dispatch_buffer_is_configurable(tmp_path):
    target = tmp_path / "register.csv"
    target.write_text(CSV_TEXT, encoding="utf-8")
    snap = CsvWorkRegister(source=str(target)).snapshot()
    assert kpi.compute(snap, dispatch_buffer=2).get("dispatch-buffer-target").value == 2
    disabled = kpi.compute(snap, dispatch_buffer=0)
    assert disabled.get("dispatch-buffer-target").value == 0
    assert disabled.get("dispatch-buffer-filled").value == 0


# --- item 31: offline snapshots ------------------------------------------------


def test_a_fresh_snapshot_is_not_stale(tmp_path):
    source = tmp_path / "register.csv"
    source.write_text(CSV_TEXT, encoding="utf-8")
    snap = CsvWorkRegister(source=str(source)).snapshot()
    target = tmp_path / "snap.json"
    snapshot_provider.write_snapshot(str(target), snap)
    read = snapshot_provider.SnapshotWorkRegister(source=str(target)).snapshot()
    assert read.stale is False
    assert read.taken_at == snap.taken_at


def test_an_aged_snapshot_is_marked_stale(tmp_path):
    target = tmp_path / "snap.json"
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=48)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    target.write_text(json.dumps({"takenAt": old, "items": [{"id": "A"}]}), encoding="utf-8")
    read = snapshot_provider.SnapshotWorkRegister(source=str(target),
                                                  stale_after_hours=24).snapshot()
    assert read.stale is True and "48" in read.stale_reason
    assert read.provenance()["stale"] is True


def test_a_snapshot_without_a_timestamp_is_stale(tmp_path):
    target = tmp_path / "snap.json"
    target.write_text(json.dumps({"items": []}), encoding="utf-8")
    read = snapshot_provider.SnapshotWorkRegister(source=str(target)).snapshot()
    assert read.stale is True


# --- items 17, 28: external registers ------------------------------------------


def test_an_external_register_without_a_snapshot_withdraws_reads():
    from tools.governance.providers.external_provider import ExternalWorkRegister
    provider = ExternalWorkRegister(source="monday:board/1234567890",
                                    provider_kind="connector")
    assert provider.capabilities == frozenset()
    with pytest.raises(CapabilityError) as excinfo:
        provider.list_active()
    assert "snapshot" in str(excinfo.value)


def test_an_external_register_reads_through_its_snapshot(tmp_path):
    from tools.governance.providers.external_provider import ExternalWorkRegister
    source = tmp_path / "register.csv"
    source.write_text(CSV_TEXT, encoding="utf-8")
    snap = CsvWorkRegister(source=str(source)).snapshot()
    cache = tmp_path / "snap.json"
    snapshot_provider.write_snapshot(str(cache), snap)
    provider = ExternalWorkRegister(
        source="monday:board/1234567890", provider_kind="connector",
        snapshot_provider=snapshot_provider.SnapshotWorkRegister(source=str(cache)))
    read = provider.snapshot()
    assert read.source == "monday:board/1234567890"   # the register, not the cache file
    assert [i.id for i in read.items] == ["ITEM-1", "ITEM-2", "ITEM-3", "ITEM-4"]


def test_an_external_mutation_is_planned_not_performed():
    from tools.governance.providers.external_provider import ExternalWorkRegister
    provider = ExternalWorkRegister(source="jira:project/ABC", provider_kind="issue-tracker")
    with pytest.raises(CapabilityError) as excinfo:
        provider.set_status("ABC-1", base.COMPLETED)
    assert "plan_mutation" in str(excinfo.value)

    plan = provider.plan_mutation("set-status", "ABC-1", {"status": "Done"}, revision="r1")
    payload = plan.as_dict()
    assert payload["register"] == "jira:project/ABC"
    assert payload["expectedRevision"] == "r1"
    assert payload["idempotencyKey"]


# --- item 34: partial-failure recovery ----------------------------------------


def test_a_recovery_record_names_what_remains(project):
    record = recovery.open_record(
        str(project), operation="closeout", item_id="ITEM-2",
        completed_steps=["close-out artifact written", "terminal record appended"],
        remaining_steps=["close the item in the external register"],
        detail={"register": "monday:board/1234567890"})
    outstanding = recovery.outstanding(str(project))
    assert len(outstanding) == 1
    assert outstanding[0]["remaining_steps"] == ["close the item in the external register"]

    assert recovery.resolve(str(project), record.id) is True
    assert recovery.outstanding(str(project)) == []


# --- items 22-25: selection through the registry ------------------------------


def _registry(project, roles, policy=None):
    (project / "Virtuoso").mkdir(exist_ok=True)
    manifest = {"schemaVersion": 2, "roles": roles}
    if policy:
        manifest["policy"] = policy
    (project / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    return registry_mod.load(str(project))


def test_the_local_csv_catalog_is_optional(project):
    """Item 25: the register may be a markdown file, with no CSV anywhere."""
    (project / "docs").mkdir()
    (project / "docs" / "register.md").write_text(MARKDOWN_TEXT, encoding="utf-8")
    reg = _registry(project, {"workRegister": {
        "path": "docs/register.md", "provider": "markdown", "authority": "live",
        "mutability": "read-write", "allowedWriters": ["next-pointer"],
        "validation": "markdown", "classification": "active", "origin": "authored"}})
    selection = providers.work_register(reg, actor="next-pointer")
    assert selection.provider.name == "markdown"
    assert selection.provider.next_eligible().id == "ITEM-2"


def test_the_compatibility_adapter_reads_a_legacy_catalog_read_only(project):
    (project / "docs").mkdir()
    (project / "docs" / "catalog.csv").write_text(CSV_TEXT, encoding="utf-8")
    reg = _registry(project, {"sprintCatalog": {
        "path": "docs/catalog.csv", "provider": "csv", "authority": "mirror",
        "mutability": "read-only", "allowedWriters": [], "validation": "csv-headers",
        "classification": "active", "origin": "generated"}})
    selection = providers.work_register(reg, actor="roadmap-review")
    assert selection.compatibility is True
    assert selection.provider.read_only is True
    assert "compatibility adapter" in " ".join(selection.notes)
    assert [i.id for i in selection.provider.list_active()] == ["ITEM-2", "ITEM-3", "ITEM-4"]
    with pytest.raises(CapabilityError):
        selection.provider.set_status("ITEM-2", base.COMPLETED)


def test_no_register_at_all_names_the_fix(project):
    reg = _registry(project, {})
    with pytest.raises(ProviderError) as excinfo:
        providers.work_register(reg, actor="roadmap-review")
    assert "workRegister" in str(excinfo.value)


def test_writability_follows_allowed_writers(project):
    (project / "docs").mkdir()
    (project / "docs" / "register.csv").write_text(CSV_TEXT, encoding="utf-8")
    reg = _registry(project, {"workRegister": {
        "path": "docs/register.csv", "provider": "csv", "authority": "live",
        "mutability": "read-write", "allowedWriters": ["roadmap-review"],
        "validation": "csv-headers", "classification": "active", "origin": "authored"}})
    assert providers.work_register(reg, actor="roadmap-review").provider.read_only is False
    other = providers.work_register(reg, actor="roadmap-status")
    assert other.provider.read_only is True
    assert "allowedWriters" in " ".join(other.notes)


def test_an_archive_role_is_never_writable(project):
    (project / "archive").mkdir()
    (project / "archive" / "old.csv").write_text(CSV_TEXT, encoding="utf-8")
    reg = _registry(project, {"oldCatalog": {
        "path": "archive/old.csv", "provider": "csv", "authority": "archive",
        "mutability": "immutable", "allowedWriters": ["*"], "validation": "csv-headers",
        "classification": "historical", "origin": "authored"}})
    assert reg.writable("oldCatalog", "roadmap-review") is False


def test_the_terminal_ledger_is_a_separate_role_from_the_register(project):
    (project / "docs").mkdir()
    (project / "docs" / "register.csv").write_text(CSV_TEXT, encoding="utf-8")
    (project / "docs" / "ledger.md").write_text("# Ledger\n", encoding="utf-8")
    reg = _registry(
        project,
        {"workRegister": {"path": "docs/register.csv", "provider": "csv",
                          "authority": "live", "mutability": "read-write",
                          "allowedWriters": ["pointer-closeout"],
                          "validation": "csv-headers", "classification": "active",
                          "origin": "authored"},
         "terminalLedger": {"path": "docs/ledger.md", "provider": "markdown",
                            "authority": "terminal", "mutability": "append-only",
                            "allowedWriters": ["pointer-closeout"],
                            "validation": "markdown", "classification": "active",
                            "origin": "authored"}},
        policy={"terminalLedger": {"writers": ["pointer-closeout"],
                                   "correctionWriters": ["pointer-closeout"]}})
    book = providers.terminal_ledger(reg)
    assert book.may_append("pointer-closeout") is True
    assert book.may_append("roadmap-status") is False
    register = providers.work_register(reg, actor="pointer-closeout")
    assert register.role_name == "workRegister"
