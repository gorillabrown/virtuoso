#!/usr/bin/env python3
"""Structural validator for the virtuoso plugin. Exit 0 = all checks pass.

Beyond the manifest and frontmatter checks, this validator enforces the
portability and single-authority rules the v2 redesign introduced (item 99):

  * absolute user paths and machine-specific paths
  * bundled resources referenced but missing
  * product-, vendor-, and model-specific host terms in shipped content
  * project-specific names, thresholds, and directory assumptions
  * non-portable shell syntax in documented commands
  * contradictory authority claims (more than one "source of truth")
  * duplicated readiness rubrics (there must be exactly one)
  * script/skill status-token mismatches against the published contract
  * retired tools still referenced anywhere
  * unsafe fallback path creation (a helper that creates a directory to answer
    a query)
  * the project-overlay clause, in every shipped skill and agent
  * agent memory directory names, against both disk and git's index

Run from anywhere: paths resolve from __file__.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skill_rules  # noqa: E402

from tools.governance import overlays as overlays_mod, result as result_mod  # noqa: E402

fails: list[str] = []
oks: list[str] = []

#: The per-host plugin manifests this plugin ships. Each is an install surface,
#: and every one of them must advertise the same version.
INSTALL_MANIFESTS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json")

TEXT_SUFFIXES = (".md", ".json", ".py", ".txt", ".yaml", ".yml", ".ps1", ".sh")
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}

#: Lines carrying this marker opt out of the text scans — for deliberate
#: fixtures and for the validator's own pattern tables.
EXEMPT = "validate-ok:"

# --- pattern tables -----------------------------------------------------------

ABSOLUTE_PATH_PATTERNS = [
    (r"C:\\\\Users", "Windows user path"),
    (r"/Users/[A-Za-z0-9._-]+/", "macOS home path"),
    (r"/home/[A-Za-z0-9._-]+/", "Linux home path"),
    (r"~/\.claude/plugins/", "hardcoded plugin install path"),
    (r"~/\.virtuoso/plugin-root", "retired unversioned plugin-root pointer"),
]

#: Product, vendor, and model names must not appear in shipped content. A host
#: adapter file may name its host; nothing else may.
HOST_TERM_PATTERNS = [
    (r"\bCowork\b", "product name"),
    (r"\bCodex\b", "product name"),
    (r"\bChatGPT\b", "product name"),
    (r"\bOpenAI\b", "vendor name"),
    (r"\b(?:Opus|Sonnet|Haiku)\b", "model name"),
    (r"(?<![\w-])(?:opus|sonnet|haiku)(?![\w-])", "model name"),
]
#: Files allowed to name a host, because naming one is their entire purpose.
HOST_ADAPTER_FILES = {
    "skills/pointer-closeout/agents/openai.yaml",
}
#: The agent frontmatter `model:` field is host configuration, not prose.
MODEL_FRONTMATTER_RE = re.compile(r"^model:\s*\S+\s*$")

#: Names, thresholds, and directory layouts belonging to one specific project.
PROJECT_SPECIFIC_PATTERNS = [
    (r"\bGoG\b", "project name"),
    (r"\bSimEngine\b", "project directory"),
    (r"\bICM\b(?!\s)", "project subsystem name"),
    (r"\bicm_[a-z]+\.py\b", "project script name"),
    (r"\bAGENT_FINDINGS\.md\b", "project document name"),
    (r"\b2\. Project Documentation/", "project directory assumption"),
    (r"\bN=1,?200\b", "project-specific threshold"),
    (r"\bSRL-\d{3}\b", "project-specific rule identifier"),
    (r"\bCL-WF-\d+\b", "project-specific rule identifier"),
]

#: Shell constructs that only work on one platform.
NONPORTABLE_SHELL_PATTERNS = [
    (r"\$\(cat\s+~/", "Unix-only command substitution over a home path"),
    (r"\bsource\s+~/", "Unix-only `source` over a home path"),
    (r"(?<![\w.])%USERPROFILE%", "Windows-only environment expansion"),
    (r"\bGet-Content\b.*\|\s*python\b", "PowerShell-only pipeline into python"),
]

#: Phrases that assert an authority the registry alone may assign.
AUTHORITY_CLAIM_RE = re.compile(
    r"(?:is|as|the)\s+(?:the\s+)?(?:single\s+)?source of truth", re.IGNORECASE)
#: An authority claim is acceptable only when it names the manifest.
AUTHORITY_ALLOWED_RE = re.compile(r"workspace-layout\.json|the registry|registry is the authority",
                                  re.IGNORECASE)

#: Tools removed in v2. A reference to one anywhere is a defect.
RETIRED_TOOLS = ["recalc.py", "build_sprint_queue.py", "prepare_closeout_files.py",
                 "sprint-queue.template.xlsx"]

#: A helper answering a query must not create a directory as a side effect.
UNSAFE_CREATE_RE = re.compile(r"(?:os\.makedirs|mkdir\(parents=True|\.mkdir\()")
#: Files where directory creation is legitimate (they exist to write).
CREATE_ALLOWED = {
    "scripts/virtuoso_preflight.py", "scripts/build_register_report.py",
    # Direct creation exists only behind --prepare/--out. mutation-plan delegates
    # its explicit recovery write to providers/recovery.py.
    "scripts/virtuoso_registry.py",
    "tools/governance/backup.py", "tools/governance/textio.py",
    "tools/governance/install.py", "tools/governance/repair.py",
    "tools/governance/providers/csv_provider.py",
    "tools/governance/providers/ledger.py",
    "tools/governance/providers/recovery.py",
    "tools/roadmap_visualizer/generate.py",
    "scripts/release.py", "scripts/validate.py",
}


def ok(message: str) -> None:
    oks.append(message)


def fail(message: str) -> None:
    fails.append(message)


def walk_text_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not name.lower().endswith(TEXT_SUFFIXES):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            try:
                with open(full, encoding="utf-8") as handle:
                    yield rel, handle.read()
            except (OSError, UnicodeDecodeError):
                continue


def scan(rel: str, text: str, patterns, label: str, hits: list) -> None:
    for number, line in enumerate(text.splitlines(), start=1):
        if EXEMPT in line:
            continue
        for pattern, why in patterns:
            if re.search(pattern, line):
                hits.append("%s:%d %s (%s)" % (rel, number, why, label))
                break


def check_frontmatter_and_manifests(skills_dir: str) -> list[str]:
    skill_names = sorted(d for d in os.listdir(skills_dir)
                         if os.path.isdir(os.path.join(skills_dir, d)))
    for name in skill_names:
        path = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(path):
            fail("skill %s: no SKILL.md" % name)
            continue
        text = open(path, encoding="utf-8").read()
        if not re.match(r"^---\s*\n", text):
            fail("skill %s: missing frontmatter" % name)
        match = re.search(r"(?m)^name:\s*(.+?)\s*$", text)
        if not match:
            fail("skill %s: no name: field" % name)
        elif match.group(1).strip() != name:
            fail("skill %s: name %r != folder" % (name, match.group(1).strip()))
    ok("%d skills; frontmatter/folder names checked" % len(skill_names))

    manifests = [(rel, os.path.join(ROOT, *rel.split("/"))) for rel in INSTALL_MANIFESTS]
    manifests += [
        (".claude-plugin/marketplace.json",
         os.path.join(ROOT, "..", "..", ".claude-plugin", "marketplace.json")),
        ("hooks/hooks.json", os.path.join(ROOT, "hooks", "hooks.json")),
    ]
    versions = {}
    for rel, path in manifests:
        try:
            data = json.load(open(path, encoding="utf-8"))
            ok("json valid: %s" % rel)
        except Exception as exc:  # noqa: BLE001
            fail("json INVALID: %s: %s" % (rel, exc))
            continue
        if rel.endswith("plugin.json") and data.get("name") != "virtuoso":
            fail("plugin name = %r in %s" % (data.get("name"), rel))
        if rel in INSTALL_MANIFESTS:
            versions[rel] = data.get("version")
        if rel.endswith("marketplace.json"):
            plugins = data.get("plugins", [])
            versions[rel] = plugins[0].get("version") if plugins else None
            if not (plugins and plugins[0].get("source") == "./plugins/virtuoso"):
                fail("marketplace source = %r (want './plugins/virtuoso')"
                     % (plugins and plugins[0].get("source")))

    # Every install surface advertises one version. A host that installs from a
    # manifest left behind at the previous release ships last release's plugin
    # while every other surface claims the new one.
    distinct = sorted({v for v in versions.values() if v is not None})
    if len(distinct) > 1 or None in versions.values():
        fail("install surfaces advertise different versions: %s"
             % {k: v for k, v in sorted(versions.items())})
    elif distinct:
        ok("%d install surface(s) all advertise %s" % (len(versions), distinct[0]))
    return skill_names


def check_session_hook() -> None:
    """Every shipped hook file's SessionStart command must run a read-only mode (item 2).

    The hook files are enumerated from the folder rather than named here: the
    plugin ships one install surface per host, each with its own hook file, and a
    rule that only covers the ones this function remembers is a rule the next
    surface ships without.
    """
    hooks_dir = os.path.join(ROOT, "hooks")
    hook_files = sorted(f for f in os.listdir(hooks_dir)) if os.path.isdir(hooks_dir) else []
    hook_files = [f for f in hook_files if f.endswith(".json")]
    if not hook_files:
        fail("no hook configuration found under hooks/")
        return

    for name in hook_files:
        try:
            data = json.load(open(os.path.join(hooks_dir, name), encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            fail("hooks/%s unreadable: %s" % (name, exc))
            return
        commands = [h.get("command", "")
                    for entry in data.get("hooks", {}).get("SessionStart", [])
                    for h in entry.get("hooks", [])]
        if not commands:
            fail("hooks/%s declares no SessionStart hook command" % name)
            return
        for command in commands:
            mode = re.search(r"--mode\s+(\S+)", command)
            if not mode or mode.group(1) not in ("check", "detect"):
                fail("hooks/%s runs SessionStart with --mode %s; it must be read-only "
                     "(check/detect)" % (name, mode.group(1) if mode else "<unset>"))
                return
    ok("%d hook file(s); every SessionStart command runs a read-only mode" % len(hook_files))


def check_relative_resources() -> None:
    """Every bundled resource a skill links to must exist (item 80)."""
    missing = []
    link_re = re.compile(r"\[[^\]]+\]\(((?!https?:)[^)#]+)")
    for rel, text in walk_text_files():
        # `assets/` holds templates whose links point at files the *generated*
        # packet will contain, not at bundled resources shipped with the plugin.
        if not rel.startswith("skills/") or not rel.endswith(".md") or "/assets/" in rel:
            continue
        base = os.path.dirname(os.path.join(ROOT, rel))
        for number, line in enumerate(text.splitlines(), start=1):
            if EXEMPT in line:
                continue
            for target in link_re.findall(line):
                target = target.strip()
                if not target or target.startswith("<"):
                    continue
                if not os.path.exists(os.path.normpath(os.path.join(base, target))):
                    missing.append("%s:%d -> %s" % (rel, number, target))
    (ok if not missing else fail)(
        "all bundled resource links resolve" if not missing
        else "missing relative resources: %s" % missing[:10])


def check_status_tokens() -> None:
    """Every status token documented in skills/references must exist in the
    published contract, and every contract status must be documented."""
    documented = set()
    token_re = re.compile(r"`?virtuoso-status:\s*([a-z-]+)`?")
    corpus = []
    for rel, text in walk_text_files():
        if rel.startswith(("skills/", "references/")) and rel.endswith(".md"):
            corpus.append((rel, text))
            for token in token_re.findall(text):
                documented.add(token)
    unknown = sorted(documented - set(result_mod.STATUSES))
    if unknown:
        fail("skills document status token(s) the contract does not define: %s" % unknown)
    else:
        ok("every documented status token exists in the contract")

    joined = "\n".join(text for _rel, text in corpus)
    undocumented = [s for s in result_mod.STATUSES if s not in joined]
    (ok if not undocumented else fail)(
        "every contract status is documented" if not undocumented
        else "contract statuses never documented: %s" % undocumented)


def check_single_rubric() -> None:
    """Exactly one readiness rubric may exist (item 52)."""
    canonical = os.path.join(ROOT, "references", "readiness-rubric.md")
    if not os.path.isfile(canonical):
        fail("references/readiness-rubric.md is missing — the rubric has no home")
        return
    duplicates = []
    rubric_heading = re.compile(r"(?m)^#{2,4}\s+Rubric\s+[A-Z]?\d", re.IGNORECASE)
    for rel, text in walk_text_files():
        if rel == "references/readiness-rubric.md" or not rel.endswith(".md"):
            continue
        if rubric_heading.search(text):
            duplicates.append(rel)
    (ok if not duplicates else fail)(
        "exactly one readiness rubric (references/readiness-rubric.md)" if not duplicates
        else "duplicated readiness rubric in: %s" % duplicates)

    # The rubric must declare its version and check count.
    text = open(canonical, encoding="utf-8").read()
    if not re.search(r"(?m)^\s*version:\s*\d", text):
        fail("readiness rubric does not declare a version")
    if not re.search(r"(?m)^\s*universal-checks:\s*\d", text):
        fail("readiness rubric does not declare its universal-check count")


def _is_test_file(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return name.startswith("test_") or name == "conftest.py"


def check_retired_tools() -> None:
    hits = []
    for rel, text in walk_text_files():
        # The validator names them; the tests assert their absence.
        if rel == "scripts/validate.py" or _is_test_file(rel):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if EXEMPT in line:
                continue
            for tool in RETIRED_TOOLS:
                if tool in line:
                    hits.append("%s:%d -> %s" % (rel, number, tool))
    (ok if not hits else fail)(
        "no references to retired tools" if not hits
        else "retired tools still referenced: %s" % hits[:10])


def check_unsafe_fallback_creation() -> None:
    """A read-only query helper must not create directories (item 86)."""
    hits = []
    for rel, text in walk_text_files():
        # Tests build fixtures on disk; that is their job.
        if not rel.endswith(".py") or rel in CREATE_ALLOWED or _is_test_file(rel):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if EXEMPT in line or line.lstrip().startswith("#"):
                continue
            if UNSAFE_CREATE_RE.search(line):
                hits.append("%s:%d" % (rel, number))
    (ok if not hits else fail)(
        "no unsafe fallback path creation" if not hits
        else "path creation in a module that should not write: %s" % hits)

    # Direct directory creation in virtuoso_registry.py may occur only behind an
    # explicit --prepare/--out path. mutation-plan's deliberate recovery write is
    # delegated to providers/recovery.py and covered by command-level tests.
    registry_cli = os.path.join(ROOT, "scripts", "virtuoso_registry.py")
    if os.path.isfile(registry_cli):
        text = open(registry_cli, encoding="utf-8").read()
        for match in re.finditer(r"os\.makedirs\(", text):
            window = text[max(0, match.start() - 300):match.start()]
            if "args.prepare" not in window and "args.out" not in window:
                fail("virtuoso_registry.py creates a directory outside an explicit "
                     "--prepare/--out path")
                break
        else:
            ok("virtuoso_registry.py creates directories directly only behind --prepare/--out")


def check_authority_claims() -> None:
    hits = []
    for rel, text in walk_text_files():
        if not rel.endswith(".md"):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if EXEMPT in line:
                continue
            if AUTHORITY_CLAIM_RE.search(line) and not AUTHORITY_ALLOWED_RE.search(line):
                hits.append("%s:%d %s" % (rel, number, line.strip()[:80]))
    (ok if not hits else fail)(
        "no contradictory authority claims" if not hits
        else "authority claimed outside the registry: %s" % hits[:6])


def check_text_scans(skill_names: list[str]) -> None:
    absolute, host, project, shell = [], [], [], []
    for rel, text in walk_text_files():
        if rel == "scripts/validate.py":
            continue
        scan(rel, text, ABSOLUTE_PATH_PATTERNS, "absolute path", absolute)
        scan(rel, text, PROJECT_SPECIFIC_PATTERNS, "project-specific", project)
        scan(rel, text, NONPORTABLE_SHELL_PATTERNS, "non-portable shell", shell)
        if rel in HOST_ADAPTER_FILES:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if EXEMPT in line or MODEL_FRONTMATTER_RE.match(line):
                continue
            for pattern, why in HOST_TERM_PATTERNS:
                if re.search(pattern, line):
                    host.append("%s:%d %s" % (rel, number, why))
                    break

    for hits, message in ((absolute, "absolute/machine-specific paths"),
                          (host, "product-, vendor-, or model-specific host terms"),
                          (project, "project-specific names, thresholds, or directories"),
                          (shell, "non-portable shell syntax")):
        (ok if not hits else fail)(
            "no %s" % message if not hits else "%s: %s" % (message, hits[:8]))

    # Skill bodies still cannot use ${CLAUDE_PLUGIN_ROOT} (hooks/MCP only).
    root_hits = [rel for rel, text in walk_text_files()
                 if rel.startswith("skills/") and "${CLAUDE_PLUGIN_ROOT}/" in text]
    (ok if not root_hits else fail)(
        "no ${CLAUDE_PLUGIN_ROOT}/ path-uses in skill bodies" if not root_hits
        else "${CLAUDE_PLUGIN_ROOT}/ used in: %s" % root_hits)

    dangling = [rel for rel, text in walk_text_files()
                if rel.startswith("skills/") and "WORKFLOW_REFERENCE.md §" in text]
    (ok if not dangling else fail)(
        "no dangling WORKFLOW_REFERENCE.md section refs" if not dangling
        else "dangling refs in: %s" % dangling)


def check_launchers_match_source() -> None:
    """The shipped launchers must be byte-identical to what install.py writes,
    so a package-relative copy can never drift from the installed one."""
    from tools.governance import install
    for name, expected in (("virtuoso", install.POSIX_LAUNCHER),
                           ("virtuoso.ps1", install.POWERSHELL_LAUNCHER)):
        path = os.path.join(ROOT, "bin", name)
        if not os.path.isfile(path):
            fail("bin/%s is missing" % name)
            continue
        with open(path, encoding="utf-8", newline="") as handle:
            actual = handle.read()
        if actual != expected:
            fail("bin/%s has drifted from tools/governance/install.py" % name)
    if not [f for f in fails if "bin/" in f]:
        ok("bundled launchers match their source of record")


def check_commands() -> None:
    skills_dir = os.path.join(ROOT, "skills")
    cmd_dir = os.path.join(ROOT, "commands")
    if not os.path.isdir(cmd_dir):
        ok("no commands/ dir (skills invoked via virtuoso: namespace)")
        return
    commands = sorted(c[:-3] for c in os.listdir(cmd_dir) if c.endswith(".md"))
    for command in commands:
        if not os.path.isdir(os.path.join(skills_dir, command)):
            fail("command %s: no matching skill" % command)
        if not open(os.path.join(cmd_dir, command + ".md"),
                    encoding="utf-8").read().startswith("---"):
            fail("command %s: no frontmatter" % command)
    ok("%d commands; all map to skills" % len(commands))


#: The one file under agents/ that is guidance about agents, not an agent.
AGENT_GUIDE = "AGENT_MEMORY_GUIDE.md"
#: A documented memory directory, e.g. `.claude/agent-memory/socrates/`.
MEMORY_DIR_RE = re.compile(r"agent-memory/([^/`\s]+)/")
#: The agent frontmatter field that turns persistent memory on.
MEMORY_FIELD_RE = re.compile(r"(?m)^memory:\s*(\S+)\s*$")


def shipped_skill_names() -> list[str]:
    """Skill folders, read off disk."""
    skills_dir = os.path.join(ROOT, "skills")
    return sorted(d for d in os.listdir(skills_dir)
                  if os.path.isdir(os.path.join(skills_dir, d)))


def shipped_agent_files() -> list[str]:
    """Agent bodies, read off disk. The memory guide is documentation, not an agent."""
    agents_dir = os.path.join(ROOT, "agents")
    if not os.path.isdir(agents_dir):
        return []
    return sorted(f for f in os.listdir(agents_dir)
                  if f.endswith(".md") and f != AGENT_GUIDE)


def check_overlay_clause() -> None:
    """Every shipped skill and agent carries the project-overlay clause, verbatim.

    Both rosters are enumerated from the folders, never from a list kept here. A
    list is exactly the thing a sixteenth skill gets added without touching — and
    the clause it would then be missing is the one telling it to read its project's
    overlay instead of being forked. Comparing against
    ``overlays.OVERLAY_CLAUSE`` rather than a second copy of the words means the
    clause has one home, so "present" and "still says the same thing" are the same
    check.
    """
    targets = ["skills/%s/SKILL.md" % name for name in shipped_skill_names()]
    targets += ["agents/%s" % name for name in shipped_agent_files()]
    if not targets:
        fail("no skills or agents found to check for the overlay clause")
        return

    missing, drifted = [], []
    for rel in targets:
        try:
            with open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            missing.append(rel)
            continue
        if overlays_mod.CLAUSE_MARKER not in text:
            missing.append(rel)
        elif overlays_mod.OVERLAY_CLAUSE not in text:
            drifted.append(rel)

    if missing:
        fail("overlay clause missing from: %s" % missing)
    if drifted:
        fail("overlay clause has drifted from tools/governance/overlays.py in: %s" % drifted)
    if not missing and not drifted:
        ok("overlay clause present and verbatim in %d skill(s) and %d agent(s)"
           % (len(shipped_skill_names()), len(shipped_agent_files())))


def _git_tracked(relative_dir: str) -> list[str] | None:
    """Paths git's index carries under ``relative_dir``, or ``None`` when there is
    no index to ask (an export, a tarball, git absent)."""
    try:
        completed = subprocess.run(
            ["git", "-C", ROOT, "ls-files", "-z", "--", relative_dir],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return [p for p in completed.stdout.split("\0") if p]


def check_agent_memory_names() -> None:
    """Agent memory directory names must be the agent's own name, lowercased.

    Audited against two records, because either one alone can lie. The filesystem
    answers case-insensitively on Windows and on a default macOS volume, so a
    memory directory spelled with the wrong case reads back as correct there and
    resolves to nothing on Linux — where the agent then starts every session with
    an empty memory and says nothing about it. Git's index stores the case it was
    given, so it catches a case-only rename the filesystem hides; but it only knows
    tracked files, so it cannot see one that was never added. Agreement between the
    two is the check.
    """
    problems = []
    agent_files = shipped_agent_files()
    for name in agent_files:
        stem = name[:-3]
        rel = "agents/%s" % name
        with open(os.path.join(ROOT, "agents", name), encoding="utf-8") as handle:
            text = handle.read()

        declared = re.search(r"(?m)^name:\s*(.+?)\s*$", text)
        if not declared:
            problems.append("%s: no name: field" % rel)
            continue
        if declared.group(1).strip() != stem:
            problems.append("%s: frontmatter name %r != filename"
                            % (rel, declared.group(1).strip()))

        directories = set(MEMORY_DIR_RE.findall(text))
        wrong = sorted(d for d in directories if d != stem.lower())
        if wrong:
            problems.append("%s: memory directory %s should be %r"
                            % (rel, wrong, stem.lower()))
        if MEMORY_FIELD_RE.search(text) and not directories:
            problems.append("%s: declares a memory: field but documents no memory location, "
                            "so nothing tells the agent where to read or write it" % rel)

    tracked = _git_tracked("agents")
    if tracked is None:
        note = " (git index unavailable; disk only)"
    else:
        note = " (disk and git index agree)"
        on_disk = set(agent_files)
        if os.path.isfile(os.path.join(ROOT, "agents", AGENT_GUIDE)):
            on_disk.add(AGENT_GUIDE)
        in_index = {p.split("/")[-1] for p in tracked}
        # Compared as exact strings: a case-only rename is invisible to the
        # filesystem on Windows and macOS but plainly visible here.
        for missing in sorted(on_disk - in_index):
            problems.append("agents/%s is on disk but not in git's index (untracked, or "
                            "tracked under a different spelling)" % missing)
        for stale in sorted(in_index - on_disk):
            problems.append("agents/%s is in git's index but not on disk under that exact "
                            "name" % stale)

    (ok if not problems else fail)(
        "%d agent memory name(s) audited%s" % (len(agent_files), note) if not problems
        else "agent memory name audit: %s" % problems)


def check_promoted_rule_anchors() -> None:
    """Every promoted rule must still be present in its skill body.

    A rule promoted into a project's lessons catalog is documentation, not
    enforcement: execution paths read skill bodies at session start, never the
    catalog, and a promoted rule with no dispatch-time machinery is applied at
    agent discretion. This is that machinery for prose.
    """
    missing = skill_rules.missing_anchors(os.path.join(ROOT, "skills"))
    total = sum(len(v) for v in skill_rules.REQUIRED_RULE_ANCHORS.values())
    (ok if not missing else fail)(
        "%d promoted-rule anchors present" % total if not missing
        else "missing rule anchors: %s" % missing)


def main() -> int:
    skill_names = check_frontmatter_and_manifests(os.path.join(ROOT, "skills"))
    check_session_hook()
    check_overlay_clause()
    check_agent_memory_names()
    check_promoted_rule_anchors()
    check_text_scans(skill_names)
    check_relative_resources()
    check_status_tokens()
    check_single_rubric()
    check_retired_tools()
    check_unsafe_fallback_creation()
    check_authority_claims()
    check_launchers_match_source()
    check_commands()

    print("VALIDATION RESULTS")
    for message in oks:
        print("  [OK]   %s" % message)
    for message in fails:
        print("  [FAIL] %s" % message)
    if fails:
        print("\n%d failure(s)" % len(fails))
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
