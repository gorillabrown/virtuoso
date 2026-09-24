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
                         r"recovery|repo|deps|protected|overlays|create-item|"
                         r"mutation-plan|mutation-confirm|policy-set|lessons)\b")
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
                                r"overlays|workflowReference)`", text))
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


def _policy_table_keys(text: str) -> set[str]:
    """The key in the first cell of every row of a table headed ``| Policy |``.

    Those tables spell keys without the ``policy.`` prefix (``roadmap.effortScale``),
    which the prefix-matching check above cannot see — and that is how a key was
    documented, read by ``kpis``, and still refused by ``policy-set`` as unknown.
    """
    keys: set[str] = set()
    in_table = False
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.lstrip().startswith("|"):
            in_table = False
            continue
        if cells and cells[0].lower() == "policy":
            in_table = True
            continue
        if not in_table or re.match(r"^:?-+:?$", cells[0]):
            continue
        match = re.fullmatch(r"`(?:policy\.)?([A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+)`",
                             cells[0])
        if match:
            keys.add(match.group(1))
    return keys


def test_every_policy_table_key_exists():
    known = set(_policy_keys(policy_mod.DEFAULTS))
    documented = set()
    for path in DOCS:
        documented |= _policy_table_keys(path.read_text(encoding="utf-8"))
    assert documented, "no policy table was found at all"
    unknown = sorted(k for k in documented if k not in known)
    assert not unknown, "policy-table keys that do not exist: %s" % unknown


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


def test_no_ceremony_restates_the_rubrics_version_or_count():
    """The rubric says no skill carries its own count of checks. Two did, and a new
    check would have left both describing a rubric that no longer exists."""
    for path in SKILLS:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\bv1\.\d+\b[^\n]{0,40}universal checks", text), path
        # "walk U1–U8 plus the extensions" is a count in disguise; the five-findings
        # mapping ("U1–U4, U6, U7, U9 plus") is checked against the rubric below.
        assert not re.search(r"\bU1[–-]U\d+\s+plus\b", text), (
            "%s restates the rubric's range of universal checks" % path)


def test_the_specification_finding_matches_the_rubric():
    rubric = (ROOT / "references" / "readiness-rubric.md").read_text(encoding="utf-8")
    wanted = re.search(r"\*\*Specification readiness\*\* — ([^.]+?) plus", rubric).group(1)
    pointer = (ROOT / "skills" / "next-pointer" / "SKILL.md").read_text(encoding="utf-8")
    assert "| **Specification readiness** | %s plus" % wanted in pointer


def test_the_rubric_reports_five_separate_findings():
    """Item 39: readiness is five findings, never one blended verdict."""
    text = (ROOT / "references" / "readiness-rubric.md").read_text(encoding="utf-8")
    for finding in ("Specification readiness", "Prerequisite readiness",
                    "Repository readiness", "External-register readiness",
                    "Execution-environment readiness"):
        assert finding in text


def test_the_ceremonies_defer_to_the_shared_rubric():
    for name in ("roadmap-review", "next-pointer", "write-plan"):
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


def test_the_machine_lines_and_their_json_keys_are_documented():
    """Every line preflight prints beside the two-line contract, and the JSON key
    that carries its detail, is in the registry contract."""
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    outcome = result_mod.Result(status=result_mod.READY, mode="check", root="/tmp")
    payload = outcome.as_dict()
    for line, key in ((outcome.overlay_line(), "overlays"),
                      (outcome.deadline_line(), "deadlines"),
                      (outcome.roadmap_integrity_line(), "roadmapIntegrity")):
        token = line.split(":")[0] + ":"
        assert token in contract, "%s is undocumented" % token
        assert key in payload and "`%s`" % key in contract, "JSON key %s" % key


def test_the_registry_contract_documents_every_pace_verdict():
    from tools.governance.providers import pace
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    for verdict in pace.VERDICTS:
        assert "| `%s` |" % verdict in contract, "pace verdict %r is undocumented" % verdict


def test_the_registry_contract_documents_every_deadline_finding():
    from tools.governance import deadlines
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    for code in deadlines.FINDING_CODES:
        assert "| `%s` |" % code in contract, "deadline finding %r is undocumented" % code


def test_the_registry_contract_documents_every_lessons_finding():
    from tools.governance import lessons
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    for code in lessons.FINDING_CODES:
        assert "| `%s` |" % code in contract, "lessons finding %r is undocumented" % code


