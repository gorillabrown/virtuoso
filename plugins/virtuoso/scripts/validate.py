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

Run from anywhere: paths resolve from __file__.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.governance import result as result_mod  # noqa: E402

fails: list[str] = []
oks: list[str] = []

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
    # Creates only behind --prepare/--out; enforced by its own targeted check below.
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

    manifests = [
        (".claude-plugin/plugin.json", os.path.join(ROOT, ".claude-plugin", "plugin.json")),
        (".claude-plugin/marketplace.json",
         os.path.join(ROOT, "..", "..", ".claude-plugin", "marketplace.json")),
        ("hooks/hooks.json", os.path.join(ROOT, "hooks", "hooks.json")),
    ]
    for rel, path in manifests:
        try:
            data = json.load(open(path, encoding="utf-8"))
            ok("json valid: %s" % rel)
        except Exception as exc:  # noqa: BLE001
            fail("json INVALID: %s: %s" % (rel, exc))
            continue
        if rel.endswith("plugin.json") and data.get("name") != "virtuoso":
            fail("plugin name = %r" % data.get("name"))
        if rel.endswith("marketplace.json"):
            plugins = data.get("plugins", [])
            if not (plugins and plugins[0].get("source") == "./plugins/virtuoso"):
                fail("marketplace source = %r (want './plugins/virtuoso')"
                     % (plugins and plugins[0].get("source")))
    return skill_names


def check_session_hook() -> None:
    """The SessionStart hook must run a read-only mode (item 2)."""
    path = os.path.join(ROOT, "hooks", "hooks.json")
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        fail("hooks.json unreadable: %s" % exc)
        return
    commands = [h.get("command", "")
                for entry in data.get("hooks", {}).get("SessionStart", [])
                for h in entry.get("hooks", [])]
    if not commands:
        fail("no SessionStart hook command found")
        return
    for command in commands:
        mode = re.search(r"--mode\s+(\S+)", command)
        if not mode or mode.group(1) not in ("check", "detect"):
            fail("SessionStart hook runs --mode %s; it must be read-only (check/detect)"
                 % (mode.group(1) if mode else "<unset>"))
            return
    ok("SessionStart hook runs a read-only mode")


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

    # virtuoso_registry.py may create only under an explicit --prepare flag.
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
            ok("virtuoso_registry.py creates directories only behind --prepare/--out")


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


def main() -> int:
    skill_names = check_frontmatter_and_manifests(os.path.join(ROOT, "skills"))
    check_session_hook()
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
