"""The close-out transactional crossing (items 40-46, 94, 95).

Exercises the ordered crossing the close-out ceremony performs — verify evidence,
create the artifact, append the terminal record, persist locally, close the item
in the live register, verify — and the failure between any two of those steps.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tools.governance import providers, registry as registry_mod
from tools.governance.providers import base, ledger, recovery
from tools.governance.errors import ConcurrencyError

CSV_TEXT = (
    "id,title,sequence,status,written_status,prerequisites,effort,completed,evidence\n"
    "ITEM-1,First thing,1,Queued,Full Spec,,S,,\n"
    "ITEM-2,Second thing,2,Queued,Full Spec,ITEM-1,M,,\n"
)


@pytest.fixture
def workspace(project):
    (project / "Virtuoso").mkdir()
    (project / "docs").mkdir()
    (project / "docs" / "register.csv").write_text(CSV_TEXT, encoding="utf-8")
    (project / "docs" / "ledger.md").write_text(
        "# Terminal Ledger\n\nAppend-only.\n\n"
        "| Record | Item | Completed | Result | Evidence | Corrects |\n"
        "|--------|------|-----------|--------|----------|----------|\n", encoding="utf-8")
    (project / "docs" / "Close-Outs").mkdir()
    manifest = {
        "schemaVersion": 2,
        "roles": {
            "workRegister": {"path": "docs/register.csv", "provider": "csv",
                             "authority": "live", "mutability": "read-write",
                             "allowedWriters": ["pointer-closeout"],
                             "validation": "csv-headers", "classification": "active",
                             "origin": "authored"},
            "terminalLedger": {"path": "docs/ledger.md", "provider": "markdown",
                               "authority": "terminal", "mutability": "append-only",
                               "allowedWriters": ["pointer-closeout"],
                               "validation": "markdown", "classification": "active",
                               "origin": "authored"},
            "closeOuts": {"path": "docs/Close-Outs", "provider": "directory",
                          "authority": "evidence", "mutability": "append-only",
                          "allowedWriters": ["pointer-closeout"], "validation": "exists",
                          "classification": "active", "origin": "authored"},
        },
        "policy": {"terminalLedger": {"writers": ["pointer-closeout"],
                                      "correctionWriters": ["pointer-closeout"]}},
    }
    (project / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    return project


def crossing(root, item_id, *, fail_after=None):
    """Run the ordered crossing, optionally failing after a named step.

    Returns the list of completed step names. On a failure it writes a recovery
    record naming exactly what remains, then re-raises.
    """
    steps = ["verify-evidence", "create-artifact", "append-terminal-record",
             "persist-local", "close-in-register", "verify-results"]
    reg = registry_mod.load(str(root))
    selection = providers.work_register(reg, actor="pointer-closeout")
    item = selection.provider.get(item_id)
    assert item is not None
    done: list[str] = []

    def maybe_fail(step):
        if fail_after == step:
            remaining = steps[steps.index(step) + 1:]
            recovery.open_record(str(root), operation="closeout", item_id=item_id,
                                 completed_steps=list(done), remaining_steps=remaining,
                                 detail={"register": selection.provider.source})
            raise RuntimeError("simulated failure after %s" % step)

    # 1 — verify completion evidence
    done.append("verify-evidence")
    maybe_fail("verify-evidence")

    # 2 — create the close-out artifact (idempotent)
    artifact = Path(reg.resolve("closeOuts")) / ("CloseOut.%s.2026-01-01.md" % item_id)
    if not artifact.exists():
        artifact.write_text("# %s close-out\n" % item_id, encoding="utf-8")
    done.append("create-artifact")
    maybe_fail("create-artifact")

    # 3 — append the terminal record (idempotent, append-only)
    book = providers.terminal_ledger(reg)
    record = ledger.LedgerRecord(record_id=book.next_record_id(), item_id=item_id,
                                 completed="2026-01-01", result="shipped",
                                 evidence=artifact.name)
    book.append(record, actor="pointer-closeout")
    done.append("append-terminal-record")
    maybe_fail("append-terminal-record")

    # 4 — persist local governance changes (stand-in: a marker file)
    (root / "docs" / "persisted.marker").write_text(item_id + "\n", encoding="utf-8")
    done.append("persist-local")
    maybe_fail("persist-local")

    # 5 — close the item in the live register
    selection.provider.record_completion(item_id, completed="2026-01-01",
                                         evidence=artifact.name, revision=item.revision)
    done.append("close-in-register")
    maybe_fail("close-in-register")

    # 6 — verify every result
    assert artifact.exists()
    assert any(r.item_id == item_id for r in book.records())
    assert selection.provider.get(item_id).status == base.COMPLETED
    done.append("verify-results")
    return done


# --- the happy path -------------------------------------------------------------


def test_the_crossing_runs_in_order_and_verifies(workspace):
    done = crossing(workspace, "ITEM-1")
    assert done == ["verify-evidence", "create-artifact", "append-terminal-record",
                    "persist-local", "close-in-register", "verify-results"]
    assert recovery.outstanding(str(workspace)) == []


def test_local_work_precedes_the_register_close(workspace):
    """Item 44/45 ordering: local persistence happens BEFORE the register closes,
    so a failure between them leaves recoverable local state, not a lost record."""
    with pytest.raises(RuntimeError):
        crossing(workspace, "ITEM-1", fail_after="persist-local")
    reg = registry_mod.load(str(workspace))
    provider = providers.work_register(reg, actor="pointer-closeout").provider
    assert provider.get("ITEM-1").status == base.QUEUED       # register untouched
    assert (workspace / "docs" / "persisted.marker").exists()  # local work survived
    assert providers.terminal_ledger(reg).records()            # ledger already carries it


# --- item 94: failures between every pair of steps -------------------------------


@pytest.mark.parametrize("fail_after,expected_remaining", [
    ("verify-evidence", ["create-artifact", "append-terminal-record", "persist-local",
                         "close-in-register", "verify-results"]),
    ("create-artifact", ["append-terminal-record", "persist-local", "close-in-register",
                         "verify-results"]),
    ("append-terminal-record", ["persist-local", "close-in-register", "verify-results"]),
    ("persist-local", ["close-in-register", "verify-results"]),
    ("close-in-register", ["verify-results"]),
])
def test_a_partial_failure_records_exactly_what_remains(workspace, fail_after,
                                                        expected_remaining):
    with pytest.raises(RuntimeError):
        crossing(workspace, "ITEM-1", fail_after=fail_after)
    outstanding = recovery.outstanding(str(workspace))
    assert len(outstanding) == 1
    assert outstanding[0]["remaining_steps"] == expected_remaining
    assert outstanding[0]["item_id"] == "ITEM-1"
    assert outstanding[0]["operation"] == "closeout"


def test_a_recovery_record_survives_until_resolved(workspace):
    with pytest.raises(RuntimeError):
        crossing(workspace, "ITEM-1", fail_after="persist-local")
    outstanding = recovery.outstanding(str(workspace))
    record_id = outstanding[0]["id"]
    # Re-running does not silently clear it.
    crossing(workspace, "ITEM-1")
    assert [r["id"] for r in recovery.outstanding(str(workspace))] == [record_id]
    recovery.resolve(str(workspace), record_id)
    assert recovery.outstanding(str(workspace)) == []


# --- item 95: idempotency --------------------------------------------------------


def test_rerunning_the_crossing_duplicates_nothing(workspace):
    crossing(workspace, "ITEM-1")
    crossing(workspace, "ITEM-1")
    crossing(workspace, "ITEM-1")

    reg = registry_mod.load(str(workspace))
    book = providers.terminal_ledger(reg)
    assert [r.item_id for r in book.records()] == ["ITEM-1"]

    artifacts = os.listdir(reg.resolve("closeOuts"))
    assert artifacts == ["CloseOut.ITEM-1.2026-01-01.md"]

    provider = providers.work_register(reg, actor="pointer-closeout").provider
    rows = [i for i in provider.snapshot().items if i.id == "ITEM-1"]
    assert len(rows) == 1 and rows[0].status == base.COMPLETED


def test_resuming_after_a_failure_completes_without_duplicating(workspace):
    with pytest.raises(RuntimeError):
        crossing(workspace, "ITEM-1", fail_after="append-terminal-record")
    done = crossing(workspace, "ITEM-1")
    assert done[-1] == "verify-results"
    reg = registry_mod.load(str(workspace))
    assert [r.item_id for r in providers.terminal_ledger(reg).records()] == ["ITEM-1"]


# --- guard rails -----------------------------------------------------------------


def test_a_concurrent_register_change_is_refused_mid_crossing(workspace):
    reg = registry_mod.load(str(workspace))
    provider = providers.work_register(reg, actor="pointer-closeout").provider
    item = provider.get("ITEM-1")
    provider.set_status("ITEM-1", base.BLOCKED)      # somebody else moved it
    with pytest.raises(ConcurrencyError):
        provider.record_completion("ITEM-1", completed="2026-01-01",
                                   revision=item.revision)


def test_an_unauthorized_actor_cannot_append_a_terminal_record(workspace):
    reg = registry_mod.load(str(workspace))
    book = providers.terminal_ledger(reg)
    with pytest.raises(ledger.LedgerError):
        book.append(ledger.LedgerRecord("TR-001", "ITEM-1", "2026-01-01", "shipped"),
                    actor="roadmap-status")


def test_existing_terminal_history_is_never_rewritten(workspace):
    crossing(workspace, "ITEM-1")
    reg = registry_mod.load(str(workspace))
    ledger_path = Path(reg.resolve("terminalLedger"))
    before = ledger_path.read_text(encoding="utf-8")

    crossing(workspace, "ITEM-2")
    after = ledger_path.read_text(encoding="utf-8")
    assert before.rstrip("\n") in after or all(
        line in after for line in before.splitlines() if line.strip())
    assert after.count("| ITEM-1 |") == 1
