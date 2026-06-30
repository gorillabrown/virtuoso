from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_only_virtuoso_init_can_create_workspace_directly():
    offenders = []
    for skill in (ROOT / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        if "virtuoso_preflight.py" in text and "--mode create" in text:
            if skill.parent.name != "virtuoso-init":
                offenders.append(str(skill.relative_to(ROOT)))

    assert offenders == []

