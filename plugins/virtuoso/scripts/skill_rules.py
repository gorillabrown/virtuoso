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
import hashlib
import os
import re
import sys

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
    "pointer-closeout": [
        ("closeout-never-amends-acceptance", "acceptance-amendment"),
        ("classify-before-completion", "failure-classification"),
        ("proportional-evidence", "evidence-proportionality"),
        ("tested-tree-is-the-published-tree", "integrated-identity"),
        ("protected-state-over-test-result", "protected-custody"),
        ("close-only-what-was-verified", "completion-scope"),
        ("name-populations-not-aggregates", "population-naming"),
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


#: The hash of each promoted rule's text (see :func:`rule_text`). A changed rule
#: fails validation until this is updated in the same commit — print the current
#: values with ``python scripts/skill_rules.py --hashes``.
RULE_TEXT_HASHES = {
    "calibration-routing": "f006ee821e45",
    "checkpoint-commits": "8156cf3c75a1",
    "cite-searchable-anchor": "1f5d7cabc7d5",
    "claim-no-broader-than-evidence": "df173ed70539",
    "classify-before-completion": "fe08b2b84fe3",
    "close-only-what-was-verified": "896ce336280c",
    "closeout-is-an-artifact": "9d77bc91469b",
    "closeout-never-amends-acceptance": "2ac31fcda313",
    "enforcement-not-disclosure": "c2177feff664",
    "git-separation-of-duties": "207f4a172087",
    "grep-registry-before-moving": "48c7deaf8645",
    "identity-not-counts": "8e75546390be",
    "inline-safety-into-worker-prompts": "953facc922b3",
    "instrument-positive-control": "3302ba204495",
    "lane-declaration": "4cbcf8cd28f8",
    "mechanical-acceptance-criteria": "6335de01c689",
    "merge-through-slot": "0d1ffba327e5",
    "name-populations-not-aggregates": "a0322ec0c04b",
    "name-the-fork-under-test": "aa7d0012d8e7",
    "orchestrator-owns-long-runs": "f5bbd311aa2a",
    "proportional-evidence": "db329b8d695d",
    "protected-state-over-test-result": "e48441114ad8",
    "re-derive-dont-restate": "dbd2c4afda6e",
    "red-base-procedure": "1f4b177bd08d",
    "registry-resolved-staging": "44be2a2a34e8",
    "reviewer-independence": "a02876417e80",
    "size-from-measured-cadence": "0298f9a2d6b0",
    "staging-memo-lifecycle": "dafb3a391aa4",
    "state-integrity-by-hash": "65c8628bcac7",
    "tested-tree-is-the-published-tree": "f36229bc44f5",
    "tier-by-blast-radius": "1a46c1baed3c",
    "user-gate-is-success": "ab8095430a12",
    "verification-spawns-remediation": "fc9b598f84bd",
    "worker-output-validation": "1ee26c9bab74",
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


def rule_text(text, anchor, citation):
    """The rule an anchor guards: the paragraph that follows the marker, up to the
    first blank line, with whitespace collapsed. ``None`` when the marker is absent."""
    marker = anchor_comment(anchor, citation)
    position = text.find(marker)
    if position < 0:
        return None
    lines = text[position + len(marker):].splitlines()[1:]
    paragraph = []
    for line in lines:
        if not line.strip():
            if paragraph:
                break
            continue
        paragraph.append(line.strip())
    return re.sub(r"\s+", " ", " ".join(paragraph)).strip()


def rule_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def current_hashes(skills_dir):
    """``{anchor: hash of the rule text beneath it}`` for every registered anchor present."""
    found = {}
    for skill, anchors in sorted(REQUIRED_RULE_ANCHORS.items()):
        try:
            with open(os.path.join(skills_dir, skill, "SKILL.md"), encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        for anchor, citation in anchors:
            body = rule_text(text, anchor, citation)
            if body is not None:
                found[anchor] = rule_hash(body)
    return found


def changed_rules(skills_dir, recorded=None):
    """Anchors whose rule text no longer matches its recorded hash. An anchor proves
    a marker exists; this proves the rule beneath it is still the rule that was
    promoted. A deliberate change updates RULE_TEXT_HASHES in the same commit."""
    recorded = RULE_TEXT_HASHES if recorded is None else recorded
    now = current_hashes(skills_dir)
    return sorted(a for a, h in recorded.items() if a in now and now[a] != h) + \
        sorted(a for a in now if a not in recorded)


if __name__ == "__main__" and "--hashes" in sys.argv:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for anchor, value in sorted(current_hashes(os.path.join(here, "skills")).items()):
        print('    "%s": "%s",' % (anchor, value))
