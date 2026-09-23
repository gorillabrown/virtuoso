"""The learning loop (v1.9.0): lessons captured at close-out, applied in the next
specification and the next epic's direction.

The tests use the prefix ``LSN``; the documented default is ``SRL``. A lesson is an
append-only entry in the registered ``lessons`` role. A close-out must
record what its dispatch taught (or say why it taught nothing); a specification must
say which live lessons it applied (readiness rubric U9). ``virtuoso_registry lessons``
is the read side and ``lessons --check`` is the mechanical half of both gates.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import lessons as lessons_mod
from tools.governance import policy as policy_mod

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")

CATALOG = """# Retrospective — Lessons Learned

### LSN-001 — Verify a gate fails before trusting it passes (ARCH-2, 2026-09-10)
**Verdict:** A certifier that had never shown red was blind to setup errors.
**Evidence:** Two weeks of green runs on a gate that could not fail.
**Recommendation:** Every new gate ships with a demonstrated red run.
**Applies to:** any item that adds or changes a gate, certifier, or check
**Status:** Observation

### LSN-002 — Name the base when a continuation starts red (ARCH-3, 2026-09-12)
**Verdict:** Unnamed base-red continuations hid which failures were new.
**Recommendation:** Record the base's failing set before the change.
**Applies to:** continuations on a red base
**Status:** Observation

## Notes that are not lessons

**Status:** this line belongs to no lesson

### LSN-003 — Long jobs belong to the orchestrator (ENG-9, 2026-09-14)
**Recommendation:** The orchestrator owns jobs over 20 minutes.
**Applies to:** engine-lane calibration runs
**Status:** Observation

```markdown
### LSN-099 — an example inside a fence, not a lesson
**Status:** Observation
```

### LSN-001 — status (ARCH-4, 2026-09-20)
**Status:** Promoted -> standing rule R-7 (second occurrence in ARCH-4)

