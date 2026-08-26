"""Documentation-to-code contract (item 100).

Every status, command, role, policy key, capability, and output the shipped
documentation names must exist in the implementation — and the reverse, for the
things the implementation publishes as a contract.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from tools.governance import policy as policy_mod, result as result_mod, schema
from tools.governance.providers import base as provider_base

ROOT = Path(PLUGIN_ROOT)
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
REFERENCES = sorted((ROOT / "references").glob("*.md"))
DOCS = SKILLS + REFERENCES


def all_doc_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in DOCS)


# --- commands ------------------------------------------------------------------


def test_every_documented_script_exists():
    referenced = set()
    # Only actual launcher invocations count — `bin/virtuoso <script>` or
    # `bin/virtuoso.ps1 <script>` — never the word "virtuoso" in prose.
    pattern = re.compile(r"bin/virtuoso(?:\.ps1)?[\"\']?\s+([a-z_][a-z0-9_]*)\b")
    for path in DOCS:
        for name in pattern.findall(path.read_text(encoding="utf-8")):
            referenced.add(name)
    for name in referenced:
        script = ROOT / "scripts" / ("%s.py" % name)
        assert script.is_file(), "documentation references scripts/%s.py, which does not exist" % name


def test_every_documented_preflight_mode_exists():
    modes = set(re.findall(r"--mode\s+([a-z-]+)", all_doc_text()))
    modes |= set(re.findall(r"`--mode ([a-z-]+)`", all_doc_text()))
    unknown = sorted(modes - set(result_mod.MODES))
    assert not unknown, "documented modes not implemented: %s" % unknown


def test_every_documented_registry_subcommand_exists():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "virtuoso_registry.py"), "--help"],
        capture_output=True, text=True)
    assert completed.returncode == 0
    implemented = set(re.findall(r"\{([a-z,-]+)\}", completed.stdout)[0].split(","))

    documented = set()
    pattern = re.compile(r"virtuoso_registry[^\n]*?(?:--json\s+|--actor \S+\s+|--root \S+\s+)*"
                         r"\b(roles|resolve|provider|items|next|kpis|closeout|snapshot|"
                         r"recovery|repo|deps|protected|mutation-plan|mutation-confirm)\b")
    for path in DOCS:
        documented.update(pattern.findall(path.read_text(encoding="utf-8")))
    assert documented, "no registry subcommands are documented at all"
    assert documented <= implemented, "documented but missing: %s" % sorted(
        documented - implemented)


def test_documented_cli_flags_are_accepted():
    flags = {"--json", "--quiet", "--strict", "--apply", "--authorize", "--check-document"}
    text = all_doc_text()
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "virtuoso_preflight.py"), "--help"],
        capture_output=True, text=True)
    for flag in flags:
        if flag in text:
            assert flag in completed.stdout, "%s is documented but not implemented" % flag


# --- roles ---------------------------------------------------------------------


def test_every_documented_role_name_is_known():
    text = all_doc_text()
    documented = set(re.findall(r"`(workRegister|terminalLedger|sprintCatalog|sprintQueue|"
                                r"roadmap|lessons|closeOuts|issues|roadmapReviews|"
                                r"outsideAudits|reference|governance|operational|temp|"
                                r"workflowReference)`", text))
    known = set(schema.DEFAULT_ROLES)
    assert documented <= known, "unknown roles documented: %s" % sorted(documented - known)


def test_every_create_role_has_declared_defaults():
    for name in schema.CREATE_ROLE_ORDER:
        meta = schema.DEFAULT_ROLES[name]
        assert meta["authority"] in schema.AUTHORITIES
        assert meta["mutability"] in schema.MUTABILITIES
        assert meta["provider"] in schema.PROVIDERS
        assert meta["classification"] in schema.CLASSIFICATIONS
        assert meta["origin"] in schema.ORIGINS


def test_the_registry_contract_documents_every_authority_level():
    text = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    for authority in schema.AUTHORITIES:
        assert "`%s`" % authority in text, "authority %r is undocumented" % authority


def test_the_registry_contract_documents_every_capability():
    text = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    for capability in provider_base.ALL_CAPABILITIES:
        assert capability in text, "capability %r is undocumented" % capability


def test_the_registry_contract_documents_every_status():
    text = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    for status in result_mod.STATUSES:
        assert "`%s`" % status in text, "status %r is undocumented" % status


# --- policy --------------------------------------------------------------------


def _policy_keys(node, prefix=""):
    for key, value in node.items():
        path = "%s.%s" % (prefix, key) if prefix else key
        yield path
        if isinstance(value, dict):
            yield from _policy_keys(value, path)


def test_every_documented_policy_key_exists():
    known = set(_policy_keys(policy_mod.DEFAULTS))
    documented = set(re.findall(r"`policy\.([A-Za-z][A-Za-z0-9_.]*)`", all_doc_text()))
    documented |= set(re.findall(r"\bpolicy\.([a-z][A-Za-z0-9]*\.[A-Za-z0-9]+)\b",
                                 all_doc_text()))
    unknown = sorted(k for k in documented if k not in known)
    assert not unknown, "documented policy keys that do not exist: %s" % unknown


def test_every_git_policy_value_is_documented():
    text = (ROOT / "references" / "git-policy.md").read_text(encoding="utf-8")
    for value in policy_mod.GIT_POLICIES:
        assert "`%s`" % value in text, "git policy %r is undocumented" % value


def test_the_default_policy_validates():
    assert policy_mod.load({}).validate() == []


# --- the rubric ----------------------------------------------------------------


def test_the_rubric_declares_its_version_and_check_count():
    text = (ROOT / "references" / "readiness-rubric.md").read_text(encoding="utf-8")
    version = re.search(r"(?m)^\s*version:\s*(\S+)", text)
    count = re.search(r"(?m)^\s*universal-checks:\s*(\d+)", text)
    assert version and count
    declared = int(count.group(1))
    headings = re.findall(r"(?m)^###\s+U(\d+)\s+—", text)
    assert len(headings) == declared, (
        "the rubric declares %d universal checks but defines %d" % (declared, len(headings)))
    assert [int(h) for h in headings] == list(range(1, declared + 1))


def test_the_rubric_version_matches_the_policy_default():
    text = (ROOT / "references" / "readiness-rubric.md").read_text(encoding="utf-8")
    version = re.search(r"(?m)^\s*version:\s*(\S+)", text).group(1)
    assert policy_mod.DEFAULTS["rubric"]["version"] == version


def test_the_rubric_reports_five_separate_findings():
    """Item 39: readiness is five findings, never one blended verdict."""
    text = (ROOT / "references" / "readiness-rubric.md").read_text(encoding="utf-8")
    for finding in ("Specification readiness", "Prerequisite readiness",
                    "Repository readiness", "External-register readiness",
                    "Execution-environment readiness"):
        assert finding in text


def test_the_ceremonies_defer_to_the_shared_rubric():
    for name in ("roadmap-review", "next-pointer"):
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "references/readiness-rubric.md" in text, (
            "%s does not point at the shared rubric" % name)


# --- outputs -------------------------------------------------------------------


def test_documented_contract_lines_match_the_implementation():
    outcome = result_mod.Result(status=result_mod.READY, mode="check", root="/tmp")
    assert outcome.contract_lines() == ["virtuoso-status: ready", "writes: 0"]
    for line in outcome.contract_lines():
        token = line.split(":")[0]
        assert token in all_doc_text(), "%s is undocumented" % token


def test_the_json_result_keys_are_documented():
    outcome = result_mod.Result(status=result_mod.READY, mode="check", root="/tmp")
    payload = outcome.as_dict()
    text = all_doc_text()
    for key in ("status", "writes", "findings", "roles"):
        assert key in payload
        assert key in text


def test_every_skill_carries_the_shared_contract_block():
    for path in SKILLS:
        text = path.read_text(encoding="utf-8")
        assert "<!-- virtuoso-shared-contract v2 -->" in text, path.name


def test_ceremony_skills_run_the_read_only_preflight():
    ceremonies = ["roadmap-review", "roadmap-status", "next-pointer", "pointer-closeout",
                  "mid-dispatch-decision", "3rd-party-audit"]
    for name in ceremonies:
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "--mode check" in text, "%s does not run the read-only preflight" % name
        assert "--mode adopt\n" not in text.split("## Preflight")[1][:1200], (
            "%s runs adopt from its preflight" % name)
