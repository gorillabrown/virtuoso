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
    """The unattended SessionStart hook must stay non-writing (detect), never adopt."""
    import json

    cfg = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    cmds = [h["command"] for grp in cfg["hooks"]["SessionStart"] for h in grp["hooks"]]
    assert any("--mode detect" in c for c in cmds), cmds
    assert not any("--mode adopt" in c for c in cmds), cmds

