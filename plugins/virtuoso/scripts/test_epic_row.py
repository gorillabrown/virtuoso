"""One row on the belt for an epic run (1.17.5).

A combination charter ran several roadmap items as one run, but left them on the belt one
by one, so `next` kept offering each as a dispatch of its own and `/next-dispatch` could
not hand over the epic's own kickoff. `epic-row` puts the run on the belt as one row: the
epic row, with the members nested under it, and `next` names the packet's launch file.
"""
from __future__ import annotations

import json

from test_combine import REGISTER, game, role_path, run  # noqa: F401  (game is a fixture)
from tools.governance import combine as combine_mod
from tools.governance.providers import mapping as mapping_mod, snapshot_provider

PACKET = "2026-11-24-payments-batch"
CHARTER = ("---\nepic: payments-batch\nid: EPIC-PAYMENTS-BATCH\n"
           "items: [PAY-LOG, PAY-RETRY]\nstatus: active\n---\n\n"
           "# Epic Charter — Payments batch\n")


def with_parent_column(text: str) -> str:
    lines = text.splitlines()
    return "\n".join([lines[0] + ",parent"] + [line + "," for line in lines[1:]]) + "\n"


def add_epics(root, charter=CHARTER, packet=PACKET):
    layout_path = root / "Virtuoso" / "workspace-layout.json"
    data = json.loads(layout_path.read_text(encoding="utf-8"))
    data["roles"]["epics"] = {"path": "Virtuoso/epics", "provider": "directory",
                              "authority": "reference", "mutability": "read-write",
                              "owner": "epic", "allowedWriters": ["epic"]}
    layout_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    directory = root / "Virtuoso" / "epics" / packet
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "charter.md").write_text(charter, encoding="utf-8")
    return directory


def epic_row(root, *extra):
    done = run("--root", str(root), "--actor", "epic", "epic-row", "--packet", PACKET,
               "--json", *extra)
    return done.returncode, json.loads(done.stdout or "{}"), done


def test_a_combination_becomes_one_row_with_its_members_nested(game):
    role_path(game, "workRegister").write_text(with_parent_column(REGISTER),
                                               encoding="utf-8", newline="\n")
    add_epics(game)
    before = role_path(game, "workRegister").read_text(encoding="utf-8")

    code, preview, _ = epic_row(game)
    assert code == 0, preview
    assert preview["kind"] == "combination" and not preview["applied"]
    assert preview["create"]["id"] == "EPIC-PAYMENTS-BATCH"
    assert preview["create"]["title"] == "Payments batch"
    assert preview["create"]["sequence"] == 11            # the earliest member's slot
    assert preview["create"]["prerequisites"] == ["PAY-BASE"]   # outside the set only
    assert preview["create"]["spec_link"] == "Virtuoso/epics/%s/charter.md" % PACKET
    assert [m["item"] for m in preview["nest"]] == ["PAY-LOG", "PAY-RETRY"]
    assert role_path(game, "workRegister").read_text(encoding="utf-8") == before

    code, applied, _ = epic_row(game, "--apply")
    assert code == 0 and applied["applied"], applied
    items = {i["id"]: i for i in json.loads(
        run("--root", str(game), "items", "--json").stdout)["items"]}
    assert items["EPIC-PAYMENTS-BATCH"]["written_status"] == "full-spec"
    assert items["PAY-LOG"]["member_of"] == "EPIC-PAYMENTS-BATCH"
    assert items["PAY-RETRY"]["member_of"] == "EPIC-PAYMENTS-BATCH"
    assert "member_of" not in items["PAY-REFUND"]

    head = json.loads(run("--root", str(game), "next", "--json").stdout)
    assert head["item"]["id"] == "EPIC-PAYMENTS-BATCH"
    assert head["inEpicPacket"] == PACKET
    assert head["epicLaunch"] == "Virtuoso/epics/%s/launch.md" % PACKET
    text = run("--root", str(game), "next").stdout
    assert "Virtuoso/epics/%s/launch.md" % PACKET in text

    code, again, _ = epic_row(game, "--apply")             # idempotent
    assert code == 0 and again["exists"] and again["create"] is None and not again["nest"]
    assert sorted(again["nested"]) == ["PAY-LOG", "PAY-RETRY"]


def test_a_stopped_run_releases_its_unfinished_members_to_the_belt(game):
    role_path(game, "workRegister").write_text(with_parent_column(REGISTER),
                                               encoding="utf-8", newline="\n")
    add_epics(game)
    assert epic_row(game, "--apply")[0] == 0
    code, preview, _ = epic_row(game, "--release")
    assert code == 0 and not preview["applied"]
    assert sorted(m["item"] for m in preview["release"]) == ["PAY-LOG", "PAY-RETRY"]
    code, released, _ = epic_row(game, "--release", "--apply")
    assert code == 0 and released["applied"]
    items = {i["id"]: i for i in json.loads(
        run("--root", str(game), "items", "--json").stdout)["items"]}
    assert "member_of" not in items["PAY-LOG"] and "member_of" not in items["PAY-RETRY"]


def test_a_register_with_nowhere_to_nest_is_refused_before_any_write(game):
    add_epics(game)
    before = role_path(game, "workRegister").read_text(encoding="utf-8")
    code, payload, _ = epic_row(game, "--apply")
    assert code == 1 and not payload["applied"]
    assert any("member_of" in p for p in payload["problems"])
    assert role_path(game, "workRegister").read_text(encoding="utf-8") == before


