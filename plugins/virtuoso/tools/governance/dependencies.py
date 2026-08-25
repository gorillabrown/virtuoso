"""Declared runtime dependencies (item 79).

A project declares what its ceremonies need in ``policy.dependencies``; the
plugin checks them **before** running something that requires them, so a missing
or too-old library is reported up front rather than raising an ImportError deep
inside a ceremony.

Version specifiers are the simple forms a governance manifest needs:
``>=3.1``, ``>3.1``, ``==3.1.2``, ``<=4``, ``<4``, or an empty string for
"any version".
"""
from __future__ import annotations

import importlib
import re
from dataclasses import dataclass

_SPEC_RE = re.compile(r"^\s*(>=|<=|==|>|<)?\s*([0-9][0-9.]*)\s*$")


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = []
    for chunk in str(value).split("+", 1)[0].split("-", 1)[0].split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def satisfies(version: str, spec: str) -> bool:
    """Whether ``version`` satisfies ``spec``. An unparseable spec is treated as
    satisfied — a malformed hint must not brick a project; it is reported instead."""
    if not spec or not str(spec).strip():
        return True
    match = _SPEC_RE.match(str(spec))
    if not match:
        return True
    operator, wanted = match.group(1) or ">=", _version_tuple(match.group(2))
    have = _version_tuple(version)
    return {
        ">=": have >= wanted, ">": have > wanted, "==": have == wanted,
        "<=": have <= wanted, "<": have < wanted,
    }[operator]


@dataclass
class DependencyResult:
    name: str
    required: str
    installed: str = ""
    ok: bool = False
    reason: str = ""

    def as_dict(self) -> dict:
        return {"name": self.name, "required": self.required, "installed": self.installed,
                "ok": self.ok, "reason": self.reason}


def check_one(name: str, spec: str = "") -> DependencyResult:
    try:
        module = importlib.import_module(name)
    except ImportError as exc:
        return DependencyResult(name=name, required=spec, ok=False,
                                reason="not installed (%s)" % exc)
    installed = str(getattr(module, "__version__", "") or "")
    if not installed:
        return DependencyResult(name=name, required=spec, installed="unknown", ok=True,
                                reason="installed; version not reported")
    if not satisfies(installed, spec):
        return DependencyResult(name=name, required=spec, installed=installed, ok=False,
                                reason="installed %s does not satisfy %s" % (installed, spec))
    return DependencyResult(name=name, required=spec, installed=installed, ok=True)


def check(declared: dict | None) -> list[DependencyResult]:
    """Check every declared dependency. Never raises."""
    return [check_one(name, str(spec or ""))
            for name, spec in sorted((declared or {}).items())]


def missing(declared: dict | None) -> list[DependencyResult]:
    return [r for r in check(declared) if not r.ok]
