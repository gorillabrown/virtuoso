"""`move-register`: the guided move of the work register between tools (HB-13)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree

SCRIPTS = Path(PLUGIN_ROOT) / "scripts"
REGISTER = "Project Documentation/2 operational/work-register.csv"
HEADER = "id,title,sequence,status,written_status\n"
OPEN = [("VIR-%03d" % n, "Open thing %d" % n, status) for n, status in
        enumerate(["Queued", "Queued", "Queued", "In Flight", "Blocked", "Queued"], start=1)]
FINISHED = [("VIR-%03d" % n, "Finished thing %d" % n, status) for n, status in
            enumerate(["Completed"] * 27 + ["Dissolved"] * 2 + ["Superseded"] * 2, start=101)]
MAPPINGS = {
    "fieldMappings": {"id": "Item ID", "title": "Name", "status": "Status",
                      "sequence": "Order"},
    "statusMappings": {"queued": ["To do"], "in-flight": ["Doing"], "blocked": ["Waiting"],
                       "completed": ["Done"]},
}


def run(script, root, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), "--root", str(root), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ))


@pytest.fixture
def moving(project):
    """A created project whose local register holds 6 open and 31 finished items."""
    created = run("virtuoso_preflight.py", project, "--mode", "create", "--authorize", "--json")
    assert created.returncode == 0, created.stdout + created.stderr
    rows = [HEADER] + ["%s,%s,%d,%s,Full Spec\n" % (i, t, n, s)
                       for n, (i, t, s) in enumerate(OPEN + FINISHED, start=1)]
    (project / REGISTER).write_text("".join(rows), encoding="utf-8")
    return project


def mappings_file(tmp_path, mappings=None):
    path = tmp_path / "mappings.json"
    path.write_text(json.dumps(mappings or MAPPINGS), encoding="utf-8")
    return str(path)


def move(root, *args):
    return run("virtuoso_registry.py", root, "move-register", *args)


def test_the_preview_counts_open_and_finished_items(moving, tmp_path):
    result = move(moving, "--to", "notion:database/abc", "--mappings", mappings_file(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "6 open items will be created; 31 finished items stay in the ledger only" \
        in result.stdout
    for item_id, title, _ in OPEN:
        assert "%-12s %s" % (item_id, title) in result.stdout
    assert "VIR-101" not in result.stdout

    data = json.loads(move(moving, "--to", "notion:database/abc", "--mappings",
                           mappings_file(tmp_path), "--json").stdout)
    assert [i["id"] for i in data["open"]] == [i for i, _, _ in OPEN]
    assert data["finished"] == 31 and data["from"] == REGISTER
    assert data["to"] == "notion:database/abc" and data["applied"] is False


def test_the_preview_writes_nothing(moving, tmp_path):
    def hashes():
        return {rel: hashlib.sha256(raw).hexdigest()
                for rel, raw in snapshot_tree(moving).items()}

    before = hashes()
    for args in (("notion:database/abc",), ("csv",), ("markdown",)):
        result = move(moving, "--to", *args, "--mappings", mappings_file(tmp_path))
        assert result.returncode in (0, 3), result.stdout + result.stderr
    assert hashes() == before


@pytest.mark.parametrize("target", ["csv", REGISTER, "./" + REGISTER])
def test_a_target_equal_to_the_current_register_is_refused(moving, tmp_path, target):
    result = move(moving, "--to", target, "--mappings", mappings_file(tmp_path))
    assert result.returncode == 3
    assert "is the current work register" in result.stderr


def test_an_open_status_with_no_word_in_the_new_mappings_is_refused(moving, tmp_path):
    mappings = json.loads(json.dumps(MAPPINGS))
    del mappings["statusMappings"]["blocked"]
    result = move(moving, "--to", "notion:database/abc", "--mappings",
                  mappings_file(tmp_path, mappings))
    assert result.returncode == 3
    assert "blocked ('Blocked'), held by VIR-005" in result.stderr


def test_mappings_without_id_title_and_status_are_refused(moving, tmp_path):
    mappings = dict(MAPPINGS, fieldMappings={"id": "Item ID"})
    result = move(moving, "--to", "notion:database/abc", "--mappings",
                  mappings_file(tmp_path, mappings))
    assert result.returncode == 3
    assert "no column for title, status" in result.stderr


# -- the plan and the confirmations ---------------------------------------------------

NOTION = "notion:database/abc"
OPEN_IDS = [i for i, _, _ in OPEN]


def outside_recovery(root):
    """Every file of the project except the recovery records."""
    return {rel: raw for rel, raw in snapshot_tree(root).items()
            if not rel.startswith("Virtuoso/.recovery/")}


def records(root):
    directory = root / "Virtuoso" / ".recovery"
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.json"))] \
        if directory.is_dir() else []


def plan_move(root, tmp_path, target=NOTION, *extra):
    return move(root, "--to", target, "--mappings", mappings_file(tmp_path), "--plan", *extra)


def applied(root, tmp_path, target=NOTION):
    result = plan_move(root, tmp_path, target, "--apply", "--actor", "virtuoso-init", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def confirm(root, record_id, item_id, provider_id):
    return move(root, "--confirm", item_id, "--provider-id", provider_id,
                "--recovery-id", record_id)


def test_the_plan_writes_nothing_without_apply(moving, tmp_path):
    before = snapshot_tree(moving)
    result = plan_move(moving, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Nothing was written" in result.stdout and '"operation": "create-item"' in result.stdout
    assert snapshot_tree(moving) == before


def test_applying_without_an_actor_is_refused(moving, tmp_path):
    result = plan_move(moving, tmp_path, NOTION, "--apply")
    assert result.returncode == 3 and "actor" in result.stderr
    assert records(moving) == []


def test_the_plan_records_the_target_mappings_approval_and_every_open_item(moving, tmp_path):
    before = outside_recovery(moving)
    data = applied(moving, tmp_path)
    [record] = records(moving)
    assert record["id"] == data["recoveryId"] and record["operation"] == "move-register"
    assert not record["resolved"]
    detail = record["detail"]
    assert detail["from"] == REGISTER and detail["to"] == NOTION and detail["external"]
    assert detail["mappings"] == MAPPINGS and detail["finished"] == 31
    assert detail["approvedAt"].endswith("Z") and detail["approvedAt"] >= record["created"]
    assert detail["actor"] == "virtuoso-init"
    assert [i["id"] for i in detail["items"]] == OPEN_IDS
    assert {i["state"] for i in detail["items"]} == {"pending"}
    assert record["remaining_steps"][:6] == ["create %s" % i for i in OPEN_IDS]
    assert outside_recovery(moving) == before          # nothing else written, no repoint


def test_external_instructions_are_in_the_create_item_handshake_shape(moving, tmp_path):
    data = applied(moving, tmp_path)
    by_id = {i["id"]: i["instruction"] for i in data["record"]["items"]}
    assert list(by_id) == OPEN_IDS
    for item_id, instruction in by_id.items():
        assert instruction["operation"] == "create-item" and instruction["register"] == NOTION
        assert instruction["itemId"] == item_id and instruction["expectedAbsent"] is True
        assert instruction["idempotencyKey"] == "create-item:%s:%s" % (NOTION, item_id)
        assert instruction["recoveryId"] == data["recoveryId"]
        assert instruction["idField"] == "Item ID"
        assert set(instruction["projectFields"]) <= {"Item ID", "Name", "Status", "Order"}
        assert instruction["projectFields"]["Item ID"] == item_id
    assert by_id["VIR-001"]["projectFields"]["Status"] == "To do"
    assert by_id["VIR-004"]["projectFields"]["Status"] == "Doing"
    assert by_id["VIR-005"]["projectFields"]["Status"] == "Waiting"
    assert by_id["VIR-002"]["projectFields"]["Name"] == "Open thing 2"
    assert by_id["VIR-002"]["projectFields"]["Order"] == 2


def test_a_move_to_csv_writes_the_rows_itself(moving, tmp_path):
    from tools.governance.providers import CsvWorkRegister, mapping

    target = "Project Documentation/2 operational/new-register.csv"
    data = applied(moving, tmp_path, target)
    assert "instruction" not in data["record"]["items"][0]
    [record] = records(moving)
    assert {i["state"] for i in record["detail"]["items"]} == {"created"}
    assert record["remaining_steps"] == [record["remaining_steps"][-1]]   # only --finish
    register = CsvWorkRegister(source=str(moving / target),
                               mapping=mapping.Mapping.from_policy(MAPPINGS))
    items = register.snapshot().items
    assert [i.id for i in items] == OPEN_IDS
    assert [i.raw_status for i in items] == ["To do"] * 3 + ["Doing", "Waiting", "To do"]
    header = (moving / target).read_text(encoding="utf-8").splitlines()[0]
    assert header.startswith("Item ID,Name,Order,Status,")

    done = finish(moving, data["recoveryId"], "--apply", "--actor", "virtuoso-init")
    assert done.returncode == 0, done.stdout + done.stderr
    data = manifest(moving)
    role = data["roles"]["workRegister"]
    assert role["path"] == target and role["provider"] == "csv" and "external" not in role
    assert data["policy"]["workRegister"]["fieldMappings"] == MAPPINGS["fieldMappings"]
    assert "workRegisterSnapshot" not in data["roles"]
    assert listed_ids(moving) == OPEN_IDS
    assert records(moving)[0]["resolved"]


def test_a_second_move_is_refused_while_one_is_open(moving, tmp_path):
    first = applied(moving, tmp_path)
    again = plan_move(moving, tmp_path, "linear:team/ENG", "--apply", "--actor", "virtuoso-init")
    assert again.returncode == 3 and first["recoveryId"] in again.stderr
    assert len(records(moving)) == 1


def test_confirm_is_idempotent_and_refuses_what_it_does_not_know(moving, tmp_path):
    record_id = applied(moving, tmp_path)["recoveryId"]
    first = confirm(moving, record_id, "VIR-001", "page-1")
    assert first.returncode == 0 and "confirmed VIR-001 as page-1" in first.stdout
    after_first = records(moving)
    second = confirm(moving, record_id, "VIR-001", "page-1")
    assert second.returncode == 0 and "already confirmed" in second.stdout
    assert records(moving) == after_first
    for item_id, provider_id, message in (
            ("VIR-001", "page-9", "already confirmed as page-1"),
            ("VIR-101", "page-2", "not one of the open items"),
            ("VIR-404", "page-2", "not one of the open items")):
        refused = confirm(moving, record_id, item_id, provider_id)
        assert refused.returncode == 3 and message in refused.stderr
    unknown = confirm(moving, "20261013T000000Z-move-register-nothing", "VIR-002", "page-2")
    assert unknown.returncode == 3 and "is not a move record" in unknown.stderr
    assert records(moving) == after_first


def test_an_interrupted_move_leaves_a_record_naming_what_was_created(moving, tmp_path):
    before = outside_recovery(moving)
    record_id = applied(moving, tmp_path)["recoveryId"]
    for n, item_id in enumerate(OPEN_IDS[:3], start=1):
        assert confirm(moving, record_id, item_id, "page-%d" % n).returncode == 0
    listing = run("virtuoso_registry.py", moving, "recovery")
    assert listing.returncode == 0
    assert "%s  move-register/%s" % (record_id, NOTION) in listing.stdout
    assert "created: VIR-001, VIR-002, VIR-003; pending: VIR-004, VIR-005, VIR-006" \
        in listing.stdout
    [record] = records(moving)
    assert not record["resolved"]
    assert [i["providerId"] for i in record["detail"]["items"]] == \
        ["page-1", "page-2", "page-3", "", "", ""]
    assert outside_recovery(moving) == before          # the manifest is byte-identical


def test_an_abandoned_move_is_closed_with_its_reason(moving, tmp_path):
    before = outside_recovery(moving)
    record_id = applied(moving, tmp_path)["recoveryId"]
    assert confirm(moving, record_id, OPEN_IDS[0], "page-1").returncode == 0
    no_reason = move(moving, "--abandon", "--recovery-id", record_id)
    assert no_reason.returncode != 0
    done = move(moving, "--abandon", "--recovery-id", record_id, "--reason", "wrong database")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "already created there: VIR-001" in done.stdout
    [record] = records(moving)
    assert record["resolved"] and record["outcome"] == "abandoned"
    assert outside_recovery(moving) == before          # the register never moved
    assert move(moving, "--abandon", "--recovery-id", record_id,
                "--reason", "again").returncode != 0


# -- the finish -----------------------------------------------------------------------

MANIFEST = "Virtuoso/workspace-layout.json"
SNAPSHOT = "Virtuoso/work-register.snapshot.json"
WORDS = {"Queued": "To do", "In Flight": "Doing", "Blocked": "Waiting"}


def manifest(root):
    return json.loads((root / MANIFEST).read_text(encoding="utf-8"))


def finish(root, record_id, *extra):
    return move(root, "--finish", "--recovery-id", record_id, *extra)


def listed_ids(root):
    listed = run("virtuoso_registry.py", root, "items", "--json")
    assert listed.returncode == 0, listed.stdout + listed.stderr
    return [i["id"] for i in json.loads(listed.stdout)["items"]]


def read_back_rows(tmp_path, rows=None):
    """The rows a session would read back from the new tool, keyed by its columns."""
    if rows is None:
        rows = [{"Item ID": i, "Name": t, "Status": WORDS[s], "Order": n}
                for n, (i, t, s) in enumerate(OPEN, start=1)]
    path = tmp_path / "read-back.json"
    path.write_text(json.dumps({"takenAt": "2026-10-13T12:00:00Z", "rows": rows}),
                    encoding="utf-8")
    return str(path)


def copied(root, tmp_path):
    """A move to the tool with every item created and confirmed; returns the record id."""
    record_id = applied(root, tmp_path)["recoveryId"]
    for n, item_id in enumerate(OPEN_IDS, start=1):
        assert confirm(root, record_id, item_id, "page-%d" % n).returncode == 0
    return record_id


def test_finish_refuses_while_an_item_is_pending(moving, tmp_path):
    record_id = applied(moving, tmp_path)["recoveryId"]
    for n, item_id in enumerate(OPEN_IDS[:5], start=1):
        assert confirm(moving, record_id, item_id, "page-%d" % n).returncode == 0
    before = snapshot_tree(moving)
    result = finish(moving, record_id, "--snapshot", read_back_rows(tmp_path), "--apply",
                    "--actor", "virtuoso-init")
    assert result.returncode == 3 and "pending item(s) VIR-006" in result.stderr
    assert snapshot_tree(moving) == before


def test_finish_repoints_only_on_a_matching_snapshot(moving, tmp_path):
    record_id = copied(moving, tmp_path)
    old_manifest = (moving / MANIFEST).read_bytes()
    rows = read_back_rows(tmp_path)
    before = snapshot_tree(moving)
    previewed = finish(moving, record_id, "--snapshot", rows)
    assert previewed.returncode == 0, previewed.stdout + previewed.stderr
    assert "Nothing was written" in previewed.stdout
    assert "VIR-004" in previewed.stdout and "in-flight -> in-flight" in previewed.stdout
    assert snapshot_tree(moving) == before

    done = finish(moving, record_id, "--snapshot", rows, "--apply", "--actor", "virtuoso-init",
                  "--json")
    assert done.returncode == 0, done.stdout + done.stderr
    result = json.loads(done.stdout)
    assert [r["id"] for r in result["table"]] == OPEN_IDS
    assert all(r["before"] == r["after"] for r in result["table"])
    data = manifest(moving)
    role = data["roles"]["workRegister"]
    assert role["external"] == NOTION and role["provider"] == "connector" and "path" not in role
    assert role["validation"] == "external"
    assert data["roles"]["workRegisterSnapshot"]["path"] == SNAPSHOT
    policy = data["policy"]["workRegister"]
    assert policy["snapshot"] == "workRegisterSnapshot"
    assert policy["fieldMappings"] == MAPPINGS["fieldMappings"]
    assert policy["statusMappings"] == MAPPINGS["statusMappings"]
    assert (moving / result["backup"] / MANIFEST).read_bytes() == old_manifest
    assert listed_ids(moving) == OPEN_IDS               # read through the new register
    [record] = records(moving)
    assert record["resolved"] and record["outcome"] == "succeeded"
    assert "no outstanding recovery records" in run("virtuoso_registry.py", moving,
                                                    "recovery").stdout


def test_a_finish_interrupted_after_the_repoint_can_be_run_again(moving, tmp_path):
    """The repoint landed but the record was never resolved: running --finish again
    leaves the manifest as it is and resolves the record."""
    record_id = copied(moving, tmp_path)
    rows = read_back_rows(tmp_path)
    first = finish(moving, record_id, "--snapshot", rows, "--apply", "--actor", "virtuoso-init")
    assert first.returncode == 0, first.stdout + first.stderr
    repointed = (moving / MANIFEST).read_bytes()
    [path] = sorted((moving / "Virtuoso" / ".recovery").glob("*.json"))
    record = json.loads(path.read_text(encoding="utf-8"))
    record.pop("outcome", None)
    record["resolved"] = None                            # as if the session died here
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    again = finish(moving, record_id, "--snapshot", rows, "--apply", "--actor", "virtuoso-init")
    assert again.returncode == 0, again.stdout + again.stderr
    assert (moving / MANIFEST).read_bytes() == repointed
    [record] = records(moving)
    assert record["resolved"] and record["outcome"] == "succeeded"


def test_a_mismatched_snapshot_changes_nothing(moving, tmp_path):
    record_id = copied(moving, tmp_path)
    rows = [{"Item ID": i, "Name": t, "Status": WORDS[s], "Order": n}
            for n, (i, t, s) in enumerate(OPEN[:5], start=1)]
    rows[1]["Status"] = "Doing"
    rows[2]["Order"] = 9
    rows.append({"Item ID": "VIR-999", "Name": "Stray", "Status": "To do", "Order": 7})
    before = snapshot_tree(moving)
    result = finish(moving, record_id, "--snapshot", read_back_rows(tmp_path, rows), "--apply",
                    "--actor", "virtuoso-init")
    assert result.returncode == 3
    for difference in ("VIR-006 is missing from the new register",
                       "VIR-999 is in the new register but not in the move",
                       "VIR-002: status in-flight, the move record says queued",
                       "VIR-003: sequence 9, the move record says 3"):
        assert difference in result.stderr
    assert snapshot_tree(moving) == before              # the manifest is byte-identical
    assert not records(moving)[0]["resolved"]


def test_history_is_byte_identical_after_a_move(moving, tmp_path):
    docs = moving / "Project Documentation"
    history = {
        "1 governance/CompletedWork.Ledger.md": None,
        "2 operational/Close-Outs/VIR-101.closeout.md": "# VIR-101 close-out\n",
        "2 operational/roadmap-reviews/2026-10-01-review.md": "# Review\n",
        "4 Outside Audits/2026-09-audit.md": "# Audit\n",
        "1 governance/Roadmap.Archive.2026-09.md": "# Archive\n",
    }
    for rel, text in history.items():
        path = docs / rel
        if text is None:
            assert path.is_file()
        else:
            path.write_text(text, encoding="utf-8")
    before = snapshot_tree(moving)

    record_id = copied(moving, tmp_path)
    done = finish(moving, record_id, "--snapshot", read_back_rows(tmp_path), "--apply",
                  "--actor", "virtuoso-init")
    assert done.returncode == 0, done.stdout + done.stderr

    after = snapshot_tree(moving)
    for rel in history:
        assert after["Project Documentation/" + rel] == before["Project Documentation/" + rel]
    allowed = (MANIFEST, SNAPSHOT, "Virtuoso/.backups/", "Virtuoso/.recovery/")
    changed = {rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel)}
    assert changed and all(rel.startswith(allowed) for rel in changed), sorted(changed)
