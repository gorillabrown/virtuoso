#!/usr/bin/env python3
"""Promoted-rule anchors that MUST be present in shipped skill bodies.

Promoting a rule into a lessons catalog produces documentation, not enforcement:
agent execution paths read skill bodies at session start, never the catalog
(SRL-122). A promoted rule with no dispatch-time machinery is applied
inconsistently, by agent discretion (SRL-046). This manifest is that machinery
for prose -- `validate.py` fails CI when a skill body loses an anchor listed here.

Each anchor appears in its SKILL.md exactly as::

    <!-- rule:<anchor> (<citation>) -->

on the line immediately above the rule it guards. Adding a rule to a skill body
without registering it here means a later edit can silently drop it, which is the
failure this file exists to prevent -- so the manifest entry is part of the rule,
not paperwork about it.
"""
import os

REQUIRED_RULE_ANCHORS = {
    "virtuoso": [
        ("calibration-routing", "SRL-087"),
        ("registry-resolved-staging", "AMEND-THE-RESTATEMENTS"),
        ("lane-declaration", "SRL-551"),
        ("merge-through-slot", "SRL-551"),
        ("checkpoint-commits", "SRL-065"),
        ("worker-output-validation", "SRL-513"),
    ],
    "governance-sweep": [
        ("grep-registry-before-moving", "SRL-680"),
    ],
}


def anchor_comment(anchor, citation):
    """The exact marker text `missing_anchors` searches for."""
    return "<!-- rule:%s (%s) -->" % (anchor, citation)


def missing_anchors(skills_dir):
    """Registered anchors absent from their skill body.

    Returns a sorted-by-registration list of "<skill>:<anchor> (<citation>)"
    strings; empty means every promoted rule is still in place. A skill with no
    readable SKILL.md yields a single "<skill>:<no SKILL.md>" entry rather than
    one line per anchor -- the file is the problem, not each rule in it.
    """
    missing = []
    for skill, anchors in sorted(REQUIRED_RULE_ANCHORS.items()):
        path = os.path.join(skills_dir, skill, "SKILL.md")
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            if anchors:
                missing.append("%s:<no SKILL.md>" % skill)
            continue
        for anchor, citation in anchors:
            if anchor_comment(anchor, citation) not in text:
                missing.append("%s:%s (%s)" % (skill, anchor, citation))
    return missing
