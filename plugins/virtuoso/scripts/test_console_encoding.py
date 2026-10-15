"""Every command writes UTF-8, whatever the console's code page (1.12.0).

On Windows a piped or redirected stream defaults to the legacy code page, cp1252.
``lessons --open`` and ``protected --json`` printed the first character outside it
(an arrow in a lesson's title, a file name) and died with
``UnicodeEncodeError: 'charmap' ...`` unless the caller set
``PYTHONIOENCODING=utf-8``. ``PYTHONIOENCODING=cp1252`` reproduces that stream on
any platform, so these tests run the same everywhere.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT

ROOT = Path(PLUGIN_ROOT)
SCRIPTS = ROOT / "scripts"
PREFLIGHT = str(SCRIPTS / "virtuoso_preflight.py")
REGISTRY_CLI = str(SCRIPTS / "virtuoso_registry.py")

#: Neither character exists in cp1252.
ARROW, CHECK = "→", "✓"


def run_cp1252(script, *args):
    """Run a command whose stdout and stderr default to cp1252, and return raw bytes."""
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    return subprocess.run([sys.executable, script, *args], capture_output=True, env=env)


@pytest.fixture
def workspace(project):
    created = subprocess.run([sys.executable, PREFLIGHT, "--root", str(project), "--mode",
                              "create", "--authorize"], capture_output=True)
    assert created.returncode == 0, created.stdout + created.stderr
    prefixed = subprocess.run([sys.executable, REGISTRY_CLI, "--root", str(project), "--actor",
                               "project-profile", "policy-set", "lessons.idPrefix",
                               "--value-json", '"LSN"', "--apply"], capture_output=True)
    assert prefixed.returncode == 0, prefixed.stdout + prefixed.stderr
    layout = json.loads((project / "Virtuoso" / "workspace-layout.json")
                        .read_text(encoding="utf-8"))
    roles = layout["roles"]
    lessons = project.joinpath(*roles["lessons"]["path"].split("/"))
    lessons.write_text("### LSN-001 — Gate %s check %s (A-1, 2026-09-01)\n"
                       "**Applies to:** gates %s checks\n**Status:** Observation\n"
                       % (ARROW, CHECK, ARROW), encoding="utf-8", newline="\n")
    closeouts = project.joinpath(*roles["closeOuts"]["path"].split("/"))
    (closeouts / ("CloseOut.A%sB.2026-09-27.md" % ARROW)).write_text("x\n", encoding="utf-8")
    return project


def test_the_stream_really_is_cp1252_without_the_fix():
    """The reproduction is sound: a plain print of the arrow fails on this stream."""
    completed = subprocess.run([sys.executable, "-c", "print('%s')" % ARROW],
                               capture_output=True,
                               env=dict(os.environ, PYTHONIOENCODING="cp1252"))
    assert completed.returncode != 0
    assert b"charmap" in completed.stderr


@pytest.mark.parametrize("args", [
    ("lessons", "--open"),
    ("lessons", "--open", "--json"),
    ("lessons",),
    ("protected", "--json"),
    ("protected",),
])
def test_registry_commands_write_utf8_to_a_cp1252_stream(workspace, args):
    completed = run_cp1252(REGISTRY_CLI, "--root", str(workspace), *args)
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    text = completed.stdout.decode("utf-8")
    # JSON output is ASCII-escaped (VIR-010): the arrow survives the round trip.
    assert ARROW in (json.dumps(json.loads(text), ensure_ascii=False) if "--json" in args
                     else text)


def test_an_error_message_reaches_a_cp1252_stderr(workspace):
    completed = run_cp1252(REGISTRY_CLI, "--root", str(workspace), "lessons", "--check",
                           "nowhere-%s.md" % ARROW)
    assert completed.returncode == 3
    assert ("nowhere-%s.md" % ARROW) in completed.stderr.decode("utf-8")
    assert b"Traceback" not in completed.stderr


def test_the_preflight_writes_utf8_to_a_cp1252_stream(workspace):
    completed = run_cp1252(PREFLIGHT, "--root", str(workspace), "--mode", "check", "--json")
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    text = completed.stdout.decode("utf-8")
    assert text.startswith("virtuoso-status: ")
    json.loads(text[text.index("{"):])      # the JSON follows the five machine lines


@pytest.mark.parametrize("script", ["virtuoso_registry.py", "virtuoso_preflight.py",
                                    "dispatch_guards.py", "build_register_report.py"])
def test_every_user_facing_entry_point_asks_for_utf8(script):
    """The fix lives in each entry point's main, so a new command cannot miss it
    without this test naming it."""
    text = (SCRIPTS / script).read_text(encoding="utf-8")
    body = text.split("def main(", 1)[1]
    assert "textio.utf8_stdio()" in body.split("\n", 3)[1] + body.split("\n", 3)[2]


def test_the_board_entry_point_asks_for_utf8():
    text = (ROOT / "tools" / "roadmap_visualizer" / "generate.py").read_text(encoding="utf-8")
    assert "textio.utf8_stdio()" in text.split("def board_main(", 1)[1].split("\n", 3)[1]


def test_json_output_is_ascii_safe(project):
    from test_tooling import build_external_workspace
    build_external_workspace(project)
    snapshot = project / "Virtuoso" / "work-register.snapshot.json"
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    data["items"][0]["title"] = "Board change — one per call"
    snapshot.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    completed = run_cp1252(REGISTRY_CLI, "--root", str(project), "items", "--json")
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert completed.stdout and all(byte < 0x80 for byte in completed.stdout)
    titles = [item["title"] for item in json.loads(completed.stdout)["items"]]
    assert titles == ["Board change — one per call"]
