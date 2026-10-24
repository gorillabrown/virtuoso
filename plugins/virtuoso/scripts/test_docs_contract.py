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
        capture_output=True, text=True, encoding="utf-8")
    assert completed.returncode == 0
    implemented = set(re.findall(r"\{([a-z,-]+)\}", completed.stdout)[0].split(","))

    documented = set()
    pattern = re.compile(r"virtuoso_registry[^\n]*?(?:--json\s+|--actor \S+\s+|--root \S+\s+)*"
                         r"\b(roles|resolve|provider|items|next|kpis|closeout|snapshot|"
                         r"recovery|repo|deps|protected|overlays|create-item|"
                         r"mutation-plan|mutation-confirm|policy-set|lessons|timing)\b")
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
        capture_output=True, text=True, encoding="utf-8")
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
    kickoff = (ROOT / "skills" / "next-dispatch" / "SKILL.md").read_text(encoding="utf-8")
    assert "| **Specification readiness** | %s plus" % wanted in kickoff


def added_since(rubric: str, pinned: str) -> dict:
    """``{check: name}`` for every check the rubric says a version after ``pinned`` added."""
    def key(version):
        return tuple(int(part) for part in version.split("."))
    return {check: name for version, check, name in
            re.findall(r"\*\*v(\d+(?:\.\d+)*)\*\* added (U\d+), \*([^*]+)\*", rubric)
            if key(version) > key(pinned)}


def test_a_pinned_project_sees_u10():
    rubric = (ROOT / "references" / "readiness-rubric.md").read_text(encoding="utf-8")
    assert "names the checks added since before assessing" in rubric
    assert added_since(rubric, "1.1") == {"U10": "Task list"}
    assert added_since(rubric, "1.0") == {"U9": "Lessons applied", "U10": "Task list"}
    assert re.search(r"(?m)^###\s+U10\s+—\s+Task list$", rubric)


EFFORT_DURATION = re.compile(r"\d+\s*(m|min|h)\b")


def effort_durations(text: str) -> list[str]:
    """Lines whose ``Effort:`` field, or whose task-list ``Effort`` column, holds a
    duration. Effort is a level; durations live in ``Estimate`` and ``Timebox``."""
    found, column = [], None
    for line in text.splitlines():
        stripped = line.strip()
        if "Effort:" in line and EFFORT_DURATION.search(line.split("Effort:", 1)[1]):
            found.append(stripped)
        if not stripped.startswith("|"):
            column = None
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if "Effort" in cells:
            column = cells.index("Effort")
        elif column is not None and column < len(cells) and EFFORT_DURATION.search(cells[column]):
            found.append(stripped)
    return found


def test_a_duration_in_an_effort_field_is_rejected():
    assert effort_durations("- **Effort:** 2h\n") == ["- **Effort:** 2h"]
    assert effort_durations("| # | Effort | Estimate |\n|---|---|---|\n| 1 | 45 min | 45m |\n"
                            ) == ["| 1 | 45 min | 45m |"]
    assert effort_durations("- **Effort:** high\n| # | Effort | Estimate |\n|---|---|---|\n"
                            "| 1 | medium | 45m |\n") == []
    templates = sorted((ROOT / "skills").glob("*/assets/*.md"))
    for path in DOCS + templates:
        assert effort_durations(path.read_text(encoding="utf-8")) == [], path


def test_the_rubric_reports_five_separate_findings():
    """Item 39: readiness is five findings, never one blended verdict."""
    text = (ROOT / "references" / "readiness-rubric.md").read_text(encoding="utf-8")
    for finding in ("Specification readiness", "Prerequisite readiness",
                    "Repository readiness", "External-register readiness",
                    "Execution-environment readiness"):
        assert finding in text


def test_the_ceremonies_defer_to_the_shared_rubric():
    for name in ("roadmap-review", "next-dispatch", "write-plan"):
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
                      (outcome.roadmap_integrity_line(), "roadmapIntegrity"),
                      (outcome.board_line(), "board")):
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
    for name in ("roadmap-review", "roadmap-status", "next-dispatch"):
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


