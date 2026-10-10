"""Whether the board is current, without reading the work register.

The page embeds, for each local source it was built from (the register or its
snapshot, the ledger, the roadmap, the comments file), that file's modification time
at generation. Session start compares those with the times now: a change means the
page is stale. Only the manifest, file times and the page itself are read — never
the register, which may be external.
"""
from __future__ import annotations

import json
import os
import re

from tools.governance import policy as policy_mod, registry as registry_mod, textio

from . import board as board_mod

_DATA_RE = re.compile(r'<script id="board-data" type="application/json">(.*?)</script>', re.S)


def _mtime(path) -> float | None:
    try:
        return os.stat(path).st_mtime
    except (OSError, TypeError, ValueError):
        return None


def source_times(reg) -> list[dict]:
    """Each registered local source of the board, with its modification time now."""
    snapshot = str(policy_mod.load(reg.policy).get("workRegister.snapshot", "") or "")
    out = []
    for name in ("workRegister", snapshot, "terminalLedger", "roadmap",
                 board_mod.COMMENTS_ROLE):
        spec = reg.roles.get(name) if name else None
        if spec is None or spec.is_external or spec.is_directory or not spec.path:
            continue
        out.append({"role": name, "path": spec.path, "mtime": _mtime(reg.resolve(name))})
    return out


def embedded_model(text: str | None) -> dict | None:
    match = _DATA_RE.search(text or "")
    if not match:
        return None
    try:
        model = json.loads(match.group(1))
    except ValueError:
        return None
    return model if isinstance(model, dict) else None


def _differs(then, now) -> bool:
    """The same file's time, stored as a float and read back exactly: any difference,
    however small, is a write after generation."""
    if then is None or now is None:
        return (then is None) != (now is None)
    return float(then) != float(now)


def board_status(root: str) -> str:
    """The preflight ``board:`` state: ``not registered``, ``missing (...)``,
    ``unreadable (...)``, ``stale (...)`` or ``current (...)``. Advisory only."""
    reg = registry_mod.load(root)
    spec = reg.roles.get(board_mod.BOARD_ROLE)
    if spec is None:
        return "not registered"
    if spec.is_external or not spec.path:
        return "external (not checked)"
    path = reg.resolve(board_mod.BOARD_ROLE)
    if not os.path.isfile(path):
        return "missing (%s; generate_board --root . builds it)" % spec.path
    model = embedded_model(textio.read_text(path))
    if model is None:
        return "unreadable (%s carries no board model; regenerate it)" % spec.path
    then = {s.get("role"): s.get("mtime") for s in model.get("sources") or []
            if isinstance(s, dict)}
    now = {s["role"]: s["mtime"] for s in source_times(reg)}
    changed = sorted(role for role in set(then) | set(now)
                     if _differs(then.get(role), now.get(role)))
    if changed:
        return "stale (%s changed since %s)" % (", ".join(changed), model.get("generatedAt"))
    return "current (generated %s)" % model.get("generatedAt")
