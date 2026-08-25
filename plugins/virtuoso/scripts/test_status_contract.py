"""The published status contract (items 10, 11, 92).

Every status in the contract is documented, reachable, and carries the write
guarantee the contract promises. The session-start path is proven to write
nothing at all.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import result as result_mod

PREFLIGHT = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_preflight.py")


def run(root, *args, env_home=None):
    import os
    env = dict(os.environ)
    if env_home:
        env["VIRTUOSO_HOME"] = str(env_home)
    completed = subprocess.run(
        [sys.executable, PREFLIGHT, "--root", str(root), *args],
        capture_output=True, text=True, env=env)
    return completed


def parse_contract(stdout: str) -> tuple[str, int]:
    status = writes = None
    for line in stdout.splitlines():
        if line.startswith("virtuoso-status: "):
            status = line.split(": ", 1)[1].strip()
        elif line.startswith("writes: "):
            writes = int(line.split(": ", 1)[1])
    return status, writes


# --- the contract itself ------------------------------------------------------


def test_status_set_is_closed():
    assert len(set(result_mod.STATUSES)) == len(result_mod.STATUSES)
    assert set(result_mod.ZERO_WRITE_STATUSES) <= set(result_mod.STATUSES)


def test_result_rejects_an_unknown_status():
    with pytest.raises(ValueError):
        result_mod.Result(status="invented", mode="check", root="/tmp")


def test_zero_write_status_cannot_report_writes():
    outcome = result_mod.Result(status=result_mod.READY, mode="check", root="/tmp",
                                writes=1, files_written=["x"])
    with pytest.raises(AssertionError):
        outcome.assert_contract()


def test_writes_count_must_match_the_file_list():
    outcome = result_mod.Result(status=result_mod.CREATED, mode="create", root="/tmp",
                                writes=2, files_written=["x"])
    with pytest.raises(AssertionError):
        outcome.assert_contract()


def test_every_status_is_documented_in_the_module():
    doc = result_mod.__doc__ or ""
    for status in result_mod.STATUSES:
        assert status in doc, "status %r is undocumented" % status


# --- reachability, end to end -------------------------------------------------


def test_none_on_an_empty_project(project, isolated_home):
    result = run(project, "--mode", "check", env_home=isolated_home)
    assert parse_contract(result.stdout) == (result_mod.NONE, 0)
    assert result.returncode == 0


def test_created_then_ready(project, isolated_home):
    created = run(project, "--mode", "create", "--authorize", env_home=isolated_home)
    status, writes = parse_contract(created.stdout)
    assert status == result_mod.CREATED and writes > 0

    ready = run(project, "--mode", "check", env_home=isolated_home)
    assert parse_contract(ready.stdout) == (result_mod.READY, 0)


def test_create_without_authorization_fails_and_writes_nothing(project, isolated_home):
    before = snapshot_tree(project)
    result = run(project, "--mode", "create", env_home=isolated_home)
    status, writes = parse_contract(result.stdout)
    assert status == result_mod.FAILED and writes == 0
    assert result.returncode == result_mod.EXIT_FAILED
    assert snapshot_tree(project) == before


def test_adoptable_then_adopted(project, isolated_home):
    docs = project / "docs" / "governance"
    docs.mkdir(parents=True)
    (docs / "ROADMAP.md").write_text(
        "# Roadmap\n\n## Completed Work Summary\n\n## Active & Remaining Work\n",
        encoding="utf-8")

    check = run(project, "--mode", "check", env_home=isolated_home)
    assert parse_contract(check.stdout) == (result_mod.ADOPTABLE, 0)

    adopt = run(project, "--mode", "adopt", env_home=isolated_home)
    status, writes = parse_contract(adopt.stdout)
    assert status == result_mod.ADOPTED and writes >= 1


def test_repair_needed_and_repair_preview(project, isolated_home):
    run(project, "--mode", "create", "--authorize", env_home=isolated_home)
    manifest = project / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["roles"]["roadmap"]["path"] = "../../outside/Roadmap.md"
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")

    check = run(project, "--mode", "check", env_home=isolated_home)
    assert parse_contract(check.stdout) == (result_mod.REPAIR_NEEDED, 0)
    # --strict is how CI turns "needs repair" into a non-zero exit.
    strict = run(project, "--mode", "check", "--strict", env_home=isolated_home)
    assert strict.returncode == result_mod.EXIT_REPAIR_NEEDED

    before = snapshot_tree(project)
    preview = run(project, "--mode", "repair", env_home=isolated_home)
    status, writes = parse_contract(preview.stdout)
    assert writes == 0
    assert snapshot_tree(project) == before


def test_repaired_is_reachable(project, isolated_home):
    run(project, "--mode", "create", "--authorize", env_home=isolated_home)
    readme = project / "Virtuoso.Governance.Readme.md"
    text = readme.read_text(encoding="utf-8")
    # Damage only the generated region; the plugin owns that and may refresh it.
    damaged = text.replace("| Roadmap / specification store |", "| WRONG LABEL |")
    readme.write_text(damaged, encoding="utf-8")

    applied = run(project, "--mode", "repair", "--apply", env_home=isolated_home)
    status, _writes = parse_contract(applied.stdout)
    assert status in (result_mod.REPAIRED, result_mod.READY)


def test_warning_is_reachable(project, isolated_home):
    """A registry-only role in the readme is a warning, not an error."""
    run(project, "--mode", "create", "--authorize", env_home=isolated_home)
    readme = project / "Virtuoso.Governance.Readme.md"
    text = readme.read_text(encoding="utf-8")
    # The machine block's terminator is the only "-->" preceded by a newline;
    # the begin-marker's "-->" is preceded by a space.
    assert "\n-->" in text
    readme.write_text(text.replace("\n-->", "\ncustomRole: docs/Custom.md\n-->", 1),
                      encoding="utf-8")
    check = run(project, "--mode", "check", env_home=isolated_home)
    status, writes = parse_contract(check.stdout)
    assert status == result_mod.WARNING and writes == 0


# --- the session-start guarantee ---------------------------------------------


@pytest.mark.parametrize("mode", ["check", "detect"])
def test_session_start_modes_write_nothing(project, isolated_home, mode):
    """Item 2/92: starting, clearing, or compacting a session must never create,
    heal, vendor, or rewrite a project file — in ANY project state."""
    states = []

    # 1. empty project
    states.append(("empty", project))

    # 2. established but unregistered
    established = project.parent / "established"
    (established / "docs" / "governance").mkdir(parents=True)
    (established / "docs" / "governance" / "ROADMAP.md").write_text(
        "# Roadmap\n\n## Completed Work Summary\n\n## Active & Remaining Work\n",
        encoding="utf-8")
    states.append(("established", established))

    # 3. registered and healthy
    registered = project.parent / "registered"
    registered.mkdir()
    run(registered, "--mode", "create", "--authorize", env_home=isolated_home)
    states.append(("registered", registered))

    # 4. registered and broken
    broken = project.parent / "broken"
    broken.mkdir()
    run(broken, "--mode", "create", "--authorize", env_home=isolated_home)
    manifest = broken / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["roles"]["roadmap"]["path"] = "../escape.md"
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    states.append(("broken", broken))

    # 5. registered with a hand-authored readme
    authored = project.parent / "authored"
    authored.mkdir()
    run(authored, "--mode", "create", "--authorize", env_home=isolated_home)
    (authored / "Virtuoso.Governance.Readme.md").write_text(
        "# My own registry\n\nHand written, no generated region.\n", encoding="utf-8")
    states.append(("authored", authored))

    for label, root in states:
        before = snapshot_tree(root)
        result = run(root, "--mode", mode, "--quiet", env_home=isolated_home)
        status, writes = parse_contract(result.stdout)
        assert writes == 0, "%s: %s reported %d write(s)" % (label, mode, writes)
        assert snapshot_tree(root) == before, "%s: %s modified the project" % (label, mode)
        assert status in result_mod.ZERO_WRITE_STATUSES


def test_contract_lines_survive_quiet(project, isolated_home):
    result = run(project, "--mode", "check", "--quiet", env_home=isolated_home)
    assert "virtuoso-status: " in result.stdout
    assert "writes: " in result.stdout


def test_json_output_is_machine_readable(project, isolated_home):
    run(project, "--mode", "create", "--authorize", env_home=isolated_home)
    result = run(project, "--mode", "check", "--json", env_home=isolated_home)
    payload = json.loads(result.stdout[result.stdout.index("{"):])
    assert payload["status"] == result_mod.READY
    assert payload["writes"] == 0
    assert payload["filesWritten"] == []
    assert {"role", "provider", "authority", "mutability", "presence"} <= set(payload["roles"][0])