def test_every_skill_names_five_effort_levels():
    for path in SKILLS:
        text = path.read_text(encoding="utf-8")
        contract = text[text.index("<!-- virtuoso-shared-contract v2 -->"):]
        line = next((l for l in contract.splitlines() if l.startswith("- **Effort levels** —")), "")
        assert "low / medium / high / xhigh / max" in line, path.parent.name
    four = re.compile(r"low\s*[/|,]\s*medium\s*[/|,]\s*high\s*[/|,]\s*max", re.I)
    for path in sorted((ROOT / "skills").rglob("*.md")) + sorted((ROOT / "references").rglob("*.md")):
        assert not four.search(path.read_text(encoding="utf-8")), \
            "%s still lists four effort levels" % path.relative_to(ROOT)


def test_ceremony_skills_run_the_read_only_preflight():
    ceremonies = ["roadmap-review", "roadmap-status", "next-dispatch", "dispatch-closeout",
                  "mid-dispatch-decision", "3rd-party-audit", "storyboard", "write-plan"]
    for name in ceremonies:
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "--mode check" in text, "%s does not run the read-only preflight" % name
        assert "--mode adopt\n" not in text.split("## Preflight")[1][:1200], (
            "%s runs adopt from its preflight" % name)


def test_every_dispatch_guard_is_documented():
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    source = (ROOT / "scripts" / "dispatch_guards.py").read_text(encoding="utf-8")
    names = re.findall(r'add_parser\(\s*"([a-z-]+)"', source)
    assert len(names) == 4, names                  # an empty list would check nothing
    for name in names:
        assert "| `%s" % name in contract, "dispatch guard %s is undocumented" % name


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
                                            outcome.roadmap_integrity_line(),
                                            outcome.board_line()]:
        token = line.split(":")[0] + ":"
        assert token in module.__doc__, "%s is not in the preflight's docstring" % token


# --- three paths to execution, one destination ---------------------------------


