"""Guard state: the one place cost guards write, the user's own ``~/.virtuoso/guard/``.

Hooks never write a project file. Bindings, hold marks, receipts and handoff notes all live
here, each file written atomically (write a temporary file, then rename it over the old).
"""
from __future__ import annotations

import json
import os

from . import install


def guard_dir() -> str:
    """Where guard state lives: the user's own folder, never a project."""
    return os.path.join(install.state_dir(), "guard")


def write_json_atomic(path: str, data) -> None:
    """Write ``data`` as JSON to ``path`` under :func:`guard_dir`, atomically."""
    if not os.path.abspath(path).startswith(os.path.abspath(guard_dir()) + os.sep):
        raise ValueError("guard state is written only under %s, not %s" % (guard_dir(), path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = "%s.%d.tmp" % (path, os.getpid())
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
    os.replace(temp, path)


def _inside(path: str) -> None:
    if not os.path.abspath(path).startswith(os.path.abspath(guard_dir()) + os.sep):
        raise ValueError("guard state is written only under %s, not %s" % (guard_dir(), path))


def append_jsonl(path: str, data: dict) -> None:
    """Append one JSON line to ``path`` under :func:`guard_dir` (receipts)."""
    _inside(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=True, sort_keys=True) + "\n")


def remove(path: str) -> None:
    """Delete one guard-state file (a used or expired handoff note)."""
    _inside(path)
    try:
        os.remove(path)
    except OSError:
        pass


def create_once(path: str) -> bool:
    """Create the empty file ``path`` under :func:`guard_dir` only if it does not exist:
    ``True`` for the one caller that created it. Two hooks racing on one key never both
    win."""
    _inside(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        return False
    return True


class Lock:
    """An exclusive lock file beside ``path`` for a read-modify-write of one JSON file. A
    lock older than ``stale`` seconds (a killed hook) is taken over; after ``wait`` seconds
    the caller goes ahead unlocked rather than stall a hook."""

    def __init__(self, path: str, wait: float = 2.0, stale: float = 10.0):
        self.path, self.wait, self.stale, self.held = path + ".lock", wait, stale, False

    def __enter__(self):
        import time
        _inside(self.path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        deadline = time.monotonic() + self.wait
        while True:
            try:
                os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                self.held = True
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.path) > self.stale:
                        os.remove(self.path)
                        continue
                except OSError:
                    continue
                if time.monotonic() > deadline:
                    return self
                time.sleep(0.02)

    def __exit__(self, *exc):
        if self.held:
            try:
                os.remove(self.path)
            except OSError:
                pass
        return False


def read_json(path: str):
    """The JSON at ``path``, or ``None`` when it is missing or cannot be read."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None
