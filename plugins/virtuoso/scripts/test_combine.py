"""Combining roadmap items into one epic run (1.12.0).

1.11 let ``/epic`` charter only one item a review had marked ``Path: epic``. The run
that worked combined several items already specified and placed, none epic-scale
alone, serialized where they shared a file. ``virtuoso_registry combine`` is the
mechanical half of deciding whether a set combines: membership, prerequisites, files,
the serial order and the lanes.
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
from tools.governance import combine as combine_mod

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")

HEADER = ("id,title,sequence,status,written_status,prerequisites,effort,lane,group,spec_link,"
          "branch,started,completed,evidence,description,notes\n")
REGISTER = HEADER + (
    "PAY-BASE,Payments base,5,Completed,Full Spec,,S,payments,,,,,2026-09-01,,,\n"
    "PAY-LOG,Payment telemetry,11,Queued,Full Spec,PAY-BASE,M,payments,,,,,,,,\n"
    "PAY-RETRY,Retry worker,12,Queued,Full Spec,,M,payments,,,,,,,,\n"
    "PAY-REFUND,Refund rule,13,Queued,Full Spec,,S,payments,,,,,,,,\n"
    "PAY-FIX,Fixture custody,14,Queued,Full Spec,,S,data,,,,,,,,\n"
    "PAY-STUB,Stub thing,15,Queued,Stub,,S,payments,,,,,,,,\n"
    "PAY-OPEN,Open prerequisite,16,Queued,Full Spec,,S,payments,,,,,,,,\n"
    "PAY-HALT,Blocked thing,17,Blocked,Full Spec,,S,payments,,,,,,,,\n"
    "PAY-RUN,Running thing,18,In Progress,Full Spec,,S,payments,,,,,,,,\n"
    "PAY-BIG,Epic-scale thing,19,Queued,Full Spec,,XL,payments,,,,,,,,\n"
)

ROADMAP = """# Shop — Roadmap

## Active & Remaining Work

#### PAY-LOG — Payment telemetry
- **What:** telemetry
- **Path:** dispatch

##### Implementation detail
- **Edit sites:** `src/payments/gateway.py:120-180` (the tick loop), `src/payments/telemetry.py`
- **Tests:** `tests/test_telemetry.py::test_emits`
- **Staging plan:** `src/payments/gateway.py`, `tests/test_telemetry.py`

#### PAY-RETRY — Retry worker
##### Implementation detail
- **Edit sites:**
    - `gateway.py` — the carrier hook
    - src/payments/retry.py
- **Staging plan:** explicit paths, per policy.git

#### PAY-REFUND — Refund rule
##### Implementation detail
- **Edit sites:** `src/rules/refund.py`

#### PAY-FIX — Fixture custody
##### Implementation detail
- **Edit sites:** `data/fixtures/`

#### PAY-OPEN — Open prerequisite
- **Edit sites:** `src/open.py`

#### PAY-HALT — Blocked thing
- **Edit sites:** `src/halt.py`

#### PAY-RUN — Running thing
- **Edit sites:** `src/run.py`