def skill_text(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_every_path_points_at_the_one_destination_contract():
    """Storyboard -> write-plan, next-dispatch and epic must arrive at the same place;
    the contract has one home, and every ceremony on a path reads it."""
    assert (ROOT / "references" / "execution-paths.md").is_file()
    for name in ("storyboard", "write-plan", "next-dispatch", "epic", "virtuoso",
                 "dispatch-closeout", "roadmap-review"):
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


def test_only_the_virtuoso_skill_executes():
    """Storyboard scopes to a draft stub, write-plan writes the full plan, and only the
    virtuoso skill executes. A storyboard run in a chat of its own must end at its
    draft stub, and the planner must hand off rather than start the run."""
    from tools.governance import holding as holding_mod
    assert holding_mod.RECORDED_BY[holding_mod.IN_FLIGHT] == ("virtuoso",)
    for name in ("storyboard", "write-plan"):
        text = skill_text(name)
        assert "--state in-flight" not in text, name
        assert "never execut" in " ".join(text.split()).lower(), name
    storyboard = skill_text("storyboard")
    assert "## Step 11 — Hand the draft stub to /write-plan" in storyboard
    assert "Make it directly" not in storyboard
    plan = skill_text("write-plan")
    assert "## Step 8 — Hand off to Virtuoso" in plan
    assert "Execute now" not in plan and "Load the **virtuoso** skill, and hand it" not in plan
    virtuoso = skill_text("virtuoso")
    assert ("--actor virtuoso holding --record <entry> --state in-flight" in virtuoso)
    assert ("--actor virtuoso holding --record <entry> --state planned" in virtuoso)
    assert "### The conflict check — before the first edit" in virtuoso
    paths = (ROOT / "references" / "execution-paths.md").read_text(encoding="utf-8")
    assert "## Only the virtuoso skill executes" in paths


def test_the_roadmap_paths_open_only_on_the_master_roadmap():
    epic = skill_text("epic")
    assert "### Step 1 — Pull the items from the master roadmap" in epic
    assert "#### Step 1a — One item marked `Path: epic`" in epic
    assert "#### Step 1b — A combination of roadmap items" in epic
    assert "`/storyboard`" in epic
    kickoff = skill_text("next-dispatch")
    assert "`Path: epic`" in kickoff and "## Edge case: Epic at head" in kickoff
    assert "Origin: roadmap — [ITEM-ID]" in kickoff


def test_the_epic_packet_carries_its_git_work_and_a_goal_line():
    """D6 says an epic carries a reconciliation recipe; the skill must fill one into the
    kickoff prompt, and print a one-line goal for `/goal` straight after it."""
    epic = " ".join(skill_text("epic").split())
    assert "**Fill the run's git work**" in epic
    assert "`policy.git.branchNameTemplate`" in epic and "Leave no placeholders" in epic
    assert "print the **goal line** from launch.md in its own fenced block" in epic
    assert "`/goal`" in epic and "BLOCKER(USER)" in epic

    assets = ROOT / "skills" / "epic" / "assets"
    launch = (assets / "launch.template.md").read_text(encoding="utf-8")
    kickoff = launch.split("## Kickoff / resume prompt", 1)[1].split("## Goal line", 1)[0]
    prompt = kickoff.split("```", 2)[1]
    # One paste carries the epic's instructions and the git work together.
    assert "RESUME PROTOCOL" in prompt and "GIT WORK" in prompt
    for step in ("git switch -c [BRANCH]", "git branch --show-current",
                 "--left-right --count", "git add -- <exact paths>"):
        assert step in prompt, step
    assert "never create it again" in prompt and "never rebase" in prompt
    completion = prompt.split("Completion only", 1)[1].split("Never:", 1)[0]
    assert "git merge --no-ff [BRANCH]" in completion
    assert ':(exclude)[PACKET DIR]' in completion
    assert completion.index("git commit") < completion.index("git merge --no-ff")

    goal = launch.split("## Goal line", 1)[1].split("## Completion protocol", 1)[0]
    block = goal.split("```", 2)[1].strip("\n")
    assert "\n" not in block, "the goal line must be one line"
    assert "done.md" in block and "Definition-of-Done" in block and "BLOCKER(USER)" in block

    charter = (assets / "charter.template.md").read_text(encoding="utf-8")
    assert "**Git, from `policy.git`" in charter
    state = (assets / "state.template.md").read_text(encoding="utf-8")
    assert "| Run branch |" in state and "| Branch created |" in state
    journal = (assets / "journal.template.md").read_text(encoding="utf-8")
    assert journal.count("- **Git:**") == 2
    paths = (ROOT / "references" / "execution-paths.md").read_text(encoding="utf-8")
    d6 = next(line for line in paths.splitlines() if line.startswith("| D6 |"))
    assert "GIT WORK" in d6 and "kickoff prompt" in d6


def test_the_holding_bay_is_reconciled_at_review_and_closed_out_in_held_plan_mode():
    review = skill_text("roadmap-review")
    assert "holding --open" in review
    assert "--actor roadmap-review holding --record <entry> --state absorbed" in review
    closeout = skill_text("dispatch-closeout")
    assert "--actor dispatch-closeout holding --record <entry> --state executed" in closeout
    assert "**The recording crossing.**" in closeout


# --- the terminal ledger: who appends a retirement ---------------------------------


def test_retirement_records_are_gated_on_writers_and_routed_to_the_close_out():
    """A retirement is an ordinary terminal record: the ledger lets only
    `terminalLedger.writers` append one, and `correctionWriters` only a record that
    names the record it corrects. The two ceremonies that retire items say the same,
    and route the record to the close-out, which says how it handles it."""
    assert policy_mod.DEFAULTS["terminalLedger"]["writers"] == ["dispatch-closeout"]
    review = skill_text("roadmap-review")
    a4 = review.split("### A.4 Apply changes", 1)[1].split("### A.4b", 1)[0]
    status = skill_text("roadmap-status")
    straggler = status.split("- **Straggler migration**", 1)[1].split(
        "- **Drift reconciliation**", 1)[0]
    for where, text, actor in (("roadmap-review A.4", a4, "roadmap-review"),
                               ("roadmap-status 2.1", straggler, "roadmap-status")):
        text = " ".join(text.split())                       # prose wraps anywhere
        assert "`policy.terminalLedger.writers`" in text, where
        assert "`/dispatch-closeout`" in text and "*Retirement records routed here*" in text, where
        assert "`policy.terminalLedger.correctionWriters` names `%s`" % actor not in text, where
    assert "## Retirement records routed here" in skill_text("dispatch-closeout")
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    assert "**Who may append what.**" in contract


def _between(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end, text.index(start))]


