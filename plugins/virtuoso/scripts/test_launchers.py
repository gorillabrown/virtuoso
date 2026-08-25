"""Cross-platform launcher and install-record coverage (items 12, 77, 78, 96).

The launchers are the only supported way for a skill body to locate the plugin.
They must resolve the newest valid *installed version* — never a hardcoded home
path — and two concurrently installed versions must not overwrite each other's
discovery state.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from tools.governance import install

PREFLIGHT = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_preflight.py")


# --- the version-qualified record ---------------------------------------------


def test_the_record_is_keyed_by_version(isolated_home):
    assert install.record(PLUGIN_ROOT, "2.0.0") is True
    assert install.record(PLUGIN_ROOT, "2.1.0") is True
    records = install.read_records()
    assert sorted(records) == ["2.0.0", "2.1.0"]
    assert records["2.0.0"]["root"] == PLUGIN_ROOT


def test_a_second_version_never_clobbers_the_first(isolated_home, tmp_path):
    """Item 12: concurrent plugin versions must not overwrite each other."""
    older = tmp_path / "v1"
    (older / "scripts").mkdir(parents=True)
    (older / "scripts" / "virtuoso_preflight.py").write_text("", encoding="utf-8")

    install.record(str(older), "1.9.0")
    install.record(PLUGIN_ROOT, "2.0.0")
    records = install.read_records()
    assert records["1.9.0"]["root"] == str(older)
    assert records["2.0.0"]["root"] == PLUGIN_ROOT
    # The newest valid install wins resolution.
    assert install.resolve() == PLUGIN_ROOT
    # ...and an explicit version can still be asked for.
    assert install.resolve("1.9.0") == str(older)


def test_recording_the_same_value_twice_does_not_churn(isolated_home):
    assert install.record(PLUGIN_ROOT, "2.0.0") is True
    assert install.record(PLUGIN_ROOT, "2.0.0") is False


def test_an_invalid_root_is_never_recorded(isolated_home, tmp_path):
    assert install.record(str(tmp_path / "not-a-plugin"), "3.0.0") is False
    assert install.read_records() == {}


def test_an_environment_override_wins(isolated_home, monkeypatch):
    install.record(PLUGIN_ROOT, "2.0.0")
    monkeypatch.setenv("VIRTUOSO_PLUGIN_ROOT", PLUGIN_ROOT)
    assert install.resolve() == PLUGIN_ROOT
    monkeypatch.setenv("VIRTUOSO_PLUGIN_ROOT", "/definitely/not/a/plugin")
    assert install.resolve() == PLUGIN_ROOT      # falls back to the record


def test_a_stale_record_entry_is_skipped(isolated_home, tmp_path):
    gone = tmp_path / "uninstalled"
    (gone / "scripts").mkdir(parents=True)
    (gone / "scripts" / "virtuoso_preflight.py").write_text("", encoding="utf-8")
    install.record(str(gone), "9.9.9")
    install.record(PLUGIN_ROOT, "2.0.0")
    shutil.rmtree(gone)
    assert install.resolve() == PLUGIN_ROOT


def test_no_unversioned_pointer_file_is_written(isolated_home):
    install.record(PLUGIN_ROOT, "2.0.0")
    install.ensure_launchers()
    assert not (Path(isolated_home) / ".virtuoso" / "plugin-root").exists()


# --- launcher content ----------------------------------------------------------


def test_launchers_are_written_and_idempotent(isolated_home):
    first = install.ensure_launchers()
    assert len(first) == 2
    assert install.ensure_launchers() == []      # identical content, no rewrite


def test_the_bundled_launchers_match_the_source_of_record():
    for name, expected in (("virtuoso", install.POSIX_LAUNCHER),
                           ("virtuoso.ps1", install.POWERSHELL_LAUNCHER)):
        with open(os.path.join(PLUGIN_ROOT, "bin", name), encoding="utf-8",
                  newline="") as handle:
            assert handle.read() == expected


@pytest.mark.parametrize("name", ["virtuoso", "virtuoso.ps1"])
def test_launchers_hardcode_no_install_path(name):
    text = getattr(install, "POSIX_LAUNCHER" if name == "virtuoso"
                   else "POWERSHELL_LAUNCHER")
    assert ".claude/plugins" not in text
    assert "plugin-root" not in text
    assert "installs.json" in text
    assert "VIRTUOSO_PLUGIN_ROOT" in text


def test_the_powershell_launcher_uses_powershell_constructs_only():
    text = install.POWERSHELL_LAUNCHER
    assert "param(" in text
    assert "$env:VIRTUOSO_PLUGIN_ROOT" in text
    assert "Test-Path" in text
    assert "ConvertFrom-Json" in text
    assert "$LASTEXITCODE" in text
    # No Unix-only syntax leaked in.
    assert "$(cat " not in text
    assert "#!/bin/sh" not in text


def test_the_posix_launcher_uses_posix_constructs_only():
    text = install.POSIX_LAUNCHER
    assert text.startswith("#!/bin/sh")
    assert "set -eu" in text
    assert "exec " in text
    # It must not depend on bash-only syntax.
    assert "[[" not in text
    assert "function " not in text


# --- the POSIX launcher, actually run ------------------------------------------

posix_only = pytest.mark.skipif(os.name == "nt", reason="POSIX shell launcher")


@posix_only
def test_the_posix_launcher_runs_a_script(isolated_home, project):
    subprocess.run([sys.executable, PREFLIGHT, "--root", str(project), "--mode", "check"],
                   capture_output=True, env=dict(os.environ))
    launcher = Path(isolated_home) / ".virtuoso" / "bin" / "virtuoso"
    assert launcher.exists() and os.access(launcher, os.X_OK)

    completed = subprocess.run([str(launcher), "virtuoso_preflight", "--root", str(project),
                                "--mode", "check"],
                               capture_output=True, text=True, env=dict(os.environ))
    assert completed.returncode == 0, completed.stderr
    assert "virtuoso-status: " in completed.stdout
    assert "writes: 0" in completed.stdout


@posix_only
def test_the_posix_launcher_reports_a_missing_install(isolated_home, tmp_path):
    install.ensure_launchers()
    launcher = Path(isolated_home) / ".virtuoso" / "bin" / "virtuoso"
    env = dict(os.environ)
    env["VIRTUOSO_HOME"] = str(tmp_path / "empty-home")
    env.pop("VIRTUOSO_PLUGIN_ROOT", None)
    completed = subprocess.run([str(launcher), "virtuoso_preflight"],
                               capture_output=True, text=True, env=env)
    assert completed.returncode == 1
    assert "no installed plugin root found" in completed.stderr


@posix_only
def test_the_posix_launcher_requires_a_script_name(isolated_home):
    install.ensure_launchers()
    launcher = Path(isolated_home) / ".virtuoso" / "bin" / "virtuoso"
    completed = subprocess.run([str(launcher)], capture_output=True, text=True,
                               env=dict(os.environ))
    assert completed.returncode == 2
    assert "usage:" in completed.stderr


@posix_only
def test_the_posix_launcher_honours_the_environment_override(isolated_home, project,
                                                             tmp_path):
    install.ensure_launchers()
    launcher = Path(isolated_home) / ".virtuoso" / "bin" / "virtuoso"
    env = dict(os.environ)
    env["VIRTUOSO_HOME"] = str(tmp_path / "no-record-here")
    env["VIRTUOSO_PLUGIN_ROOT"] = PLUGIN_ROOT
    completed = subprocess.run([str(launcher), "virtuoso_preflight", "--root", str(project),
                                "--mode", "check"],
                               capture_output=True, text=True, env=env)
    assert completed.returncode == 0, completed.stderr
    assert "virtuoso-status: " in completed.stdout


# --- the PowerShell launcher, when pwsh is present -----------------------------


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh is not installed")
def test_the_powershell_launcher_runs_a_script(isolated_home, project):
    subprocess.run([sys.executable, PREFLIGHT, "--root", str(project), "--mode", "check"],
                   capture_output=True, env=dict(os.environ))
    launcher = Path(isolated_home) / ".virtuoso" / "bin" / "virtuoso.ps1"
    completed = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(launcher), "virtuoso_preflight",
         "--root", str(project), "--mode", "check"],
        capture_output=True, text=True, env=dict(os.environ))
    assert completed.returncode == 0, completed.stderr
    assert "virtuoso-status: " in completed.stdout


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh is not installed")
def test_the_powershell_launcher_reports_a_missing_install(isolated_home, tmp_path):
    install.ensure_launchers()
    launcher = Path(isolated_home) / ".virtuoso" / "bin" / "virtuoso.ps1"
    env = dict(os.environ)
    env["VIRTUOSO_HOME"] = str(tmp_path / "empty-home")
    env.pop("VIRTUOSO_PLUGIN_ROOT", None)
    completed = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(launcher), "virtuoso_preflight"],
        capture_output=True, text=True, env=env)
    assert completed.returncode != 0


# --- documentation shows both forms --------------------------------------------


def test_every_launcher_invocation_in_the_docs_shows_both_shells():
    """Item 77: no Unix-only launcher snippets."""
    contract = Path(PLUGIN_ROOT) / "references" / "registry-contract.md"
    text = contract.read_text(encoding="utf-8")
    assert "bin/virtuoso\"" in text or "bin/virtuoso'" in text
    assert "virtuoso.ps1" in text

    for skill in (Path(PLUGIN_ROOT) / "skills").glob("*/SKILL.md"):
        body = skill.read_text(encoding="utf-8")
        if "virtuoso_preflight --root . --mode check" not in body:
            continue
        assert "virtuoso.ps1" in body, "%s shows only a Unix launcher form" % skill.name
