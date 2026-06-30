#!/usr/bin/env python3
"""Structural validator for the virtuoso plugin. Exit 0 = all checks pass.

Checks: skill frontmatter (name == folder), manifest JSON validity + key fields,
no absolute C:\\ paths, no dangling WORKFLOW_REFERENCE.md section refs, no
${CLAUDE_PLUGIN_ROOT}/ path-uses inside skill bodies (hooks/MCP only), and a
1:1 command<->skill mapping. Run from anywhere: paths are resolved from __file__.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails, oks = [], []


def ok(m):
    oks.append(m)


def fail(m):
    fails.append(m)


def main():
    skills_dir = os.path.join(ROOT, "skills")
    skill_names = sorted(d for d in os.listdir(skills_dir)
                         if os.path.isdir(os.path.join(skills_dir, d)))

    # 1. Frontmatter name == folder
    for name in skill_names:
        sk = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(sk):
            fail(f"skill {name}: no SKILL.md")
            continue
        text = open(sk, encoding="utf-8").read()
        if not re.match(r"^---\s*\n", text):
            fail(f"skill {name}: missing frontmatter")
        m = re.search(r"(?m)^name:\s*(.+?)\s*$", text)
        if not m:
            fail(f"skill {name}: no name: field")
        elif m.group(1).strip() != name:
            fail(f"skill {name}: name '{m.group(1).strip()}' != folder")
    ok(f"{len(skill_names)} skills; frontmatter/folder names checked")

    # 2. Manifests. The plugin lives at <repo>/plugins/virtuoso (ROOT); marketplace.json
    # stays at the repo root, two levels up.
    manifests = [
        (".claude-plugin/plugin.json", os.path.join(ROOT, ".claude-plugin", "plugin.json")),
        (".claude-plugin/marketplace.json", os.path.join(ROOT, "..", "..", ".claude-plugin", "marketplace.json")),
        ("hooks/hooks.json", os.path.join(ROOT, "hooks", "hooks.json")),
    ]
    for rel, path in manifests:
        try:
            data = json.load(open(path, encoding="utf-8"))
            ok(f"json valid: {rel}")
        except Exception as e:  # noqa: BLE001
            fail(f"json INVALID: {rel}: {e}")
            continue
        if rel.endswith("plugin.json"):
            if data.get("name") != "virtuoso":
                fail(f"plugin name = {data.get('name')!r}")
        if rel.endswith("marketplace.json"):
            plugins = data.get("plugins", [])
            if not (plugins and plugins[0].get("source") == "./plugins/virtuoso"):
                fail(f"marketplace source = {plugins and plugins[0].get('source')!r} (want './plugins/virtuoso')")

    # 3/4/5. Text scans
    abs_hits, ref_hits, root_path_hits = [], [], []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in (".git", "__pycache__", ".pytest_cache")]
        for fn in fns:
            if not fn.lower().endswith((".md", ".json", ".py", ".txt", ".yaml", ".yml")):
                continue
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            try:
                t = open(full, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            if "C:\\Users" in t:
                abs_hits.append(rel)
            if rel.startswith("skills/") and "WORKFLOW_REFERENCE.md §" in t:
                ref_hits.append(rel)
            if rel.startswith("skills/") and "${CLAUDE_PLUGIN_ROOT}/" in t:
                root_path_hits.append(rel)
    (ok if not abs_hits else fail)(
        "no C:\\Users absolute paths" if not abs_hits else f"absolute paths in: {abs_hits}")
    (ok if not ref_hits else fail)(
        "no dangling WORKFLOW_REFERENCE.md section refs" if not ref_hits else f"dangling refs in: {ref_hits}")
    (ok if not root_path_hits else fail)(
        "no ${CLAUDE_PLUGIN_ROOT}/ path-uses in skill bodies"
        if not root_path_hits else f"${{CLAUDE_PLUGIN_ROOT}}/ path-use in skills: {root_path_hits}")

    # 6. Commands (optional): if present, each must map 1:1 to a skill.
    # Skills are invoked via the `virtuoso:` namespace, so standalone command
    # wrappers are not required — they only duplicated the slash menu.
    cmd_dir = os.path.join(ROOT, "commands")
    if os.path.isdir(cmd_dir):
        cmds = sorted(c[:-3] for c in os.listdir(cmd_dir) if c.endswith(".md"))
        for c in cmds:
            if not os.path.isdir(os.path.join(skills_dir, c)):
                fail(f"command {c}: no matching skill")
            if not open(os.path.join(cmd_dir, c + ".md"), encoding="utf-8").read().startswith("---"):
                fail(f"command {c}: no frontmatter")
        ok(f"{len(cmds)} commands; all map to skills")
    else:
        ok("no commands/ dir (skills invoked via virtuoso: namespace)")

    print("VALIDATION RESULTS")
    for m in oks:
        print("  [OK]  ", m)
    for m in fails:
        print("  [FAIL]", m)
    if fails:
        print(f"\n{len(fails)} failure(s)")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