def test_a_member_nested_elsewhere_or_finished_blocks_the_row(game):
    done = REGISTER.replace("PAY-RETRY,Retry worker,12,Queued", "PAY-RETRY,Retry worker,12,Done")
    role_path(game, "workRegister").write_text(with_parent_column(done),
                                               encoding="utf-8", newline="\n")
    add_epics(game)
    code, payload, _ = epic_row(game)
    assert code == 1
    assert any("PAY-RETRY is already completed" in p for p in payload["problems"])


def test_a_path_epic_item_is_its_own_row(game):
    charter = ("---\nepic: big\nid: PAY-BIG\nitem: PAY-BIG\nstatus: active\n---\n\n"
               "# Epic Charter — Epic-scale thing\n")
    add_epics(game, charter=charter)
    code, payload, done = epic_row(game)
    assert code == 0 and payload["kind"] == "item" and payload["create"] is None
    assert not payload["nest"]
    text = run("--root", str(game), "--actor", "epic", "epic-row", "--packet", "PAY-BIG").stdout
    assert "nothing to write" in text


def test_the_epic_row_and_its_members_are_claimed_by_the_charter(tmp_path):
    packet = tmp_path / PACKET
    packet.mkdir()
    (packet / "charter.md").write_text(CHARTER, encoding="utf-8")
    claimed = combine_mod.active_charters(str(tmp_path))
    assert claimed == {"PAY-LOG": PACKET, "PAY-RETRY": PACKET, "EPIC-PAYMENTS-BATCH": PACKET}
    assert combine_mod.epic_members(str(tmp_path)) == {
        "PAY-LOG": "EPIC-PAYMENTS-BATCH", "PAY-RETRY": "EPIC-PAYMENTS-BATCH"}
    (packet / "charter.md").write_text(CHARTER.replace("active", "complete"), encoding="utf-8")
    assert combine_mod.active_charters(str(tmp_path)) == {}
    # A finished member still answers its dependants' prerequisites.
    assert "PAY-LOG" in combine_mod.epic_members(str(tmp_path))


def test_an_import_keeps_nested_members_and_leaves_other_subitems_out():
    rows = [
        {"Item": "EPIC-PAYMENTS-BATCH", "Name": "Payments batch", "Seq": "11",
         "Status": "Queued", "Written": "Full Spec", "Parent item": ""},
        {"Item": "PAY-LOG", "Name": "Payment telemetry", "Seq": "11", "Status": "Queued",
         "Written": "Full Spec", "Parent item": "https://example.test/page/epic"},
        {"Item": "DEC-1", "Name": "Owner decision", "Seq": "", "Status": "Queued",
         "Written": "", "Parent item": "https://example.test/page/card"},
        {"Item": "PAY-NEXT", "Name": "Depends on telemetry", "Seq": "20",
         "Status": "Queued", "Written": "Full Spec", "Depends On": "PAY-LOG",
         "Parent item": ""},
    ]
    snap, report = snapshot_provider.from_rows(
        rows, mapping_mod.Mapping(), source="board", taken_at="2026-11-24T00:00:00Z",
        members={"PAY-LOG": "EPIC-PAYMENTS-BATCH"})
    by_id = {i.id: i for i in snap.items}
    assert by_id["PAY-LOG"].member_of == "EPIC-PAYMENTS-BATCH"
    assert "DEC-1" not in by_id and [s["id"] for s in report.subitems] == ["DEC-1"]
    assert report.members == [{"id": "PAY-LOG", "title": "Payment telemetry",
                               "epicRow": "EPIC-PAYMENTS-BATCH"}]
    assert by_id["PAY-NEXT"].prerequisites == ["PAY-LOG"]   # still a known item


def test_figures_count_the_members_work_once_and_the_row_once_on_the_belt():
    from tools.governance.providers import base, kpi
    snap = base.Snapshot(items=[
        base.WorkItem(id="EPIC-X", sequence=11, status=base.QUEUED,
                      written_status=base.FULL_SPEC),
        base.WorkItem(id="A", sequence=11, status=base.QUEUED, effort="M",
                      written_status=base.FULL_SPEC, member_of="EPIC-X"),
        base.WorkItem(id="B", sequence=12, status=base.COMPLETED, effort="S",
                      written_status=base.FULL_SPEC, member_of="EPIC-X"),
        base.WorkItem(id="C", sequence=20, status=base.QUEUED, effort="S",
                      written_status=base.STUB),
    ], provider="test", source="memory", taken_at="2026-11-24T00:00:00Z",
        fields=["id", "status", "sequence", "effort", "written_status"])
    figures = {m.name: m for m in kpi.compute(snap, dispatch_buffer=2).metrics}
    assert figures["total-items"].value == 3                 # A, B, C — not the row
    assert figures["total-effort"].computable                # the row's empty effort is fine
    assert figures["dispatch-buffer-filled"].value == 1      # EPIC-X once; C is a stub


def test_next_never_names_a_member_as_the_head(tmp_path):
    from tools.governance.providers import base
    snap = base.Snapshot(items=[
        base.WorkItem(id="EPIC-X", sequence=12, status=base.QUEUED, written_status="full-spec"),
        base.WorkItem(id="A", sequence=11, status=base.QUEUED, member_of="EPIC-X"),
        base.WorkItem(id="B", sequence=13, status=base.IN_FLIGHT, member_of="EPIC-X"),
    ], provider="test", source="memory", taken_at="2026-11-24T00:00:00Z")

    class Memory(base.WorkRegisterProvider):
        capabilities = frozenset({base.NEXT_ELIGIBLE})

        def snapshot(self):
            return snap

    provider = Memory(source="memory")
    assert provider.next_eligible().id == "EPIC-X"
    assert provider.in_flight() == []