### LSN-003 — status (ENG-12, 2026-09-21)
**Status:** retired — the orchestrator was replaced
"""


def run(script, *args):
    return subprocess.run([sys.executable, script, *args], capture_output=True,
                          text=True, env=dict(os.environ))


# =============================================================================
# Parsing: one entry per id, status appended, never edited
# =============================================================================


def test_parse_reads_each_lesson_once_in_first_appearance_order():
    lessons = lessons_mod.parse(CATALOG, "LSN")
    assert [lesson.id for lesson in lessons] == ["LSN-001", "LSN-002", "LSN-003"]
    first = lessons[0]
    assert first.title == "Verify a gate fails before trusting it passes"
    assert first.source == "ARCH-2, 2026-09-10"
    assert first.applies_to == "any item that adds or changes a gate, certifier, or check"
    assert first.fields["recommendation"] == "Every new gate ships with a demonstrated red run."


def test_a_later_entry_for_the_same_id_is_its_status_record():
    by_id = {lesson.id: lesson for lesson in lessons_mod.parse(CATALOG, "LSN")}
    assert by_id["LSN-001"].history == [
        "Observation", "Promoted -> standing rule R-7 (second occurrence in ARCH-4)"]
    assert by_id["LSN-001"].live is False
    assert by_id["LSN-002"].live is True
    assert by_id["LSN-003"].status.startswith("retired")
    assert by_id["LSN-003"].live is False
    # the status record's own title never replaces the lesson's
    assert by_id["LSN-001"].title == "Verify a gate fails before trusting it passes"


def test_a_fenced_example_is_never_a_lesson():
    assert "LSN-099" not in [lesson.id for lesson in lessons_mod.parse(CATALOG, "LSN")]


def test_crlf_parses_the_same():
    crlf = CATALOG.replace("\n", "\r\n")
    assert [(lesson.id, lesson.status) for lesson in lessons_mod.parse(crlf, "LSN")] == \
        [(lesson.id, lesson.status) for lesson in lessons_mod.parse(CATALOG, "LSN")]


def test_a_field_after_an_unrelated_heading_belongs_to_no_lesson():
    by_id = {lesson.id: lesson for lesson in lessons_mod.parse(CATALOG, "LSN")}
    assert by_id["LSN-002"].history == ["Observation"]


@pytest.mark.parametrize("heading", ["### LSN-004 — Title", "## LSN-004: Title",
                                     "#### LSN-004 Title", "### LSN-004 - Title"])
def test_heading_forms(heading):
    [lesson] = lessons_mod.parse(heading + "\n**Status:** Observation\n", "LSN")
    assert (lesson.id, lesson.title) == ("LSN-004", "Title")


def test_an_entry_without_a_status_is_an_observation():
    [lesson] = lessons_mod.parse("### LSN-005 — Untracked\n**Verdict:** x\n", "LSN")
    assert lesson.status == "Observation" and lesson.live


def test_another_prefix_is_not_this_projects_lesson():
    text = "### LL-001 — Theirs\n### LSN-006 — Ours\n"
    assert [lesson.id for lesson in lessons_mod.parse(text, "LSN")] == ["LSN-006"]
    assert [lesson.id for lesson in lessons_mod.parse(text, "LL")] == ["LL-001"]


# =============================================================================
# Checking a specification (rubric U9)
# =============================================================================

LESSONS = lessons_mod.parse(CATALOG, "LSN")


def spec(body):
    return "# ITEM-7 — Add the calibration gate\n\n## Scope\nIn scope: the gate.\n\n" + body


def test_a_specification_without_the_section_fails():
    result = lessons_mod.check(spec(""), LESSONS, "LSN")
    assert result.passed is False
    assert result.findings[0]["code"] == "lessons-section-missing"


def test_a_specification_citing_every_live_lesson_passes_cleanly():
    result = lessons_mod.check(spec("## Lessons applied\n- LSN-002: the base's failing set "
                                    "is recorded in step 1.\n"), LESSONS, "LSN")
    assert result.passed is True
    assert result.cited == ["LSN-002"]
    assert result.findings == []          # LSN-001 is promoted and LSN-003 retired


def test_live_lessons_left_uncited_are_listed_for_the_author_to_confirm():
    catalog = CATALOG + ("\n### LSN-004 — Name the fixture (ARCH-4, 2026-09-20)\n"
                         "**Applies to:** fixtures shared across suites\n"
                         "**Status:** Observation\n")
    result = lessons_mod.check(spec("## Lessons applied\n- LSN-002 applied.\n"),
                               lessons_mod.parse(catalog, "LSN"), "LSN")
    assert result.passed is True                                 # information, not a failure
    [info] = result.findings
    assert info["code"] == "lessons-not-cited" and info["severity"] == "info"
    assert "LSN-004 (fixtures shared across suites)" in info["message"]


def test_no_live_lesson_applies_is_an_answer():
    result = lessons_mod.check(spec("## Lessons applied\nNo live lesson applies: the item "
                                    "adds no gate and runs on a green base.\n"), LESSONS, "LSN")
    assert result.passed is True


def test_an_empty_section_is_not_an_answer():
    result = lessons_mod.check(spec("## Lessons applied\n\n## Tests\n"), LESSONS, "LSN")
    assert result.passed is False
    assert result.findings[0]["code"] == "lessons-section-empty"


def test_an_unknown_lesson_fails():
    result = lessons_mod.check(spec("## Lessons applied\n- LSN-042 applied.\n"), LESSONS, "LSN")
    assert result.passed is False
    assert any(f["code"] == "lesson-unknown" for f in result.findings)


def test_citing_a_promoted_lesson_warns_and_names_what_it_became():
    result = lessons_mod.check(spec("## Lessons applied\n- LSN-001 applied.\n"), LESSONS, "LSN")
    assert result.passed is True
    warning = next(f for f in result.findings if f["code"] == "lesson-closed-cited")
    assert "standing rule R-7" in warning["message"]


ROADMAP = """# Roadmap

