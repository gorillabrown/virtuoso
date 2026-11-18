"""Every SKILL.md body fits Antigravity's skill loader, which reads only the first 24,000
bytes of a body and silently drops the rest. Long skills hand detail off to references/."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from conftest import PLUGIN_ROOT

ROOT = Path(PLUGIN_ROOT)


def load_validate():
    spec = importlib.util.spec_from_file_location("validate_size", ROOT / "scripts" / "validate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_skill_body_fits_the_loader():
    validate = load_validate()
    sizes = {p.parent.name: validate.skill_body_bytes(p.read_text(encoding="utf-8"))
             for p in sorted((ROOT / "skills").glob("*/SKILL.md"))}
    over = {name: size for name, size in sizes.items() if size > validate.SKILL_BODY_LIMIT}
    assert not over, over


def test_body_size_counts_crlf_and_skips_frontmatter():
    validate = load_validate()
    text = "---\nname: x\ndescription: y\n---\nab\ncd\n"
    assert validate.skill_body_bytes(text) == len("ab\r\ncd\r\n")
    assert validate.skill_body_bytes(text.replace("\n", "\r\n")) == len("ab\r\ncd\r\n")


def test_every_skill_reference_is_linked_from_its_skill():
    """A reference file nobody hands off to is never read: each one under a skill's
    references/ is named in that skill's SKILL.md or in another of its references."""
    unlinked = []
    for refs in sorted((ROOT / "skills").glob("*/references")):
        skill = refs.parent
        texts = [(skill / "SKILL.md").read_text(encoding="utf-8")]
        texts += [p.read_text(encoding="utf-8") for p in refs.glob("*.md")]
        for ref in sorted(refs.glob("*.md")):
            others = [t for t, p in zip(texts, [skill / "SKILL.md", *refs.glob("*.md")])
                      if p != ref]
            if not any(ref.name in t for t in others):
                unlinked.append("%s/references/%s" % (skill.name, ref.name))
    assert not unlinked, unlinked
