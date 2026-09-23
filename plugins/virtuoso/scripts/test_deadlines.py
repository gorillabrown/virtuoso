"""Deadlines: the declaration, its validation, its write path, its body, and the
session-start line (v1.8.1).

A deadline is a value (``policy.roadmap.deadlines.<id>``) paired with a body (the
roadmap heading that defines the finish line it dates). These tests cover everything
about a deadline except the pace computed against it, which lives in
``test_pace.py``.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import policy as policy_mod
from tools.governance.providers import kpi

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")


def run(script, *args):
    return subprocess.run([sys.executable, script, *args], capture_output=True,
                          text=True, env=dict(os.environ))


def manifest(root):
    return json.loads((root / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8"))


def policy_set(root, key, value_json, *extra, actor="roadmap-review"):
    return run(REGISTRY_CLI, "--root", str(root), "--actor", actor,
               "policy-set", key, "--value-json", value_json, *extra)


@pytest.fixture
def workspace(project):
    """A freshly created workspace: registered, valid, no policy of its own."""
    completed = run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return project


# =============================================================================
# roadmap.effortScale — documented, read by kpis, and now settable
# =============================================================================


def test_effort_scale_is_a_documented_key():
    assert policy_mod.is_documented("roadmap.effortScale")
    assert policy_mod.type_problem("roadmap.effortScale", {"s": 1}) == ""


def test_effort_scale_is_settable(workspace):
    preview = policy_set(workspace, "roadmap.effortScale", '{"s": 1, "m": 3}')
    assert preview.returncode == 0, preview.stdout + preview.stderr
    applied = policy_set(workspace, "roadmap.effortScale", '{"s": 1, "m": 3}', "--apply")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert manifest(workspace)["policy"]["roadmap"]["effortScale"] == {"s": 1, "m": 3}


def test_an_empty_effort_scale_means_the_generic_scale():
    from tools.governance.providers import base
    items = [base.WorkItem(id="A-1", status=base.QUEUED, effort="m"),
             base.WorkItem(id="A-2", status=base.COMPLETED, effort="s")]
    snap = base.Snapshot(items=items, provider="test", source="memory",
                         taken_at="2026-09-22T00:00:00Z", fields=["status", "effort"])
    assert kpi.compute(snap, effort_scale=None).as_dict() == \
        kpi.compute(snap, effort_scale={}).as_dict()
    # The merged default is {}, which kpis must read as "use the generic scale".
    assert policy_mod.load({}).get("roadmap.effortScale") == {}


def test_a_project_scale_replaces_the_generic_one_rather_than_merging():
    """A union would silently price a size the project never defined."""
    merged = policy_mod.load({"roadmap": {"effortScale": {"small": 1}}})
    assert merged.get("roadmap.effortScale") == {"small": 1}


# =============================================================================
# The declaration: policy.roadmap.deadlines and policy.roadmap.pace
# =============================================================================

GAME_BUILD = {"date": "2027-01-01", "owner": "Evan", "label": "Overall game build",
              "recorded": "2026-09-22"}


def test_deadlines_and_pace_are_documented():
    for key in ("roadmap.deadlines", "roadmap.pace", "roadmap.pace.trailingWeeks",
                "roadmap.pace.tolerance"):
        assert policy_mod.is_documented(key), key
    assert policy_mod.load({}).get("roadmap.deadlines") == {}
    assert policy_mod.load({}).get("roadmap.pace") == {"trailingWeeks": 4, "tolerance": 0.1}


def test_a_project_named_deadline_is_documented_by_its_template():
    assert policy_mod.is_documented("roadmap.deadlines.game-build")
    assert policy_mod.is_documented("roadmap.deadlines.game-build.date")
    assert policy_mod.is_documented("roadmap.deadlines.game-build.scope.values")
    assert not policy_mod.is_documented("roadmap.deadlines.game-build.dat")
    assert not policy_mod.is_documented("roadmap.deadlines.")
    # the template carries the types the type gate checks
    assert policy_mod.type_problem("roadmap.deadlines.game-build", GAME_BUILD) == ""
    assert policy_mod.type_problem("roadmap.deadlines.game-build", "2027-01-01") != ""
    assert policy_mod.type_problem("roadmap.deadlines.game-build.date", "2027-01-01") == ""
    assert policy_mod.type_problem("roadmap.deadlines.game-build.date", 20270101) != ""


def test_only_a_named_entry_is_an_open_child():
    assert policy_mod.open_child("roadmap.deadlines.game-build")
    assert not policy_mod.open_child("roadmap.deadlines")
    assert not policy_mod.open_child("roadmap.deadlines.game-build.date")
    assert not policy_mod.open_child("rubric.extensions")


def test_withdraw_is_pure_and_keeps_siblings():
    raw = {"roadmap": {"deadlines": {"a": dict(GAME_BUILD), "b": dict(GAME_BUILD)},
                       "dispatchBuffer": 3}}
    out = policy_mod.withdraw(raw, "roadmap.deadlines.a")
    assert out == {"roadmap": {"deadlines": {"b": GAME_BUILD}, "dispatchBuffer": 3}}
    assert "a" in raw["roadmap"]["deadlines"]              # pure
    assert policy_mod.withdraw({}, "roadmap.deadlines.a") == {}


@pytest.mark.parametrize("text, expected", [
    ("2027-01-01", (2027, 1, 1)),
    ("2028-02-29", (2028, 2, 29)),
    ("2027-02-29", None),        # not a calendar date
    ("2027-13-01", None),
    ("20270101", None),          # 3.11+ fromisoformat accepts this; a deadline must not
    ("2027-W01-1", None),
    ("01/01/2027", None),
    ("2027-01-01T00:00", None),
    ("", None),
    (None, None),
    (20270101, None),
])
def test_iso_date_is_strict(text, expected):
    got = policy_mod.iso_date(text)
    assert (got.timetuple()[:3] if got else None) == expected


def test_a_valid_deadline_has_no_problems():
    assert policy_mod.deadline_problems({}) == []
    assert policy_mod.deadline_problems({"game-build": GAME_BUILD}) == []
    scoped = dict(GAME_BUILD, finishLine="Finish Line C",
                  scope={"field": "group", "values": ["B1", "B2", "B3", "C"]})
    assert policy_mod.deadline_problems({"game_build-2": scoped}) == []
    assert policy_mod.deadline_problems({"x": dict(GAME_BUILD, scope={})}) == []


@pytest.mark.parametrize("deadlines, names", [
    ({"g": dict(GAME_BUILD, date="2027-13-01")}, "g.date"),
    ({"g": dict(GAME_BUILD, date="01/01/2027")}, "g.date"),
    ({"g": {k: v for k, v in GAME_BUILD.items() if k != "date"}}, "g.date"),
    ({"g": {k: v for k, v in GAME_BUILD.items() if k != "owner"}}, "g.owner"),
    ({"g": dict(GAME_BUILD, owner="  ")}, "g.owner"),
    ({"g": dict(GAME_BUILD, dat="2027-01-01")}, "unknown field(s) dat"),
    ({"b3.final": GAME_BUILD}, "b3.final: a deadline id"),
    ({"-lead": GAME_BUILD}, "-lead: a deadline id"),
    ({"g": dict(GAME_BUILD, scope={"field": "group", "values": []})}, "g.scope.values"),
    ({"g": dict(GAME_BUILD, scope={"field": "", "values": ["B3"]})}, "g.scope.field"),
    ({"g": dict(GAME_BUILD, scope={"field": "group", "values": ["B3"], "x": 1})},
     "g.scope has unknown field(s) x"),
    ({"g": dict(GAME_BUILD, scope=["B3"])}, "g.scope is a list"),
    ({"g": dict(GAME_BUILD, recorded="yesterday")}, "g.recorded"),
    ({"g": dict(GAME_BUILD, label=7)}, "g.label"),
    ({"g": "2027-01-01"}, "g is a string, not a deadline"),
    (["game-build"], "policy.roadmap.deadlines is a list"),
])
def test_deadline_validation_names_each_problem(deadlines, names):
    problems = policy_mod.deadline_problems(deadlines)
    assert len(problems) == 1, problems
    assert names in problems[0], problems[0]


@pytest.mark.parametrize("pace, names", [
    ({"trailingWeeks": 0}, "trailingWeeks"),
    ({"trailingWeeks": 53}, "trailingWeeks"),
    ({"trailingWeeks": True}, "trailingWeeks"),
    ({"trailingWeeks": "4"}, "trailingWeeks"),
    ({"trailingWeeks": 4.0}, "trailingWeeks"),
    ({"tolerance": 1}, "tolerance"),
    ({"tolerance": -0.1}, "tolerance"),
    ({"tolerance": True}, "tolerance"),
    ({"trailingWeek": 4}, "unknown field(s) trailingWeek"),
])
def test_pace_validation_names_each_problem(pace, names):
    problems = policy_mod.pace_problems(dict({"trailingWeeks": 4, "tolerance": 0.1}, **pace))
    assert len(problems) == 1, problems
    assert names in problems[0], problems[0]


def test_the_default_pace_and_zero_tolerance_are_valid():
    assert policy_mod.pace_problems({"trailingWeeks": 4, "tolerance": 0.1}) == []
    assert policy_mod.pace_problems({"trailingWeeks": 52, "tolerance": 0}) == []


def test_validate_reports_deadline_and_pace_problems():
    bad = policy_mod.load({"roadmap": {"deadlines": {"g": {"date": "soon"}},
                                       "pace": {"tolerance": 2}}})
    problems = bad.validate()
    assert any("g.date" in p for p in problems)
    assert any("g.owner" in p for p in problems)
    assert any("tolerance" in p for p in problems)


# --- the write path -----------------------------------------------------------


def test_policy_set_adds_a_deadline_beside_another(workspace):
    first = policy_set(workspace, "roadmap.deadlines.alpha", json.dumps(GAME_BUILD), "--apply")
    assert first.returncode == 0, first.stdout + first.stderr
    alpha_bytes = json.dumps(manifest(workspace)["policy"]["roadmap"]["deadlines"]["alpha"])
    second = policy_set(workspace, "roadmap.deadlines.beta",
                        json.dumps(dict(GAME_BUILD, date="2027-06-30")), "--apply")
    assert second.returncode == 0, second.stdout + second.stderr
    deadlines = manifest(workspace)["policy"]["roadmap"]["deadlines"]
    assert sorted(deadlines) == ["alpha", "beta"]
    assert json.dumps(deadlines["alpha"]) == alpha_bytes


def test_policy_set_moves_one_date(workspace):
    policy_set(workspace, "roadmap.deadlines.alpha", json.dumps(GAME_BUILD), "--apply")
    moved = policy_set(workspace, "roadmap.deadlines.alpha.date", '"2027-02-01"', "--apply")
    assert moved.returncode == 0, moved.stdout + moved.stderr
    assert manifest(workspace)["policy"]["roadmap"]["deadlines"]["alpha"] == \
        dict(GAME_BUILD, date="2027-02-01")


def test_setting_a_field_of_an_undeclared_deadline_is_refused(workspace):
    before = snapshot_tree(str(workspace))
    refused = policy_set(workspace, "roadmap.deadlines.nope.date", '"2027-02-01"', "--apply")
    assert refused.returncode != 0
    assert "owner" in refused.stdout + refused.stderr
    assert snapshot_tree(str(workspace)) == before


def test_policy_set_refuses_an_invalid_deadline_and_writes_nothing(workspace):
    before = snapshot_tree(str(workspace))
    refused = policy_set(workspace, "roadmap.deadlines.alpha",
                         json.dumps(dict(GAME_BUILD, date="2027-13-01")), "--apply")
    assert refused.returncode != 0
    assert "alpha.date" in refused.stdout + refused.stderr
    assert snapshot_tree(str(workspace)) == before


def test_null_withdraws_a_deadline(workspace):
    policy_set(workspace, "roadmap.deadlines.alpha", json.dumps(GAME_BUILD), "--apply")
    policy_set(workspace, "roadmap.deadlines.beta", json.dumps(GAME_BUILD), "--apply")
    preview = policy_set(workspace, "roadmap.deadlines.alpha", "null")
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert "withdraw" in preview.stdout
    withdrawn = policy_set(workspace, "roadmap.deadlines.alpha", "null", "--apply")
    assert withdrawn.returncode == 0, withdrawn.stdout + withdrawn.stderr
    assert "withdrawn" in withdrawn.stdout
    assert sorted(manifest(workspace)["policy"]["roadmap"]["deadlines"]) == ["beta"]


def test_null_on_an_undeclared_deadline_is_refused(workspace):
    before = snapshot_tree(str(workspace))
    refused = policy_set(workspace, "roadmap.deadlines.nope", "null", "--apply")
    assert refused.returncode != 0
    assert "nothing to withdraw" in refused.stdout + refused.stderr
    assert snapshot_tree(str(workspace)) == before


def test_null_is_still_refused_where_it_withdraws_nothing(workspace):
    refused = policy_set(workspace, "rubric.extensions", "null", "--apply")
    assert refused.returncode != 0
    assert "is documented as a list" in refused.stdout + refused.stderr


def test_policy_set_reads_the_value_back(workspace):
    applied = policy_set(workspace, "roadmap.deadlines.alpha", json.dumps(GAME_BUILD), "--apply")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert "verified: read back from disk" in applied.stdout
    as_json = policy_set(workspace, "roadmap.deadlines.alpha.owner", '"Owner Two"', "--apply",
                         "--json")
    assert as_json.returncode == 0, as_json.stdout + as_json.stderr
    assert json.loads(as_json.stdout)["verified"] is True


def test_the_read_back_compares_what_was_written_not_the_merged_defaults(workspace):
    """A partial mapping merges with its defaults when read through policy; the
    read-back must not mistake that for a wrong write."""
    applied = policy_set(workspace, "roadmap.pace", '{"trailingWeeks": 6}', "--apply")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert "verified: read back from disk" in applied.stdout
    assert manifest(workspace)["policy"]["roadmap"]["pace"] == {"trailingWeeks": 6}
    explicit_null = policy_set(workspace, "workRegister.creators", "null", "--apply")
    assert explicit_null.returncode == 0, explicit_null.stdout + explicit_null.stderr
    assert "verified: read back from disk" in explicit_null.stdout
