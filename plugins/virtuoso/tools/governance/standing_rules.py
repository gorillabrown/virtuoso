"""Standing rules: declared once in policy, defined once in their source document.

``policy.standingRules.ids`` declares the rules every item inherits;
``policy.standingRules.source`` names the registered role whose document defines
them (the roadmap, by default). The pairing rule applies here as it does to
overlays and deadlines: each declared id must head a section in that document —
a depth 2-4 heading starting with the id — or the rule every item is said to
inherit has no text anyone can apply.

Findings are warnings or information, never errors: a project's rules are the
project's to fix.
"""
from __future__ import annotations

import os

from . import overlays as overlays_mod, policy as policy_mod, textio
from .registry import Finding

UNPAIRED = "standing-rule-unpaired"
SOURCE_UNREGISTERED = "standing-rules-source-unregistered"
SOURCE_UNREAD = "standing-rules-source-unread"
FINDING_CODES = (UNPAIRED, SOURCE_UNREGISTERED, SOURCE_UNREAD)

#: "The caller has not read the source; read it here."
UNREAD = object()


def declared(reg) -> tuple[list[str], str]:
    """``(rule ids, source role name)`` from the project's policy."""
    project_policy = policy_mod.load(reg.policy)
    ids = project_policy.get("standingRules.ids") or []
    ids = [str(i).strip() for i in ids if str(i).strip()] if isinstance(ids, list) else []
    return ids, str(project_policy.get("standingRules.source") or "roadmap")


def findings(reg, *, source_raw=UNREAD) -> list[Finding]:
    """The pairing findings for the declared standing rules. ``source_raw`` is the
    source document's bytes when the caller has already read them."""
    ids, role = declared(reg)
    if not ids:
        return []
    spec = reg.roles.get(role)
    if spec is None:
        return [Finding(SOURCE_UNREGISTERED, "warning",
                        "policy.standingRules.source names %r, which is not a registered role; "
                        "%d declared rule(s) have nowhere to be defined" % (role, len(ids)),
                        role=role)]
    if spec.is_external:
        return [Finding(SOURCE_UNREAD, "info",
                        "the standing rules' source %r is external and is not read here; "
                        "their definitions are not checked" % role, role=role)]
    if source_raw is UNREAD:
        source_raw = textio.read_bytes(os.path.join(reg.root, *spec.path.split("/")))
    text = textio.decode(source_raw) if source_raw is not None else None
    if text is None:
        return [Finding(SOURCE_UNREAD, "warning",
                        "the standing rules' source %s cannot be read, so %d declared rule(s) "
                        "cannot be checked" % (spec.path, len(ids)), role=role)]
    body = overlays_mod.without_fenced_blocks(text)
    return [Finding(UNPAIRED, "warning",
                    "standing rule %s is declared in policy.standingRules.ids and no heading "
                    "in %s starts with it: every item is said to inherit a rule with no text"
                    % (rule, spec.path), role=role, identifier=rule)
            for rule in ids if not overlays_mod.body_heading(rule).search(body)]
