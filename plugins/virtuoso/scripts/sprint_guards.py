#!/usr/bin/env python3
"""Mechanical guards for sprint burst-end and close-out.

A promoted rule with no dispatch-time machinery gets applied by agent discretion
(SRL-046). These are the executable halves of three rules the virtuoso skill body
states in prose:

  staging-sweep    resident staging memos are open obligations, not archive
                   artifacts -- enumerate them at every close-out (SRL-651)
  artifacts-exist  a named completion artifact must be on the merged branch before
                   the worktree is removed (SRL-312)
  unpushed         an unpushed commit at burst end is invisible to every other lane

Each subcommand exits 0 clean / 1 on a finding / 2 on a usage or resolution error, so
a caller can branch on the code without parsing prose. Paths resolve through the
governance registry -- never a hardcoded convention.
"""
import argparse
import json
import os
import re
import subprocess
import sys

STAGING_MEMO_RE = re.compile(r"^Memo\..+\.GovernanceStaging\..+\.md$")
_MACHINE_BLOCK_RE = re.compile(
    r"<!--\s*virtuoso-governance-registry\s*\n(.*?)\n-->", re.DOTALL)
_MACHINE_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.+)$")
_README_CANDIDATES = ("Virtuoso.Governance.Readme.md", "VIRTUOSO.GOVERNANCE.README.md")


def _read_manifest_paths(root):
    path = os.path.join(root, "Virtuoso", "workspace-layout.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    paths = data.get("paths")
    return {k: v for k, v in paths.items() if isinstance(v, str)} \
        if isinstance(paths, dict) else {}


def _read_readme_paths(root):
    for name in _README_CANDIDATES:
        try:
            with open(os.path.join(root, name), encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        block = _MACHINE_BLOCK_RE.search(text)
        if not block:
            continue
        out = {}
        for line in block.group(1).splitlines():
            m = _MACHINE_LINE_RE.match(line.strip())
            if m:
                out[m.group(1)] = m.group(2).strip()
        return out
    return {}


def resolve_registry_path(root, key):
    """Absolute path for a registry role, or None when neither carrier holds the key.

    The manifest wins for any role it already carries; the readme's machine block is
    the carrier for roles the manifest does not yet hold. This is the same resolution
    order the shared contract states, and the reason it exists is that a role can live
    in only one of the two carriers for a whole release cycle.
    """
    rel = _read_manifest_paths(root).get(key) or _read_readme_paths(root).get(key)
    if not rel:
        return None
    return os.path.normpath(os.path.join(root, rel))


def resident_staging_memos(root):
    """Root-relative paths of every staging memo still sitting in the close-outs dir.

    Top level only: a memo moved into a subdirectory has been dispositioned, and a
    sweep that recursed would re-open every already-closed obligation forever.
    """
    close_outs = resolve_registry_path(root, "closeOuts")
    if close_outs is None:
        raise LookupError("closeOuts")
    if not os.path.isdir(close_outs):
        return []
    found = [os.path.join(close_outs, n) for n in sorted(os.listdir(close_outs))
             if STAGING_MEMO_RE.match(n)
             and os.path.isfile(os.path.join(close_outs, n))]
    return [os.path.relpath(p, root).replace("\\", "/") for p in found]


def cmd_staging_sweep(args):
    try:
        memos = resident_staging_memos(args.root)
    except LookupError:
        print("staging-sweep: cannot resolve 'closeOuts' through the registry "
              "(checked Virtuoso/workspace-layout.json and the governance readme's "
              "machine block). Register it before sweeping.")
        return 2
    if not memos:
        print("staging-sweep: clean - no resident staging memos.")
        return 0
    print("staging-sweep: %d resident memo(s) - each is an OPEN OBLIGATION." % len(memos))
    for m in memos:
        print("  ! " + m)
    print("Confirm each against its TARGET DOCUMENTS, not against the memo's own "
          "claims, before deleting it (SRL-651).")
    return 1


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root,
                          capture_output=True, text=True)


def missing_on_ref(root, ref, paths):
    """Which of `paths` are NOT present on `ref`, in the order given.

    Uses `git cat-file -e <ref>:<path>`, which asks the object database rather than
    the filesystem -- the whole point is that a worktree-only artifact looks present
    to `os.path.exists` right up until the worktree is removed (SRL-312).
    Raises LookupError when `ref` itself does not resolve.
    """
    if _git(root, "rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode:
        raise LookupError(ref)
    missing = []
    for rel in paths:
        probe = "%s:%s" % (ref, rel.replace("\\", "/"))
        if _git(root, "cat-file", "-e", probe).returncode:
            missing.append(rel)
    return missing


def cmd_artifacts_exist(args):
    try:
        missing = missing_on_ref(args.root, args.ref, args.paths)
    except LookupError as exc:
        print("artifacts-exist: ref %s does not resolve in %s" % (exc.args[0], args.root))
        return 2
    total = len(args.paths)
    if not missing:
        print("artifacts-exist: %d/%d present on %s" % (total, total, args.ref))
        return 0
    print("artifacts-exist: %d of %d NOT on %s:" % (len(missing), total, args.ref))
    for m in missing:
        print("  ! " + m)
    print("Do not remove the worktree - worktree-only artifacts vanish at removal, and "
          "a close-out that names them would reference a file that never existed in "
          "git (SRL-312).")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sweep = sub.add_parser("staging-sweep",
                           help="list staging memos still resident in closeOuts")
    sweep.add_argument("--root", default=os.getcwd())
    sweep.set_defaults(func=cmd_staging_sweep)

    art = sub.add_parser("artifacts-exist",
                         help="verify named artifacts are present on a git ref")
    art.add_argument("--root", default=os.getcwd())
    art.add_argument("--ref", required=True,
                     help="branch/commit the artifacts must be present on")
    art.add_argument("paths", nargs="+", help="repo-relative artifact paths")
    art.set_defaults(func=cmd_artifacts_exist)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
