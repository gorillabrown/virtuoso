#!/usr/bin/env python3
"""Scripted release pipeline for the virtuoso plugin (DEP-01).

Replaces the 5-step manual procedure whose hand-verified gaps produced three incidents in
one day (2026-07-19): a stale app UI trusted over filesystem state, a poisoned plugin-root
bridge, and two releases shipped on red CI because the local flow ran pytest but never
validate.py. Every gate below traces to one of those.

Usage:
    python release.py X.Y.Z [--notes "..."] [--allow-regen-diff]
    python release.py X.Y.Z --redeploy     # resume publish/deploy/verify after main was
                                           # already released (bump+push done) but a later
                                           # gate failed
    python release.py --dry-run            # all read-only gates vs the CURRENT state
    python release.py --public-tree        # print the public release tree and how it
                                           # differs from the public main; nothing else

Steps (real run):
  1  preflight   clean tree; main == origin/main (fetched); validate.py green; full pytest
                 green; bump_version.py --check in sync; target well-formed and != current
  2  regen-diff  installed writer vs repo writer on a fresh fixture: file sets + bytes must
                 match, else --allow-regen-diff is required and the diff is printed
  3  bump        bump_version.py X.Y.Z (writes every manifest .version-bump.json declares)
  4  git         explicit-stage exactly those files; chore(release) commit; push main to
                 origin, the development repository
  5  publish     the release tree -- PUBLIC_TREE only -- becomes one commit on the public
                 repository's main, tagged vX.Y.Z (VIR-008); a repeat run is a no-op
  6  deploy      marketplace clone pull --ff-only (version must match target);
                 cache/<ver> installed fresh from the clone
  7  sweep       SR-5 from THIS process (the harness's own filesystem view): normalized
                 writer hash equal across repo / clone / cache-target. Per-session
                 snapshots are named UNVERIFIABLE (no local process shares that subtree's
                 view) -- the restart instruction is the mitigation.
  8  verify      the INSTALLED copy runs a fixture battery: create, then a second run that
                 must report nothing to do with byte-identical output
  9  registry    LAST, only after sweep+verify pass: installed_plugins.json updated after
                 shape validation, atomically (write-beside + os.replace), with a
                 timestamped backup written first; .last-update-check refreshed
Exit codes: 0 all gates passed; 1 a gate failed (message names it); 2 usage error.

Dry-run performs 1, 2, the step-5 preview, 7 and 8 against the current installed version,
reads (never writes) the registry of step 9, and writes NOTHING -- fetching the public main
aside.
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
PLUGIN_KEY = "virtuoso@virtuoso-marketplace"
WRITER_REL = os.path.join("scripts", "virtuoso_preflight.py")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

#: What the public repository carries (VIR-008), as repository-relative paths; a directory
#: brings its whole tree. Development material -- the rest of docs/, Project Documentation/,
#: the Virtuoso/ workspace -- stays in the development repository. Every entry must exist in
#: the release commit, so dropping one is a deliberate edit here, never a side effect.
PUBLIC_TREE = (".claude-plugin", ".gitattributes", ".github", ".gitignore", "LICENSE",
               "PRIVACY.md", "README.md", "RELEASE-NOTES.md", "docs/MIGRATION-1.4.md",
               "plugins")
#: Names a publish target other than plugin.json's `repository` (tests use a local bare repo).
PUBLIC_REMOTE_ENV = "VIRTUOSO_RELEASE_PUBLIC_REMOTE"
_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


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

def _create_command(writer, root):
    """Build a create probe compatible with both legacy and fail-closed writers."""
    help_result = subprocess.run(
        [sys.executable, writer, "--help"], capture_output=True, text=True, timeout=30)
    command = [sys.executable, writer, "--root", root, "--mode", "create"]
    if help_result.returncode == 0 and "--authorize" in help_result.stdout:
        command.append("--authorize")
    return command


#: Files that record WHERE the running writer lives rather than what it produces:
#: the retired plugin-root bridge (PF-04) and its v1.4 successor, the version-keyed
#: install record. Two different installs always differ here -- identity, not output.
IDENTITY_FILES = frozenset({".virtuoso/plugin-root", ".virtuoso/installs.json"})


def _writer_outputs(writer, label):
    """Run an explicitly authorized create fixture and return {relpath: sha}."""
    out = {}
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, VIRTUOSO_HOME=td)
        p = subprocess.run(_create_command(writer, td) + ["--quiet"],
                           capture_output=True, text=True, env=env, timeout=120)
        if p.returncode != 0:
            raise Gate("%s writer failed on fresh fixture: %s" % (label, (p.stderr or p.stdout)[:400]))
        for dirpath, _dirs, files in os.walk(td):
            for fn in files:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, td).replace("\\", "/")
                # Identity records differ whenever two different installs are compared.
                # Excluding them keeps this gate about what the writer PRODUCES.
                if rel in IDENTITY_FILES:
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

def _porcelain_paths(stdout):
    """Paths from `git status --porcelain` output. Slices each LINE's fixed 2-char status +
    separator individually — never .strip() the whole blob first: that eats the FIRST line's
    leading status space and shifts the slice, mangling `.claude-plugin/...` into
    `claude-plugin/...` (the pipeline's first real-run bug, v1.3.6 attempt 1, 2026-07-19)."""
    return {ln[2:].strip() for ln in stdout.splitlines() if ln.strip()}


def _expected_release_files():
    """The tripwire set, DERIVED from bump_version.py's own config rather than hardcoded —
    if the declared-file list ever grows, the tripwire tracks it instead of contradicting
    it (SR-1 review). Config paths are PLUGIN-relative (marketplace.json via "../../");
    git porcelain is repo-relative with forward slashes — resolve then relativize. Falls
    back to the known pair if the config is unreadable: the tripwire only ever blocks, so
    a stale fallback fails safe. A module-level function so tests exercise THIS code, not
    a hand-copied formula (SR-1 loop 2)."""
    try:
        with open(os.path.join(PLUGIN, ".version-bump.json"), encoding="utf-8") as f:
            declared = json.load(f)["files"]
        return {
            os.path.relpath(os.path.normpath(os.path.join(PLUGIN, d["path"])), REPO).replace("\\", "/")
            for d in declared
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {"plugins/virtuoso/.claude-plugin/plugin.json", ".claude-plugin/marketplace.json"}


def do_bump_and_push(target, notes):
    p = run([sys.executable, os.path.join(SCRIPTS, "bump_version.py"), target], check=False)
    if p.returncode != 0 or "All declared files in sync at %s" % target not in p.stdout:
        raise Gate("bump did not report in-sync at %s:\n%s" % (target, p.stdout.strip()[-400:]))
    say("[bump] all declared files in sync at %s" % target)

    actual = _porcelain_paths(run(["git", "status", "--porcelain"]).stdout)
    expected = _expected_release_files()
    if actual != expected:
        raise Gate("tripwire: dirty set %s != expected %s\nNOTE: the version bump already "
                   "wrote the declared files — `git checkout -- <them>` to restore before "
                   "re-running." % (sorted(actual), sorted(expected)))
    # Stage the SAME derived set the tripwire just checked, not a hand-listed pair:
    # a manifest the bumper writes but the commit leaves behind is a host installing
    # last release's plugin while every other surface advertises this one.
    run(["git", "add", "--", *sorted(expected)])
    msg = "chore(release): v%s — %s" % (target, notes or "release")
    run(["git", "commit", "-m", msg])
    run(["git", "push", "origin", "main"])
    say("[git] release commit pushed: %s" % run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip())


# --- step 5: publish (VIR-008) -------------------------------------------------------------

def _git(args, input=None, env=None, check=True):
    """git in the development repository, bytes in and out: tree plumbing carries
    NUL-separated paths, and no console codepage may touch them. REPO is read at call
    time, so tests can point it at a fixture."""
    p = subprocess.run(["git", *args], cwd=REPO, input=input, env=env,
                       capture_output=True, timeout=600)
    if check and p.returncode != 0:
        raise Gate("command failed (%d): git %s\n%s" % (
            p.returncode, " ".join(args),
            (p.stderr or p.stdout).decode("utf-8", "replace").strip()[:800]))
    return p.stdout


def _normalized_remote(url):
    """host/owner/repo, lower-cased, so the https, ssh and .git spellings of one repository
    compare equal. An existing local path compares as its real path."""
    u = (url or "").strip()
    if u and os.path.isdir(u):
        return os.path.realpath(u)
    u = re.sub(r"^[a-z][a-z0-9+.-]*://", "", u.rstrip("/"))
    u = re.sub(r"^[^@/]*@", "", u)
    u = re.sub(r"^([^/:]+):(?!\d)", r"\1/", u)
    return re.sub(r"\.git$", "", u).lower()


def public_remote():
    """Where releases publish: plugin.json's `repository`, unless PUBLIC_REMOTE_ENV names
    another. `origin` is the development repository; the two are never the same."""
    override = os.environ.get(PUBLIC_REMOTE_ENV, "").strip()
    if override:
        return override
    with open(PLUGIN_JSON, encoding="utf-8") as f:
        remote = (json.load(f).get("repository") or "").strip()
    if not remote:
        raise Gate("plugin.json names no `repository`, so the public repository is unknown")
    return remote


def public_tree_files(ref="HEAD"):
    """The public repository's files at ``ref``, as (mode, sha, path) in tree order.
    Raises Gate, naming it, when a PUBLIC_TREE entry is missing."""
    raw = _git(["ls-tree", "-r", "-z", "--full-tree", ref, "--", *PUBLIC_TREE])
    entries = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode, kind, sha = meta.decode("ascii").split()
        if kind != "blob":
            raise Gate("public path %s is a %s, not a file; only files are published"
                       % (path.decode("utf-8", "replace"), kind))
        entries.append((mode, sha, path.decode("utf-8")))
    paths = [p for _mode, _sha, p in entries]
    missing = [entry for entry in PUBLIC_TREE
               if not any(p == entry or p.startswith(entry + "/") for p in paths)]
    if missing:
        raise Gate("public path(s) missing from %s: %s -- rename or drop one only by "
                   "editing PUBLIC_TREE" % (ref, ", ".join(missing)))
    return entries


def _write_public_tree(entries):
    """Write ``entries`` as a tree object through a throwaway index, so blobs and modes are
    copied exactly: no working tree, no line-ending conversion."""
    workdir = tempfile.mkdtemp(prefix="virtuoso-public-")
    env = dict(os.environ, GIT_INDEX_FILE=os.path.join(workdir, "index"))
    try:
        info = b"".join(b"%s blob %s\t%s\0" % (mode.encode(), sha.encode(), path.encode("utf-8"))
                        for mode, sha, path in entries)
        _git(["update-index", "--add", "-z", "--index-info"], input=info, env=env)
        return _git(["write-tree"], env=env).decode("ascii").strip()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _remote_ref(remote, ref):
    """The commit ``ref`` names on ``remote`` (a tag is peeled), or None when it is absent."""
    out = _git(["ls-remote", remote, ref, ref + "^{}"]).decode("utf-8", "replace")
    found = {}
    for line in out.splitlines():
        sha, _, name = line.partition("\t")
        if name:
            found[name] = sha
    return found.get(ref + "^{}") or found.get(ref)


def _changes(old_tree, new_tree):
    """(status, path) for every file that differs between two trees."""
    out = _git(["diff-tree", "-r", "-z", "--no-renames", "--name-status", old_tree, new_tree])
    parts = [p.decode("utf-8") for p in out.split(b"\0") if p]
    return list(zip(parts[0::2], parts[1::2]))


def publish_release(target, notes="", preview=False):
    """Step 5: make the public repository's main carry the release tree and nothing else.

    The tree is PUBLIC_TREE at the release commit, built from git objects. It lands as one
    commit on top of the public main, tagged v<target>; both pushes are plain pushes, never
    forced, so a public main that moved meanwhile refuses the push and nothing is
    overwritten. Re-running is safe: when the public main already carries the tree there is
    nothing to commit, and a tag already naming the release commit is left alone -- which
    is what lets --redeploy pass through this step. A tag naming any other commit stops the
    release: a published tag is never moved. ``preview`` prints the tree and how it differs
    from the public main, and pushes nothing."""
    remote = public_remote()
    origin = _git(["remote", "get-url", "origin"], check=False).decode("utf-8", "replace").strip()
    if origin and _normalized_remote(origin) == _normalized_remote(remote):
        raise Gate("origin is the public repository (%s); releases run from the development "
                   "repository and publish to the public one" % remote)
    head = _git(["rev-parse", "HEAD"]).decode("ascii").strip()
    if not preview:
        main_ref = _git(["rev-parse", "--verify", "-q", "refs/heads/main"], check=False)
        if main_ref.decode("ascii").strip() != head:
            raise Gate("HEAD is not main; the release commit is main's, so publish from main")
    entries = public_tree_files(head)
    tree = _write_public_tree(entries)
    public_main = _remote_ref(remote, "refs/heads/main")
    if public_main:
        _git(["fetch", "--no-tags", remote, "refs/heads/main"])
        public_tree = _git(["rev-parse", public_main + "^{tree}"]).decode("ascii").strip()
    else:
        public_tree = _EMPTY_TREE
    changes = _changes(public_tree, tree)

    if preview:
        say("[publish] public tree at %s: %d files, for %s" % (head[:9], len(entries), remote))
        for _mode, _sha, path in entries:
            say("    %s" % path)
        say("[publish] against the public main (%s): %s" % (
            public_main[:9] if public_main else "none yet",
            ("%d file(s) differ" % len(changes)) if changes else "identical"))
        for status, path in changes:
            say("    %s %s" % (status, path))
        return None

    tag = "v%s" % target
    if public_main and public_tree == tree:
        commit = public_main
        say("[publish] the public main already carries this tree @ %s" % commit[:9])
    else:
        message = "release: %s — %s\n\nBuilt from development commit %s.\n" % (
            tag, notes or "release", head)
        command = ["commit-tree", tree, "-m", message]
        if public_main:
            command += ["-p", public_main]
        commit = _git(command).decode("ascii").strip()
    tagged = _remote_ref(remote, "refs/tags/" + tag)
    if tagged and tagged != commit:
        raise Gate("tag %s already names %s on the public repository, not %s; a published "
                   "tag is never moved -- resolve it by hand" % (tag, tagged[:9], commit[:9]))
    if commit != public_main:
        _git(["push", remote, "%s:refs/heads/main" % commit])
        say("[publish] public main -> %s (%d files; %d changed)"
            % (commit[:9], len(entries), len(changes)))
    if not tagged:
        _git(["push", remote, "%s:refs/tags/%s" % (commit, tag)])
    say("[publish] %s tagged %s on the public repository" % (commit[:9], tag))
    return commit


# --- steps 6 and 9: deploy + registry ------------------------------------------------------

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
    # Gate-wrapped like deploy_cache (SR-1 loop 2): an OSError here must surface through
    # the progress-aware report, not as a bare traceback that says nothing about whether
    # main was released — this is the step people most need legibility on. The atomic
    # write-beside + os.replace means REGISTRY's content is intact either way.
    try:
        backup = REGISTRY + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
        shutil.copyfile(REGISTRY, backup)
        e["installPath"] = cache_dir
        e["version"] = target
        e["lastUpdated"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + ".000Z"
        body = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        tmp = REGISTRY + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(tmp, REGISTRY)
        with open(LAST_UPDATE_CHECK, "w", encoding="utf-8") as f:
            f.write(str(int(time.time() * 1000)))
    except OSError as exc:
        raise Gate("registry update failed (%r). The atomic write means %s is either the "
                   "previous or the new content, never truncated; verify it, then resume "
                   "with --redeploy." % (exc, os.path.basename(REGISTRY)))
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
    # Mid-cycle (--dry-run), the repo may legitimately run ahead of the active install.
    # The marketplace clone may match either lineage: it can still be at the installed
    # release, or already track the newer source commit. A third, unrelated hash fails.
    ref_label = "cache-target" if dry_run else "repo"
    rows = [("repo", os.path.join(PLUGIN, WRITER_REL)),
            ("clone", os.path.join(CLONE, "plugins", "virtuoso", WRITER_REL)),
            ("cache-target", os.path.join(target_dir, WRITER_REL))]
    hashes = {label: (norm_sha(p) if os.path.isfile(p) else None) for label, p in rows}
    ref = hashes[ref_label]
    bad = []
    for label, _p in rows:
        h = hashes[label]
        if dry_run and label == "repo":
            ok = h is not None
            state = "SOURCE" if ok else "MISSING"
        elif dry_run and label == "clone":
            ok = h is not None and h in {hashes["repo"], hashes["cache-target"]}
            if h == hashes["repo"]:
                state = "OK (matches source)"
            elif h == hashes["cache-target"]:
                state = "OK (matches active install)"
            else:
                state = "MISMATCH"
        else:
            ok = h is not None and h == ref
            state = "OK" if ok else "MISMATCH"
        say("[sweep] %-13s %s  %s" % (label, h or "(absent)", state))
        if not ok:
            bad.append(label)
    if bad:
        raise Gate("SR-5 sweep mismatch vs %s: %s" % (ref_label, bad))
    say("[sweep] per-session snapshots: UNVERIFIABLE from any local process (the harness and "
        "shell disagree about that subtree — known divergence, 2026-07-19).")
    say("[sweep] >>> RESTART the Claude app to re-provision session snapshots from this cache. <<<")


# --- step 8: verify installed --------------------------------------------------------------

def verify_installed(cache_dir):
    writer = os.path.join(cache_dir, WRITER_REL)
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, VIRTUOSO_HOME=td)
        p1 = subprocess.run(_create_command(writer, td),
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
                    help="resume publish/deploy/verify for the CURRENT (already bumped+pushed) "
                         "version")
    ap.add_argument("--public-tree", action="store_true",
                    help="print the public release tree and how it differs from the public "
                         "main, then exit; reads only")
    a = ap.parse_args()

    if a.public_tree:
        if a.version or a.dry_run or a.redeploy:
            ap.error("--public-tree takes no version and runs alone")
        try:
            publish_release(None, preview=True)
            return 0
        except Gate as exc:
            say("\nGATE FAILURE:\n%s" % exc)
            return 1
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
            publish_release(cur, preview=True)
            sweep(installed_root, dry_run=True)
            verify_installed(installed_root)
            say("\nDRY-RUN COMPLETE: every gate green against version %s. Nothing written." % cur)
            return 0
        if a.redeploy:
            say("[redeploy] resuming deploy/verify for already-released v%s" % a.version)
        else:
            do_bump_and_push(a.version, a.notes)
        # Same state either way (preflight proved main==origin at target), but the failure
        # report distinguishes "pushed in THIS run" from "verified as already released".
        progress.append("released-to-main" if not a.redeploy else "release-verified-preexisting")
        publish_release(a.version, a.notes)
        progress.append("published")
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
        if "released-to-main" in progress or "release-verified-preexisting" in progress:
            how = ("bump commit pushed in this run" if "released-to-main" in progress
                   else "already released prior to this run")
            say("\nSTATE: main IS RELEASED (%s). Completed: %s." % (how, ", ".join(progress)))
            if "published" not in progress:
                say("The public repository has NOT received this release; --redeploy "
                    "publishes it first (publishing again is a no-op).")
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
