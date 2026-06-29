#!/usr/bin/env python3
"""Bump / check / audit the plugin version across declared manifest files.

Zero non-stdlib dependencies (the plugin already requires Python). Reads
``.version-bump.json`` for the file+field list and audit excludes.

Usage:
  python scripts/bump_version.py --check        Report versions; detect drift.
  python scripts/bump_version.py --audit        Check + grep repo for stale strings.
  python scripts/bump_version.py <new-version>  Set all declared files to <new-version>.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, ".version-bump.json")


def load_cfg():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def get_field(path, field):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        cur = json.load(f)
    for part in field.split("."):
        cur = cur[int(part)] if part.isdigit() else cur[part]
    return cur


def set_version_in_file(path, new):
    full = os.path.join(ROOT, path)
    with open(full, encoding="utf-8") as f:
        text = f.read()
    new_text, n = re.subn(r'("version"\s*:\s*")[^"]+(")',
                          r"\g<1>" + new + r"\g<2>", text, count=1)
    if n == 0:
        print(f"  warning: no version field in {path}", file=sys.stderr)
        return False
    with open(full, "w", encoding="utf-8") as f:
        f.write(new_text)
    return True


def cmd_check():
    cfg = load_cfg()
    versions = []
    print("Version check:")
    for f in cfg["files"]:
        try:
            v = get_field(f["path"], f["field"])
            versions.append(v)
            print(f"  {f['path']} ({f['field']}): {v}")
        except Exception as e:  # noqa: BLE001
            print(f"  {f['path']} ({f['field']}): MISSING ({e})")
            versions.append(None)
    uniq = {v for v in versions if v is not None}
    if len(uniq) > 1 or None in versions:
        print(f"DRIFT DETECTED: {sorted(str(v) for v in set(versions))}")
        return 1
    print(f"All declared files in sync at {next(iter(uniq))}")
    return 0


def cmd_bump(new):
    if not re.fullmatch(r"\d+\.\d+\.\d+", new):
        print(f"error: '{new}' is not semver (X.Y.Z)", file=sys.stderr)
        return 2
    cfg = load_cfg()
    for f in cfg["files"]:
        ok = set_version_in_file(f["path"], new)
        print(f"  {'set ' if ok else 'skip'} {f['path']} -> {new}")
    return cmd_check()


def cmd_audit():
    rc = cmd_check()
    cfg = load_cfg()
    cur = None
    for f in cfg["files"]:
        try:
            cur = get_field(f["path"], f["field"])
            break
        except Exception:  # noqa: BLE001
            continue
    if not cur:
        return rc
    excl = set(cfg.get("audit", {}).get("exclude", [])) | {".git", "node_modules", "__pycache__"}
    declared = {f["path"] for f in cfg["files"]}
    print(f"\nAudit: scanning for stale version string '{cur}'...")
    hits = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in excl]
        for fn in fns:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            if rel in declared or any(rel == e or rel.startswith(e.rstrip("/") + "/") for e in excl):
                continue
            try:
                with open(full, encoding="utf-8") as fh:
                    for i, line in enumerate(fh, 1):
                        if cur in line:
                            hits.append(f"{rel}:{i}: {line.strip()[:80]}")
            except (OSError, UnicodeDecodeError):
                continue
    if hits:
        print(f"  {len(hits)} undeclared occurrence(s) of '{cur}':")
        for h in hits:
            print("   ", h)
    else:
        print("  no undeclared version strings found")
    return rc


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    arg = argv[0]
    if arg == "--check":
        return cmd_check()
    if arg == "--audit":
        return cmd_audit()
    if arg.startswith("--"):
        print(__doc__)
        return 2
    return cmd_bump(arg)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
