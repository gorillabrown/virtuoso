"""The human governance registry view (``Virtuoso.Governance.Readme.md``).

Redesign items 5, 13, 18, 89.

The readme is a **generated view** of the manifest, not an independent
authority. It is never regenerated from a fixed template over an existing file.
Instead it carries two plugin-owned regions:

* a *generated region* between ``<!-- virtuoso:begin-generated -->`` and
  ``<!-- virtuoso:end-generated -->`` holding the role table, and
* a *machine block* — ``<!-- virtuoso-governance-registry ... -->`` — a
  verbatim-parseable ``role: target`` mapping that lets a lost manifest be
  reconstructed.

Everything outside those two regions is user prose and is preserved
byte-for-byte. A readme with no generated region is a *user-authored* registry:
the plugin reads it, reports divergence from the manifest as a diagnostic, and
refuses to rewrite it without an approved repair (item 13).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

BEGIN_MARK = "<!-- virtuoso:begin-generated -->"
END_MARK = "<!-- virtuoso:end-generated -->"

_GENERATED_RE = re.compile(
    re.escape(BEGIN_MARK) + r"\n(?P<body>.*?)\n?" + re.escape(END_MARK),
    re.DOTALL,
)
_MACHINE_RE = re.compile(
    r"<!--\s*virtuoso-governance-registry\s*\n(?P<body>.*?)\n-->",
    re.DOTALL,
)
_MACHINE_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.\-]*):\s*(.+)$")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<!^)(?=[A-Z])")


@dataclass
class ReadmeView:
    text: str
    has_generated_region: bool
    has_machine_block: bool
    targets: dict[str, str]

    @property
    def is_plugin_managed(self) -> bool:
        """True when the readme carries the plugin's generated region — the only
        shape the plugin may rewrite without an approved repair."""
        return self.has_generated_region


def parse(text: str | None) -> ReadmeView:
    if text is None:
        return ReadmeView(text="", has_generated_region=False, has_machine_block=False, targets={})
    machine = _MACHINE_RE.search(text)
    targets: dict[str, str] = {}
    if machine:
        for line in machine.group("body").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = _MACHINE_LINE_RE.match(line)
            if match:
                targets[match.group(1)] = match.group(2).strip()
    return ReadmeView(
        text=text,
        has_generated_region=bool(_GENERATED_RE.search(text)),
        has_machine_block=bool(machine),
        targets=targets,
    )


def derive_label(name: str, *, directory: bool = False) -> str:
    """Human label for a role with no declared one: split camelCase, sentence-case,
    and mark directories. ``x-roadmapArchives`` -> ``Roadmap archives (directory)``."""
    stem = name[2:] if name.startswith("x-") else name
    spaced = _CAMEL_BOUNDARY_RE.sub(" ", stem).replace("-", " ").replace("_", " ")
    label = spaced.strip()
    label = label[:1].upper() + label[1:] if label else stem
    if directory and "(directory)" not in label:
        label += " (directory)"
    return label


def render_table(roles) -> str:
    """The generated role table. ``roles`` is an ordered iterable of RoleSpec."""
    header = (
        "| Role | Target | Provider | Authority | Mutability | Writers | State |\n"
        "|------|--------|----------|-----------|------------|---------|-------|"
    )
    rows = []
    for role in roles:
        label = role.label or derive_label(role.name, directory=role.is_directory)
        target = "`%s`" % role.target if role.target else "—"
        writers = ", ".join(role.allowed_writers) if role.allowed_writers else "—"
        rows.append(
            "| %s | %s | %s | %s | %s | %s | %s |"
            % (label, target, role.provider, role.authority, role.mutability,
               writers, _presence_label(role.presence))
        )
    return header + "\n" + "\n".join(rows) if rows else header


def _presence_label(presence: str) -> str:
    return {
        "present": "present",
        "absent": "registered, not present",
        "external": "external",
        "unverifiable": "unverified",
    }.get(presence, presence)


def render_machine_block(roles) -> str:
    lines = ["<!-- virtuoso-governance-registry"]
    lines.append("# Generated view of Virtuoso/workspace-layout.json — the manifest is the authority.")
    for role in roles:
        if role.target:
            lines.append("%s: %s" % (role.name, role.target))
    lines.append("-->")
    return "\n".join(lines)


def render_generated_region(roles) -> str:
    return "\n".join([BEGIN_MARK, render_table(roles), "", render_machine_block(roles), END_MARK])


def sync(existing: str | None, roles) -> tuple[str, str]:
    """Return ``(new_text, action)`` for a readme synchronized to ``roles``.

    ``action`` is one of:

    * ``"created"`` — no readme existed; a fresh one is composed from the
      template (only ``create`` mode ever accepts this).
    * ``"updated"`` — the plugin's generated region was replaced in place; every
      byte outside it is preserved.
    * ``"unmanaged"`` — the readme exists but carries no generated region. The
      text is returned unchanged; the caller must report divergence rather than
      overwrite (item 5/13).
    """
    region = render_generated_region(roles)
    if existing is None:
        return _FRESH_TEMPLATE.replace("{generated}", region), "created"
    match = _GENERATED_RE.search(existing)
    if not match:
        return existing, "unmanaged"
    return existing[: match.start()] + region + existing[match.end():], "updated"


_FRESH_TEMPLATE = """# Virtuoso Governance Registry

`Virtuoso/workspace-layout.json` is the **authority** for this project's governance
configuration. This document is a synchronized, human-readable view of it.

Everything outside the generated region below is yours: prose, extra tables, notes,
project-specific rules. The plugin never rewrites it. Inside the generated region the
plugin renders the registered roles; edit the manifest (or run the registry repair
preview) to change them.

## Registered roles

{generated}

## Rules for skills

1. **Resolve every governance document through this registry** before reading or writing.
2. **Never create a new document for a role already registered** — open the registered
   target in place.
3. A registered target that is absent is *reported*, never replaced by a similarly named
   file the plugin went looking for.
4. **Authority is declared, not inferred.** A role is authoritative only when its
   `authority` says so.
5. Write only to a role whose `allowedWriters` names you, and never to an `archive`,
   `immutable`, `read-only`, or `unknown` role.
6. Project-defined roles and metadata live under the `x-` prefix and are preserved
   verbatim across plugin upgrades.

## Project extensions

<!-- Add your own roles, notes, and tables here. This section is never regenerated. -->
"""