def test_the_ceremonies_read_pace_rather_than_derive_it():
    for name in ("roadmap-review", "roadmap-status", "next-pointer"):
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "`pace` block" in text, "%s does not read the pace block" % name
    review = (ROOT / "skills" / "roadmap-review" / "SKILL.md").read_text(encoding="utf-8")
    assert "policy-set roadmap.deadlines.<id>" in review


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
                  "mid-dispatch-decision", "3rd-party-audit", "storyboard", "write-plan"]
    for name in ceremonies:
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "--mode check" in text, "%s does not run the read-only preflight" % name
        assert "--mode adopt\n" not in text.split("## Preflight")[1][:1200], (
            "%s runs adopt from its preflight" % name)


def test_every_sprint_guard_is_documented():
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    source = (ROOT / "scripts" / "sprint_guards.py").read_text(encoding="utf-8")
    for name in re.findall(r'add_parser\(\s*"([a-z-]+)"', source):
        assert "| `%s" % name in contract, "sprint guard %s is undocumented" % name


def test_every_standing_rules_finding_is_documented():
    from tools.governance import standing_rules
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    for code in standing_rules.FINDING_CODES:
        assert "`%s`" % code in contract, "standing-rules finding %s is undocumented" % code


def test_the_learning_metrics_are_documented():
    from tools.governance import learning
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    for metric in learning.metrics([], learning.Outcomes()):
        assert "| `%s` |" % metric.name in contract, "metric %s is undocumented" % metric.name


def test_the_preflight_docstring_lists_every_machine_line():
    """The script's own help is the first place an operator reads what it prints."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("preflight_doc",
                                                  str(ROOT / "scripts" / "virtuoso_preflight.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    outcome = result_mod.Result(status=result_mod.READY, mode="check", root="/tmp")
    for line in outcome.contract_lines() + [outcome.overlay_line(), outcome.deadline_line(),
                                            outcome.roadmap_integrity_line()]:
        token = line.split(":")[0] + ":"
        assert token in module.__doc__, "%s is not in the preflight's docstring" % token


# --- three paths to execution, one destination ---------------------------------


def skill_text(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_every_path_points_at_the_one_destination_contract():
    """Storyboard -> write-plan, next-pointer and epic must arrive at the same place;
    the contract has one home, and every ceremony on a path reads it."""
    assert (ROOT / "references" / "execution-paths.md").is_file()
    for name in ("storyboard", "write-plan", "next-pointer", "epic", "virtuoso",
                 "pointer-closeout", "roadmap-review"):
        assert "references/execution-paths.md" in skill_text(name), name


def test_the_ad_hoc_path_does_no_roadmapping():
    """storyboard and write-plan write the holding bay and nothing else: every command
    they run under their own name is a read or a holding-bay move."""
    reads_and_holding = {"holding", "provider", "items", "next", "kpis", "lessons", "repo",
                         "deps", "roles", "resolve"}
    for name in ("storyboard", "write-plan"):
        text = skill_text(name)
        used = set(re.findall(r"--actor %s (\S+)" % re.escape(name), text))
        assert used, name
        assert used <= reads_and_holding, (name, sorted(used - reads_and_holding))


def test_write_plan_always_starts_from_the_storyboard():
    text = skill_text("write-plan")
    assert "## Step 0 — Pull back into the storyboard (always first)" in text
    assert "run `/storyboard`" in text


def test_the_roadmap_paths_open_only_on_the_master_roadmap():
    epic = skill_text("epic")
    assert "### Step 1 — Pull the item from the master roadmap" in epic
    assert "`/storyboard`" in epic
    pointer = skill_text("next-pointer")
    assert "`Path: epic`" in pointer and "## Edge case: Epic at head" in pointer
    assert "Origin: roadmap — [ITEM-ID]" in pointer


def test_the_holding_bay_is_reconciled_at_review_and_closed_out_in_held_plan_mode():
    review = skill_text("roadmap-review")
    assert "holding --open" in review
    assert "--actor roadmap-review holding --record <entry> --state absorbed" in review
    closeout = skill_text("pointer-closeout")
    assert "--actor pointer-closeout holding --record <entry> --state executed" in closeout
    assert "**The recording crossing.**" in closeout
