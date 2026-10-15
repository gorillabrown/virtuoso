"""The close-out transactional crossing (items 40-46, 94, 95).

Exercises the ordered crossing the close-out ceremony performs — verify evidence,
create the artifact, append the terminal record, persist locally, close the item
in the live register, verify — and the failure between any two of those steps.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from tools.governance import providers, registry as registry_mod, schema
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
                             "allowedWriters": ["dispatch-closeout"],
                             "validation": "csv-headers", "classification": "active",
                             "origin": "authored"},
            "terminalLedger": {"path": "docs/ledger.md", "provider": "markdown",
                               "authority": "terminal", "mutability": "append-only",
                               "allowedWriters": ["dispatch-closeout"],
                               "validation": "markdown", "classification": "active",
                               "origin": "authored"},
            "closeOuts": {"path": "docs/Close-Outs", "provider": "directory",
                          "authority": "evidence", "mutability": "append-only",
                          "allowedWriters": ["dispatch-closeout"], "validation": "exists",
                          "classification": "active", "origin": "authored"},
        },
        "policy": {"terminalLedger": {"writers": ["dispatch-closeout"],
                                      "correctionWriters": ["dispatch-closeout"]}},
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
    selection = providers.work_register(reg, actor="dispatch-closeout")
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
    book.append(record, actor="dispatch-closeout")
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
    provider = providers.work_register(reg, actor="dispatch-closeout").provider
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

    provider = providers.work_register(reg, actor="dispatch-closeout").provider
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
    provider = providers.work_register(reg, actor="dispatch-closeout").provider
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


# --- the registration crossing: a specification becomes a work item -------------


def test_registering_a_new_item_is_idempotent_and_leaves_no_recovery(workspace):
    reg = registry_mod.load(str(workspace))
    provider = providers.work_register(reg, actor="dispatch-closeout").provider
    request = {"id": "ITEM-3", "title": "Third thing", "sequence": 3,
               "prerequisites": ["ITEM-2"], "effort": "S"}
    for _ in range(3):
        item = provider.create_item(request)
        assert item.status == base.QUEUED and item.written_status == base.STUB
    rows = [i for i in provider.snapshot().items if i.id == "ITEM-3"]
    assert len(rows) == 1 and rows[0].prerequisites == ["ITEM-2"]
    assert recovery.outstanding(str(workspace)) == []
    assert provider.next_eligible().id == "ITEM-1"      # the belt order is unchanged


# --- the crossing as one governed command (record-completion) ----------------------

import subprocess  # noqa: E402
import sys  # noqa: E402

REGISTRY_CLI = str(Path(__file__).resolve().parent / "virtuoso_registry.py")


def record_completion(root, *extra, actor="dispatch-closeout"):
    return subprocess.run([sys.executable, REGISTRY_CLI, "--root", str(root), "--actor", actor,
                           "record-completion", "--item", "ITEM-1", "--date", "2026-01-01",
                           "--result", "shipped", "--evidence", "CloseOut.ITEM-1.2026-01-01.md",
                           *extra], capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))


def test_record_completion_previews_without_writing(workspace):
    before = (workspace / "docs" / "ledger.md").read_bytes(), \
        (workspace / "docs" / "register.csv").read_bytes()
    completed = record_completion(workspace)
    assert completed.returncode == 0, completed.stderr
    assert "preview" in completed.stdout and "append TR-001" in completed.stdout
    assert ((workspace / "docs" / "ledger.md").read_bytes(),
            (workspace / "docs" / "register.csv").read_bytes()) == before


def test_record_completion_appends_closes_and_verifies_in_order(workspace):
    completed = record_completion(workspace, "--apply", "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["steps"] == ["append-terminal-record", "close-in-register", "verify-results"]
    reg = registry_mod.load(str(workspace))
    assert [r.item_id for r in providers.terminal_ledger(reg).records()] == ["ITEM-1"]
    assert providers.work_register(reg).provider.get("ITEM-1").status == base.COMPLETED
    assert recovery.outstanding(str(workspace)) == []
    again = record_completion(workspace, "--apply", "--json")
    assert again.returncode == 0
    assert json.loads(again.stdout)["appendRecord"] is False
    assert len(providers.terminal_ledger(registry_mod.load(str(workspace))).records()) == 1


def test_record_completion_records_the_registers_effort(workspace):
    (workspace / "docs" / "ledger.md").write_text(
        "# Terminal Ledger\n\nAppend-only.\n\n"
        "| Record | Item | Completed | Result | Evidence | Corrects | Effort |\n"
        "|--------|------|-----------|--------|----------|----------|--------|\n",
        encoding="utf-8")
    completed = record_completion(workspace, "--apply", "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["ledgerRecord"]["effort"] == "S" and result["effortRecorded"] is True


def test_record_completion_says_when_the_ledger_has_no_effort_column(workspace, tmp_path):
    second = tmp_path / "second"
    shutil.copytree(workspace, second)
    completed = record_completion(workspace, "--apply", "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout)["effortRecorded"] is False
    text = record_completion(second, "--apply")
    assert text.returncode == 0, text.stdout + text.stderr
    assert "no Effort column" in text.stdout


def test_record_completion_leaves_a_recovery_record_when_the_register_refuses(workspace):
    completed = record_completion(workspace, "--apply", "--revision", "stale-revision")
    assert completed.returncode != 0
    assert "Recovery record" in completed.stdout + completed.stderr
    [open_record] = recovery.outstanding(str(workspace))
    assert open_record["completed_steps"] == ["append-terminal-record"]
    assert open_record["remaining_steps"] == ["close-in-register", "verify-results"]


def test_record_completion_refuses_a_writer_the_ledger_does_not_allow(workspace):
    completed = record_completion(workspace, "--apply", actor="roadmap-status")
    assert completed.returncode != 0
    assert (workspace / "docs" / "ledger.md").read_text(encoding="utf-8").count("ITEM-1") == 0


# --- who may append: ordinary records and corrections, under the default policy ---------
#
# A retirement at audit (roadmap-review A.4, roadmap-status's straggler migration) is an
# ordinary terminal record: it names no record it corrects. The ledger lets only
# `policy.terminalLedger.writers` append one, and by default that is dispatch-closeout
# alone, so the retiring ceremonies route the record there. These pin that agreement.

from conftest import snapshot_tree  # noqa: E402

PREFLIGHT = str(Path(__file__).resolve().parent / "virtuoso_preflight.py")


@pytest.fixture
def default_workspace(tmp_path):
    """A workspace `create` laid down, with no terminal-ledger policy of its own, so the
    plugin's defaults decide who may append — and ITEM-1 in its register."""
    root = tmp_path / "default"
    root.mkdir()
    made = subprocess.run([sys.executable, PREFLIGHT, "--root", str(root), "--mode", "create",
                           "--authorize"], capture_output=True, text=True, encoding="utf-8")
    assert made.returncode == 0, made.stdout + made.stderr
    created = subprocess.run([sys.executable, REGISTRY_CLI, "--root", str(root), "--actor",
                              "roadmap-review", "create-item", "--item", "ITEM-1",
                              "--fields-json", '{"title": "First thing"}'],
                             capture_output=True, text=True, encoding="utf-8")
    assert created.returncode == 0, created.stdout + created.stderr
    return root