def test_the_staging_catch_all_names_agent_files_overlays_and_briefs():
    rule = _between(skill_text("virtuoso"), "### Rule 1", "### Rule 2")
    for fragment in ("`agents/<Agent>.md`", "`<overlays>/agents/<Agent>.md`",
                     "`.claude/agents/`", "names the file as an edit site"):
        assert fragment in rule, fragment


def test_the_virtuoso_skill_titles_the_session_first():
    naming = _between(skill_text("virtuoso"), "## Dispatch Record Naming", "## Architecture")
    order = [naming.index(fragment) for fragment in
             ("session-title tool", "before implementation begins",
              "first substantive visible line")]
    assert order == sorted(order), order
    means = [naming.index(fragment) for fragment in
             ("1. **A session-title tool", "2. **A title command", "3. **The first visible line")]
    assert means == sorted(means), means


def test_the_kickoff_block_names_the_session():
    block = _between(skill_text("next-dispatch"), "## Kickoff\n",
                     "## Standing rules that apply").split("\\```")[1]   # the code block
    assert any(line.startswith("Session: [ITEM-ID] — ") for line in block.splitlines())


def test_the_kickoff_is_one_block():
    output = _between(skill_text("next-dispatch"), "## Kickoff\n",
                      "## Standing rules that apply")
    parts = output.split("\\```")
    assert len(parts) == 3, "exactly one fence under ## Kickoff"
    lines = [line for line in parts[1].splitlines() if line.strip()]
    flat = [" ".join(line.split()) for line in lines]      # a wrap never splits a phrase
    session = next(i for i, line in enumerate(lines) if line.startswith("Session: [ITEM-ID] — "))
    label = next(i for i, line in enumerate(flat)
                 if "REPOSITORY RECONCILIATION — run this FIRST, before any edit" in line)
    assert session < label < len(lines) - 1
    assert all(line.startswith("  ") for line in lines[label + 1:-1])   # the recipe, indented
    assert flat[-1] == ("Halt on any STOP and report the git output — a halt is a dispatch "
                        "blocker, not something to improvise around.")
    assert "## Repository reconciliation — run this FIRST" not in output
    assert "```" not in parts[1]


def test_the_epic_prompt_titles_each_session():
    launch = (ROOT / "skills" / "epic" / "assets" / "launch.template.md").read_text(
        encoding="utf-8")
    kickoff = launch.split("## Kickoff / resume prompt", 1)[1].split("## Goal line", 1)[0]
    prompt = kickoff.split("```", 2)[1]
    assert "-S<n> — " in prompt and "title this session" in prompt


def test_the_virtuoso_skill_turns_remote_control_on():
    setup = " ".join(_between(skill_text("virtuoso"), "## Dispatch Record Naming",
                              "## Architecture").split())     # a wrap never splits a phrase
    for fragment in ("Remote Control", "only when the owner", "never turns it off",
                     "offers no Remote Control switch"):
        assert fragment in setup, fragment


def test_the_kickoff_session_line_names_remote_control():
    block = _between(skill_text("next-dispatch"), "## Kickoff\n",
                     "## Standing rules that apply").split("\\```")[1]
    session = [line for line in block.splitlines() if line.startswith("Session: ")]
    assert len(session) == 1 and "· Remote Control:" in session[0], session


def test_the_epic_prompt_turns_remote_control_on():
    launch = (ROOT / "skills" / "epic" / "assets" / "launch.template.md").read_text(
        encoding="utf-8")
    kickoff = launch.split("## Kickoff / resume prompt", 1)[1].split("## Goal line", 1)[0]
    prompt = kickoff.split("```", 2)[1]
    assert "Remote Control" in prompt and "never turn it off" in " ".join(prompt.split())


def test_the_held_plan_carries_one_kickoff_block():
    step = _between(skill_text("write-plan"), "## Step 7 — Hold the plan", "2. Check the entry")
    flat = " ".join(step.split())
    assert "**Kickoff** (one block carrying the repository-reconciliation recipe" in flat
    assert "**Repository reconciliation — run this FIRST**" not in flat


def test_the_held_plan_template_names_one_kickoff_block():
    template = (ROOT / "skills" / "storyboard" / "assets" / "held-plan.template.md").read_text(
        encoding="utf-8")
    plan = " ".join(template.split("## Plan", 1)[1].split())
    assert "one block carrying its repository-reconciliation recipe" in plan
    assert "kickoff, repository reconciliation" not in plan