#### PAY-BIG — Epic-scale thing
- **Path:** epic — a quarter's worth of payments work
- **Edit sites:** `src/big.py`
"""


def run(*args):
    return subprocess.run([sys.executable, REGISTRY_CLI, *args], capture_output=True,
                          text=True, encoding="utf-8", env=dict(os.environ))


def layout(root):
    return json.loads((root / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8"))


def role_path(root, role):
    return root.joinpath(*layout(root)["roles"][role]["path"].split("/"))


@pytest.fixture
def game(project):
    created = subprocess.run([sys.executable, PREFLIGHT, "--root", str(project), "--mode",
                              "create", "--authorize"], capture_output=True, text=True,
                             encoding="utf-8")
    assert created.returncode == 0, created.stdout + created.stderr
    role_path(project, "workRegister").write_text(REGISTER, encoding="utf-8", newline="\n")
    role_path(project, "roadmap").write_text(ROADMAP, encoding="utf-8", newline="\n")
    return project


def combine(root, *args):
    completed = run("--root", str(root), "--actor", "epic", "combine", *args, "--json")
    assert completed.returncode in (0, 1), completed.stderr
    return completed.returncode, json.loads(completed.stdout)


def codes(payload, severity="error"):
    return sorted({f["code"] for f in payload["findings"] if f["severity"] == severity})


# --- reading a specification ---------------------------------------------------------


def test_a_field_carries_its_indented_continuation_and_stops_at_the_next():
    lines = ROADMAP.splitlines()
    section = lines[lines.index("#### PAY-RETRY — Retry worker"):]
    text = combine_mod.field_text(section, "edit sites")
    assert "gateway.py" in text and "src/payments/retry.py" in text
    assert "Staging" not in text
    assert combine_mod.field_text(section, "staging plan") == "explicit paths, per policy.git"
    assert combine_mod.field_text(section, "nonexistent") is None


@pytest.mark.parametrize("text, expected", [
    ("`src/a.py:12-40`, `src/b.py#L3`", ["src/a.py", "src/b.py"]),
    ("`tests/test_x.py::test_y`", ["tests/test_x.py"]),
    ("`gateway.py` and src/payments/retry.py", ["gateway.py", "src/payments/retry.py"]),
    ("`data/fixtures/`", ["data/fixtures/"]),
    ("`.\\src\\win.py`", ["src/win.py"]),
    ("run `pytest -q` then call `run_tick()` in `v1.2`", []),
    ("see `https://example.com/a/b.py`", []),
    ("explicit paths, per policy.git", []),
])
def test_paths_in_a_field(text, expected):
    assert combine_mod.paths_in(text) == expected


def test_a_shared_file_is_matched_by_its_tail_and_a_directory_holds_its_files():
    assert combine_mod._same_file("gateway.py", "src/payments/gateway.py")
    assert combine_mod._same_file("data/fixtures/", "data/fixtures/pins.json")
    assert not combine_mod._same_file("core.py", "src/payments/gateway.py")
    assert not combine_mod._same_file("src/a.py", "src/b.py")


def test_the_charter_frontmatter_names_the_items_and_the_status():
    single = "---\nepic: x\nitem: PAY-BIG   # the item\nstatus: active\n---\n# Charter\n"
    assert combine_mod.charter_items(single) == (["PAY-BIG"], "active")
    combined = "---\nepic: y\nitems: [PAY-LOG, PAY-RETRY]\nstatus: complete\n---\n"
    assert combine_mod.charter_items(combined) == (["PAY-LOG", "PAY-RETRY"], "complete")
    template = "---\nitem: [ITEM-ID]   # placeholder\n---\n"
    assert combine_mod.charter_items(template) == ([], "")
    block = "---\nepic: z\nitems:\n  - PAY-LOG   # first\n  - PAY-RETRY\nstatus: active\n---\n"
    assert combine_mod.charter_items(block) == (["PAY-LOG", "PAY-RETRY"], "active")


# --- the command -----------------------------------------------------------------------


def test_a_batch_serializes_shared_files_and_splits_the_rest_into_lanes(game):
    """Payment telemetry and the retry worker both edit gateway.py, so the worker
    runs after the telemetry; the refund rule and fixture custody touch nothing
    either does, so each has a lane of its own."""
    code, payload = combine(game, "--items", "PAY-REFUND", "PAY-RETRY", "PAY-LOG", "PAY-FIX")
    assert code == 0 and payload["combinable"] is True, payload["findings"]
    assert payload["order"] == ["PAY-LOG", "PAY-RETRY", "PAY-REFUND", "PAY-FIX"]
    assert payload["lanes"] == [["PAY-LOG", "PAY-RETRY"], ["PAY-REFUND"], ["PAY-FIX"]]
    assert {"before": "PAY-LOG", "after": "PAY-RETRY",
            "why": "shared files: src/payments/gateway.py"} in payload["edges"]
    assert payload["effort"] == {"computable": True, "points": 8.0,
                                 "scale": "the default t-shirt scale"}
    cal = next(i for i in payload["items"] if i["id"] == "PAY-LOG")
    assert cal["files"] == ["src/payments/gateway.py", "src/payments/telemetry.py",
                            "tests/test_telemetry.py"]
    assert cal["spec"].endswith("Roadmap.md#PAY-LOG")


def test_the_text_report_leads_with_the_verdict_and_names_every_edge(game):
    completed = run("--root", str(game), "combine", "--items", "PAY-LOG,PAY-RETRY")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("combination: COMBINABLE (2 item(s), 1 lane(s))")
    assert "1. Payment telemetry (PAY-LOG)" in completed.stdout
    assert "PAY-LOG before PAY-RETRY — shared files: src/payments/gateway.py" in completed.stdout


def test_a_prerequisite_in_the_set_orders_it_whatever_the_sequence(game):
    register = REGISTER.replace("PAY-LOG,Payment telemetry,11,Queued,Full Spec,PAY-BASE",
                                "PAY-LOG,Payment telemetry,11,Queued,Full Spec,PAY-REFUND")
    role_path(game, "workRegister").write_text(register, encoding="utf-8", newline="\n")
    code, payload = combine(game, "--items", "PAY-LOG", "PAY-REFUND", "PAY-RETRY")
    assert code == 0, payload["findings"]
    assert payload["order"] == ["PAY-REFUND", "PAY-LOG", "PAY-RETRY"]
    assert payload["lanes"] == [["PAY-REFUND", "PAY-LOG", "PAY-RETRY"]]


def test_a_prerequisite_outside_the_set_that_is_not_done_blocks(game):
    register = REGISTER.replace("PAY-RETRY,Retry worker,12,Queued,Full Spec,,",
                                "PAY-RETRY,Retry worker,12,Queued,Full Spec,PAY-OPEN;PAY-GONE,")
    role_path(game, "workRegister").write_text(register, encoding="utf-8", newline="\n")
    code, payload = combine(game, "--items", "PAY-LOG", "PAY-RETRY")
    assert code == 1 and codes(payload) == ["combine-prerequisite-outside"]
    [finding] = payload["findings"]
    assert "PAY-OPEN (queued)" in finding["message"]
    assert "PAY-GONE (not in the register)" in finding["message"]
    code, payload = combine(game, "--items", "PAY-LOG", "PAY-RETRY", "PAY-OPEN")
    assert "combine-prerequisite-outside" in codes(payload)          # PAY-GONE still missing


@pytest.mark.parametrize("item, code_expected", [
    ("PAY-BASE", "combine-item-terminal"),
    ("PAY-STUB", "combine-item-stub"),
    ("PAY-HALT", "combine-item-blocked"),
    ("PAY-RUN", "combine-item-in-flight"),
    ("PAY-BIG", "combine-item-epic"),
    ("PAY-NOPE", "combine-item-unknown"),
])
def test_an_item_that_cannot_join_blocks_the_combination(game, item, code_expected):
    code, payload = combine(game, "--items", "PAY-LOG", item)
    assert code == 1 and code_expected in codes(payload), payload["findings"]


def test_one_item_is_not_a_combination(game):
    code, payload = combine(game, "--items", "PAY-LOG")
    assert code == 1 and codes(payload) == ["combine-single"]


def test_a_cycle_in_the_set_is_named(game):
    register = (REGISTER
                .replace("PAY-LOG,Payment telemetry,11,Queued,Full Spec,PAY-BASE",
                         "PAY-LOG,Payment telemetry,11,Queued,Full Spec,PAY-RETRY")
                .replace("PAY-RETRY,Retry worker,12,Queued,Full Spec,,",
                         "PAY-RETRY,Retry worker,12,Queued,Full Spec,PAY-LOG,"))
    role_path(game, "workRegister").write_text(register, encoding="utf-8", newline="\n")
    code, payload = combine(game, "--items", "PAY-LOG", "PAY-RETRY")
    assert code == 1 and "combine-cycle" in codes(payload)
    assert sorted(payload["order"]) == ["PAY-LOG", "PAY-RETRY"]


def test_an_item_whose_files_are_unknown_runs_serially_with_everything(game):
    roadmap = ROADMAP.replace("- **Edit sites:** `src/rules/refund.py`", "- **What:** rules")
    role_path(game, "roadmap").write_text(roadmap, encoding="utf-8", newline="\n")
    code, payload = combine(game, "--items", "PAY-REFUND", "PAY-FIX")
    assert code == 0 and codes(payload, "warning") == ["combine-files-unlisted"]
    assert payload["lanes"] == [["PAY-REFUND", "PAY-FIX"]]
    assert {"before": "PAY-REFUND", "after": "PAY-FIX",
            "why": "files unknown for PAY-REFUND"} in payload["edges"]


def test_an_unlocated_specification_is_a_warning_not_a_guess(game):
    roadmap = ROADMAP.replace("#### PAY-FIX — Fixture custody", "#### Fixture custody")
    role_path(game, "roadmap").write_text(roadmap, encoding="utf-8", newline="\n")
    code, payload = combine(game, "--items", "PAY-REFUND", "PAY-FIX")
    assert code == 0 and codes(payload, "warning") == ["combine-spec-unlocated"]
    assert len(payload["lanes"]) == 1


def test_an_item_an_active_charter_names_is_already_in_a_run(game):
    data = layout(game)
    data["roles"]["epics"] = {"path": "Virtuoso/epics", "provider": "directory",
                              "authority": "reference", "mutability": "read-write",
                              "owner": "epic", "allowedWriters": ["epic"]}
    (game / "Virtuoso" / "workspace-layout.json").write_text(json.dumps(data, indent=2),
                                                             encoding="utf-8")
    packet = game / "Virtuoso" / "epics" / "2026-09-24-payments-batch"
    packet.mkdir(parents=True)
    (packet / "charter.md").write_text(
        "---\nepic: payments-batch\nitems: [PAY-RETRY, PAY-REFUND]\nstatus: active\n---\n",
        encoding="utf-8")
    code, payload = combine(game, "--items", "PAY-LOG", "PAY-RETRY")
    assert code == 1 and codes(payload) == ["combine-item-chartered"]
    assert "2026-09-24-payments-batch" in payload["findings"][0]["message"]
    done = REGISTER.replace("PAY-LOG,Payment telemetry,11,Queued",
                            "PAY-LOG,Payment telemetry,11,Done")
    role_path(game, "workRegister").write_text(done, encoding="utf-8", newline="\n")
    head = json.loads(run("--root", str(game), "next", "--json").stdout)
    assert head["item"]["id"] == "PAY-RETRY"
    assert head["inEpicPacket"] == "2026-09-24-payments-batch"
    assert "in epic run:   2026-09-24-payments-batch" in run("--root", str(game), "next").stdout
    role_path(game, "workRegister").write_text(REGISTER, encoding="utf-8", newline="\n")
    (packet / "charter.md").write_text(
        "---\nepic: payments-batch\nitems: [PAY-RETRY, PAY-REFUND]\nstatus: complete\n---\n",
        encoding="utf-8")
    code, payload = combine(game, "--items", "PAY-LOG", "PAY-RETRY")
    assert code == 0, payload["findings"]


def test_a_lane_and_a_range_select_the_active_items_between(game):
    code, payload = combine(game, "--lane", "Payments", "--from", "11", "--to", "13")
    assert code == 0, payload["findings"]
    assert payload["order"] == ["PAY-LOG", "PAY-RETRY", "PAY-REFUND"]
    assert payload["selection"] == {"lane": "Payments", "from": 11, "to": 13}


def test_an_empty_lane_selection_blocks(game):
    code, payload = combine(game, "--lane", "nowhere")
    assert code == 1 and codes(payload) == ["combine-selection-empty"]


def test_a_stale_snapshot_blocks_the_combination(project):
    (project / "Virtuoso").mkdir()
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=38)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    items = [{"id": i, "title": i, "status": "queued", "written_status": "full-spec",
              "sequence": n} for n, i in enumerate(("A-1", "A-2"), start=1)]
    (project / "Virtuoso" / "snap.json").write_text(
        json.dumps({"takenAt": old, "items": items}), encoding="utf-8")
    (project / "Virtuoso" / "workspace-layout.json").write_text(json.dumps({
        "schemaVersion": 2, "roles": {"workRegister": {
            "path": "Virtuoso/snap.json", "provider": "snapshot", "authority": "live",
            "mutability": "read-only", "allowedWriters": [], "validation": "exists",
            "classification": "active", "origin": "generated"}}}), encoding="utf-8")
    code, payload = combine(project, "--items", "A-1", "A-2")
    assert code == 1 and "combine-snapshot-stale" in codes(payload)


@pytest.mark.parametrize("args, message", [
    (("--items", "PAY-LOG", "--lane", "payments"), "not both and not neither"),
    ((), "not both and not neither"),
    (("--items", "PAY-LOG", "PAY-RETRY", "--from", "3"), "bound a --lane selection"),
])
def test_a_malformed_selection_is_unanswerable(game, args, message):
    completed = run("--root", str(game), "combine", *args)
    assert completed.returncode == 3 and message in completed.stderr


def test_combine_writes_nothing(game):
    before = snapshot_tree(str(game))
    combine(game, "--items", "PAY-REFUND", "PAY-RETRY", "PAY-LOG", "PAY-FIX")
    run("--root", str(game), "combine", "--lane", "payments")
    assert snapshot_tree(str(game)) == before


# --- the ceremonies say so -------------------------------------------------------------


def skill(name):
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def flat(text):
    return " ".join(text.split())


def test_the_epic_skill_charters_a_combination_without_a_marker_or_a_holding_bay():
    epic = skill("epic")
    assert "#### Step 1a — One item marked `Path: epic`" in epic
    assert "#### Step 1b — A combination of roadmap items" in epic
    assert "--actor epic combine --items" in epic and "combine --lane" in epic
    for code in ("combine-item-stub", "combine-prerequisite-outside", "combine-snapshot-stale"):
        assert code in epic or code.replace("combine-item-", "-") in epic, code
    assert "needs no `Path` marker and no holding bay" in flat(epic)
    assert "[PACKET-ID]-S<n>" in epic


def test_the_charter_template_carries_the_items_of_a_combination():
    charter = (ROOT / "skills" / "epic" / "assets" / "charter.template.md").read_text(
        encoding="utf-8")
    assert "# items: [ITEM-ID, ITEM-ID, ITEM-ID]" in charter
    assert "id: [PACKET-ID]" in charter
    launch = (ROOT / "skills" / "epic" / "assets" / "launch.template.md").read_text(
        encoding="utf-8")
    assert "[PACKET-ID]-S<n>" in launch and "[ITEM-ID]-S<n>" not in launch


def test_every_ceremony_knows_an_item_in_a_combined_run():
    paths = (ROOT / "references" / "execution-paths.md").read_text(encoding="utf-8")
    assert "`/epic <ITEM-ID> <ITEM-ID> …`" in paths
    assert "A combination leaves each item's `Path` as it is." in flat(paths)
    assert "`item:` or its `items:`" in flat(skill("next-pointer"))
    assert "names (`item:` or `items:`" in flat(skill("roadmap-review"))
    assert "**Set the path of items already on the roadmap.**" in skill("roadmap-review")
    assert "## Combined epics — one run, several items" in skill("pointer-closeout")
    assert "`/epic <ITEM-ID> <ITEM-ID> …`" in skill("storyboard")
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    assert "## Combining roadmap items into one epic" in contract
    for code in combine_mod.FINDING_CODES:
        assert "`%s`" % code in contract, code
