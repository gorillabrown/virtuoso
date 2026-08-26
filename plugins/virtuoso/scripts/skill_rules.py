#!/usr/bin/env python3
"""Promoted-rule anchors that MUST be present in shipped skill bodies.

Promoting a rule into a project's lessons catalog produces documentation, not
enforcement: agent execution paths read skill bodies at session start, never the
catalog, and a promoted rule with no dispatch-time machinery is applied
inconsistently, by agent discretion. This manifest is that machinery for prose --
`validate.py` fails CI when a skill body loses an anchor listed here.

Each anchor appears in its SKILL.md exactly as::

    <!-- rule:<anchor> (<citation>) -->

on the line immediately above the rule it guards. Citations are host- and
project-neutral tags, never a specific project's rule identifiers; a consuming
project maps a tag back to its own catalog entry in its own register.

Adding a rule to a skill body without registering it here means a later edit can
silently drop it, which is the failure this file exists to prevent -- so the
manifest entry is part of the rule, not paperwork about it.
"""
import os

REQUIRED_RULE_ANCHORS = {
    "adversarial-review": [
        ("reviewer-independence", "independent-review"),
    ],
    "effort-levels": [
        ("size-from-measured-cadence", "measured-cadence"),
    ],
    "epic": [
        ("claim-no-broader-than-evidence", "evidence-scope"),
    ],
    "governance-sweep": [
        ("grep-registry-before-moving", "registry-before-move"),
    ],
    "virtuoso": [
        ("lane-declaration", "lane-concurrency"),
        ("mechanical-acceptance-criteria", "mechanical-criteria"),
        ("red-base-procedure", "red-base"),
        ("instrument-positive-control", "INSTRUMENT-CONTROL"),
        ("identity-not-counts", "GATE-IDENTITY"),
        ("name-the-fork-under-test", "FORK-SURFACE"),
        ("cite-searchable-anchor", "CITE-ANCHOR"),
        ("state-integrity-by-hash", "content-not-presence"),
        ("tier-by-blast-radius", "blast-radius"),
        ("calibration-routing", "measurement-dispatch"),
        ("worker-output-validation", "evidence-not-assertion"),
        ("re-derive-dont-restate", "re-derivation"),
        ("enforcement-not-disclosure", "enforcement-required"),
        ("orchestrator-owns-long-runs", "long-run-ownership"),
        ("inline-safety-into-worker-prompts", "safety-inlined"),
        ("checkpoint-commits", "task-boundary-commit"),
        ("user-gate-is-success", "operator-gate"),
        ("git-separation-of-duties", "separation-of-duties"),
        ("closeout-is-an-artifact", "closeout-artifact"),
        ("verification-spawns-remediation", "verification-scope"),
        ("merge-through-slot", "lane-concurrency"),
        ("registry-resolved-staging", "AMEND-THE-RESTATEMENTS"),
        ("staging-memo-lifecycle", "staging-lifecycle"),
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
