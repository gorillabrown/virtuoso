"""The holding bay: ad hoc plans between storyboard / write-plan and roadmap review.

A held plan is one Markdown file in the registered ``holdingBay`` role. Its trail is
its state machine: one row per move, appended through ``virtuoso_registry holding
--record`` by the ceremony that owns the move, and only when the entry carries what
the new state promises. Neither ad hoc ceremony writes the roadmap or the register;
the next roadmap review absorbs or withdraws every open entry.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import holding as holding_mod
from tools.governance import schema

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")
TEMPLATE = ROOT / "skills" / "storyboard" / "assets" / "held-plan.template.md"
MANIFEST = Path("Virtuoso") / "workspace-layout.json"

ENTRY = "2026-09-24-export-retry"

ALIGNED = """# Held Plan — Retry failed exports

<!-- virtuoso-held-plan v1 -->

- **Entry:** 2026-09-24-export-retry
- **Size:** single item
- **Origin:** storyboard 2026-09-24 — a customer escalation that cannot wait

## Trail

| Date | State | By | Note |
|---|---|---|---|

## Storyboard

### Alignment record

**Outcome:** A failed export retries three times before it is reported.

### Frames

1. **Transient failure** — Given a timeout, when an export runs, then it retries.

### Alignment verdict

<!-- guidance the parser must not read as the verdict -->
**Aligned** — 2026-09-24. The user approved: "yes, that is it".

## Plan
"""

PLAN = """
#### HB-3 — Retry failed exports

- **What:** retry the export job.

##### Lessons applied
- No live lesson applies — 0 read

