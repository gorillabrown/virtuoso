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