## Active & Remaining Work

### ITEM-7 — Add the calibration gate
Full spec.

#### Lessons applied
- LSN-002: record the base's failing set first.

### ITEM-8 — Tune the stall timer
Full spec with no lessons section.

## Notes
"""


def test_item_locates_an_inline_specification():
    assert lessons_mod.check(ROADMAP, LESSONS, "LSN", item="ITEM-7").passed is True
    other = lessons_mod.check(ROADMAP, LESSONS, "LSN", item="ITEM-8")
    assert other.passed is False
    assert other.findings[0]["code"] == "lessons-section-missing"      # ITEM-7's does not count


def test_an_item_the_document_does_not_name_fails():
    result = lessons_mod.check(ROADMAP, LESSONS, "LSN", item="ITEM-70")
    assert result.findings[0]["code"] == "lessons-item-section-missing"


# =============================================================================
# Checking a close-out
# =============================================================================


def closeout(body):
    return "# ARCH-4 Close-Out\n\n## Sprint Brief\n**Learned:** see below\n\n" + body


def test_a_closeout_naming_a_lesson_recorded_from_its_item_passes():
    text = closeout("## Lessons\n- New: LSN-001 promoted; see the status record.\n")
    catalog = CATALOG + "\n### LSN-004 — Name the fixture (ARCH-4, 2026-09-20)\n**Status:** Observation\n"
    lessons = lessons_mod.parse(catalog, "LSN")
    assert lessons_mod.check(text + "- LSN-004\n", lessons, "LSN", item="ARCH-4",
                             closeout=True).passed is True


def test_a_closeout_naming_only_older_lessons_fails():
    result = lessons_mod.check(closeout("## Lessons\n- LSN-002 held.\n"), LESSONS, "LSN",
                               item="ARCH-4", closeout=True)
    assert result.passed is False
    assert result.findings[0]["code"] == "lessons-section-empty"


def test_no_new_lesson_with_a_reason_passes():
    result = lessons_mod.check(
        closeout("## Lessons\nNo new lesson — the dispatch followed LSN-002 exactly.\n"),
        LESSONS, "LSN", item="ARCH-4", closeout=True)
    assert result.passed is True


@pytest.mark.parametrize("line", ["No new lesson.", "No new lesson —", "Nothing learned."])
def test_no_new_lesson_needs_a_reason(line):
    result = lessons_mod.check(closeout("## Lessons\n%s\n" % line), LESSONS, "LSN",
                               item="ARCH-4", closeout=True)
    assert result.passed is False


def test_a_lesson_named_but_never_appended_fails():
    result = lessons_mod.check(closeout("## Lessons\n- LSN-050 (new)\n"), LESSONS, "LSN",
                               item="ARCH-4", closeout=True)
    assert result.passed is False
    assert any(f["code"] == "lesson-not-appended" for f in result.findings)


def test_a_closeouts_lessons_applied_heading_is_not_its_lessons_section():
    result = lessons_mod.check(closeout("## Lessons applied\n- LSN-002\n"), LESSONS, "LSN",
                               item="ARCH-4", closeout=True)
    assert result.findings[0]["code"] == "lessons-section-missing"


# =============================================================================
# Policy and the CLI
# =============================================================================


def test_the_prefix_is_documented_policy():
    assert policy_mod.is_documented("lessons.idPrefix")
    assert policy_mod.load({}).lesson_prefix == "SRL"
    assert policy_mod.load({"lessons": {"idPrefix": "LL"}}).lesson_prefix == "LL"


@pytest.mark.parametrize("prefix", ["", "1LL", "LL-", "L L", 7])
def test_an_unusable_prefix_is_refused(prefix):
    assert policy_mod.lessons_problems({"idPrefix": prefix})
    assert policy_mod.load({"lessons": {"idPrefix": prefix}}).lesson_prefix == "SRL"


@pytest.fixture
def workspace(project):
    """A created workspace whose lesson prefix is ``LSN`` — set through policy, the
    way a project sets its own."""
    assert run(PREFLIGHT, "--root", str(project), "--mode", "create",
               "--authorize").returncode == 0
    applied = run(REGISTRY_CLI, "--root", str(project), "--actor", "project-profile",
                  "policy-set", "lessons.idPrefix", "--value-json", '"LSN"', "--apply")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    return project


def lessons_file(root):
    data = json.loads((root / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8"))
    return root.joinpath(*data["roles"]["lessons"]["path"].split("/"))


def lessons_cli(root, *args):
    return run(REGISTRY_CLI, "--root", str(root), "lessons", *args)


def test_the_seeded_catalog_lists_nothing(workspace):
    completed = lessons_cli(workspace)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("0 lesson(s) in Project Documentation/")


def test_the_listing_and_the_open_filter(workspace):
    lessons_file(workspace).write_text(CATALOG, encoding="utf-8", newline="\n")
    listing = lessons_cli(workspace).stdout
    assert "3 lesson(s)" in listing and "1 live, 2 closed" in listing
    assert "LSN-001   closed" in listing
    opened = lessons_cli(workspace, "--open").stdout
    assert "LSN-002" in opened and "LSN-001" not in opened.split("\n", 1)[1]
    payload = json.loads(lessons_cli(workspace, "--json").stdout)
    assert payload["prefix"] == "LSN" and payload["live"] == 1 and payload["closed"] == 2
    assert [lesson["id"] for lesson in payload["lessons"]] == ["LSN-001", "LSN-002", "LSN-003"]


def test_the_listing_writes_nothing(workspace):
    lessons_file(workspace).write_text(CATALOG, encoding="utf-8", newline="\n")
    before = snapshot_tree(str(workspace))
    lessons_cli(workspace, "--json")
    assert snapshot_tree(str(workspace)) == before


def test_no_lessons_role_is_unanswerable(workspace):
    path = workspace / "Virtuoso" / "workspace-layout.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["roles"].pop("lessons")
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    completed = lessons_cli(workspace)
    assert completed.returncode == 3
    assert "no `lessons` role is registered" in completed.stderr


def test_the_prefix_comes_from_policy(workspace):
    lessons_file(workspace).write_text("### LL-001 — Theirs (X-1, 2026-09-01)\n",
                                       encoding="utf-8", newline="\n")
    applied = run(REGISTRY_CLI, "--root", str(workspace), "--actor", "project-profile",
                  "policy-set", "lessons.idPrefix", "--value-json", '"LL"', "--apply")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert json.loads(lessons_cli(workspace, "--json").stdout)["lessons"][0]["id"] == "LL-001"
    resolved = run(REGISTRY_CLI, "--root", str(workspace), "closeout", "--item", "X-2",
                   "--date", "2026-09-23", "--json")
    assert json.loads(resolved.stdout)["nextLessonId"] == "LL-002"


def test_check_exit_codes(workspace):
    lessons_file(workspace).write_text(CATALOG, encoding="utf-8", newline="\n")
    good = workspace / "spec.md"
    good.write_text(spec("## Lessons applied\n- LSN-002 applied in step 1.\n"),
                    encoding="utf-8")
    bad = workspace / "bad.md"
    bad.write_text(spec(""), encoding="utf-8")
    passed = lessons_cli(workspace, "--check", "spec.md")
    assert passed.returncode == 0, passed.stdout
    assert passed.stdout.startswith("U9 lessons applied: PASS")
    failed = lessons_cli(workspace, "--check", "bad.md")
    assert failed.returncode == 1
    assert "lessons-section-missing" in failed.stdout
    payload = json.loads(lessons_cli(workspace, "--check", "spec.md", "--json").stdout)
    assert payload["passed"] is True and payload["cited"] == ["LSN-002"]


def test_closeout_check_through_the_cli(workspace):
    lessons_file(workspace).write_text(
        CATALOG + "\n### LSN-004 — Name the fixture (ARCH-4, 2026-09-20)\n"
                  "**Status:** Observation\n", encoding="utf-8", newline="\n")
    report = workspace / "CloseOut.ARCH-4.md"
    report.write_text(closeout("## Lessons\n- LSN-004 — Name the fixture.\n"),
                      encoding="utf-8")
    passed = lessons_cli(workspace, "--check", str(report), "--closeout", "--item", "ARCH-4")
    assert passed.returncode == 0, passed.stdout
    assert passed.stdout.startswith("close-out lessons: PASS")
    wrong_item = lessons_cli(workspace, "--check", str(report), "--closeout",
                             "--item", "ARCH-5")
    assert wrong_item.returncode == 1


def test_a_missing_document_is_unanswerable(workspace):
    completed = lessons_cli(workspace, "--check", "nope.md")
    assert completed.returncode == 3 and "cannot be read" in completed.stderr


# =============================================================================
# The shipped templates and ceremonies honour the loop
# =============================================================================


def test_the_unfilled_closeout_template_does_not_pass_the_gate():
    """"No new lesson — [reason]" is a placeholder, not a reason."""
    template = (ROOT / "skills" / "pointer-closeout" / "assets" / "CloseOut.template.md")
    result = lessons_mod.check(template.read_text(encoding="utf-8"), LESSONS, "LSN",
                               item="SPRINT-1", closeout=True)
    assert result.passed is False


def test_the_shipped_templates_carry_the_lessons_sections():
    closeout_template = (ROOT / "skills" / "pointer-closeout" / "assets"
                         / "CloseOut.template.md").read_text(encoding="utf-8")
    assert "\n## Lessons\n" in closeout_template
    charter = (ROOT / "skills" / "epic" / "assets" / "charter.template.md").read_text(
        encoding="utf-8")
    assert "## Lessons applied" in charter
    entry = (ROOT / "skills" / "pointer-closeout" / "assets"
             / "SpecRetro.entry.template.md").read_text(encoding="utf-8")
    [lesson] = lessons_mod.parse(entry.replace("<prefix>-NNN", "LSN-001"), "LSN")
    assert lesson.status == "Observation" and "applies to" in lesson.fields


@pytest.mark.parametrize("skill, fragment", [
    ("pointer-closeout", "lessons --check"),
    ("pointer-closeout", "--closeout --item"),
    ("roadmap-review", "lessons --open"),
    ("roadmap-review", "lessons --check <spec> --item"),
    ("next-pointer", "lessons --open"),
    ("next-pointer", "lessons --check <spec> --item"),
    ("epic", "lessons --open"),
    ("mid-dispatch-decision", "lessons --open"),
])
def test_each_ceremony_reads_or_checks_the_lessons(skill, fragment):
    text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    assert fragment in text, "%s does not run `%s`" % (skill, fragment)


def test_no_shipped_file_names_a_lessons_document_by_filename():
    """The lessons document is a registered role, resolved through the registry."""
    offenders = []
    for path in list((ROOT / "skills").rglob("*.md")) + list((ROOT / "agents").glob("*.md")) \
            + list((ROOT / "references").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "LESSONS_LEARNED" in text or "Lessons_Learned.md" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_the_specification_format_the_review_ships_carries_the_section_u9_reads():
    """D.5.2's format is what authors copy. A specification shaped exactly like it
    must have the section U9 looks for, or every new specification fails at the gate."""
    text = (ROOT / "skills" / "roadmap-review" / "SKILL.md").read_text(encoding="utf-8")
    start = text.index("**D.5.2**")
    block = text[text.index("```\n", start) + 4:]
    block = block[:block.index("```")]
    result = lessons_mod.check(block, LESSONS, "LSN")
    assert result.passed is True
    assert not any(f["code"].startswith("lessons-section") for f in result.findings)