def test_scope_discipline_defines_each_delta():
    section = _between(skill_text("roadmap-review"), "### B.3", "### B.4")
    for fragment in ("**Forward**", "**Sideways**", "**Backward**",
                     "policy.roadmap.deadlines.<id>.scope", "is not scored"):
        assert fragment in section, fragment
    assert "as deltas like any other" not in section


def test_an_epics_completion_record_reaches_the_default_branch():
    """The record lands on the default branch in a docs-only merge after the code merge,
    and the close-out checks it is there before it crosses."""
    flat = lambda t: " ".join(t.split())  # noqa: E731
    launch = (ROOT / "skills" / "epic" / "assets" / "launch.template.md").read_text(
        encoding="utf-8")
    protocol = flat(_between(launch, "## Completion protocol", "## Monitoring"))
    for fragment in ("docs-only commit", "after the code merge, never folded into it",
                     "`--no-ff`", "touches only this directory"):
        assert fragment in protocol, fragment
    assert protocol.index("docs-only commit") < protocol.index("is the stop signal")

    epic = flat(skill_text("epic"))
    assert "once `done.md` exists on the default branch" in epic
    assert "docs-only merge after the code merge" in epic
    assert "Completion only lines commit the record after the code merge" in epic

    closeout = skill_text("dispatch-closeout")
    step1 = flat(_between(closeout, "### Step 1 — Verify completion evidence",
                          "### Acceptance and evidence reconciliation"))
    assert ("dispatch_guards artifacts-exist --ref <default branch> <packet directory>/done.md"
            in step1)
    assert "docs-only completion commit" in step1
    [row] = [line for line in closeout.splitlines() if line.startswith("| Step 1 — evidence |")
             and "charter DoD" in line]
    assert "on the default branch (Step 1)" in row


def test_the_record_merge_is_scope_checked_before_it_lands():
    """A stray commit on the run branch stops the record merge before it reaches the
    default branch; the commit names the paths it staged; the close-out, not the run,
    checks the record merge itself."""
    flat = lambda t: " ".join(t.split())  # noqa: E731
    launch = (ROOT / "skills" / "epic" / "assets" / "launch.template.md").read_text(
        encoding="utf-8")
    kickoff = launch.split("## Kickoff / resume prompt", 1)[1].split("## Goal line", 1)[0]
    completion = kickoff.split("```", 2)[1].split("Completion only", 1)[1].split("Never:", 1)[0]
    before = completion.index("git diff --name-only [DEFAULT]...[BRANCH]")
    merge = completion.index("git merge --no-ff")
    assert before < merge < completion.index("git diff --name-only HEAD^1 HEAD")
    [scope] = [line for line in completion.splitlines()
               if "git diff --name-only [DEFAULT]...[BRANCH]" in line]
    assert '-- . ":(exclude)[PACKET DIR]"' in scope
    [add] = [line for line in completion.splitlines() if line.strip().startswith("git add")]
    [commit] = [line for line in completion.splitlines()
                if line.strip().startswith("git commit")]
    assert commit.rstrip().endswith("[PACKET DIR]/journal.md")
    assert add.split(" -- ", 1)[1].split() == commit.split(" -- ", 1)[1].split()
    assert completion.index(add) < completion.index("git diff --cached --name-only") \
        < completion.index(commit)
    protocol = flat(_between(launch, "## Completion protocol", "## Monitoring"))
    assert "record only checks that run before the record commit" in protocol

    step1 = flat(_between(skill_text("dispatch-closeout"),
                          "### Step 1 — Verify completion evidence",
                          "### Acceptance and evidence reconciliation"))
    assert "runs the record merge's scope check itself" in step1


def test_the_plan_is_the_time_log():
    """The virtuoso skill runs `timing --check`, reprints compactly past 12 rows, parks
    what it will not do; zeus numbers setup as row 1; the close-out files parked rows."""
    skill = " ".join(skill_text("virtuoso").split())
    for fragment in ("timing --dispatch <DISPATCH-ID> --check", "after a compaction and again "
                     "before the close-out", "`timing --status --compact`", "Past 12 rows",
                     "the last 3 done", "every fifth task", "**A row the run will not do is "
                     "parked, not deleted:**", "--park N --reason", "--origin review",
                     "--evidence \"<what proves it>\"", "[D/N ✓ · R ■ · X ✗ · O □ · P ◇]"):
        assert fragment in skill, fragment
    assert "rows done = " not in skill
    zeus = (ROOT / "skills" / "virtuoso" / "references" / "zeus.md").read_text(encoding="utf-8")
    assert "Task 0" not in zeus and "There is no row 0" in " ".join(zeus.split())
    closeout = " ".join(_between(skill_text("dispatch-closeout"), "### Step 4",
                                 "### Step 5").split())
    assert "**Parked rows become findings.**" in closeout and "**Disposition:** `open`" in closeout