def test_the_default_policy_keeps_ordinary_records_to_the_close_out(default_workspace):
    reg = registry_mod.load(str(default_workspace))
    assert "terminalLedger" not in (reg.policy or {})          # the defaults decide
    book = providers.terminal_ledger(reg)
    assert book.may_append("dispatch-closeout") is True
    assert book.may_append("roadmap-review") is False          # a retirement is ordinary
    assert book.may_append("roadmap-review", correction=True) is True


@pytest.mark.parametrize("extra", [(), ("--apply",)], ids=["preview", "apply"])
def test_record_completion_refuses_roadmap_review_before_it_previews(default_workspace, extra):
    before = snapshot_tree(str(default_workspace))
    refused = record_completion(default_workspace, *extra, actor="roadmap-review")
    assert refused.returncode == 3
    assert "policy.terminalLedger.writers" in refused.stderr
    assert "/dispatch-closeout" in refused.stderr
    assert "preview" not in refused.stdout                     # no promise of a write
    assert snapshot_tree(str(default_workspace)) == before


def test_the_close_out_records_the_retirement_the_review_routes_to_it(default_workspace):
    routed = record_completion(default_workspace, "--apply")
    assert routed.returncode == 0, routed.stdout + routed.stderr
    reg = registry_mod.load(str(default_workspace))
    assert [r.item_id for r in providers.terminal_ledger(reg).records()] == ["ITEM-1"]
    assert providers.work_register(reg).provider.get("ITEM-1").status == base.COMPLETED


