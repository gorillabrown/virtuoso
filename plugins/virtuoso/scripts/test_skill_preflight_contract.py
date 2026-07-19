from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Governance skills whose Phase-0 brings the project under management before running.
GATE_SKILLS = {
    "roadmap-review",
    "roadmap-status",
    "next-pointer",
    "pointer-closeout",
    "mid-dispatch-decision",
    "3rd-party-audit",
}


def test_only_virtuoso_init_can_create_workspace_directly():
    offenders = []
    for skill in (ROOT / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        if "virtuoso_preflight.py" in text and "--mode create" in text:
            if skill.parent.name != "virtuoso-init":
                offenders.append(str(skill.relative_to(ROOT)))

    assert offenders == []


def test_gate_skills_adopt_rather_than_detect():
    """Governance gate skills must bring the project under management with `--mode adopt`
    (which adopts an established tree in place) and not the superseded `--mode detect`."""
    missing_adopt = []
    for name in GATE_SKILLS:
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        if "--mode adopt" not in text:
            missing_adopt.append(name)
    assert missing_adopt == [], f"gate skills not using --mode adopt: {missing_adopt}"


def test_gate_skills_reference_governance_registry_first():
    """Every gate skill must resolve documents through the project-root governance registry
    (`Virtuoso.Governance.Readme.md`) so it defers to existing docs instead of scaffolding a
    parallel/competing governance tree."""
    missing = []
    for name in GATE_SKILLS:
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        if "Virtuoso.Governance.Readme.md" not in text:
            missing.append(name)
    assert missing == [], f"gate skills not referencing the governance registry: {missing}"


def test_no_skill_uses_superseded_detect_mode():
    offenders = []
    for skill in (ROOT / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        if "--mode detect" in text:
            offenders.append(skill.parent.name)
    assert offenders == [], f"skills still calling --mode detect: {offenders}"


def test_roadmap_review_wires_the_integrity_gate():
    """The only skill that destructively rewrites the roadmap must gate on --check-roadmap."""
    text = (ROOT / "skills" / "roadmap-review" / "SKILL.md").read_text(encoding="utf-8")
    assert "--check-roadmap" in text, "roadmap-review must gate the rewrite with --check-roadmap"


def test_session_start_hook_uses_detect_not_adopt():
    """The unattended SessionStart hook must use detect, never adopt.

    Wording corrected 2026-07-19 (audit PRE-03/D-04, docstring-only — assertions unchanged,
    owner-authorized): detect is NOT "non-writing". It is an idempotent-on-settled WRITER —
    it heals drifted markered trees, auto-scaffolds brand-new roots, and always writes the
    plugin-root bridge. What this test actually guarantees is only that the hook avoids
    adopt-mode's broader behaviours. A genuinely read-only mode does not exist yet; that is
    PF-03 (`check`), which will amend this test's assertions under the sign-off recorded in
    the Roadmap's PF-03 spec."""
    import json

    cfg = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    cmds = [h["command"] for grp in cfg["hooks"]["SessionStart"] for h in grp["hooks"]]
    assert any("--mode detect" in c for c in cmds), cmds
    assert not any("--mode adopt" in c for c in cmds), cmds

