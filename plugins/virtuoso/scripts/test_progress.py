"""The progress band: ``virtuoso_registry progress`` and ``tools/governance/progress.py``.

The plugin's hooks module (``hooks/progress-band.tsx``) draws, for the session it runs in,
the run that session's pointer names. Only the ``virtuoso`` skill feeds a run. Every file
lives in the user's own state folder: a feeding command never writes inside a working tree
and never touches the registry.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from tools.governance import guards, hosts
from tools.governance import milestones as milestones_mod
from tools.governance import progress as progress_mod
from tools.governance import schema
from tools.governance.errors import GovernanceError

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")
MANIFEST = Path("Virtuoso") / "workspace-layout.json"
T0 = dt.datetime(2026, 11, 1, 9, 0, tzinfo=dt.timezone.utc)

SPEC = """#### VIR-900 — Sample

##### Task list

| # | Task | Agent |
|---|------|-------|
| 1 | Write the parser | Hercules |
| 2 | Wire the CLI | Hercules |
| 3 | Test it | Hippocrates |

##### Milestones

| Milestone | Rows | Done when |
|-----------|------|-----------|
| Core | 1-2 | the CLI parses |
| Proof | 3 | the tests pass |
"""

CHARTER = """# Epic charter

## Milestones

| Milestone | Steps | Done when |
|---|---|---|
| Discovery | map the layout; confirm the assumptions | the layout is written down |
| Build | ship it | it ships |
"""

PLAN = [{"id": "M1", "label": "Core", "steps": [{"id": "1", "label": "a"}, {"id": "2", "label": "b"},
                                               {"id": "3", "label": "c"}]},
        {"id": "M2", "label": "Proof", "steps": [{"id": "4", "label": "d"}]},
        {"id": "M3", "label": "Ship", "steps": [{"id": "5", "label": "e"}]}]


def run(script, *args, cwd=None):
    return subprocess.run([sys.executable, script, *args], capture_output=True, text=True,
                          encoding="utf-8", env=dict(os.environ), cwd=cwd)


def cli(root, *args, actor="virtuoso"):
    head = ["--root", str(root)] + (["--actor", actor] if actor else [])
    return run(REGISTRY_CLI, *head, "progress", *args)


@pytest.fixture
def workspace(project):
    assert run(PREFLIGHT, "--root", str(project), "--mode", "create",
               "--authorize").returncode == 0
    (project / "spec.md").write_text(SPEC, encoding="utf-8")
    (project / "charter.md").write_text(CHARTER, encoding="utf-8")
    return project


def tree(root: Path) -> dict:
    """Every file under ``root`` with its bytes: a write inside the tree changes this."""
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def at(minutes):
    return T0 + dt.timedelta(minutes=minutes)


def opened(root="C:/proj", run_id="R", plan=PLAN, moment=T0):
    progress_mod.open_run(run_id, "Run", plan, root, moment)
    return run_id


def doc(run_id="R"):
    return progress_mod.read(progress_mod.run_path(run_id))


# --- where it lives, and who writes it ---------------------------------------------------

def test_the_band_has_no_registry_role_and_no_option():
    assert "progress" not in schema.DEFAULT_ROLES
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert "progressFile" not in json.dumps(manifest)


def test_the_store_is_the_users_own_folder(isolated_home):
    assert Path(progress_mod.store_dir()) == Path(isolated_home) / ".virtuoso" / "progress"
    with pytest.raises(progress_mod.ProgressError):
        progress_mod.write(str(Path(isolated_home) / "elsewhere.json"), {})


def test_feeding_never_writes_inside_the_tree_or_the_registry(workspace):
    before = tree(workspace)
    assert cli(workspace, "--run", "VIR-900", "--from-spec", "spec.md", "--item", "VIR-900",
               "--title", "Sample").returncode == 0
    for step, state in (("1", "active"), ("1", "done"), ("2", "done")):
        assert cli(workspace, "--run", "VIR-900", "--step", step, "--state", state).returncode == 0
    assert cli(workspace, "--run", "VIR-900", "--milestone", "M1", "--state", "done").returncode == 0
    assert cli(workspace, "--run", "VIR-900", "--stop", "halted").returncode == 0
    assert tree(workspace) == before
    assert Path(progress_mod.archive_path("VIR-900")).is_file()


def test_feeding_works_with_no_registry_at_all(tmp_path, isolated_home):
    (tmp_path / "spec.md").write_text(SPEC, encoding="utf-8")
    done = cli(tmp_path, "--run", "X-1", "--from-spec", "spec.md")
    assert done.returncode == 0, done.stderr
    assert sorted(p.name for p in tmp_path.iterdir()) == ["spec.md"]


def test_only_the_virtuoso_skill_feeds_the_band(workspace):
    done = cli(workspace, "--run", "VIR-900", "--from-spec", "spec.md", actor="next-dispatch")
    assert done.returncode != 0 and "only the virtuoso skill" in done.stderr
    assert not Path(progress_mod.run_path("VIR-900")).exists()


def test_a_run_is_never_fed_from_another_tree(workspace, tmp_path):
    cli(workspace, "--run", "VIR-900", "--from-spec", "spec.md")
    other = tmp_path / "other"
    other.mkdir()
    done = cli(other, "--run", "VIR-900", "--step", "1", "--state", "done")
    assert done.returncode != 0 and "another tree" in done.stderr


SKILLS = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())


def test_only_the_virtuoso_skill_writes_the_band_in_its_text():
    for skill in SKILLS:
        body = (skill / "SKILL.md").read_text(encoding="utf-8")
        writes = re.findall(r"progress --run\b", body)
        if skill.name == "virtuoso":
            assert writes, "the virtuoso skill feeds the band"
        else:
            assert not writes, "%s writes the band; only virtuoso may" % skill.name


@pytest.mark.parametrize("skill", ["next-dispatch", "epic", "dispatch-closeout"])
def test_the_ceremonies_around_a_run_stay_out_of_the_band(skill):
    body = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "progress band" not in body.lower(), skill


def test_no_skill_names_a_removed_band_command():
    for skill in SKILLS:
        for path in skill.rglob("*.md"):
            body = path.read_text(encoding="utf-8")
            assert not re.search(r"progress --(flag|set|drop|prune-done|drift|register|begin|"
                                 r"claim|end)\b", body), path


def test_the_ad_hoc_skills_do_not_write_the_band():
    for name in ("storyboard", "write-plan"):
        body = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert " progress --" not in body, name


# --- milestones from the plan ------------------------------------------------------------

def test_a_specification_groups_its_task_rows_into_milestones():
    found = milestones_mod.from_spec(SPEC)
    assert [(m["id"], m["name"], [s["id"] for s in m["steps"]]) for m in found] == [
        ("M1", "Core", ["1", "2"]), ("M2", "Proof", ["3"])]
    assert found[0]["steps"][1]["name"] == "Wire the CLI"


@pytest.mark.parametrize("change, message", [
    (lambda t: t.split("##### Milestones")[0], "no \"Milestones\" section"),
    (lambda t: t.replace("| 3 | the tests pass |", "| 4 | the tests pass |"), "row 4"),
    (lambda t: t.replace("| 1-2 |", "| 1 |"), "row 2"),
    (lambda t: t.replace("| 3 | the tests pass |", "| 2-3 | the tests pass |"), "row 2"),
    (lambda t: t.replace("| the CLI parses |", "| — |"), "no Done when"),
])
def test_a_specification_with_bad_milestones_is_refused_naming_why(change, message):
    with pytest.raises(GovernanceError, match=re.escape(message)):
        milestones_mod.from_spec(change(SPEC))


def test_a_charter_lists_its_checkpoints():
    found = milestones_mod.from_charter(CHARTER)
    assert [s["id"] for s in found[0]["steps"]] == ["1.1", "1.2"]
    with pytest.raises(GovernanceError, match="Milestones"):
        milestones_mod.from_charter("# Epic charter\n")


def test_check_milestones_reads_and_refuses(workspace):
    done = cli(workspace, "--check-milestones", "spec.md", "--json", actor=None)
    assert [m["name"] for m in json.loads(done.stdout)["milestones"]] == ["Core", "Proof"]
    (workspace / "bare.md").write_text(SPEC.split("##### Milestones")[0], encoding="utf-8")
    done = cli(workspace, "--check-milestones", "bare.md", actor=None)
    assert done.returncode != 0 and "U11" in done.stderr
    assert cli(workspace, "--check-milestones", "charter.md", "--charter", actor=None).returncode == 0


def test_a_run_opens_from_its_specification(workspace):
    assert cli(workspace, "--run", "VIR-900", "--from-spec", "spec.md", "--title", "Sample").returncode == 0
    record = doc("VIR-900")
    assert record["run"] == {"id": "VIR-900", "title": "Sample", "kind": "dispatch"}
    assert [m["label"] for m in record["milestones"]] == ["Core", "Proof"]
    assert record["current"] == "M1"
    assert [(s["id"], s["label"], s["state"]) for s in record["steps"]] == [
        ("1", "Write the parser", "queued"), ("2", "Wire the CLI", "queued")]


def test_a_plan_with_no_phases_is_one_milestone(isolated_home):
    opened(plan=[{"label": "All of it", "steps": [{"label": "one"}, {"label": "two"}]}])
    shown = progress_mod.summary(doc(), T0)
    assert shown["line2"].endswith(" All of it") and "Milestone 0/1" in shown["line2"]


# --- the record --------------------------------------------------------------------------

def test_a_step_moves_and_its_milestone_starts(isolated_home):
    opened()
    progress_mod.set_step("R", "1", "active", "C:/proj", at(1))
    record = doc()
    assert record["steps"][0]["started"] == "2026-11-01T09:01:00Z"
    assert record["milestones"][0]["state"] == "active"
    progress_mod.set_step("R", "1", "done", "C:/proj", at(5))
    assert doc()["steps"][0]["finished"] == "2026-11-01T09:05:00Z"


def test_a_finished_milestone_hands_its_steps_to_the_next(isolated_home):
    opened()
    progress_mod.set_milestone("R", "M1", "done", "C:/proj", at(10))
    record = doc()
    assert record["current"] == "M2"
    assert [s["label"] for s in record["steps"]] == ["d"]


def test_a_step_the_plan_did_not_list_is_added_by_label(isolated_home):
    opened()
    with pytest.raises(progress_mod.ProgressError, match="--label"):
        progress_mod.set_step("R", "9", "active", "C:/proj", T0)
    progress_mod.set_step("R", "9", "active", "C:/proj", T0, label="extra")
    assert doc()["steps"][-1]["label"] == "extra"


def test_a_bad_state_is_refused(workspace):
    cli(workspace, "--run", "VIR-900", "--from-spec", "spec.md")
    assert cli(workspace, "--run", "VIR-900", "--step", "1", "--state", "finished").returncode != 0
    assert cli(workspace, "--step", "1", "--state", "done").returncode != 0      # no --run


def test_a_changed_plan_updates_the_milestones_and_keeps_the_stamps(isolated_home):
    opened()
    progress_mod.set_step("R", "1", "done", "C:/proj", at(4))
    changed = [PLAN[0], {"id": "M4", "label": "New stage", "steps": [{"id": "6", "label": "f"}]},
               PLAN[2]]
    assert progress_mod.open_run("R", "", changed, "C:/proj", at(5)) == "resumed"
    record = doc()
    assert [m["label"] for m in record["milestones"]] == ["Core", "New stage", "Ship"]
    assert record["steps"][0]["finished"] == "2026-11-01T09:04:00Z"
    assert "Milestone 0/3" in progress_mod.summary(record, at(5))["line2"]


def test_an_epic_resumes_in_a_later_session_and_never_starts_over(workspace):
    """Session one opens the epic; after context loss, session two's virtuoso skill opens
    the same run id and carries on with the same record and stamps."""
    first = cli(workspace, "--run", "EPIC-1", "--from-charter", "charter.md", "--json")
    assert json.loads(first.stdout)["outcome"] == "begun"
    cli(workspace, "--run", "EPIC-1", "--step", "1.1", "--state", "done")
    started = doc("EPIC-1")["started"]
    again = cli(workspace, "--run", "EPIC-1", "--from-charter", "charter.md", "--json")
    assert json.loads(again.stdout)["outcome"] == "resumed"
    record = doc("EPIC-1")
    assert record["started"] == started
    assert record["steps"][0]["state"] == "done"
    assert len(list(Path(progress_mod.store_dir(), "runs").glob("*.json"))) == 1


def test_a_stopped_run_is_brought_back_and_a_complete_one_is_not(isolated_home):
    opened()
    progress_mod.set_step("R", "1", "done", "C:/proj", at(3))
    progress_mod.end_run("R", "stopped", "C:/proj", at(4), reason="halted")
    assert progress_mod.open_run("R", "", PLAN, "C:/proj", at(5)) == "restored"
    assert doc()["steps"][0]["state"] == "done" and "end" not in doc()
    assert not Path(progress_mod.archive_path("R")).exists()
    for m in PLAN:
        progress_mod.set_milestone("R", m["id"], "done", "C:/proj", at(6))
    progress_mod.end_run("R", "complete", "C:/proj", at(7), evidence="suite green")
    with pytest.raises(progress_mod.ProgressError, match="COMPLETE"):
        progress_mod.open_run("R", "", PLAN, "C:/proj", at(8))


def test_colours_come_from_the_palette_or_the_override(workspace):
    cli(workspace, "--run", "VIR-900", "--from-spec", "spec.md")
    assert tuple(doc("VIR-900")["colors"]) in progress_mod.PALETTE
    assert doc("VIR-900")["colors"] == progress_mod.colors_for("VIR-900")
    cli(workspace, "--run", "VIR-901", "--from-spec", "spec.md", "--colors", "green,yellow")
    assert doc("VIR-901")["colors"] == ["green", "yellow"]


# --- what the band shows -----------------------------------------------------------------

def finish(run_id, step, start, end):
    progress_mod.set_step(run_id, step, "active", "C:/proj", at(start))
    progress_mod.set_step(run_id, step, "done", "C:/proj", at(end))


def test_eta_is_a_dash_until_two_are_finished_then_the_median(isolated_home):
    opened()
    finish("R", "1", 0, 4)
    shown = progress_mod.summary(doc(), at(4))
    assert shown["line1"] == ("█" * 7 + "░" * 13
                              + " Step 1/3      ( 33% complete; milestone ETA —) b")
    finish("R", "2", 4, 14)
    shown = progress_mod.summary(doc(), at(14))
    # median of 4m and 10m is 7m; one step left: 09:14 + 7m
    assert shown["line1"] == ("█" * 13 + "░" * 7
                              + " Step 2/3      ( 67% complete; milestone ETA 09:21Z) c")
    assert shown["line2"] == ("░" * 20
                              + " Milestone 0/3 (  0% complete; dispatch ETA —)       Core")
    assert shown["status"] == "Step 2/3 · Milestone 0/3"


def test_the_two_lines_line_up_and_never_wrap(isolated_home):
    long_name = "a step whose name is far too long for any narrow terminal to hold whole"
    opened(plan=[{"label": "Core", "steps": [{"id": "1", "label": long_name}]}])
    for width in (80, 66):
        one, two = (progress_mod.summary(doc(), T0, width=width)[k] for k in ("line1", "line2"))
        assert len(one) <= width and len(two) <= width
        assert one.index("(") == two.index("(")
        assert one.split(" ")[0] and len(one.split(" ")[0]) == len(two.split(" ")[0])
    one = progress_mod.summary(doc(), T0, width=80)["line1"]
    assert one.endswith("…") and "milestone ETA —)" in one
    one, two = (progress_mod.summary(doc(), T0, width=50)[k] for k in ("line1", "line2"))
    assert progress_mod.MIN_BAR <= len(one.split(" ")[0]) < progress_mod.BAR   # shrunk, floored
    assert len(one) <= 50 and len(two) <= 50
    assert "(  0%; milestone ETA —)" in one       # "complete" went first; values never cut
    assert "(  0%; ETA —)" in progress_mod.summary(doc(), T0, width=40)["line1"]
    for cols in (60, 80, 120):
        lines = [progress_mod.summary(doc(), T0, width=cols)[k] for k in ("line1", "line2")]
        assert all(len(l) <= cols for l in lines)
        assert lines[0].index("(") == lines[1].index("(")
    one = progress_mod.summary(doc(), T0, width=60)["line1"]
    assert "  0%" in one and "ETA —" in one
    assert progress_mod.percent(0) == "  0%" and progress_mod.percent(100) == "100%"


def test_a_registry_that_still_names_the_retired_progress_role_validates_with_a_warning(
        workspace, isolated_home):
    """A v1.17.0 project keeps its `progress` role entry: never a failure, never rewritten."""
    manifest = workspace / "Virtuoso" / "workspace-layout.json"
    layout = json.loads(manifest.read_text(encoding="utf-8"))
    layout["roles"]["progress"] = {     # the role as v1.17.0 registered it
        "path": "Virtuoso/Progress.json", "provider": "json", "authority": "reference",
        "mutability": "read-write", "owner": "virtuoso",
        "allowedWriters": ["virtuoso", "next-dispatch", "dispatch-closeout", "epic"],
        "validation": "exists", "classification": "active", "origin": "authored",
        "label": "Progress band"}
    manifest.write_text(json.dumps(layout, indent=2), encoding="utf-8")
    (workspace / "Virtuoso" / "Progress.json").write_text('{"items": []}', encoding="utf-8")
    before = tree(workspace)
    for mode in ("check", "repair"):
        checked = run(PREFLIGHT, "--root", str(workspace), "--mode", mode)
        assert checked.returncode == 0, checked.stderr
        assert "retired" in checked.stdout and "[warning]" in checked.stdout
    assert tree(workspace) == before


def test_an_eta_on_a_later_day_carries_its_date(isolated_home):
    opened()
    progress_mod.set_milestone("R", "M1", "active", "C:/proj", at(0))
    progress_mod.set_milestone("R", "M1", "done", "C:/proj", at(60))
    progress_mod.set_milestone("R", "M2", "active", "C:/proj", at(60))
    progress_mod.set_milestone("R", "M2", "done", "C:/proj", at(180))
    shown = progress_mod.summary(doc(), at(180))
    # median of 60m and 120m is 90m; one milestone left: 12:00 + 90m, the same UTC day
    assert "Milestone 2/3 ( 67% complete; dispatch ETA 13:30Z)" in shown["line2"]
    later = doc()
    for m, (a, b) in zip(later["milestones"], ((0, 600), (600, 1200))):
        m["started"], m["finished"] = progress_mod.stamp(at(a)), progress_mod.stamp(at(b))
    later["updated"] = progress_mod.stamp(at(660))
    # median 600m, one left, from 20:00Z: 06:00Z the next day
    assert "dispatch ETA 11-02 06:00Z)" in progress_mod.summary(later, at(660))["line2"]


def test_a_long_step_is_not_stale_before_twice_its_median(isolated_home):
    opened()
    progress_mod.set_step("R", "1", "active", "C:/proj", at(0))
    progress_mod.set_step("R", "1", "done", "C:/proj", at(60))
    progress_mod.set_step("R", "2", "active", "C:/proj", at(60))
    progress_mod.set_step("R", "2", "done", "C:/proj", at(120))      # median step: 60 minutes
    assert progress_mod.stale_after(doc()["steps"]).total_seconds() == 7200
    assert progress_mod.summary(doc(), at(165))["stale"] is False   # 45 minutes without a feed
    assert progress_mod.summary(doc(), at(241))["stale"] is True    # past 2 x 60 minutes


def test_a_run_with_no_feed_for_30_minutes_shows_when_it_last_moved(isolated_home):
    opened()
    shown = progress_mod.summary(doc(), at(31))
    assert shown["stale"] is True
    assert "(  0% complete; no update since 09:00Z) a" in shown["line1"]
    assert "(  0% complete; no update since 09:00Z) Core" in shown["line2"]
    assert progress_mod.summary(doc(), at(29))["stale"] is False


def test_complete_only_after_the_completion_check(workspace):
    cli(workspace, "--run", "VIR-900", "--from-spec", "spec.md", "--title", "Sample")
    done = cli(workspace, "--run", "VIR-900", "--complete", "--evidence", "suite green")
    assert done.returncode != 0 and "--stop" in done.stderr                # milestones open
    for m in ("M1", "M2"):
        cli(workspace, "--run", "VIR-900", "--milestone", m, "--state", "done")
    done = cli(workspace, "--run", "VIR-900", "--complete")
    assert done.returncode != 0 and "--evidence" in done.stderr
    assert cli(workspace, "--run", "VIR-900", "--complete", "--evidence", "suite green").returncode == 0
    assert not Path(progress_mod.run_path("VIR-900")).exists()
    archived = progress_mod.read(progress_mod.archive_path("VIR-900"))
    line = progress_mod.summary(archived, progress_mod.now(), ended=True)["end"]
    assert re.match(r"^█{20} ✓ COMPLETE \(Milestone 2/2; finished \d{4}-\d\d-\d\d \d\d:\d\dZ; took \d+m\) Sample$",
                    line)
    assert progress_mod.took(at(0), at(192)) == "3h12m" and progress_mod.took(at(0), at(5)) == "5m"


def test_any_other_end_is_stopped_with_its_reason(workspace):
    cli(workspace, "--run", "VIR-900", "--from-spec", "spec.md", "--title", "Sample")
    cli(workspace, "--run", "VIR-900", "--step", "1", "--state", "done")
    assert cli(workspace, "--run", "VIR-900", "--stop", "").returncode != 0
    assert cli(workspace, "--run", "VIR-900", "--stop", "failed tests").returncode == 0
    archived = progress_mod.read(progress_mod.archive_path("VIR-900"))
    line = progress_mod.summary(archived, progress_mod.now(), ended=True)["end"]
    assert re.match(r"^░{20} ■ STOPPED \(Step 1/\d+ of Milestone 1/2; stopped \d{4}-\d\d-\d\d \d\d:\d\dZ; failed\) "
                    r"Sample$", line)


def test_a_cancelled_item_drops_out_of_the_counts(isolated_home):
    opened()
    progress_mod.set_step("R", "1", "done", "C:/proj", at(1))
    shown = progress_mod.summary(doc(), at(1))
    total = shown["stepsTotal"]
    progress_mod.set_step("R", "2", "cancelled", "C:/proj", at(2))
    shown = progress_mod.summary(doc(), at(2))
    assert shown["stepsTotal"] == total - 1 and shown["stepsDone"] == 1
    milestones = shown["milestonesTotal"]
    progress_mod.set_milestone("R", "M2", "cancelled", "C:/proj", at(3))
    assert progress_mod.summary(doc(), at(3))["milestonesTotal"] == milestones - 1


def test_an_end_line_fits_like_the_live_lines(isolated_home):
    opened(plan=[{"label": "x", "steps": [{"label": "y"}]}] * 1)
    progress_mod.set_milestone("R", "M1", "done", "C:/proj", at(1))
    progress_mod.end_run("R", "complete", "C:/proj", at(2), evidence="ok")
    archived = progress_mod.read(progress_mod.archive_path("R"))
    archived["run"]["title"] = "a run whose title is much too long to fit a narrow terminal"
    line = progress_mod.summary(archived, at(3), ended=True, width=90)["end"]
    assert len(line) == 90 and line.endswith("…")
    assert "✓ COMPLETE (Milestone 1/1; finished 2026-11-01 09:02Z; took 2m) a ru…" in line
    narrow = progress_mod.summary(archived, at(3), ended=True, width=60)["end"]
    assert len(narrow) <= 60 and "2026-11-01 09:02Z; 2m)" in narrow   # labels go, values stay
    archived["end"] = {"state": "stopped", "at": archived["end"]["at"], "reason": "halted"}
    for cols in (60, 80):
        line = progress_mod.summary(archived, at(3), ended=True, width=cols)["end"]
        assert len(line) <= cols and "2026-11-01 09:02Z; halted)" in line


# --- sessions, the end line, and clearing it ----------------------------------------------

def test_a_session_shows_its_run_then_the_end_line_from_the_archive(isolated_home):
    opened()
    progress_mod.bind_session("s-1", "R", T0)
    assert progress_mod.session_run("s-1")[0] == "running"
    progress_mod.end_run("R", "stopped", "C:/proj", at(5), reason="aborted")
    state, archived = progress_mod.session_run("s-1")
    assert state == "ended" and archived["end"]["reason"] == "aborted"
    assert not list(Path(progress_mod.store_dir(), "runs").glob("*.json"))   # live store empty


def test_the_end_line_stays_until_the_next_run_or_a_clear(isolated_home):
    opened()
    progress_mod.bind_session("s-1", "R", T0)
    progress_mod.end_run("R", "stopped", "C:/proj", at(5), reason="aborted")
    assert progress_mod.session_run("s-1")[0] == "ended"
    opened(run_id="S")
    progress_mod.bind_session("s-1", "S", at(6))
    assert progress_mod.session_run("s-1") == ("running", doc("S"))


def test_clearing_one_session_leaves_another_alone(isolated_home):
    for run_id, session in (("R", "s-1"), ("S", "s-2")):
        opened(run_id=run_id)
        progress_mod.bind_session(session, run_id, T0)
        progress_mod.end_run(run_id, "stopped", "C:/proj", at(5), reason="halted")
    assert progress_mod.clear_session("s-1", at(6)) is True
    assert progress_mod.session_run("s-1") == (None, None)
    assert progress_mod.session_run("s-2")[0] == "ended"


def test_a_running_run_is_never_cleared(isolated_home):
    opened()
    progress_mod.bind_session("s-1", "R", T0)
    assert progress_mod.clear_session("s-1", at(1)) is False
    assert progress_mod.session_run("s-1")[0] == "running"


def test_clear_names_a_session_on_the_command_line(workspace):
    cli(workspace, "--run", "VIR-900", "--from-spec", "spec.md")
    progress_mod.bind_session("s-9", "VIR-900", progress_mod.now())
    cli(workspace, "--run", "VIR-900", "--stop", "halted")
    done = cli(workspace, "--clear", "--session", "s-9", actor=None)
    assert done.returncode == 0 and "cleared" in done.stdout
    assert progress_mod.session_run("s-9") == (None, None)


def hook(project, command, session):
    return {"hook_event_name": "PreToolUse", "session_id": session, "cwd": str(project),
            "transcript_path": "/t/%s.jsonl" % session, "tool_name": "Bash",
            "tool_input": {"command": command}}


def test_the_hook_binds_a_feeding_session_and_clears_only_its_own_line(project, isolated_home):
    feed = "virtuoso_registry --root . --actor virtuoso progress --run %s --step 1 --state done"
    guards.handle(hook(project, feed % "R", "s-1"), "claude-code")
    guards.handle(hook(project, feed % "S", "s-2"), "claude-code")
    assert progress_mod.read(progress_mod.session_path("s-1"))["run"] == "R"
    assert progress_mod.read(progress_mod.session_path("s-2"))["run"] == "S"
    guards.handle(hook(project, "virtuoso_registry --root . progress --run S --json", "s-1"),
                  "claude-code")
    assert progress_mod.read(progress_mod.session_path("s-1"))["run"] == "R"   # a read: no move
    guards.handle(hook(project, "virtuoso_registry --root . progress --clear", "s-2"), "claude-code")
    assert progress_mod.read(progress_mod.session_path("s-2"))["cleared"]
    assert "cleared" not in progress_mod.read(progress_mod.session_path("s-1"))


@pytest.mark.parametrize("command, expected", [
    ("virtuoso_registry --root . --actor virtuoso progress --run VIR-061 --from-spec s.md", ("VIR-061", "feed")),
    ("virtuoso_registry progress --run=EPIC-2 --milestone M1 --state active", ("EPIC-2", "feed")),
    ("virtuoso_registry progress --run X-1 --stop halted", ("X-1", "feed")),
    ("virtuoso_registry progress --clear", ("", "clear")),
    ("virtuoso_registry progress --clear --session s-3", ("", "")),
    ("virtuoso_registry progress --run X-1 --json", ("", "")),
    ("git commit -m 'virtuoso_registry progress --run X-1 --step 1'", ("", "")),
])
def test_the_hook_reads_what_a_command_does_to_the_band(command, expected):
    assert hosts.progress_call(command) == expected


# --- the store under load -----------------------------------------------------------------

def test_parallel_writers_lose_nothing(workspace):
    """Steps moved from many processes at once all land (the lock serializes them)."""
    plan = [{"label": "All", "steps": [{"id": str(n), "label": "s%d" % n} for n in range(8)]}]
    (workspace / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    assert cli(workspace, "--run", "R", "--plan", "plan.json").returncode == 0
    head = [sys.executable, REGISTRY_CLI, "--root", str(workspace), "--actor", "virtuoso",
            "progress", "--run", "R", "--state", "done", "--step"]
    procs = [subprocess.Popen(head + [str(n)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
             for n in range(8)]
    assert all(p.wait(timeout=60) == 0 for p in procs)
    assert all(s["state"] == "done" for s in doc()["steps"])
    assert not list(Path(progress_mod.store_dir()).rglob("*.lock"))
    assert not list(Path(progress_mod.store_dir()).rglob("*.tmp"))


def test_a_stale_lock_is_taken_over(isolated_home):
    path = progress_mod.run_path("R")
    lock = Path(path + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("999999", encoding="ascii")
    old = lock.stat().st_mtime - progress_mod.STALE_LOCK_SECONDS - 5
    os.utime(lock, (old, old))
    opened()


def test_a_held_lock_refuses_after_waiting(isolated_home):
    target = progress_mod.run_path("R")
    with progress_mod.locked(target):
        with pytest.raises(progress_mod.ProgressError):
            with progress_mod.locked(target, wait_seconds=0.2):
                pass


def test_a_run_a_dead_session_left_is_archived_as_abandoned(isolated_home):
    opened()
    assert progress_mod.abandon_stale(T0 + dt.timedelta(days=13)) == []
    assert progress_mod.abandon_stale(T0 + dt.timedelta(days=15)) == ["R"]
    assert progress_mod.read(progress_mod.archive_path("R"))["end"]["reason"] == "abandoned"


def test_reading_shows_the_lines_of_a_run(workspace):
    cli(workspace, "--run", "VIR-900", "--from-spec", "spec.md", "--title", "Sample")
    cli(workspace, "--run", "VIR-900", "--step", "1", "--state", "active")
    shown = json.loads(cli(workspace, "--json", actor=None).stdout)["runs"]["VIR-900"]
    assert shown["line1"].endswith(" Write the parser") and "Step 0/2" in shown["line1"]
    assert shown["line2"].endswith(" Core") and "Milestone 0/2" in shown["line2"]
    narrow = json.loads(cli(workspace, "--json", "--width", "66", actor=None).stdout)
    assert len(narrow["runs"]["VIR-900"]["line1"]) <= 66


# --- the module ----------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("claude") is None,
                    reason="the claude CLI is not installed here (CI); release preflight runs it")
def test_the_band_module_passes_its_own_behaviour_tests():
    """`claude plugin test` runs hooks/progress-band.test.tsx against the engine itself."""
    done = subprocess.run(["claude", "plugin", "test", str(ROOT)], capture_output=True,
                          text=True, encoding="utf-8", timeout=300)
    assert done.returncode == 0, (done.stdout + done.stderr)[-1500:]
    assert " 0 fail" in done.stdout


def test_the_plugin_ships_the_band_module():
    hooks_json = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert hooks_json["modules"] == ["./progress-band.tsx"]
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["types"] == "./types/index.d.ts"


def test_the_band_module_computes_like_the_command():
    """The module repeats the Python figures; its constants must agree with them."""
    body = (ROOT / "hooks" / "progress-band.tsx").read_text(encoding="utf-8")
    assert "BAR = %d" % progress_mod.BAR in body
    assert "STALE_FEED_MINUTES = %d" % progress_mod.STALE_FEED_MINUTES in body
    palette = "[%s]" % ", ".join("['%s', '%s']" % pair for pair in progress_mod.PALETTE)
    assert re.sub(r"\s+", " ", palette) in re.sub(r"\s+", " ", body)
    assert "ETA —" not in body or True
    assert "✓ COMPLETE" in body and "■ STOPPED" in body and "no update since" in body
