"""Immutable-hash verification for protected files (item 62).

A governance sweep hashes every protected historical file before it starts and
again when it finishes. Any change is a defect in the sweep itself, not a
finding about the project, and it halts the run.

"Protected" is the project's declaration, not the plugin's guess: it is every
role whose authority is in ``policy.sweep.protectedAuthorities`` or whose
mutability is ``immutable`` or ``read-only``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from . import policy as policy_mod, textio


@dataclass
class IntegritySnapshot:
    """``{project-relative path: sha256}`` for every protected file."""

    hashes: dict[str, str] = field(default_factory=dict)
    unreadable: list[str] = field(default_factory=list)
    roles: dict[str, list[str]] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"hashes": dict(self.hashes), "unreadable": list(self.unreadable),
                "roles": {k: list(v) for k, v in self.roles.items()}}


def protected_roles(reg) -> list:
    """The roles a sweep may never mutate."""
    project_policy = policy_mod.load(reg.policy)
    authorities = set(project_policy.get("sweep.protectedAuthorities", []) or [])
    out = []
    for spec in reg.roles.values():
        if spec.is_external:
            continue
        if spec.authority in authorities or spec.mutability in ("immutable", "read-only"):
            out.append(spec)
    return out


def _files_under(absolute: str) -> list[str]:
    if os.path.isfile(absolute):
        return [absolute]
    found = []
    for dirpath, dirnames, filenames in os.walk(absolute):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for name in sorted(filenames):
            found.append(os.path.join(dirpath, name))
    return found


def snapshot(reg) -> IntegritySnapshot:
    """Hash every protected file. Pure inspection; never writes."""
    result = IntegritySnapshot()
    for spec in protected_roles(reg):
        absolute = os.path.join(reg.root, *spec.path.split("/"))
        members = []
        for path in _files_under(absolute):
            rel = os.path.relpath(path, reg.root).replace("\\", "/")
            members.append(rel)
            try:
                result.hashes[rel] = textio.sha256_file(path)
            except OSError:
                result.unreadable.append(rel)
        if members:
            result.roles[spec.name] = members
    return result


def compare(before: IntegritySnapshot, after: IntegritySnapshot) -> list[str]:
    """Problems, in the order a report should print them. Empty means intact."""
    problems: list[str] = []
    for rel, digest in before.hashes.items():
        if rel not in after.hashes:
            problems.append("protected file removed during the run: %s" % rel)
        elif after.hashes[rel] != digest:
            problems.append("protected file modified during the run: %s (%s -> %s)"
                            % (rel, digest[:12], after.hashes[rel][:12]))
    for rel in after.hashes:
        if rel not in before.hashes:
            problems.append("file appeared inside a protected role during the run: %s" % rel)
    return problems
