"""Version-qualified installation records and a host-neutral launcher (items 12, 77, 78).

The old design wrote a single machine-global, *unversioned* pointer file. Two
concurrently installed plugin versions raced each other for it, and whoever ran
last repointed every project on the machine at its own copy.

This module replaces that with:

* ``<home>/.virtuoso/installs.json`` — a record keyed **by plugin version**, so
  installing or running a second version never overwrites the first one's entry;
* ``<home>/.virtuoso/bin/virtuoso`` and ``virtuoso.ps1`` — small, *version-
  agnostic* launchers whose content is identical for every version (so concurrent
  writers are idempotent) and which resolve the newest valid install at run time.

Resolution order, used by the launchers and by :func:`resolve`:

1. ``VIRTUOSO_PLUGIN_ROOT`` — an explicit override always wins.
2. the highest version in ``installs.json`` whose recorded root is still valid.
3. nothing — callers must report that the plugin could not be located rather
   than guessing at a home-directory layout.

Nothing here ever writes inside a *project*.
"""
from __future__ import annotations

import datetime as _dt
import json
import os

from . import textio

RECORD_NAME = "installs.json"
RECORD_VERSION = 1


def home() -> str:
    return os.environ.get("VIRTUOSO_HOME") or os.path.expanduser("~")


def state_dir() -> str:
    return os.path.join(home(), ".virtuoso")


def record_path() -> str:
    return os.path.join(state_dir(), RECORD_NAME)


def bin_dir() -> str:
    return os.path.join(state_dir(), "bin")


def is_valid_root(path) -> bool:
    """True when ``path`` really is a plugin root. Type-guarded because the value
    can come from a JSON file this module does not own."""
    if not isinstance(path, str) or not path:
        return False
    try:
        return os.path.isfile(os.path.join(path, "scripts", "virtuoso_preflight.py"))
    except (OSError, ValueError):
        return False


def _version_key(value: str) -> tuple:
    parts = []
    for chunk in str(value).split("-", 1)[0].split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def read_records() -> dict:
    text = textio.read_text(record_path())
    if text is None:
        return {}
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    installs = data.get("installs") if isinstance(data, dict) else None
    return installs if isinstance(installs, dict) else {}