# --- --ledger-only: the terminal record alone, for an external register ---------------
#
# An external register is closed by the mutation handshake the host's connector runs; the
# ledger is local, so record-completion appends and verifies the record and nothing else.

EXTERNAL_LEDGER = (
    "# Terminal Ledger\n\nAppend-only.\n\n"
    "| Record | Item | Completed | Result | Evidence | Corrects | Estimate | Actual | Effort |\n"
    "|--------|------|-----------|--------|----------|----------|----------|--------|--------|\n")
THIS_PROJECTS_LEDGER = (Path(__file__).resolve().parents[3] / "Project Documentation"
                        / "1 governance" / "CompletedWork.Ledger.md")


@pytest.fixture
def external_workspace(project):
    (project / "Virtuoso").mkdir()
    (project / "Virtuoso" / "snap.json").write_text(json.dumps({
        "snapshotVersion": 1, "takenAt": "2099-01-01T00:00:00Z", "provider": "connector",
        "source": "monday:board/1234567890", "fields": ["id", "status", "effort", "revision"],
        "items": [{"id": "ITEM-1", "title": "First thing", "status": "queued",
                   "raw_status": "Queued", "effort": "S", "revision": "rev-1"}]}),
        encoding="utf-8")
    (project / "docs").mkdir()
    (project / "docs" / "ledger.md").write_text(EXTERNAL_LEDGER, encoding="utf-8")
    (project / "docs" / "Close-Outs").mkdir()
    manifest = {
        "schemaVersion": 2,
        "roles": {
            "workRegister": {"external": "monday:board/1234567890", "provider": "connector",
                             "authority": "live", "mutability": "read-write",
                             "allowedWriters": ["dispatch-closeout"],
                             "validation": "external", "classification": "active",
                             "origin": "authored"},
            "workRegisterSnapshot": {"path": "Virtuoso/snap.json", "provider": "snapshot",
                                     "authority": "report", "mutability": "generated",
                                     "validation": "exists", "classification": "active",
                                     "origin": "generated"},
            "terminalLedger": {"path": "docs/ledger.md", "provider": "markdown",
                               "authority": "terminal", "mutability": "append-only",
                               "allowedWriters": ["dispatch-closeout"],
                               "validation": "markdown", "classification": "active",
                               "origin": "authored"},
            "closeOuts": {"path": "docs/Close-Outs", "provider": "directory",
                          "authority": "evidence", "mutability": "append-only",
                          "allowedWriters": ["dispatch-closeout"], "validation": "exists",
                          "classification": "active", "origin": "authored"},
        },
        "policy": {"workRegister": {"snapshot": "workRegisterSnapshot"},
                   "terminalLedger": {"writers": ["dispatch-closeout"],
                                      "correctionWriters": ["dispatch-closeout"]}},
    }
    (project / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    return project


def _ledger_bytes(root):
    return (root / "docs" / "ledger.md").read_bytes()


def test_ledger_only_appends_the_record_for_an_external_register(external_workspace):
    ext = external_workspace
    snapshot = (ext / "Virtuoso" / "snap.json").read_bytes()
    completed = record_completion(ext, "--ledger-only", "--estimate", "40m", "--actual", "55m",
                                  "--apply", "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["steps"] == ["append-terminal-record", "verify-results"]
    assert result["closeInRegister"] is False and result["ledgerOnly"] is True
    record = result["ledgerRecord"]
    assert (record["effort"], record["effortEstimate"], record["effortActual"]) == \
        ("S", "40m", "55m")
    assert result["effortRecorded"] is True
    assert (ext / "Virtuoso" / "snap.json").read_bytes() == snapshot
    assert recovery.outstanding(str(ext)) == []


def test_ledger_only_is_idempotent(external_workspace):
    ext = external_workspace
    first = record_completion(ext, "--ledger-only", "--apply", "--json")
    assert first.returncode == 0, first.stdout + first.stderr
    assert json.loads(first.stdout)["appendRecord"] is True
    after_first = _ledger_bytes(ext)
    second = record_completion(ext, "--ledger-only", "--apply", "--json")
    assert second.returncode == 0, second.stdout + second.stderr
    assert json.loads(second.stdout)["appendRecord"] is False
    assert _ledger_bytes(ext) == after_first
    reg = registry_mod.load(str(ext))
    assert [r.item_id for r in providers.terminal_ledger(reg).records()] == ["ITEM-1"]


def test_ledger_only_previews_without_writing(external_workspace):
    before = _ledger_bytes(external_workspace)
    completed = record_completion(external_workspace, "--ledger-only")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "append TR-001" in completed.stdout and "not written" in completed.stdout
    assert _ledger_bytes(external_workspace) == before


def test_an_external_register_without_ledger_only_names_it(external_workspace):
    before = _ledger_bytes(external_workspace)
    completed = record_completion(external_workspace, "--apply")
    assert completed.returncode != 0
    assert "--ledger-only" in completed.stdout + completed.stderr
    assert _ledger_bytes(external_workspace) == before


def test_ledger_only_is_refused_for_a_local_register(workspace):
    register = (workspace / "docs" / "register.csv").read_bytes()
    completed = record_completion(workspace, "--ledger-only", "--apply")
    assert completed.returncode != 0
    assert "--ledger-only is for an external register" in completed.stdout + completed.stderr
    assert "ITEM-1" not in (workspace / "docs" / "ledger.md").read_text(encoding="utf-8")
    assert (workspace / "docs" / "register.csv").read_bytes() == register


def test_ledger_only_opens_a_recovery_record_when_the_record_does_not_read_back(
        external_workspace, monkeypatch):
    import virtuoso_registry
    ext = external_workspace
    monkeypatch.setattr(ledger.TerminalLedger, "append", lambda self, record, **kw: True)
    assert virtuoso_registry.main([
        "--root", str(ext), "--actor", "dispatch-closeout", "record-completion",
        "--ledger-only", "--item", "ITEM-1", "--date", "2026-01-01", "--result", "shipped",
        "--apply"]) != 0
    [rec] = recovery.outstanding(str(ext))
    assert rec["completed_steps"] == ["append-terminal-record"]
    assert rec["remaining_steps"] == ["verify-results"]
    assert rec["detail"]["ledgerOnly"] is True


def test_ledger_only_appends_to_this_projects_ledger(external_workspace):
    if not THIS_PROJECTS_LEDGER.is_file():
        pytest.skip("this project's ledger is not in this tree")
    ext = external_workspace
    original = THIS_PROJECTS_LEDGER.read_bytes()
    (ext / "docs" / "ledger.md").write_bytes(original)
    expected = ledger.TerminalLedger(str(ext / "docs" / "ledger.md")).next_record_id()
    completed = record_completion(ext, "--ledger-only", "--apply", "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["ledgerRecord"]["recordId"] == expected
    assert result["ledgerRecord"]["effort"] == "S"
    after = _ledger_bytes(ext)
    assert after.startswith(original)
    added = after[len(original):].decode("utf-8").splitlines()
    assert len(added) == 1 and added[0].endswith("| S |")


# --- the 1.15 rename: old skill names keep working for one release ------------------

#: The 1.14 name of each renamed skill, read from the alias table itself.
OLD = {new: old for old, new in schema.ACTOR_ALIASES.items()}
OLD_KICKOFF, OLD_CLOSEOUT = OLD["dispatch-kickoff"], OLD["dispatch-closeout"]


def _check(root):
    return subprocess.run([sys.executable, PREFLIGHT, "--root", str(root), "--mode", "check"],
                          capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))


def _renamed(root):
    return [f for f in registry_mod.load(str(root)).findings if f.code == "actor-renamed"]


def _rename_in_manifest(root, mapping):
    path = root / "Virtuoso" / "workspace-layout.json"
    text = path.read_text(encoding="utf-8")
    for before, after in mapping.items():
        text = text.replace('"%s"' % before, '"%s"' % after)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize("actor, names, allowed", [
    (OLD_CLOSEOUT, ["dispatch-closeout"], True),           # old actor, new list
    ("dispatch-kickoff", [OLD_KICKOFF], True),             # new actor, old list
    ("dispatch-closeout", ["dispatch-kickoff"], False),    # the aliases stay distinct
    ("anyone", ["*"], True),
    ("", ["dispatch-closeout"], False),
    (OLD_CLOSEOUT, [], False),
    (OLD_CLOSEOUT, [["nested"], OLD_CLOSEOUT], True),      # junk entries skipped
])
def test_actor_allowed_reads_both_names(actor, names, allowed):
    assert schema.actor_allowed(actor, names) is allowed


def test_old_actor_names_are_accepted_for_one_release(workspace, tmp_path):
    assert set(OLD) == {"dispatch-kickoff", "dispatch-closeout"}
    # A project the plugin creates writes only the new names, so it never warns.
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    made = subprocess.run([sys.executable, PREFLIGHT, "--root", str(fresh), "--mode", "create",
                           "--authorize"], capture_output=True, text=True, encoding="utf-8")
    assert made.returncode == 0, made.stdout + made.stderr
    assert _renamed(fresh) == []

    # A 1.14 project: its manifest names both old skills.
    _rename_in_manifest(workspace, OLD)
    path = workspace / "Virtuoso" / "workspace-layout.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["roles"]["workRegister"]["allowedWriters"].append(OLD_KICKOFF)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    assert "dispatch-closeout" not in path.read_text(encoding="utf-8")

    checked = _check(workspace)
    assert "virtuoso-status: warning" in checked.stdout, checked.stdout + checked.stderr
    [finding] = _renamed(workspace)
    assert finding.severity == "warning"
    for fragment in ("%s -> dispatch-kickoff" % OLD_KICKOFF,
                     "%s -> dispatch-closeout" % OLD_CLOSEOUT, "Fix:"):
        assert fragment in finding.message

    reg = registry_mod.load(str(workspace))
    assert reg.writable("workRegister", "dispatch-kickoff")      # a new name, an old manifest
    assert providers.terminal_ledger(reg).may_append("dispatch-closeout")
    completed = record_completion(workspace, "--apply", "--json", actor=OLD_CLOSEOUT)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert [r.item_id for r in providers.terminal_ledger(
        registry_mod.load(str(workspace))).records()] == ["ITEM-1"]

    # The control: the same project on the new names carries no rename warning.
    _rename_in_manifest(workspace, schema.ACTOR_ALIASES)
    assert _renamed(workspace) == []
    assert registry_mod.load(str(workspace)).writable("workRegister", OLD_KICKOFF)  # reverse
