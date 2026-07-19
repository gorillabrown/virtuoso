#!/usr/bin/env python3
"""Scripted release pipeline for the virtuoso plugin (DEP-01).

Replaces the 5-step manual procedure whose hand-verified gaps produced three incidents in
one day (2026-07-19): a stale app UI trusted over filesystem state, a poisoned plugin-root
bridge, and two releases shipped on red CI because the local flow ran pytest but never
validate.py. Every gate below traces to one of those.

Usage:
    python release.py X.Y.Z [--notes "..."] [--allow-regen-diff]
    python release.py X.Y.Z --redeploy     # resume deploy/verify after main was already
                                           # released (bump+push done) but a later gate failed
    python release.py --dry-run            # all read-only gates vs the CURRENT state

Steps (real run):
  1  preflight   clean tree; main == origin/main (fetched); validate.py green; full pytest
                 green; bump_version.py --check in sync; target well-formed and != current
  2  regen-diff  installed writer vs repo writer on a fresh fixture: file sets + bytes must
                 match, else --allow-regen-diff is required and the diff is printed
  3  bump        bump_version.py X.Y.Z (writes plugin.json + marketplace.json)
  4  git         explicit-stage exactly those two files; chore(release) commit; push main
  5  deploy      marketplace clone pull --ff-only (version must match target);
                 cache/<ver> installed fresh from the clone
  6  registry    installed_plugins.json updated ONLY after shape validation, with a
                 timestamped backup written beside it first; .last-update-check refreshed
  7  sweep       SR-5 from THIS process (the harness's own filesystem view): normalized
                 writer hash equal across repo / clone / cache-target; bridge state
                 reported. Per-session snapshots are named UNVERIFIABLE (no local process
                 shares that subtree's view) -- the restart instruction is the mitigation.
  8  verify      the INSTALLED copy runs a fixture battery: create, then a second run that
                 must report nothing to do with byte-identical output
Exit codes: 0 all gates passed; 1 a gate failed (message names it); 2 usage error.

Dry-run performs 1, 2, 7 and 8 against the current installed version and writes NOTHING.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(SCRIPTS)
REPO = os.path.dirname(os.path.dirname(PLUGIN))
PLUGIN_JSON = os.path.join(PLUGIN, ".claude-plugin", "plugin.json")
MARKETPLACE_JSON = os.path.join(REPO, ".claude-plugin", "marketplace.json")

HOME = os.path.expanduser("~")
CLONE = os.path.join(HOME, ".claude", "plugins", "marketplaces", "virtuoso-marketplace")
CACHE = os.path.join(HOME, ".claude", "plugins", "cache", "virtuoso-marketplace", "virtuoso")
REGISTRY = os.environ.get(
    "VIRTUOSO_RELEASE_REGISTRY",
    os.path.join(HOME, ".claude", "plugins", "installed_plugins.json"),
)
LAST_UPDATE_CHECK = os.path.join(HOME, ".claude", "plugins", ".last-update-check")
BRIDGE = os.path.join(HOME, ".virtuoso", "plugin-root")
PLUGIN_KEY = "virtuoso@virtuoso-marketplace"
WRITER_REL = os.path.join("scripts", "virtuoso_preflight.py")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class Gate(Exception):
    """A named pipeline gate failed; the release must not proceed."""


def say(msg):
    # Defensive: a UnicodeEncodeError from print() under a strict console codepage must
    # never abort the pipeline (SR-1 review: imagine it firing on the line AFTER push).
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def run(cmd, cwd=REPO, check=True, timeout=600):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise Gate("command failed (%d): %s\n%s" % (p.returncode, " ".join(cmd),
                                                    (p.stderr or p.stdout).strip()[:800]))
    return p


def norm_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()[:16]


def current_version():
    with open(PLUGIN_JSON, encoding="utf-8") as f:
        return json.load(f)["version"]


# --- step 1: preflight ---------------------------------------------------------------------

def gate_preflight(target, redeploy=False):
    # Cheap usage gates first — a malformed target should fail in milliseconds, not after
    # a full suite run. --redeploy INVERTS the equality gate: it resumes a release whose
    # bump+push already landed, so the target must EQUAL the repo's current version.
    if target is not None:
        if not _VERSION_RE.match(target):
            raise Gate("target version %r is not X.Y.Z" % target)
        if redeploy and target != current_version():
            raise Gate("--redeploy resumes the CURRENT version (%s), not %s"
                       % (current_version(), target))
        if not redeploy and target == current_version():
            raise Gate("target version %s equals the current version (already released? "
                       "resume an incomplete deploy with --redeploy)" % target)

    st = run(["git", "status", "--porcelain"]).stdout.strip()
    if st:
        raise Gate("working tree not clean:\n" + st)
    say("[preflight] tree clean")

    run(["git", "fetch", "origin"])
    local = run(["git", "rev-parse", "main"]).stdout.strip()
    remote = run(["git", "rev-parse", "origin/main"]).stdout.strip()
    if local != remote:
        raise Gate("main != origin/main (%s vs %s) — reconcile before releasing"
                   % (local[:9], remote[:9]))
    say("[preflight] main == origin/main @ %s" % local[:9])

    # The gate that was missing when v1.3.4/v1.3.5 shipped on red CI.
    p = run([sys.executable, os.path.join(SCRIPTS, "validate.py")], check=False)
    if p.returncode != 0 or "All checks passed" not in p.stdout:
        raise Gate("validate.py is RED — CI would fail:\n" + p.stdout.strip()[-600:])
    say("[preflight] validate.py green")

    p = run([sys.executable, "-m", "pytest", PLUGIN, "-q"], check=False)
    tail = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "(no output)"
    if p.returncode != 0:
        raise Gate("pytest RED: " + tail)
    say("[preflight] pytest green: %s" % tail)

    p = run([sys.executable, os.path.join(SCRIPTS, "bump_version.py"), "--check"], check=False)
    if p.returncode != 0 or "in sync" not in p.stdout:
        raise Gate("bump_version.py --check failed:\n" + p.stdout.strip()[-400:])
    cur = current_version()
    say("[preflight] versions in sync at %s" % cur)
    return cur


# --- step 2: regen-diff (charter A2 class) -------------------------------------------------

def _writer_outputs(writer, label):
    """Run `writer --root <tmp> --mode create` and return {relpath: sha}, or raise Gate."""
    out = {}
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, VIRTUOSO_HOME=td)
        p = subprocess.run([sys.executable, writer, "--root", td, "--mode", "create",
                            "--quiet"], capture_output=True, text=True, env=env, timeout=120)
        if p.returncode != 0:
            raise Gate("%s writer failed on fresh fixture: %s" % (label, (p.stderr or p.stdout)[:400]))
        for dirpath, _dirs, files in os.walk(td):
            for fn in files:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, td).replace("\\", "/")
                # The bridge records the RUNNING writer's own location (PF-04), so it
                # differs whenever two different installs are compared -- identity, not
                # output. Excluding it keeps this gate about what the writer PRODUCES.
                if rel == ".virtuoso/plugin-root":
                    continue
                out[rel] = norm_sha(full)
    return out


def gate_regen_diff(installed_root, allow):
    installed_writer = os.path.join(installed_root, WRITER_REL)
    repo_writer = os.path.join(PLUGIN, WRITER_REL)
    old = _writer_outputs(installed_writer, "installed")
    new = _writer_outputs(repo_writer, "repo")
    if old == new:
        say("[regen-diff] installed vs repo writer: byte-identical output (%d files)" % len(new))
        return
    lines = []
    for rel in sorted(set(old) | set(new)):
        a, b = old.get(rel), new.get(rel)
        if a != b:
            lines.append("  %-50s %s -> %s" % (rel, a or "(absent)", b or "(absent)"))
    say("[regen-diff] OUTPUT DIFFERS:\n" + "\n".join(lines))
    if not allow:
        raise Gate("regeneration output differs between installed and repo writers; "
                   "review the diff above and re-run with --allow-regen-diff if intended")
    say("[regen-diff] difference explicitly allowed by --allow-regen-diff")


# --- steps 3-4: bump + git -----------------------------------------------------------------

def do_bump_and_push(target, notes):
    p = run([sys.executable, os.path.join(SCRIPTS, "bump_version.py"), target], check=False)
    if p.returncode != 0 or "All declared files in sync at %s" % target not in p.stdout:
        raise Gate("bump did not report in-sync at %s:\n%s" % (target, p.stdout.strip()[-400:]))
    say("[bump] all declared files in sync at %s" % target)

    st = run(["git", "status", "--porcelain"]).stdout.strip().splitlines()
    # Tripwire set is DERIVED from bump_version.py's own config, not hardcoded — if the
    # declared-file list ever grows, the tripwire tracks it instead of contradicting it
    # (SR-1 review). Falls back to the known pair if the config is unreadable: the tripwire
    # only ever blocks, so a stale fallback fails safe.
    try:
        with open(os.path.join(PLUGIN, ".version-bump.json"), encoding="utf-8") as f:
            declared = json.load(f)["files"]
        # Config paths are PLUGIN-relative (marketplace.json via "../../"); git porcelain
        # is repo-relative with forward slashes — resolve then relativize.
        expected = {
            os.path.relpath(os.path.normpath(os.path.join(PLUGIN, d["path"])), REPO).replace("\\", "/")
            for d in declared
        }
    except (OSError, ValueError, KeyError, TypeError):
        expected = {"plugins/virtuoso/.claude-plugin/plugin.json", ".claude-plugin/marketplace.json"}
    actual = {ln[3:].strip() for ln in st}
    if actual != expected:
        raise Gate("tripwire: dirty set %s != expected %s" % (sorted(actual), sorted(expected)))
    run(["git", "add", PLUGIN_JSON, MARKETPLACE_JSON])
    msg = "chore(release): v%s — %s" % (target, notes or "release")
    run(["git", "commit", "-m", msg])
    run(["git", "push", "origin", "main"])
    say("[git] release commit pushed: %s" % run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip())


# --- steps 5-6: deploy + registry ----------------------------------------------------------

def deploy_cache(target):
    run(["git", "pull", "--ff-only"], cwd=CLONE)
    with open(os.path.join(CLONE, "plugins", "virtuoso", ".claude-plugin", "plugin.json"),
              encoding="utf-8") as f:
        clone_ver = json.load(f)["version"]
    if clone_ver != target:
        raise Gate("marketplace clone at %s, expected %s — push/pull mismatch" % (clone_ver, target))
    dst = os.path.join(CACHE, target)
    try:
        if os.path.isdir(dst):
            # Only reachable on a retry/--redeploy after an earlier partial attempt.
            shutil.rmtree(dst)
        shutil.copytree(os.path.join(CLONE, "plugins", "virtuoso"), dst)
    except OSError as exc:
        # Registry has NOT been touched yet (it is updated last, after verification), so
        # the machine still runs the previous version — state the fact.
        raise Gate("cache install failed (%r). The registry still points at the previous "
                   "version; remove the partial dir %s and resume with --redeploy." % (exc, dst))
    say("[deploy] cache installed: %s" % dst)
    return dst


def _validated_registry():
    """Load + shape-validate installed_plugins.json (charter A1). Returns (data, entry)."""
    try:
        with open(REGISTRY, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise Gate("installed_plugins.json unreadable/unparseable: %r" % exc)
    entries = data.get("plugins", {}).get(PLUGIN_KEY)
    if not isinstance(entries, list) or not entries or not isinstance(entries[0], dict):
        raise Gate("registry shape unexpected: plugins[%r] is not a non-empty list of dicts"
                   % PLUGIN_KEY)
    e = entries[0]
    if not isinstance(e.get("installPath"), str) or not isinstance(e.get("version"), str):
        raise Gate("registry entry shape unexpected: installPath/version not both strings — "
                   "refusing to write (schema may have changed; see charter A1)")
    return data, e


def update_registry(target, cache_dir):
    data, e = _validated_registry()
    backup = REGISTRY + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(REGISTRY, backup)
    e["installPath"] = cache_dir
    e["version"] = target
    e["lastUpdated"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + ".000Z"
    body = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    # Atomic: write beside, then os.replace() — a crash mid-write must never leave the
    # machine-wide registry truncated (SR-1 review CRITICAL). Same-directory replace is
    # atomic on both POSIX and Windows.
    tmp = REGISTRY + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, REGISTRY)
    with open(LAST_UPDATE_CHECK, "w", encoding="utf-8") as f:
        f.write(str(int(time.time() * 1000)))
    # Prune old backups, newest 5 kept — they accumulate one per release otherwise.
    baks = sorted(f for f in os.listdir(os.path.dirname(REGISTRY))
                  if f.startswith(os.path.basename(REGISTRY) + ".bak-"))
    for old in baks[:-5]:
        try:
            os.remove(os.path.join(os.path.dirname(REGISTRY), old))
        except OSError:
            pass
    say("[registry] %s -> %s (backup: %s)" % (PLUGIN_KEY, target, os.path.basename(backup)))


# --- step 7: SR-5 sweep --------------------------------------------------------------------

def sweep(target_dir, dry_run=False):
    # Post-release, all three copies MUST match the repo (that is what "released" means).
    # Mid-cycle (--dry-run), the repo legitimately runs ahead of the installed version, so
    # the reference is the cache-target and the repo is reported informationally -- failing
    # on it would make every between-releases dry-run red, which trains people to ignore
    # the gate (the exact reflex this phase exists to kill).
    ref_label = "cache-target" if dry_run else "repo"
    rows = [("repo", os.path.join(PLUGIN, WRITER_REL)),
            ("clone", os.path.join(CLONE, "plugins", "virtuoso", WRITER_REL)),
            ("cache-target", os.path.join(target_dir, WRITER_REL))]
    hashes = {label: (norm_sha(p) if os.path.isfile(p) else None) for label, p in rows}
    ref = hashes[ref_label]
    bad = []
    for label, _p in rows:
        h = hashes[label]
        if dry_run and label == "repo" and h != ref:
            say("[sweep] %-13s %s  differs (unreleased changes pending — expected mid-cycle)"
                % (label, h or "(absent)"))
            continue
        ok = h is not None and h == ref
        say("[sweep] %-13s %s  %s" % (label, h or "(absent)", "OK" if ok else "MISMATCH"))
        if not ok:
            bad.append(label)
    if bad:
        raise Gate("SR-5 sweep mismatch vs %s: %s" % (ref_label, bad))
    try:
        with open(BRIDGE, encoding="utf-8") as f:
            b = f.read().strip()
        valid = os.path.isfile(os.path.join(b, WRITER_REL))
        say("[sweep] bridge -> %s (%s)" % (b, "valid" if valid else "INVALID"))
    except OSError:
        say("[sweep] bridge absent (will be written by the next hook run)")
    say("[sweep] per-session snapshots: UNVERIFIABLE from any local process (the harness and "
        "shell disagree about that subtree — known divergence, 2026-07-19).")
    say("[sweep] >>> RESTART the Claude app to re-provision session snapshots from this cache. <<<")


# --- step 8: verify installed --------------------------------------------------------------

def verify_installed(cache_dir):
    writer = os.path.join(cache_dir, WRITER_REL)
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, VIRTUOSO_HOME=td)
        p1 = subprocess.run([sys.executable, writer, "--root", td, "--mode", "create"],
                            capture_output=True, text=True, env=env, timeout=120)
        if p1.returncode != 0:
            raise Gate("installed writer create failed: %s" % (p1.stderr or p1.stdout)[:400])
        before = {}
        for dirpath, _d, files in os.walk(td):
            for fn in files:
                full = os.path.join(dirpath, fn)
                before[full] = norm_sha(full)
        p2 = subprocess.run([sys.executable, writer, "--root", td, "--mode", "adopt"],
                            capture_output=True, text=True, env=env, timeout=120)
        if p2.returncode != 0 or "nothing to do" not in p2.stdout.lower():
            raise Gate("installed writer second run was not a clean no-op: %r"
                       % (p2.stdout or p2.stderr)[:300])
        for full, h in before.items():
            if norm_sha(full) != h:
                raise Gate("installed writer idempotency violation: %s changed" % full)
    say("[verify] installed writer: create OK, second run no-op, bytes stable")


# --- main ----------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="virtuoso release pipeline (DEP-01)")
    ap.add_argument("version", nargs="?", help="target X.Y.Z (omit with --dry-run)")
    ap.add_argument("--dry-run", action="store_true",
                    help="read-only gates against the current state; writes nothing")
    ap.add_argument("--notes", default="", help="release-note line for the commit message")
    ap.add_argument("--allow-regen-diff", action="store_true")
    ap.add_argument("--redeploy", action="store_true",
                    help="resume deploy/verify for the CURRENT (already bumped+pushed) version")
    a = ap.parse_args()

    if not a.dry_run and not a.version:
        ap.error("a target version is required unless --dry-run")
    if a.dry_run and a.redeploy:
        ap.error("--dry-run and --redeploy are mutually exclusive")

    # `progress` makes the failure report honest: "ABORTED" must never imply "nothing
    # happened" once main has been pushed (SR-1 review CRITICAL). Ordering note: the
    # registry is updated LAST, after sweep+verify — a deploy the pipeline itself flags as
    # suspect must never become the active install target.
    progress = []
    try:
        cur = gate_preflight(None if a.dry_run else a.version, redeploy=a.redeploy)
        _data, entry = _validated_registry()
        installed_root = entry["installPath"]
        if not os.path.isfile(os.path.join(installed_root, WRITER_REL)):
            raise Gate("registry installPath lacks the writer: %s" % installed_root)
        say("[registry] installed %s at %s" % (entry["version"], installed_root))
        progress.append("preflight")
        gate_regen_diff(installed_root, a.allow_regen_diff)
        progress.append("regen-diff")
        if a.dry_run:
            sweep(installed_root, dry_run=True)
            verify_installed(installed_root)
            say("\nDRY-RUN COMPLETE: every gate green against version %s. Nothing written." % cur)
            return 0
        if a.redeploy:
            say("[redeploy] resuming deploy/verify for already-released v%s" % a.version)
        else:
            do_bump_and_push(a.version, a.notes)
        progress.append("released-to-main")
        cache_dir = deploy_cache(a.version)
        progress.append("cache-installed")
        sweep(cache_dir)
        verify_installed(cache_dir)
        progress.append("verified")
        update_registry(a.version, cache_dir)
        progress.append("registry-updated")
        say("\nRELEASE v%s COMPLETE. Remember: restart the app to propagate session snapshots."
            % a.version)
        return 0
    except Gate as exc:
        say("\nGATE FAILURE:\n%s" % exc)
        if "released-to-main" in progress:
            say("\nSTATE: main IS RELEASED (bump commit pushed). Completed: %s." % ", ".join(progress))
            if "registry-updated" in progress:
                say("The registry was already updated — investigate before trusting the install.")
            else:
                say("The registry still points at the PREVIOUS version; the machine keeps "
                    "working. Resume with: release.py %s --redeploy" % (a.version or ""))
        else:
            say("\nSTATE: nothing was released. Completed: %s." % (", ".join(progress) or "none"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