def record(plugin_root: str, version: str, *, now: _dt.datetime | None = None) -> bool:
    """Record ``plugin_root`` under ``version``. Returns True when the file changed.

    Only this version's entry is touched; every other version's entry is carried
    through verbatim, so two installed versions never clobber each other.
    Non-fatal: any I/O failure leaves the previous state untouched.
    """
    if not is_valid_root(plugin_root) or not version:
        return False
    try:
        installs = read_records()
        stamp = (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
        existing = installs.get(version)
        if isinstance(existing, dict) and existing.get("root") == plugin_root:
            return False  # unchanged — no mtime churn
        installs[version] = {"root": plugin_root, "recordedAt": stamp}
        payload = {"recordVersion": RECORD_VERSION, "installs": installs}
        os.makedirs(state_dir(), exist_ok=True)
        return textio.write_if_changed(
            record_path(), json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    except OSError:
        return False


def resolve(version: str = "") -> str:
    """The plugin root to use. See the module docstring for the order."""
    override = os.environ.get("VIRTUOSO_PLUGIN_ROOT")
    if is_valid_root(override):
        return override
    installs = read_records()
    if version:
        entry = installs.get(version)
        if isinstance(entry, dict) and is_valid_root(entry.get("root")):
            return entry["root"]
    for name in sorted(installs, key=_version_key, reverse=True):
        entry = installs.get(name)
        if isinstance(entry, dict) and is_valid_root(entry.get("root")):
            return entry["root"]
    return ""


def forget(version: str) -> bool:
    installs = read_records()
    if version not in installs:
        return False
    installs.pop(version)
    payload = {"recordVersion": RECORD_VERSION, "installs": installs}
    return textio.write_if_changed(
        record_path(), json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


POSIX_LAUNCHER = """#!/bin/sh
# Virtuoso launcher (version-agnostic — identical content for every installed
# version, so concurrent versions writing it is idempotent).
#
# Resolves the plugin root from $VIRTUOSO_PLUGIN_ROOT, else the newest valid
# entry in ~/.virtuoso/installs.json.
#
# Usage: virtuoso <script-name> [args...]
#   virtuoso virtuoso_preflight --root . --mode check
#   virtuoso virtuoso_registry --root . next
set -eu

if [ "$#" -lt 1 ]; then
  echo "usage: virtuoso <script-name> [args...]" >&2
  exit 2
fi

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

VIRTUOSO_ROOT=$("$PY" - <<'PY'
import json, os, sys

def valid(path):
    return bool(path) and os.path.isfile(os.path.join(path, "scripts", "virtuoso_preflight.py"))

override = os.environ.get("VIRTUOSO_PLUGIN_ROOT", "")
if valid(override):
    print(override)
    sys.exit(0)

home = os.environ.get("VIRTUOSO_HOME") or os.path.expanduser("~")
record = os.path.join(home, ".virtuoso", "installs.json")

def key(name):
    parts = []
    for chunk in str(name).split("-", 1)[0].split("."):
        parts.append(int(chunk) if chunk.isdigit() else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])

try:
    with open(record, encoding="utf-8") as handle:
        installs = json.load(handle).get("installs", {})
except (OSError, ValueError, AttributeError):
    installs = {}

for name in sorted(installs, key=key, reverse=True):
    entry = installs.get(name) or {}
    if valid(entry.get("root", "")):
        print(entry["root"])
        sys.exit(0)
print("")
PY
)

if [ -z "$VIRTUOSO_ROOT" ]; then
  echo "virtuoso: no installed plugin root found. Set VIRTUOSO_PLUGIN_ROOT, or reinstall the plugin." >&2
  exit 1
fi

SCRIPT="$1"
shift
exec "$PY" "$VIRTUOSO_ROOT/scripts/$SCRIPT.py" "$@"
"""

POWERSHELL_LAUNCHER = """# Virtuoso launcher (version-agnostic — identical content for every installed
# version, so concurrent versions writing it is idempotent).
#
# Resolves the plugin root from $env:VIRTUOSO_PLUGIN_ROOT, else the newest valid
# entry in ~/.virtuoso/installs.json.
#
# Usage: virtuoso.ps1 <script-name> [args...]
#   ./virtuoso.ps1 virtuoso_preflight --root . --mode check
#   ./virtuoso.ps1 virtuoso_registry --root . next
param(
  [Parameter(Mandatory = $true, Position = 0)][string]$Script,
  [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest
)

function Test-VirtuosoRoot([string]$Path) {
  return $Path -and (Test-Path (Join-Path $Path 'scripts/virtuoso_preflight.py'))
}

$root = $env:VIRTUOSO_PLUGIN_ROOT
if (-not (Test-VirtuosoRoot $root)) {
  $stateHome = if ($env:VIRTUOSO_HOME) { $env:VIRTUOSO_HOME } else { $HOME }
  $record = Join-Path $stateHome '.virtuoso/installs.json'
  $root = ''
  if (Test-Path $record) {
    $installs = (Get-Content $record -Raw | ConvertFrom-Json).installs
    if ($installs) {
      $names = $installs.PSObject.Properties.Name |
        Sort-Object { try { [version](($_ -split '-')[0]) } catch { [version]'0.0.0' } } -Descending
      foreach ($name in $names) {
        $candidate = $installs.$name.root
        if (Test-VirtuosoRoot $candidate) { $root = $candidate; break }
      }
    }
  }
}

if (-not (Test-VirtuosoRoot $root)) {
  Write-Error 'virtuoso: no installed plugin root found. Set VIRTUOSO_PLUGIN_ROOT, or reinstall the plugin.'
  exit 1
}

$py = if (Get-Command python3 -ErrorAction SilentlyContinue) { 'python3' } else { 'python' }
& $py (Join-Path $root "scripts/$Script.py") @Rest
exit $LASTEXITCODE
"""


def ensure_launchers() -> list[str]:
    """Write the launchers if their content differs. Content is identical across
    plugin versions, so concurrent versions writing them is idempotent."""
    written = []
    try:
        os.makedirs(bin_dir(), exist_ok=True)
        posix = os.path.join(bin_dir(), "virtuoso")
        if textio.write_if_changed(posix, POSIX_LAUNCHER):
            written.append(posix)
        try:
            os.chmod(posix, 0o755)
        except OSError:
            pass
        pwsh = os.path.join(bin_dir(), "virtuoso.ps1")
        if textio.write_if_changed(pwsh, POWERSHELL_LAUNCHER):
            written.append(pwsh)
    except OSError:
        pass
    return written
