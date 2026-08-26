import importlib.util, os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "skill_rules", os.path.join(HERE, "skill_rules.py"))
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)

SKILLS_DIR = os.path.join(os.path.dirname(HERE), "skills")


def _write_skill(root, name, body):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(body, encoding="utf-8")


def test_anchor_comment_is_the_exact_marker_searched_for():
    assert (sr.anchor_comment("calibration-routing", "SRL-087")
            == "<!-- rule:calibration-routing (SRL-087) -->")


def test_missing_anchors_reports_an_absent_rule(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "REQUIRED_RULE_ANCHORS",
                        {"demo": [("some-rule", "SRL-001")]})
    _write_skill(tmp_path, "demo", "# Demo\n\nno anchors here\n")
    assert sr.missing_anchors(str(tmp_path)) == ["demo:some-rule (SRL-001)"]


def test_missing_anchors_is_empty_when_the_anchor_is_present(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "REQUIRED_RULE_ANCHORS",
                        {"demo": [("some-rule", "SRL-001")]})
    _write_skill(tmp_path, "demo",
                 "# Demo\n\n<!-- rule:some-rule (SRL-001) -->\nThe rule text.\n")
    assert sr.missing_anchors(str(tmp_path)) == []


def test_a_near_miss_anchor_does_not_satisfy_the_check(tmp_path, monkeypatch):
    """A renamed citation is a different rule. Substring luck must not pass."""
    monkeypatch.setattr(sr, "REQUIRED_RULE_ANCHORS",
                        {"demo": [("some-rule", "SRL-001")]})
    _write_skill(tmp_path, "demo",
                 "# Demo\n\n<!-- rule:some-rule (SRL-999) -->\nThe rule text.\n")
    assert sr.missing_anchors(str(tmp_path)) == ["demo:some-rule (SRL-001)"]


def test_missing_anchors_flags_a_skill_with_no_skill_md(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "REQUIRED_RULE_ANCHORS",
                        {"ghost": [("some-rule", "SRL-001")]})
    assert sr.missing_anchors(str(tmp_path)) == ["ghost:<no SKILL.md>"]


def test_every_registered_anchor_is_present_in_the_shipped_skills():
    """The live gate. Fails the moment a promoted rule leaves a skill body."""
    assert sr.missing_anchors(SKILLS_DIR) == []