```markdown
#### HB-41 — an example inside a fence, not an item
```
"""


def run(script, *args):
    return subprocess.run([sys.executable, script, *args], capture_output=True,
                          text=True, env=dict(os.environ))


def rows(*triples):
    return "".join("| %s | %s | %s | %s |\n" % t for t in triples)


def with_trail(text: str, *triples) -> str:
    return text.replace("|---|---|---|---|\n", "|---|---|---|---|\n" + rows(*triples), 1)


def parsed(text: str, name: str = ENTRY) -> holding_mod.Entry:
    return holding_mod.load("/bay/%s.md" % name, text)


def codes(entry) -> list[str]:
    return [problem["code"] for problem in entry.problems]


# =============================================================================
# Parsing
# =============================================================================


def test_parse_reads_the_header_the_verdict_and_the_items():
    entry = parsed(ALIGNED + PLAN)
    assert entry.title == "Retry failed exports"
    assert entry.size == holding_mod.SINGLE_ITEM
    assert entry.origin.startswith("storyboard 2026-09-24")
    assert entry.has_alignment_record and entry.aligned
    # The fenced example is not an item.
    assert entry.items == ["HB-3"]
    assert entry.state == holding_mod.UNRECORDED and entry.open


def test_the_template_is_not_aligned_until_someone_says_so():
    """A freshly copied template must not pass for an agreed storyboard."""
    entry = parsed(TEMPLATE.read_text(encoding="utf-8"))
    assert entry.has_alignment_record
    assert not entry.aligned


def test_the_template_parses_as_an_unrecorded_entry_once_its_header_is_filled():
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("[yyyy-mm-dd-slug]", ENTRY).replace(
        "[single item | item set (N) | epic-scale]", "item set (2)")
    entry = parsed(text)
    assert entry.size == holding_mod.ITEM_SET
    assert codes(entry) == [holding_mod.UNRECORDED_ENTRY]


def test_the_trail_decides_the_state():
    entry = parsed(with_trail(ALIGNED + PLAN,
                              ("2026-09-24", "storyboarded", "storyboard", "aligned"),
                              ("2026-09-24", "planned", "write-plan", "HB-3 passed")))
    assert entry.state == holding_mod.PLANNED
    assert entry.since == "2026-09-24"
    assert entry.problems == []


# =============================================================================
# Validation: the trail is a state machine, and each state has a price of entry
# =============================================================================


def test_an_illegal_move_is_named():
    entry = parsed(with_trail(ALIGNED + PLAN,
                              ("2026-09-24", "storyboarded", "storyboard", ""),
                              ("2026-09-24", "executed", "pointer-closeout", "close-out x")))
    assert holding_mod.TRANSITION_ILLEGAL in codes(entry)


def test_only_the_owning_ceremony_records_a_state():
    entry = parsed(with_trail(ALIGNED + PLAN,
                              ("2026-09-24", "storyboarded", "storyboard", ""),
                              ("2026-09-24", "planned", "roadmap-review", "")))
    assert holding_mod.RECORDER_WRONG in codes(entry)


def test_a_storyboard_that_is_not_aligned_is_not_held():
    text = ALIGNED.replace("**Aligned** — 2026-09-24.", "Not aligned — frame 2 open.")
    entry = parsed(with_trail(text, ("2026-09-24", "storyboarded", "storyboard", "")))
    assert holding_mod.NOT_ALIGNED in codes(entry)


def test_a_planned_entry_carries_a_plan():
    entry = parsed(with_trail(ALIGNED,
                              ("2026-09-24", "storyboarded", "storyboard", ""),
                              ("2026-09-24", "planned", "write-plan", "")))
    assert holding_mod.PLAN_MISSING in codes(entry)


def test_an_epic_scale_entry_is_never_planned_here():
    text = ALIGNED.replace("single item", "epic-scale") + PLAN
    entry = parsed(with_trail(text,
                              ("2026-09-24", "storyboarded", "storyboard", ""),
                              ("2026-09-24", "planned", "write-plan", "")))
    assert holding_mod.EPIC_PLANNED in codes(entry)


def test_the_closing_moves_say_why():
    entry = parsed(with_trail(ALIGNED + PLAN,
                              ("2026-09-24", "storyboarded", "storyboard", ""),
                              ("2026-09-25", "withdrawn", "roadmap-review", "")))
    assert holding_mod.NOTE_MISSING in codes(entry)
    assert not entry.open


def test_the_name_and_the_entry_field_agree():
    assert holding_mod.ENTRY_MISMATCH in codes(parsed(ALIGNED, "2026-09-25-export-retry"))
    assert holding_mod.NAME_INVALID in codes(parsed(ALIGNED, "Export Retry"))


def test_every_recorder_is_a_default_writer_of_the_role():
    """The code's owners and the schema's writers cannot drift apart."""
    writers = set(schema.DEFAULT_ROLES["holdingBay"]["allowedWriters"])
    for state, owners in holding_mod.RECORDED_BY.items():
        assert set(owners) <= writers, state


def test_the_role_is_opt_in():
    assert "holdingBay" not in schema.CREATE_ROLE_ORDER
    assert schema.DEFAULT_ROLES["holdingBay"]["allowedWriters"] == [
        "storyboard", "write-plan", "pointer-closeout", "roadmap-review"]


def test_provisional_identifiers_are_never_reused():
    absorbed = with_trail(ALIGNED + PLAN.replace("HB-3", "HB-7"),
                          ("2026-09-24", "storyboarded", "storyboard", ""))
    assert holding_mod.next_id([ALIGNED + PLAN, absorbed]) == "HB-42"   # the fence counts too
    assert holding_mod.next_id([]) == "HB-1"


# =============================================================================
# The CLI
# =============================================================================


@pytest.fixture
def workspace(project):
    assert run(PREFLIGHT, "--root", str(project), "--mode", "create",
               "--authorize").returncode == 0
    return project


def register(root: Path, writers=None) -> Path:
    path = root / MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    data["roles"]["holdingBay"] = {
        "path": "Virtuoso/holding", "provider": "directory", "authority": "reference",
        "mutability": "read-write", "owner": "write-plan",
        "allowedWriters": writers or list(schema.DEFAULT_ROLES["holdingBay"]["allowedWriters"])}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    bay = root / "Virtuoso" / "holding"
    bay.mkdir(parents=True, exist_ok=True)
    return bay


def record(root, entry, state, actor, *extra):
    return run(REGISTRY_CLI, "--root", str(root), "--actor", actor, "holding",
               "--record", entry, "--state", state, "--date", "2026-09-24", *extra)


def test_no_role_is_an_answer_that_names_the_fix(workspace):
    completed = run(REGISTRY_CLI, "--root", str(workspace), "holding", "--open")
    assert completed.returncode == 3
    assert "holdingBay" in completed.stderr and "allowedWriters" in completed.stderr


def test_the_read_side_writes_nothing(workspace):
    bay = register(workspace)
    (bay / ("%s.md" % ENTRY)).write_text(ALIGNED + PLAN, encoding="utf-8")
    before = snapshot_tree(str(workspace))
    listing = run(REGISTRY_CLI, "--root", str(workspace), "--json", "holding", "--open")
    assert listing.returncode == 0, listing.stderr
    payload = json.loads(listing.stdout)
    assert payload["open"] == 1 and payload["nextId"] == "HB-42"
    assert payload["entries"][0]["state"] == "unrecorded"
    run(REGISTRY_CLI, "--root", str(workspace), "holding", "--check", ENTRY)
    record(workspace, ENTRY, "storyboarded", "storyboard")          # a preview
    assert snapshot_tree(str(workspace)) == before


def test_the_whole_lifecycle_moves_only_through_its_owners(workspace):
    bay = register(workspace)
    path = bay / ("%s.md" % ENTRY)
    path.write_text(ALIGNED + PLAN, encoding="utf-8")

    moves = [("storyboarded", "storyboard", "aligned; skeleton approved"),
             ("planned", "write-plan", "HB-3 passed the rubric"),
             ("in-flight", "write-plan", "executing here under virtuoso"),
             ("executed", "pointer-closeout", "close-out: Virtuoso/closeouts/HB-3.md; complete"),
             ("absorbed", "roadmap-review", "as ADD-051, completed")]
    for state, actor, note in moves:
        completed = record(workspace, ENTRY, state, actor, "--note", note, "--apply")
        assert completed.returncode == 0, completed.stderr
    entry = holding_mod.load(str(path), path.read_text(encoding="utf-8"))
    assert [row.state for row in entry.trail] == [m[0] for m in moves]
    assert entry.problems == [] and not entry.open

    listing = run(REGISTRY_CLI, "--root", str(workspace), "--json", "holding", "--open")
    assert json.loads(listing.stdout)["entries"] == []


@pytest.mark.parametrize("state, actor, why", [
    ("planned", "write-plan", "held-transition-illegal"),        # unrecorded → planned
    ("storyboarded", "roadmap-review", "held-recorder-wrong"),
    ("storyboarded", "next-pointer", "may not write the holdingBay role"),
])
def test_a_move_the_rules_forbid_is_refused(workspace, state, actor, why):
    bay = register(workspace)
    path = bay / ("%s.md" % ENTRY)
    path.write_text(ALIGNED + PLAN, encoding="utf-8")
    before = path.read_bytes()
    completed = record(workspace, ENTRY, state, actor, "--apply")
    assert completed.returncode == 3
    assert why in completed.stderr
    assert path.read_bytes() == before


def test_a_storyboard_that_is_not_aligned_cannot_be_recorded(workspace):
    bay = register(workspace)
    path = bay / ("%s.md" % ENTRY)
    path.write_text(ALIGNED.replace("**Aligned** — 2026-09-24.", "Not aligned — open."),
                    encoding="utf-8")
    completed = record(workspace, ENTRY, "storyboarded", "storyboard", "--apply")
    assert completed.returncode == 3 and "held-not-aligned" in completed.stderr


def test_a_crlf_entry_keeps_its_line_endings(workspace):
    bay = register(workspace)
    path = bay / ("%s.md" % ENTRY)
    path.write_bytes((ALIGNED + PLAN).replace("\n", "\r\n").encode("utf-8"))
    completed = record(workspace, ENTRY, "storyboarded", "storyboard", "--apply")
    assert completed.returncode == 0, completed.stderr
    raw = path.read_bytes()
    assert b"\r\n| 2026-09-24 | storyboarded | storyboard |  |\r\n" in raw
    assert raw.count(b"\n") == raw.count(b"\r\n")


def test_check_passes_and_fails_by_exit_code(workspace):
    bay = register(workspace)
    good = bay / ("%s.md" % ENTRY)
    good.write_text(with_trail(ALIGNED + PLAN,
                               ("2026-09-24", "storyboarded", "storyboard", "aligned")),
                    encoding="utf-8")
    assert run(REGISTRY_CLI, "--root", str(workspace), "holding",
               "--check", ENTRY).returncode == 0
    bad = bay / "2026-09-25-other.md"
    bad.write_text(ALIGNED, encoding="utf-8")
    failed = run(REGISTRY_CLI, "--root", str(workspace), "holding", "--check",
                 "2026-09-25-other")
    assert failed.returncode == 1
    assert "held-entry-mismatch" in failed.stdout and "held-unrecorded" in failed.stdout


def test_the_registry_contract_documents_every_finding_and_state():
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    for code in holding_mod.FINDING_CODES:
        assert "| `%s` |" % code in contract, code
    for state in holding_mod.STATES:
        assert "| `%s` |" % state in contract, state