def test_the_sweep_runs_the_footprint_audit():
    sweep = " ".join(skill_text("governance-sweep").split())
    assert "virtuoso_registry --root . footprint" in sweep
    assert "Disk footprint" in sweep


def test_the_close_out_records_the_dispatch_footprint():
    closeout = " ".join(skill_text("dispatch-closeout").split())
    assert "footprint --dispatch" in closeout
    template = (ROOT / "skills" / "dispatch-closeout" / "assets" /
                "CloseOut.template.md").read_text(encoding="utf-8")
    assert "- **Footprint:**" in template


def test_delayed_start_blocks_only_the_deferred_task():
    flat = " ".join(skill_text("delayed-start").split())
    for gone in ("The sleep is blocking", "hold the terminal", "time.sleep(",
                 "sleeps until the target"):
        assert gone not in flat, gone
    for fragment in ("blocks only the deferred task", "other work carries on",
                     "hold everything", "the host's scheduler", "a background agent's report"):
        assert fragment in flat, fragment


def test_delayed_start_shows_the_deferred_task_blocked_on_the_plan():
    text = skill_text("delayed-start")
    flat = " ".join(text.split())
    for fragment in ("deferred until <time> <zone>", "waits on #N", "raises no issue document",
                     "Meanwhile:", "with the zone"):
        assert fragment in flat, fragment
    assert "sleeps" not in text.split("---", 2)[1]


# --- the kickoff skill's name ------------------------------------------------------------

def _frontmatter(text: str) -> tuple[str, str]:
    """A skill's frontmatter ``name`` and its ``description`` text."""
    head = text.split("---", 2)[1]
    name = re.search(r"^name:\s*(\S+)", head, re.M).group(1)
    return name, head[head.index("description:"):]


def test_the_kickoff_skill_is_next_dispatch():
    text = skill_text("next-dispatch")
    assert _frontmatter(text)[0] == "next-dispatch"
    assert "/next-dispatch" in text and "--actor next-dispatch next --json" in text
    assert "dispatch-kickoff" not in text


def test_the_old_kickoff_command_redirects():
    text = skill_text("dispatch-kickoff")
    name, description = _frontmatter(text)
    assert name == "dispatch-kickoff"
    assert "/next-dispatch" in text and "skills/next-dispatch/SKILL.md" in text
    assert "<!-- virtuoso-shared-contract v2 -->" in text
    assert "<!-- virtuoso-overlay-clause v2 -->" in text
    assert len(text.splitlines()) < 60
    assert "what's next" not in description.lower() and "show next" not in description.lower()


def test_no_shipped_file_names_the_old_kickoff():
    allowed = {ROOT / "skills" / "dispatch-kickoff" / "SKILL.md"}
    schema_file = ROOT / "tools" / "governance" / "schema.py"
    named = []
    for path in sorted(ROOT.rglob("*")):
        if (not path.is_file() or "__pycache__" in path.parts or path in allowed
                or (path.parent.name == "scripts" and path.name.startswith("test_"))):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue                    # not a text file
        lines = [line for line in text.splitlines() if "dispatch-kickoff" in line]
        if path == schema_file:
            lines = [line for line in lines if not line.startswith("ACTOR_ALIASES = ")]
        named += ["%s: %s" % (path.relative_to(ROOT).as_posix(), line.strip())
                  for line in lines]
    assert not named, "\n".join(named)


def test_the_1_16_migration_note_names_the_rename():
    note = (ROOT.parents[1] / "docs" / "MIGRATION-1.16.md").read_text(encoding="utf-8")
    assert any(line.startswith("|") and "`dispatch-kickoff`" in line and "`next-dispatch`" in line
               for line in note.splitlines())
