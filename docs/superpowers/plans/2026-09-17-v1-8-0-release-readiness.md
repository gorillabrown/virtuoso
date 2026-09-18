# v1.8.0 Release Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the v1.8.0 project-specificity work true on every platform the plugin claims to support, give `project-profile` the write path it documents, and release it through the pipeline that exists for that purpose.

**Architecture:** Nine tasks on one branch, in dependency order. Tasks 1-3 repair the Windows CI leg so it becomes a gate again. Tasks 4-6 fix three defects that make the documented operator loop fail or silently mislead on Windows. Task 7 adds `policy-set`, the missing explicit writer, built on the transactional backup path `repair` already uses. Tasks 8-9 reconcile the shipped record and run the release pipeline.

**Tech Stack:** Python 3.12 (CI) / 3.14 (dev machine), pytest, GitHub Actions (ubuntu-latest + windows-latest), the plugin's own `validate.py` and `release.py`.

**Spec:** `C:\Users\estra\Projects\Virtuoso\audits\Audit.AdversarialReview.v1.8.0-project-specificity.2026-09-17.md` (the adversarial review this plan implements; lives in the LOCAL-ONLY governance workspace, not in this repo). Design context: `docs/superpowers/specs/2026-09-17-project-specificity-architecture-design.md` in this repo.

## Global Constraints

Every task's requirements implicitly include this section.

- **Version stays `1.8.0`.** All three install manifests already advertise it. Do not bump. The release in Task 9 runs `--redeploy`, which requires the target to *equal* the current version.
- **Python behaviour must be identical on 3.12 and 3.13+.** `os.path.isabs("/x")` returns `True` on Windows under 3.12 and `False` under 3.13+. Never gate a portability decision on it.
- **Both CI legs must pass.** `ubuntu-latest` and `windows-latest`, Python 3.12, running `validate.py`, `bump_version.py --check`, and `pytest plugins/virtuoso/ -q`.
- **Overlay findings are never `error` severity.** Info or warning only. An overlay problem is the project's to fix; `repair` has nothing to propose for a file the project owns.
- **The `overlays` role stays `read-only` with `allowedWriters: []`.** No task may add a flag, ceremony, or code path that writes a project's overlays. Task 7 writes *policy*, which lives in the manifest, never an overlay.
- **Stage explicitly.** `git add <path>` only. Never `git add .` or `git add -A`. No destructive flags, no force-push.
- **`validate.py` must print `All checks passed.` after every task.**

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `plugins/virtuoso/tools/governance/overlays.py` | Mirror-path resolution, overlay audit, pairing checks, scaffolds, the clause | 1, 4, 5, 6 |
| `plugins/virtuoso/tools/governance/safepath.py` | Registered-path validation | 3 |
| `plugins/virtuoso/tools/governance/textio.py` | Byte and text I/O for governance documents | 4 |
| `plugins/virtuoso/tools/governance/registry.py` | `Finding` dataclass, registry load and validation | 5 |
| `plugins/virtuoso/tools/governance/policy.py` | Policy defaults, dotted lookup, validation, assignment | 7 |
| `plugins/virtuoso/tools/governance/repair.py` | Transactional manifest writes with backup and rollback | 7 |
| `plugins/virtuoso/scripts/virtuoso_registry.py` | The read-only query CLI plus explicit writers | 4, 7 |
| `plugins/virtuoso/scripts/test_overlays.py` | Overlay, pairing, scaffold, clause, and profile tests | 1, 2, 4, 5, 6, 7 |
| `plugins/virtuoso/scripts/test_registry_preservation.py` | Path-validation and preservation tests | 3 |
| `plugins/virtuoso/references/readiness-rubric.md` | Where a project reads about extensions and their bodies | 6 |
| `plugins/virtuoso/references/registry-contract.md` | The overlay contract and its finding table | 4, 6, 7 |
| `plugins/virtuoso/skills/project-profile/SKILL.md` | The specificity ceremony | 7 |
| `RELEASE-NOTES.md` | The release narrative | 8 |
| `docs/superpowers/specs/2026-09-17-project-specificity-architecture-design.md` | The design record | 8 |

---

## Before you start: branch setup

The working clone is on `feat/worktree-housekeeping` at `0acd927`, which is unrelated unmerged work. Local `main` and `origin/main` are both at `b06a6ed` (v1.6.0). The v1.8.0 work is six commits on `origin/eb/zealous-einstein-zxvy3w` at `0be47b1`, zero commits behind main.

**There is a checkout collision.** The clone has an untracked 1,859-line file at `docs/superpowers/specs/2026-09-16-project-overlays-design.md`. The target branch tracks a *different* 198-line document at that same path. `git checkout` will refuse rather than clobber it. Move it aside first.

- [ ] **Step 1: Preserve the untracked local spec**

```bash
cd /c/Users/estra/Projects/Virtuoso/virtuoso.dev
mkdir -p ../local-notes
mv docs/superpowers/specs/2026-09-16-project-overlays-design.md ../local-notes/2026-09-16-project-overlays-design.LOCAL-1859-line.md
git status --short
```

Expected: no output from `git status --short`. If anything else is listed, stop and resolve it before continuing.

- [ ] **Step 2: Check out the branch the work is on**

This plan originally created `fix/v1.8.0-release-readiness`. It was executed on
`eb/zealous-einstein-zxvy3w` instead — the executing session's designated branch — so that
is the branch that exists and the one Task 9 merges. Track it rather than branching from it.

```bash
git fetch origin
git checkout -B eb/zealous-einstein-zxvy3w origin/eb/zealous-einstein-zxvy3w
git log --oneline -1
```

Expected: the branch tip, whatever it currently is. `0be47b1` was the tip when this plan was
written; Tasks 1-8 and the review remediation have landed on top of it since.

- [ ] **Step 3: Confirm the starting failure count**

```bash
python -m pytest plugins/virtuoso -q 2>&1 | tail -10
```

Expected on Windows: `6 failed, 486 passed, 4 skipped`. On Linux: `492 passed, 2 skipped` (the count differs because two `pwsh`-gated launcher tests skip on Windows and the six failures do not occur on a case-sensitive filesystem). Record what you see — Task 1 and Task 2 are measured against it.

- [ ] **Step 4: Commit this plan to the branch**

```bash
git add docs/superpowers/plans/2026-09-17-v1-8-0-release-readiness.md
git commit -m "docs(plans): v1.8.0 release-readiness plan from the adversarial review

The review found the branch red on the Windows CI leg, the documented
scaffold redirect producing an overlay the plugin cannot read, the session
start line silent in two of three states, and project-profile's Phase 4
prescribing a write path that does not exist. This plan closes all four and
releases through the pipeline.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 1: Reject a rooted mirror key on every interpreter

**Files:**
- Modify: `plugins/virtuoso/tools/governance/overlays.py` (`case_exact_join`, `mirror_path`)
- Test: `plugins/virtuoso/scripts/test_overlays.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `overlays._rooted(candidate: str) -> bool`. `mirror_path(relative) -> str` and `case_exact_join(root, relative) -> str` keep their existing signatures and return `""` for a rooted or drive-qualified key on every platform and interpreter.

`mirror_path` currently rejects an absolute key with `os.path.isabs(relative.strip())`. Python 3.13 stopped treating a lone leading slash as absolute on Windows, so `mirror_path("/skills/epic/SKILL.md")` returns `"skills/epic/SKILL.md"` on a 3.13+ Windows machine and `""` everywhere else. That is the exact per-platform divergence the module's own docstring promises to prevent. CI runs 3.12 and cannot see it.

- [ ] **Step 1: Write the failing test**

Add to `plugins/virtuoso/scripts/test_overlays.py`, immediately after `test_mirror_path_rejects_unusable_keys`:

```python
@pytest.mark.parametrize("bad", [
    "/skills/epic/SKILL.md",
    "\\skills\\epic\\SKILL.md",
    "C:/skills/epic/SKILL.md",
    "C:\\skills\\epic\\SKILL.md",
])
def test_a_rooted_or_drive_qualified_key_is_refused_everywhere(bad):
    """Refused by both resolvers, on every OS and every interpreter.

    `os.path.isabs` is not a portable test for this: it answers differently per
    platform AND per interpreter, because Python 3.13 stopped treating a lone
    leading slash as absolute on Windows. A key one interpreter accepts and
    another drops is the divergence this module exists to prevent, and CI's
    3.12 cannot see it.
    """
    assert overlays_mod.mirror_path(bad) == ""
    assert overlays_mod.case_exact_join(str(ROOT), bad) == ""
```

- [ ] **Step 2: Run it and watch it fail**

```bash
python -m pytest plugins/virtuoso/scripts/test_overlays.py::test_a_rooted_or_drive_qualified_key_is_refused_everywhere -q
```

Expected on a 3.13+ machine: 2 of 4 parameters FAIL with `assert 'skills/epic/SKILL.md' == ''`. On 3.12 all four pass already — that is the point of the task, so read the next step regardless.

- [ ] **Step 3: Add the explicit root test**

In `plugins/virtuoso/tools/governance/overlays.py`, insert immediately above `case_exact_join`:

```python
def _rooted(candidate: str) -> bool:
    """Whether ``candidate`` is anchored to a filesystem root or a drive.

    Tested explicitly rather than with :func:`os.path.isabs`, which answers
    differently per platform *and* per interpreter: Python 3.13 stopped treating
    a lone leading slash as absolute on Windows. A mirror key is a relative
    address by definition, so anything anchored is refused identically
    everywhere. The ``candidate[1] == ":"`` form matches ``safepath``'s own
    drive-letter idiom.
    """
    if not candidate:
        return False
    if candidate[0] in "/\\":
        return True
    return len(candidate) > 1 and candidate[1] == ":"
```

- [ ] **Step 4: Use it in both resolvers**

Replace the opening guard of `case_exact_join`:

```python
    if not isinstance(relative, str) or not relative.strip():
        return ""
    candidate = relative.strip()
    if _rooted(candidate):
        return ""
    normalized = candidate.replace("\\", "/").strip("/")
    if not normalized:
        return ""
```

Replace the body of `mirror_path` entirely:

```python
def mirror_path(relative: str) -> str:
    """Normalize a shipped file's path to the posix form overlays are keyed by.

    Returns ``""`` when the path is unusable as a mirror key: rooted at a
    filesystem root or a drive, empty, or containing a traversal segment.
    """
    if not isinstance(relative, str):
        return ""
    candidate = relative.strip()
    if not candidate or _rooted(candidate):
        return ""
    segments = [s for s in candidate.replace("\\", "/").split("/") if s]
    if not segments or any(s in (".", "..") for s in segments):
        return ""
    return "/".join(segments)
```

- [ ] **Step 5: Run the overlay suite**

```bash
python -m pytest plugins/virtuoso/scripts/test_overlays.py -q 2>&1 | tail -10
```

Expected: the new test passes and `test_mirror_path_rejects_unusable_keys` passes for every parameter including `/skills/epic/SKILL.md`. The five case-collision failures from the fixture remain — Task 2 owns those.

- [ ] **Step 6: Commit**

```bash
git add plugins/virtuoso/tools/governance/overlays.py plugins/virtuoso/scripts/test_overlays.py
git commit -m "fix(overlays): a rooted mirror key is refused on every interpreter

mirror_path gated on os.path.isabs, which returns False for '/skills/...' on
Windows under Python 3.13+ and True under 3.12. The same registry therefore
resolved differently per interpreter, on the one code path whose whole purpose
is platform-identical resolution. CI runs 3.12 and could not see it.

_rooted tests for a leading separator or a drive letter directly, matching
safepath's existing idiom.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Overlay fixtures that work on a case-insensitive filesystem

**Files:**
- Modify: `plugins/virtuoso/scripts/test_overlays.py` (imports, `with_overlays` fixture, four assertions)

**Interfaces:**
- Consumes: nothing.
- Produces: `test_overlays.CASE_SENSITIVE_FS: bool`, a module-level constant other tests in this file branch on.

The `with_overlays` fixture writes `skills/epic/SKILL.md` and then `skills/EPIC/SKILL.md`. On NTFS and a default macOS volume those are one file, so the second write clobbers the first and the fixture silently produces four overlays instead of five with the wrong content in one of them. Five tests inherit the damage. This is the whole of the Windows CI failure except the mount-drive test in Task 3.

- [ ] **Step 1: Write the probe and make the fixture conditional**

In `plugins/virtuoso/scripts/test_overlays.py`, add `import tempfile` to the imports, then add below `HAVE_GIT = shutil.which("git") is not None`:

```python
def _probe_case_sensitivity() -> bool:
    """Whether the temp filesystem distinguishes ``probe`` from ``PROBE``.

    Measured, never inferred from ``sys.platform``: a case-sensitive volume can
    be mounted on Windows or macOS and a case-insensitive one on Linux, and the
    fixtures below create two files whose names differ only in case. pytest's
    tmp_path lives under the same temp root this probes.
    """
    base = tempfile.mkdtemp()
    try:
        with open(os.path.join(base, "probe"), "w", encoding="utf-8") as handle:
            handle.write("lower")
        return not os.path.exists(os.path.join(base, "PROBE"))
    finally:
        shutil.rmtree(base, ignore_errors=True)


#: True where two names differing only in case are two files.
CASE_SENSITIVE_FS = _probe_case_sensitivity()

#: Overlay files `with_overlays` lays down, and findings the audit then reports.
#: Both are two fewer where the case-only pair collapses into one file.
EXPECTED_OVERLAYS = 5 if CASE_SENSITIVE_FS else 4
EXPECTED_FINDINGS = 3 if CASE_SENSITIVE_FS else 2
```

- [ ] **Step 2: Replace the fixture**

```python
@pytest.fixture
def with_overlays(registered):
    """Overlays covering every classification the audit makes.

    One applies, one mirrors nothing, one is outside the mirrorable subtrees, and
    one agent overlay applies. The case-only duplicate is laid down ONLY on a
    case-sensitive filesystem: elsewhere it is the same file as its lowercase
    twin, so writing it would overwrite that file's content and quietly change
    what every test built on this fixture is asserting about.
    """
    base = registered / "Virtuoso" / "overlays"
    files = [
        ("skills/epic/SKILL.md", "always name the ticket\n"),
        ("skills/no-such-skill/SKILL.md", "mirrors nothing\n"),
        ("notes/scratch.md", "not addressable\n"),
    ]
    if CASE_SENSITIVE_FS:
        files.append(("skills/EPIC/SKILL.md", "wrong case\n"))
    for relative, body in files:
        target = base.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    (base / "agents").mkdir(parents=True, exist_ok=True)
    (base / "agents" / AGENT_FILES[0]).write_text("agent addition\n", encoding="utf-8")
    return registered
```

- [ ] **Step 3: Make the four count-dependent assertions honest**

In `test_audit_flags_a_case_only_mismatch_and_names_the_right_spelling`, add the marker directly above the `def` line and leave the body unchanged:

```python
@pytest.mark.skipif(not CASE_SENSITIVE_FS,
                    reason="two names differing only in case are one file here, so the "
                           "condition under test cannot be created")
def test_audit_flags_a_case_only_mismatch_and_names_the_right_spelling(with_overlays):
```

In `test_the_status_line_counts_applied_overlays_and_findings`, replace the second assertion:

```python
    assert "%d finding(s)" % EXPECTED_FINDINGS in line
```

In `test_the_json_result_carries_the_overlay_detail`, replace the length assertion:

```python
    assert len(payload["overlays"]["overlays"]) == EXPECTED_OVERLAYS
```

`test_find_resolves_a_skill_overlay` and `test_the_overlays_verb_resolves_one_file_to_a_path` need no edit: with the clobbering write gone, `skills/epic/SKILL.md` keeps its own content.

- [ ] **Step 4: Add a test that the lost coverage is covered elsewhere**

Add immediately after the skipped case-mismatch test:

```python
def test_case_exactness_itself_is_covered_on_every_filesystem(with_overlays):
    """The audit's case-mismatch FINDING needs a case-sensitive volume to exist.
    The module's case-exactness does not, and is what actually protects a project.

    Skipping the finding test where the condition cannot be built is honest.
    Skipping it and testing nothing in its place would mean the property silently
    lost its coverage on the maintainer's own platform.
    """
    reg = registry_mod.load(str(with_overlays))
    exact = overlays_mod.find(reg, PLUGIN_ROOT, "skills/epic/SKILL.md")
    assert exact is not None and exact.mirrors_shipped_file

    # A wrongly-cased request never stands in for the shipped file. On a
    # case-sensitive volume the uppercase directory exists as its own overlay, so
    # find() may return it — but it must never claim to mirror a shipped file,
    # because the plugin ships no `skills/EPIC/`.
    assert overlays_mod.find(reg, PLUGIN_ROOT, "skills/epic/skill.md") is None
    wrong_case = overlays_mod.find(reg, PLUGIN_ROOT, "skills/EPIC/SKILL.md")
    assert wrong_case is None or not wrong_case.mirrors_shipped_file
```

- [ ] **Step 5: Run the full suite**

```bash
python -m pytest plugins/virtuoso -q 2>&1 | tail -10
```

Expected on Windows: `0 failed`, one skip added (`494 passed, 5 skipped` or similar — the exact pass count rises by the new tests from Tasks 1 and 2). No failures. If any remain, they are not case-related; diagnose before continuing.

- [ ] **Step 6: Commit**

```bash
git add plugins/virtuoso/scripts/test_overlays.py
git commit -m "test(overlays): fixtures that survive a case-insensitive filesystem

with_overlays wrote skills/epic/SKILL.md and skills/EPIC/SKILL.md, which are one
file on NTFS and on a default macOS volume. The second write clobbered the
first, so five tests asserted against content and counts the fixture had not
actually produced. Every push of this branch was red on windows-latest for this
reason and the failure was never read.

The case-only pair is now laid down only where it can exist, the counts derive
from that, and the audit finding it produces is skipped with a stated reason
rather than failing. The module's case-exactness -- the property that actually
protects a project -- is asserted on every filesystem instead.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `safepath.normalize` survives a path on another Windows drive

**Files:**
- Modify: `plugins/virtuoso/tools/governance/safepath.py` (`normalize`)
- Test: `plugins/virtuoso/scripts/test_registry_preservation.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `safepath.normalize(root, raw) -> tuple[str, str]` no longer raises `ValueError` when `raw` and `root` are on different Windows drives.

`normalize` calls `os.path.relpath(absolute, root_abs)`, which raises `ValueError: path is on mount 'D:', start on mount 'C:'` on Windows. `is_inside` already guards this; `normalize` does not. On a GitHub Windows runner the checkout is on `C:` and the temp directory is on `D:`, so a test project root and `/etc/passwd` land on different mounts. This has made `windows-latest` red since v1.6.0, which is why it absorbed Task 2's five failures unnoticed.

- [ ] **Step 1: Write the failing tests**

Add to `plugins/virtuoso/scripts/test_registry_preservation.py`, immediately after `test_unsafe_registered_paths_are_rejected`. Add `from tools.governance import safepath` to that file's imports if it is not already there.

```python
@pytest.mark.skipif(os.name != "nt", reason="drive letters are a Windows concept")
def test_normalize_survives_a_path_on_another_drive():
    """os.path.relpath raises across Windows drives; normalize must not.

    Pure string work -- D: need not exist. On a GitHub Windows runner the
    checkout is on C: and the temp directory is on D:, so a project root under
    tmp_path and an absolute path resolving against the checkout's drive are on
    different mounts. That is why windows-latest has been red since v1.6.0.
    """
    rel, absolute = safepath.normalize("C:\\project", "D:\\elsewhere\\file.md")
    assert absolute.upper().startswith("D:")
    assert rel                                   # an answer, not an exception
    assert safepath.is_inside("C:\\project", absolute) is False


def test_normalize_reports_rather_than_raises_when_there_is_no_relative_form(monkeypatch):
    """The same guard, exercised on the Linux leg too.

    Patched rather than skipped, because the guard is the thing under test and a
    guard only one CI leg ever executes is a guard half-tested.
    """
    def no_relative_form(path, start=None):
        raise ValueError("path is on mount 'D:', start on mount 'C:'")

    monkeypatch.setattr(safepath.os.path, "relpath", no_relative_form)
    rel, absolute = safepath.normalize("/project", "/elsewhere/file.md")
    assert rel and absolute
```

- [ ] **Step 2: Run them and watch the second fail**

```bash
python -m pytest plugins/virtuoso/scripts/test_registry_preservation.py -q -k normalize 2>&1 | tail -12
```

Expected: `test_normalize_reports_rather_than_raises_when_there_is_no_relative_form` FAILS with `ValueError: path is on mount 'D:', start on mount 'C:'`. The first test passes on this machine only because its temp directory happens to share a drive with the checkout — it is the CI condition it reproduces.

- [ ] **Step 3: Guard the relpath call**

In `plugins/virtuoso/tools/governance/safepath.py`, replace the last two lines of `normalize`:

```python
    try:
        rel = os.path.relpath(absolute, root_abs)
    except ValueError:
        # Different Windows drives: there is no relative form, and a path with no
        # relative form to the root is definitionally outside it. Answer with the
        # absolute path as its own normalized form and let the caller's
        # is_inside() check -- which already guards this -- do the rejecting. The
        # alternative, raising, turns "report this path as unsafe" into a crash.
        return _to_posix(absolute), absolute
    return _to_posix(rel), absolute
```

- [ ] **Step 4: Run the path-validation tests**

```bash
python -m pytest plugins/virtuoso/scripts/test_registry_preservation.py -q 2>&1 | tail -6
```

Expected: all pass, including all three parameters of `test_unsafe_registered_paths_are_rejected`.

- [ ] **Step 5: Run the full suite**

```bash
python -m pytest plugins/virtuoso -q 2>&1 | tail -6
python plugins/virtuoso/scripts/validate.py 2>&1 | tail -3
```

Expected: no failures; `All checks passed.`

- [ ] **Step 6: Commit and push for the CI gate**

```bash
git add plugins/virtuoso/tools/governance/safepath.py plugins/virtuoso/scripts/test_registry_preservation.py
git commit -m "fix(safepath): a path on another Windows drive is reported, not raised

normalize called os.path.relpath without the ValueError guard is_inside already
has. Across Windows drives relpath raises, so validating a registered path
crashed instead of reporting it unsafe. On a GitHub Windows runner the checkout
is on C: and the temp directory on D:, which is why windows-latest has been red
since v1.6.0 -- and why it absorbed five more failures this release without
anyone noticing.

A path with no relative form to the root is outside it; normalize now says so
and lets is_inside reject it.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push -u origin eb/zealous-einstein-zxvy3w
```

- [ ] **Step 7: GATE — both CI legs green**

```bash
gh run list --repo gorillabrown/virtuoso --branch eb/zealous-einstein-zxvy3w --limit 1
```

Wait for completion, then:

```bash
gh run view --repo gorillabrown/virtuoso $(gh run list --repo gorillabrown/virtuoso --branch eb/zealous-einstein-zxvy3w --limit 1 --json databaseId -q '.[0].databaseId')
```

Expected: `✓ validate (windows-latest)` and `✓ validate (ubuntu-latest)`.

**Do not proceed past this gate on a red leg.** Every task after this one is measured by CI, and a red leg measures nothing. If windows-latest is still red, read `gh run view <id> --log-failed`, fix the named test, and re-push.

---

### Task 4: Scaffold output and overlay reading survive a Windows shell redirect

**Files:**
- Modify: `plugins/virtuoso/tools/governance/textio.py` (`read_text`)
- Modify: `plugins/virtuoso/scripts/virtuoso_registry.py` (`cmd_overlays`)
- Modify: `plugins/virtuoso/tools/governance/overlays.py` (`_audit_overlay_files`, `_pairing_findings`)
- Modify: `plugins/virtuoso/references/registry-contract.md` (finding table)
- Test: `plugins/virtuoso/scripts/test_overlays.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-3.
- Produces: `textio.read_text(path)` decodes a BOM-prefixed file instead of returning `None`. A new finding code `overlay-unreadable` (severity `warning`). `cmd_overlays` writes scaffold content as UTF-8 bytes regardless of console encoding.

The documented loop ends with `overlays --scaffold --for <path> > <path>`. Measured on Windows: under pwsh 7 the child Python's stdout is cp1252, the scaffold's em-dashes become bytes that are not valid UTF-8, `read_text` returns `None`, and the audit reports `pairing-body-missing` — "nothing defines this" — for a file containing exactly the right heading. Under Windows PowerShell 5.1 the redirect writes UTF-16 LE with a BOM, same outcome.

**Both halves are required.** A UTF-8 emit does not help 5.1, which re-encodes whatever it receives. A tolerant reader does not help pwsh, whose cp1252 bytes carry no BOM and are not valid UTF-8. Verified: with the emit fix alone the pwsh path produces the correct `pairing-body-stub`; with the reader fix alone the 5.1 path does.

- [ ] **Step 1: Write the failing tests**

Add to `plugins/virtuoso/scripts/test_overlays.py`, in the pairings section after `test_a_malformed_policy_value_is_ignored_not_raised`. Add `import codecs` to the imports.

```python
def test_a_utf16_overlay_is_read_rather_than_called_missing(registered):
    """Windows PowerShell 5.1's `>` writes UTF-16 with a BOM.

    That is the documented way to save a scaffold, so a reader that rejects a BOM
    turns the documented workflow into a file the plugin calls absent -- and the
    operator, who wrote a correct heading, is told nothing defines it.
    """
    _declare(registered, ["db-migration"])
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True)
    (base / "readiness-rubric.md").write_bytes(
        "## db-migration\n\nboth directions named\n".encode("utf-16"))
    codes = _codes(registered)
    assert "pairing-body-missing" not in codes
    assert "overlay-unreadable" not in codes


def test_a_utf8_bom_overlay_is_read(registered):
    _declare(registered, ["db-migration"])
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True)
    (base / "readiness-rubric.md").write_bytes(
        codecs.BOM_UTF8 + "## db-migration\n\nboth directions named\n".encode("utf-8"))
    assert "pairing-body-missing" not in _codes(registered)


def test_an_undecodable_overlay_says_so_instead_of_saying_missing(registered):
    """pwsh 7 redirects a legacy code page when the console is not UTF-8.

    Those bytes carry no BOM and are not valid UTF-8, so nothing can read them.
    The operator must be told the file is unreadable -- "nothing defines this id"
    sends them to rewrite a section that is already there.
    """
    _declare(registered, ["db-migration"])
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True)
    (base / "readiness-rubric.md").write_bytes(
        "## db-migration \u2014 both directions\n".encode("cp1252"))
    codes = _codes(registered)
    assert "overlay-unreadable" in codes
    assert "pairing-body-missing" not in codes


def test_the_scaffold_redirect_round_trips_through_a_byte_stream(registered):
    """`--scaffold --for X > X` must produce a file this plugin can read back.

    The redirect is the whole write, so stdout here is a file the audit will
    later parse. Capturing bytes rather than text is the point: a console
    encoding must not be able to change what lands on disk.
    """
    _declare(registered, ["db-migration"])
    completed = subprocess.run(
        [sys.executable, REGISTRY_CLI, "--root", str(registered), "overlays",
         "--scaffold", "--for", "references/readiness-rubric.md"],
        capture_output=True, env=dict(os.environ))
    assert completed.returncode == 0, completed.stderr
    target = registered / "Virtuoso" / "overlays" / "references" / "readiness-rubric.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(completed.stdout)
    assert "pairing-body-stub" in _codes(registered)
```

- [ ] **Step 2: Run them and watch them fail**

```bash
python -m pytest plugins/virtuoso/scripts/test_overlays.py -q -k "utf16 or bom or undecodable or byte_stream" 2>&1 | tail -20
```

Expected: all four FAIL. The first three because `read_text` returns `None`; the fourth because `overlay-unreadable` does not exist yet and, on a non-UTF-8 console, because the em-dashes are mangled.

- [ ] **Step 3: Make `read_text` honour a byte-order mark**

In `plugins/virtuoso/tools/governance/textio.py`, add `import codecs` to the imports and replace `read_text` entirely:

```python
#: BOMs, longest first. UTF-32 LE begins with the UTF-16 LE BOM, so testing
#: UTF-16 first would decode a UTF-32 file as UTF-16 and produce mojibake.
_BOMS = (
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)


def read_text(path: str) -> str | None:
    """The file's text, or ``None`` when its bytes are not decodable as text.

    A byte-order mark is honoured rather than rejected. Governance documents are
    written by people and by their shells: Windows PowerShell's ``>`` writes
    UTF-16 with a BOM, and several editors add a UTF-8 one. Refusing those made
    the plugin report a file it could plainly see as absent, which is a worse
    answer than reading it.

    ``None`` still means "these bytes are not text I can read", and callers
    report that; it no longer also means "these bytes are text with a BOM".
    """
    raw = read_bytes(path)
    if raw is None:
        return None
    for bom, encoding in _BOMS:
        if raw.startswith(bom):
            try:
                return raw.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
```

- [ ] **Step 4: Report an unreadable overlay as such**

In `plugins/virtuoso/tools/governance/overlays.py`, inside `_audit_overlay_files`, add this immediately after the `overlay-case-mismatch` / `overlay-orphan` `if/elif` block, at the same indentation as that `if`:

```python
        if applies and textio.read_text(resolved) is None:
            status.findings.append(Finding(
                "overlay-unreadable", "warning",
                "overlay %s exists but its bytes are not decodable as text, so nothing in "
                "it can be applied or define anything. A shell redirect on Windows can "
                "write a legacy code page; re-save the file as UTF-8." % mirror,
                role=OVERLAY_ROLE))
```

Then in `_pairing_findings`, replace the two lines that read the overlay text:

```python
        overlay = next((o for o in status.overlays
                        if o.mirror == pairing.mirror and o.present), None)
        text = textio.read_text(overlay.path) if overlay else None
        if overlay is not None and text is None:
            # The audit already reported this file as unreadable. Reporting each
            # id as undefined on top of that would send the operator to write
            # sections that are already there.
            continue
```

- [ ] **Step 5: Emit scaffolds as UTF-8 bytes**

In `plugins/virtuoso/scripts/virtuoso_registry.py`, add above `cmd_overlays`:

```python
def _write_bytes_to_stdout(content: str) -> None:
    """Write ``content`` to stdout as UTF-8, whatever the console's encoding is.

    The documented workflow is ``... --scaffold --for <path> > <path>``, so this
    stdout is a file the plugin will later read back. A Windows console defaults
    to a legacy code page, and the text layer would then encode the scaffold's
    own punctuation into bytes no reader can decode -- the operator saves a
    correct overlay and is told the section does not exist.
    """
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:              # a replaced stdout (capture); text is all there is
        sys.stdout.write(content)
        return
    sys.stdout.flush()
    buffer.write(content.encode("utf-8"))
    buffer.flush()
```

In `cmd_overlays`, replace both `sys.stdout.write(content)` calls with `_write_bytes_to_stdout(content)`.

- [ ] **Step 6: Run the new tests, then the whole suite**

```bash
python -m pytest plugins/virtuoso/scripts/test_overlays.py -q -k "utf16 or bom or undecodable or byte_stream" 2>&1 | tail -6
python -m pytest plugins/virtuoso -q 2>&1 | tail -6
python plugins/virtuoso/scripts/validate.py 2>&1 | tail -3
```

Expected: the four new tests pass; no failures anywhere; `All checks passed.`

`write_if_changed` calls `read_text`, so a BOM-prefixed governance file now compares by its real content instead of looking unreadable and being overwritten. That is the intended direction. If any preservation test fails here, read it carefully before changing it — it is telling you something real.

- [ ] **Step 7: Verify the real redirect under both Windows shells**

```bash
python -m pytest plugins/virtuoso/scripts/test_overlays.py -q -k byte_stream
pwsh -NoProfile -Command "python plugins/virtuoso/scripts/virtuoso_registry.py --root . overlays --scaffold --for references/readiness-rubric.md > \$env:TEMP\scaffold-pwsh.md"
python -c "print(open(__import__('os').environ['TEMP']+r'\scaffold-pwsh.md','rb').read().decode('utf-8')[:60])"
```

Expected: the last command prints the scaffold's opening comment without raising `UnicodeDecodeError`.

- [ ] **Step 8: Document the finding**

In `plugins/virtuoso/references/registry-contract.md`, add a row to the overlay finding table, directly below the `overlay-not-overlayable` row:

```markdown
| `overlay-unreadable` | the file's bytes are not decodable as text; re-save it as UTF-8 |
```

- [ ] **Step 9: Commit**

```bash
git add plugins/virtuoso/tools/governance/textio.py plugins/virtuoso/tools/governance/overlays.py plugins/virtuoso/scripts/virtuoso_registry.py plugins/virtuoso/references/registry-contract.md plugins/virtuoso/scripts/test_overlays.py
git commit -m "fix(overlays): the documented redirect produces a readable overlay on Windows

'--scaffold --for X > X' is the documented write, and on Windows it produced a
file the plugin then reported as missing. Under pwsh the child's stdout is a
legacy code page, so the scaffold's own punctuation became bytes no reader can
decode. Under Windows PowerShell 5.1 the redirect writes UTF-16 with a BOM.
Either way read_text returned None and the audit said 'nothing defines this id'
about a file carrying exactly the right heading.

Both halves are needed and neither is sufficient: scaffolds are now written as
UTF-8 bytes straight to the stdout buffer, and read_text honours a BOM. Bytes
that are genuinely undecodable are reported as overlay-unreadable instead of
being laundered into a pairing-body-missing that sends the operator to rewrite
prose that is already there.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: The overlay status line reports findings in every state

**Files:**
- Modify: `plugins/virtuoso/tools/governance/registry.py` (`Finding`)
- Modify: `plugins/virtuoso/tools/governance/overlays.py` (`OverlayStatus.state`, the two pairing findings)
- Test: `plugins/virtuoso/scripts/test_overlays.py`

**Interfaces:**
- Consumes: `overlay-unreadable` from Task 4 (its `continue` must not suppress the count).
- Produces: `Finding(code, severity, message, role="", identifier="")` — one new optional field, emitted by `as_dict` only when set. `OverlayStatus.state` appends a finding suffix in every state, and names undefined identifiers.

The loop's second step is "session start says the id has nowhere to live". Measured: unregistered prints `overlays: not registered` and nothing else; registered-with-no-directory prints `registered but absent (<path>)` and nothing else, because `state` returns before it counts findings. Only once the directory exists does a bare `; 1 finding(s)` appear. Those first two are the states a new project is actually in.

- [ ] **Step 1: Write the failing tests**

Add to `plugins/virtuoso/scripts/test_overlays.py`, in the status-line section after `test_the_status_line_distinguishes_absent_from_empty`:

```python
def test_an_undefined_id_is_named_when_no_overlays_role_exists(project):
    """The state a project is in the moment it declares its first extension.

    Printing only "not registered" here is the loop's second step saying nothing
    at the exact point the operator needs to be told what to do.
    """
    run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    _declare(project, ["deployment"])
    line = overlays_mod.audit(registry_mod.load(str(project)), PLUGIN_ROOT).line()
    assert "not registered" in line
    assert "deployment" in line


def test_an_undefined_id_is_named_when_the_directory_is_absent(registered):
    _declare(registered, ["deployment"])
    line = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT).line()
    assert "registered but absent" in line
    assert "deployment" in line


def test_every_undefined_id_is_named(registered):
    _declare(registered, ["deployment", "db-migration"])
    line = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT).line()
    assert "db-migration" in line and "deployment" in line


def test_a_clean_project_says_nothing_extra(registered):
    """The suffix must be absent, not empty-but-present: a line that always ends
    in punctuation trains the reader to stop looking at the end of it."""
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered, "## db-migration\n\nboth directions named\n")
    line = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT).line()
    assert "undefined" not in line and "finding(s)" not in line


def test_the_session_start_line_names_the_undefined_id(registered):
    _declare(registered, ["deployment"])
    completed = run(PREFLIGHT, "--root", str(registered), "--mode", "check", "--quiet")
    assert "virtuoso-status: ready" in completed.stdout
    assert "deployment" in completed.stdout
```

- [ ] **Step 2: Run them and watch four fail**

```bash
python -m pytest plugins/virtuoso/scripts/test_overlays.py -q -k "undefined or says_nothing_extra or session_start_line_names" 2>&1 | tail -16
```

Expected: the four that assert an id appears FAIL; `test_a_clean_project_says_nothing_extra` passes already.

- [ ] **Step 3: Give `Finding` an identifier**

In `plugins/virtuoso/tools/governance/registry.py`, add the field to `Finding` and emit it conditionally:

```python
class Finding:
    code: str
    severity: str          # "error" | "warning" | "info"
    message: str
    role: str = ""
    #: The project identifier this finding is about, when it is about one. Carried
    #: as data so a caller can name it without parsing the message back out.
    identifier: str = ""

    def as_dict(self) -> dict:
        data = {"code": self.code, "severity": self.severity, "message": self.message}
        if self.role:
            data["role"] = self.role
        if self.identifier:
            data["identifier"] = self.identifier
        return data
```

- [ ] **Step 4: Populate it on every pairing finding**

In `plugins/virtuoso/tools/governance/overlays.py`, add `identifier=identifier` to the `Finding(...)` constructions for `pairing-body-missing` and `pairing-body-stub`. For `pairing-mirror-unregistered`, which covers a whole list at once, pass the joined ids:

```python
                   OVERLAY_ROLE, pairing.mirror), role=OVERLAY_ROLE,
                identifier=", ".join(ids)))
```

- [ ] **Step 5: Append the suffix in every state**

Replace `OverlayStatus.state` and add the helper below it:

```python
    @property
    def state(self) -> str:
        """The result, without the label. Always states something: an unregistered
        project reports ``not registered`` rather than nothing, because no output is
        indistinguishable from an all-clear.

        The finding suffix is appended in EVERY state. It used to be computed only
        after the early returns, so the two states a project is actually in when it
        first declares an extension -- no role, and a role with no directory --
        reported a clean line while the audit was holding a finding about them.
        """
        suffix = self._finding_suffix()
        if not self.registered:
            return "not registered%s" % suffix
        if self.external:
            return "registered externally (%s); not readable as files%s" % (self.external, suffix)
        if not self.root_present:
            return "registered but absent (%s)%s" % (self.root, suffix)
        count = len(self.applied)
        if not count:
            return "registered, none present (%s)%s" % (self.root, suffix)
        return "%d applied (%s)%s" % (count, self.root, suffix)

    def _finding_suffix(self) -> str:
        """The finding count, and the undefined identifiers by name.

        Named, not merely counted: the operator's next action is to define one, and
        "1 finding(s)" tells them something is wrong where "undefined: deployment"
        tells them what to write. Absent entirely when there is nothing to say, so
        the end of the line stays worth reading.
        """
        undefined = []
        for finding in self.findings:
            if not finding.code.startswith("pairing-") or not finding.identifier:
                continue
            for name in finding.identifier.split(","):
                name = name.strip()
                if name and name not in undefined:
                    undefined.append(name)
        problems = sum(1 for f in self.findings if f.severity in ("error", "warning"))
        parts = []
        if problems:
            parts.append("%d finding(s)" % problems)
        if undefined:
            parts.append("undefined: %s" % ", ".join(sorted(undefined)))
        return ("; " + "; ".join(parts)) if parts else ""
```

- [ ] **Step 6: Run the suite**

```bash
python -m pytest plugins/virtuoso -q 2>&1 | tail -8
```

Expected: no failures. `test_the_status_line_counts_applied_overlays_and_findings` still passes — the fixture declares no extensions, so `undefined` is empty and the line is unchanged. If `test_a_missing_body_shows_in_the_session_start_line` now reads oddly, leave it: it asserts `"finding(s)" in stdout`, which is still true.

- [ ] **Step 7: Commit**

```bash
git add plugins/virtuoso/tools/governance/registry.py plugins/virtuoso/tools/governance/overlays.py plugins/virtuoso/scripts/test_overlays.py
git commit -m "fix(overlays): the status line reports findings in every state, by name

The loop's second step is session start telling a project that a declared id has
nowhere to live. It did not: the finding suffix was computed after the early
returns, so 'not registered' and 'registered but absent' -- the two states a
project is in the moment it declares its first extension -- printed a clean line
while the audit held a finding about exactly that.

The suffix now applies in every state and names the undefined identifiers rather
than counting them, because the operator's next action is to define one.
Finding carries the identifier as data so nothing has to parse it back out of a
message.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Body detection — empty sections, fenced examples, case, and newlines

**Files:**
- Modify: `plugins/virtuoso/tools/governance/overlays.py` (`body_heading`, `_body_section`, `_pairing_findings`)
- Modify: `plugins/virtuoso/references/readiness-rubric.md`
- Modify: `plugins/virtuoso/references/registry-contract.md`
- Test: `plugins/virtuoso/scripts/test_overlays.py`

**Interfaces:**
- Consumes: `Finding.identifier` from Task 5.
- Produces: `overlays.without_fenced_blocks(text: str) -> str`, length-preserving. `body_heading(identifier)` matches case-insensitively and does not span a newline. `pairing-body-stub` now also covers an empty section.

Four measured defects, all in the same few lines:

1. `\s+` in the heading pattern spans newlines, so a bare `##` line followed by a line beginning with the id counts as a heading.
2. A heading inside a fenced code block counts. The shipped rubric's own example shows `## db-migration` inside a ` ```markdown ` fence, so a project that copies it gets a false pass.
3. Matching is case-sensitive and nothing says so. `## Deployment — environment and rollback` is the natural way to write that section and is reported undefined.
4. Deleting the placeholder line leaves an empty section, which passes green. The stub sentinel closed one route to "green with nothing written" and left the more natural one open: the remedy for the stub warning is to delete the placeholder.

- [ ] **Step 1: Write the failing tests**

Replace the existing `test_what_counts_as_a_body` parametrize list with this one, and add the four tests below it:

```python
@pytest.mark.parametrize("heading,defines", [
    ("## db-migration — forward and backward", True),
    ("### db-migration", True),
    ("#### db-migration (both directions)", True),
    ("##\tdb-migration", True),                     # a tab is a valid heading separator
    ("## DB-Migration — capitalized by a human", True),
    ("## Why we dropped db-migration", False),      # discusses it; does not define it
    ("## db-migration-rollback — a different id", False),
    ("## db-migrations", False),
    ("# db-migration", False),                      # depth 1 is the document title
    ("db-migration", False),                        # not a heading at all
    ("##\ndb-migration", False),                    # a bare ## and then a paragraph
])
def test_what_counts_as_a_body(heading, defines):
    assert bool(overlays_mod.body_heading("db-migration").search(heading)) is defines


def test_a_heading_inside_a_code_fence_is_an_example_not_a_definition(registered):
    """This plugin's own rubric shows `## db-migration` inside a fence.

    A project that copies that example into its overlay is showing what a section
    looks like, not writing one, and must not thereby satisfy the check.
    """
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered,
                    "# additions\n\n```markdown\n## db-migration\nexample\n```\n")
    assert "pairing-body-missing" in _codes(registered)


def test_a_real_section_after_a_fenced_example_still_counts(registered):
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered,
                    "# additions\n\n```markdown\n## db-migration\nexample\n```\n\n"
                    "## db-migration\n\nboth directions named\n")
    assert not [c for c in _codes(registered) if c.startswith("pairing-")]


def test_a_heading_with_nothing_under_it_is_a_stub(registered):
    """Deleting the placeholder is the obvious way to 'fix' the stub warning.

    If an empty section passed, the gate's own remedy would satisfy it by a second
    route -- the same failure pairing-body-stub was added to close.
    """
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered, "## db-migration\n\n\n## something else\n\nprose\n")
    codes = _codes(registered)
    assert "pairing-body-stub" in codes
    assert "pairing-body-missing" not in codes


def test_a_capitalized_heading_defines_the_declared_id(registered):
    """An id is an identifier; a heading is prose a person writes.

    Requiring the prose to match the identifier's case reports the natural way to
    write the section as undefined, which is a false report about correct work.
    """
    _declare(registered, ["deployment"])
    _rubric_overlay(registered, "## Deployment — environment and rollback\n\nrehearsed\n")
    assert not [c for c in _codes(registered) if c.startswith("pairing-")]
```

- [ ] **Step 2: Run them and watch them fail**

```bash
python -m pytest plugins/virtuoso/scripts/test_overlays.py -q -k "what_counts or code_fence or fenced_example or nothing_under_it or capitalized" 2>&1 | tail -20
```

Expected: FAILures for the `DB-Migration` and `##\ndb-migration` parameters, plus all four new tests except `test_a_real_section_after_a_fenced_example_still_counts`.

- [ ] **Step 3: Tighten the heading pattern**

In `plugins/virtuoso/tools/governance/overlays.py`, replace `body_heading`:

```python
def body_heading(identifier: str) -> re.Pattern:
    """The heading that counts as ``identifier``'s body: a depth 2-4 heading whose
    text *starts with* the id, on one line, in any case.

    Anchored at the start on purpose. Matching the id anywhere in the heading would
    let ``## Why we dropped db-migration`` satisfy ``db-migration`` — a heading that
    says the opposite of a body. The trailing guard rejects a longer id standing in
    for a shorter one, so ``## db-migration-rollback`` is not ``db-migration``.

    ``[ \\t]`` rather than ``\\s``: ``\\s`` matches a newline, so a bare ``##`` line
    followed by a paragraph beginning with the id read as a heading.

    Case-insensitive because an id is an identifier and a heading is prose. A
    person writing the section calls it ``## Deployment``; reporting that as
    undefined is a false report about correct work, and two ids differing only in
    case would be a collision inside one project's own list.
    """
    return re.compile(r"(?m)^#{2,4}[ \t]+%s(?![\w-])" % re.escape(identifier),
                      re.IGNORECASE)
```

- [ ] **Step 4: Blank fenced blocks before matching**

Add above `_body_section`:

```python
#: A fenced code block, closed by a fence of the same character. Matched lazily so
#: two separate blocks are two matches rather than one spanning the prose between.
_FENCE_RE = re.compile(r"(?ms)^(?P<fence>```+|~~~+).*?^(?P=fence)[ \t]*$")


def without_fenced_blocks(text: str) -> str:
    """``text`` with fenced code blocks blanked out, every offset preserved.

    A heading inside a fence is an *example* of a heading. This plugin's own
    readiness rubric shows ``## db-migration`` inside one, so a project that copies
    that example is showing what a section looks like rather than writing one.

    Non-newline characters become spaces rather than being deleted, so the result
    is the same length as the input and an offset found here indexes the original
    text unchanged. That is what lets the caller detect on this string and slice
    the real prose out of the original.
    """
    return _FENCE_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
```

Replace `_body_section`:

```python
def _body_section(text: str, pattern: re.Pattern) -> str | None:
    """The prose under the matched heading, up to the next heading of any depth.
    ``None`` when the heading is absent.

    Headings are located in the fence-blanked copy and the body is sliced out of
    the original, so a fenced example never defines anything and a real section's
    own fenced content is still returned intact.
    """
    scan = without_fenced_blocks(text)
    match = pattern.search(scan)
    if not match:
        return None
    following = re.search(r"(?m)^#{1,6}[ \t]", scan[match.end():])
    end = match.end() + following.start() if following else len(text)
    return text[match.end():end]
```

- [ ] **Step 5: Treat an empty section as a stub**

In `_pairing_findings`, replace the `elif SCAFFOLD_PLACEHOLDER in section:` branch:

```python
            elif not section.strip() or SCAFFOLD_PLACEHOLDER in section:
                reason = ("has nothing under it" if not section.strip()
                          else "is still the scaffold's placeholder")
                found.append(Finding(
                    "pairing-body-stub", "warning",
                    "policy.%s declares the %s %r and %s has a section for it that %s. "
                    "Write what must actually be true; a heading shaped like a definition "
                    "is not one."
                    % (pairing.policy_key, pairing.label, identifier, pairing.mirror,
                       reason),
                    role=OVERLAY_ROLE, identifier=identifier))
```

Update the `SCAFFOLD_PLACEHOLDER` docstring's final sentence to cover both routes:

```python
#: satisfies is not a gate. An empty section is reported for the same reason: the
#: obvious way to clear the stub warning is to delete the placeholder line.
```

- [ ] **Step 6: Run the suite**

```bash
python -m pytest plugins/virtuoso -q 2>&1 | tail -8
python plugins/virtuoso/scripts/validate.py 2>&1 | tail -3
```

Expected: no failures; `All checks passed.`

- [ ] **Step 7: Document the rules where a project reads them**

In `plugins/virtuoso/references/readiness-rubric.md`, replace the paragraph that begins "The heading must start with the id" with:

```markdown
The heading must start with the id, so `## Why we dropped db-migration` does not count —
a heading that discusses a check is not a definition of it. A longer id does not stand in
for a shorter one either: `## db-migration-rollback` does not define `db-migration`.

Case does not matter, so `## Deployment — environment and rollback` defines `deployment`:
the id is an identifier and the heading is prose you write. The id and the `#` marks must
be on the same line, and a heading inside a fenced code block is an example of a heading
rather than one — the block just above is exactly that, and copying it verbatim into your
overlay defines nothing.

A section with a heading and no prose under it is reported too. The placeholder is not
the only way to leave a check undefined; deleting it is the other.
```

In `plugins/virtuoso/references/registry-contract.md`, replace the `pairing-body-stub` row of the finding table:

```markdown
| `pairing-body-stub` | the section exists but is empty, or still the scaffold's placeholder |
```

- [ ] **Step 8: Commit**

```bash
git add plugins/virtuoso/tools/governance/overlays.py plugins/virtuoso/references/readiness-rubric.md plugins/virtuoso/references/registry-contract.md plugins/virtuoso/scripts/test_overlays.py
git commit -m "fix(overlays): body detection stops passing what is not a body

Four ways a declared id was reported wrongly, all in the same few lines.

'\\s+' spans a newline, so a bare '##' followed by a paragraph starting with the
id read as a heading. A heading inside a code fence counted -- and the shipped
rubric's own example shows '## db-migration' inside one, so copying it was a
false pass. Matching was case-sensitive with nothing saying so, which reports
'## Deployment', the natural way to write that section, as undefined. And an
empty section passed green, which matters because deleting the placeholder is
the obvious way to clear the stub warning: the gate had a second route its own
remedy could satisfy.

Fences are blanked length-preservingly, so detection ignores them while the body
is still sliced out of the real text.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: `policy-set` — the write path `project-profile` documents

**Files:**
- Modify: `plugins/virtuoso/tools/governance/policy.py` (add `assign`, `is_documented`)
- Modify: `plugins/virtuoso/tools/governance/repair.py` (add `policy_plan`, `apply_plan` label)
- Modify: `plugins/virtuoso/scripts/virtuoso_registry.py` (add `cmd_policy_set`, parser, imports, docstring)
- Modify: `plugins/virtuoso/skills/project-profile/SKILL.md` (Phase 4, catalogue row 8)
- Modify: `plugins/virtuoso/references/registry-contract.md` (writer list)
- Test: `plugins/virtuoso/scripts/test_overlays.py`

**Interfaces:**
- Consumes: `_codes(root)`, `_declare(root, ids)`, `registered` from the existing test file.
- Produces:
  - `policy.assign(raw: dict | None, path: str, value) -> dict` — pure, returns a new dict.
  - `policy.is_documented(path: str) -> bool`.
  - `repair.policy_plan(reg, key: str, before, after) -> RepairPlan`.
  - `repair.apply_plan(reg, plan, *, plugin_version="", now=None, label="repair")`.
  - CLI: `virtuoso_registry.py --actor <ceremony> policy-set <key> --value-json <json> [--apply]`.

`project-profile` Phase 4 says it "writes only the machine-readable half, through the existing previewed and backed-up repair path". No such path exists. `repair.plan()` takes no policy input and carries `reg.policy` through unchanged; no subcommand writes a policy value; `project-profile` appears in no `allowedWriters`. The skill forbids hand-editing the manifest and then prescribes a path that cannot carry the interview's answers.

It is cheap to make true. `reg.policy` is a plain dict, `to_manifest()` already emits it, and `apply_plan` already validates a candidate registry, backs up every affected file, writes, re-validates, and rolls back on any failure. The readme carries roles rather than policy, so a policy write touches the manifest alone.

Also fix the catalogue: it has eight rows, not the seven claimed, and row 8 maps to overlay bodies with no declaration — which contradicts the catalogue's own rule that every question names exactly one declaration.

- [ ] **Step 1: Write the failing tests**

Add a new section at the end of `plugins/virtuoso/scripts/test_overlays.py`, before the install-surfaces section:

```python
# =============================================================================
# policy-set — the declaration half, written
# =============================================================================


def _manifest(root):
    return json.loads((root / "Virtuoso" / "workspace-layout.json")
                      .read_text(encoding="utf-8"))


def test_assign_sets_a_dotted_key_without_mutating_its_input():
    from tools.governance import policy as policy_mod
    original = {"rubric": {"version": "1.0"}}
    updated = policy_mod.assign(original, "rubric.extensions", ["db-migration"])
    assert updated["rubric"]["extensions"] == ["db-migration"]
    assert updated["rubric"]["version"] == "1.0"       # siblings survive
    assert "extensions" not in original["rubric"]      # pure


def test_assign_creates_intermediate_levels():
    from tools.governance import policy as policy_mod
    assert policy_mod.assign({}, "a.b.c", 1) == {"a": {"b": {"c": 1}}}


def test_is_documented_distinguishes_a_real_key_from_a_storage_slot():
    from tools.governance import policy as policy_mod
    assert policy_mod.is_documented("rubric.extensions")
    assert not policy_mod.is_documented("rubric.notAKey")


def test_policy_set_previews_without_writing(registered):
    before = snapshot_tree(str(registered))
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "rubric.extensions", "--value-json", '["db-migration"]')
    assert completed.returncode == 0, completed.stderr
    assert "rubric.extensions" in completed.stdout
    assert snapshot_tree(str(registered)) == before


def test_policy_set_writes_the_value_and_backs_the_manifest_up(registered):
    from tools.governance import backup as backup_mod
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "rubric.extensions", "--value-json", '["db-migration"]',
                    "--apply")
    assert completed.returncode == 0, completed.stderr
    assert _manifest(registered)["policy"]["rubric"]["extensions"] == ["db-migration"]
    backups = registered.joinpath(*backup_mod.BACKUP_DIRNAME.split(os.sep))
    assert backups.is_dir() and any(backups.iterdir())


def test_policy_set_feeds_the_pairing_check(registered):
    """The half this writes must be the half the audit reads.

    This is the whole loop in one assertion: the ceremony writes the declaration,
    and session start immediately reports that its body is missing.
    """
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "rubric.extensions", "--value-json", '["db-migration"]',
                    "--apply")
    assert completed.returncode == 0, completed.stderr
    assert "pairing-body-missing" in _codes(registered)


def test_policy_set_preserves_unrelated_manifest_content(registered):
    before = _manifest(registered)
    run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
        "policy-set", "rubric.extensions", "--value-json", '["db-migration"]', "--apply")
    after = _manifest(registered)
    assert after["roles"] == before["roles"]
    assert after["schemaVersion"] == before["schemaVersion"]


def test_policy_set_refuses_without_an_actor(registered):
    completed = run(REGISTRY_CLI, "--root", str(registered),
                    "policy-set", "rubric.extensions", "--value-json", "[]", "--apply")
    assert completed.returncode == 3
    assert "actor" in completed.stderr


def test_policy_set_refuses_an_undocumented_key(registered):
    """A key nothing documents is a storage slot: no ceremony reads it, so writing
    it produces configuration that looks live and is inert."""
    before = snapshot_tree(str(registered))
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "rubric.notAKey", "--value-json", '"x"', "--apply")
    assert completed.returncode == 3
    assert "documented" in completed.stderr
    assert snapshot_tree(str(registered)) == before


def test_policy_set_refuses_a_value_that_fails_validation(registered):
    before = snapshot_tree(str(registered))
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "git.policy", "--value-json", '"yolo"', "--apply")
    assert completed.returncode == 3
    assert "not valid" in completed.stderr
    assert snapshot_tree(str(registered)) == before


def test_policy_set_refuses_malformed_json(registered):
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "rubric.extensions", "--value-json", "[not json",
                    "--apply")
    assert completed.returncode == 3
    assert "valid JSON" in completed.stderr


def test_policy_set_never_writes_an_overlay(registered):
    """The role stays read-only with no writers. A ceremony that can write policy
    must not have acquired the ability to write the other half."""
    run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
        "policy-set", "rubric.extensions", "--value-json", '["db-migration"]', "--apply")
    reg = registry_mod.load(str(registered))
    assert reg.writable("overlays", "project-profile") is False
    assert not (registered / "Virtuoso" / "overlays").exists()


def _catalogue_rows() -> list[str]:
    """The Phase 2 interview table's data rows, header and rule excluded."""
    body = PROFILE.read_text(encoding="utf-8").split("## Phase 2")[1].split("## Phase 3")[0]
    return [line for line in body.splitlines()
            if line.startswith("|") and not line.startswith("|---")
            and not line.startswith("| Ask")]


def test_every_catalogue_row_either_names_a_declaration_or_says_it_has_none():
    """The catalogue's own rule is that each question maps to exactly one
    declaration. One row collects bodies instead, which is legitimate — but it has
    to SAY so, or it quietly contradicts the rule it is printed underneath.
    """
    rows = _catalogue_rows()
    assert rows, "the catalogue has no rows"
    for row in rows:
        assert "`policy." in row or "no declaration" in row, \
            "catalogue row neither names a policy key nor admits it has none: %s" % row


def test_exactly_one_catalogue_row_collects_bodies():
    """If a second row ever stops naming a declaration, that is drift, not design."""
    assert sum(1 for row in _catalogue_rows() if "no declaration" in row) == 1


def test_project_profile_names_the_command_that_writes_policy():
    said = flat(PROFILE.read_text(encoding="utf-8"))
    assert "policy-set" in said
```

- [ ] **Step 2: Run them and watch them fail**

```bash
python -m pytest plugins/virtuoso/scripts/test_overlays.py -q -k "assign or is_documented or policy_set or catalogue or names_the_command" 2>&1 | tail -20
```

Expected: every one FAILs — `AttributeError` on `policy_mod.assign`, exit 2 from argparse for the unknown `policy-set` subcommand, and assertion failures on the two skill tests.

- [ ] **Step 3: Add the policy helpers**

In `plugins/virtuoso/tools/governance/policy.py`, add at module level after `_deep_merge`:

```python
def assign(raw: dict | None, path: str, value) -> dict:
    """``raw`` with the dotted ``path`` set to ``value``. Pure; returns a new dict.

    Intermediate levels are created as needed. A non-dict standing where a level
    must go is replaced, because the caller has just declared what that level is.
    Siblings at every level survive, so setting one key never silently drops the
    rest of a project's configuration.
    """
    parts = [p for p in path.split(".") if p]
    if not parts:
        raise ValueError("an empty policy key sets nothing")
    out = copy.deepcopy(raw or {})
    cursor = out
    for part in parts[:-1]:
        if not isinstance(cursor.get(part), dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = copy.deepcopy(value)
    return out


def is_documented(path: str) -> bool:
    """Whether ``path`` names a key the defaults document.

    A key nothing documents is a storage slot rather than a setting: no ceremony
    reads it, so writing one produces configuration that looks live and is inert.
    Project-owned configuration has the ``x-`` extension prefix and its own rules.
    """
    return Policy(DEFAULTS).get(path, None) is not None
```

- [ ] **Step 4: Add the transactional policy plan**

In `plugins/virtuoso/tools/governance/repair.py`, add after `plan()`:

```python
def policy_plan(reg: registry_mod.Registry, key: str, before, after) -> RepairPlan:
    """A one-action plan that writes ``reg``'s current policy to the manifest.

    Built as a RepairPlan so a policy write inherits :func:`apply_plan`'s
    transaction exactly — validate the reconstruction before touching anything,
    back up every affected file, write, re-validate, roll back on any failure.
    A second write path would be a second set of those guarantees to keep true.

    The readme view carries roles, not policy, so the manifest is the only file
    affected and the human view needs no resynchronization.
    """
    return RepairPlan(
        root=reg.root,
        actions=[RepairAction(
            kind="set-policy",
            role="",
            detail="set policy.%s" % key,
            current="(unset)" if before is None else json.dumps(before, ensure_ascii=False),
            proposed=json.dumps(after, ensure_ascii=False),
        )],
        files_affected=[schema.MANIFEST_RELPATH],
        manifest_text=reg.manifest_json(),
    )
```

Add `set-policy` to the `RepairAction.kind` comment. Then give `apply_plan` a label, changing its signature and the two `backup_mod` calls:

```python
def apply_plan(reg: registry_mod.Registry, repair_plan: RepairPlan, *,
               plugin_version: str = "", now=None,
               label: str = "repair") -> tuple[list[str], backup_mod.BackupSet]:
    """Apply an approved plan transactionally. Returns ``(files_written, backup_set)``.

    ``label`` names the backup directory, so a restore is traceable to the
    operation that caused it rather than to whichever machinery performed it.
    """
```

```python
    backup_set = backup_mod.open_set(reg.root, label, now=now)
    for rel in repair_plan.files_affected:
        backup_set.add(os.path.join(reg.root, *rel.split("/")), label)
```

- [ ] **Step 5: Add the CLI writer**

In `plugins/virtuoso/scripts/virtuoso_registry.py`, add `repair as repair_mod` to the `tools.governance` import list. Add the helper and command above `build_parser`:

```python
def _json_value(raw: str, label: str):
    """Any JSON value. A policy value may be a list, string, number, or object, so
    this deliberately does not require an object the way ``_json_object`` does."""
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise GovernanceError("%s must be valid JSON: %s" % (label, exc)) from exc


def cmd_policy_set(args) -> int:
    """Set one policy value in the manifest. Previews by default; ``--apply`` writes.

    Policy is the machine-readable half of a project rule. Until now the only way
    to set one was to hand-edit the manifest — which every ceremony is forbidden to
    do, and which skips validation, the backup, and the rollback. This routes it
    through the same transaction repair uses, so the ceremony that documents a
    previewed, backed-up write actually performs one.
    """
    if not args.actor:
        raise CapabilityError(
            "an explicit ceremony actor is required to set a policy value, for example "
            "--actor project-profile")
    reg = _load(args.root)
    if [f for f in reg.findings if f.severity == "error"]:
        raise GovernanceError(
            "this registry reports errors; run `virtuoso_preflight.py --mode repair` first. "
            "Writing policy onto an invalid registry buries the invalidity under a change "
            "that looks successful.")
    if not policy_mod.is_documented(args.key):
        raise GovernanceError(
            "policy.%s is not a documented key, so no ceremony reads it. Project-owned "
            "configuration belongs under an `x-` extension key." % args.key)

    value = _json_value(args.value_json, "--value-json")
    before = policy_mod.load(reg.policy).get(args.key)
    candidate = policy_mod.assign(reg.policy, args.key, value)
    problems = policy_mod.load(candidate).validate()
    if problems:
        raise GovernanceError("the resulting policy is not valid; nothing was written:\n  %s"
                              % "\n  ".join(problems))

    reg.policy = candidate
    plan = repair_mod.policy_plan(reg, args.key, before, value)

    if not args.apply:
        payload = {"key": args.key, "current": before, "proposed": value,
                   "applied": False, "plan": plan.as_dict()}
        if args.as_json:
            return _emit(payload, True)
        print(plan.render())
        print("Nothing was written. Re-run with --apply to write it.")
        return EXIT_OK

    written, backup_set = repair_mod.apply_plan(reg, plan, label="policy-set")
    payload = {"key": args.key, "current": before, "proposed": value, "applied": True,
               "filesWritten": written, "backup": backup_set.as_dict()}
    if args.as_json:
        return _emit(payload, True)
    print("policy.%s set" % args.key)
    print("  was:    %s" % json.dumps(before, ensure_ascii=False))
    print("  now:    %s" % json.dumps(value, ensure_ascii=False))
    print("  wrote:  %s" % (", ".join(written) or "(already that value)"))
    print("  backup: %s" % backup_set.relative_directory)
    return EXIT_OK
```

Register it in `build_parser`, directly after the `overlays` subparser:

```python
    policy_set = sub.add_parser("policy-set", parents=[common])
    policy_set.add_argument("key", help="dotted policy key, e.g. rubric.extensions")
    policy_set.add_argument("--value-json", required=True,
                            help='the new value as JSON, e.g. \'["db-migration"]\'')
    policy_set.add_argument("--apply", action="store_true",
                            help="write it; without this the change is previewed only")
    policy_set.set_defaults(func=cmd_policy_set)
```

Add it to the module docstring's subcommand list, under the explicit writers:

```
  policy-set <key> --value-json V   set one policy value (preview; --apply writes)
```

- [ ] **Step 6: Run the new tests**

```bash
python -m pytest plugins/virtuoso/scripts/test_overlays.py -q -k "assign or is_documented or policy_set" 2>&1 | tail -10
```

Expected: all pass. The two skill tests still fail — Step 7 fixes those.

- [ ] **Step 7: Make the skill honest**

In `plugins/virtuoso/skills/project-profile/SKILL.md`, replace the Phase 4 body (everything between the `## Phase 4` heading and the `---` before Phase 5):

```markdown
Only after approval, and only the machine-readable half. Policy lives in the manifest, so
it is written through the registry helper's explicit writer — never by hand-editing the
file. Preview first; `--apply` is what writes:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor project-profile \
        policy-set rubric.extensions --value-json '["db-migration"]'
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor project-profile \
        policy-set rubric.extensions --value-json '["db-migration"]' --apply

One key per invocation, so each approved line in the Phase 3 preview is one write you can
point at. The value is JSON, so a list stays a list. The write validates the resulting
policy before touching anything, backs the manifest up, and rolls back if the registry
would not reload cleanly.

The helper refuses a key the plugin does not document, because a key no ceremony reads is
configuration that looks live and is inert. If an answer has nowhere documented to go, it
is a body, not a declaration — take it to Phase 5.

Re-run `--mode check` afterwards and confirm the status is `ready` or `warning`. A profile
that leaves a registry in `repair-needed` has made the project worse.
```

In the Phase 2 catalogue table, replace the last row so every row names a declaration:

```markdown
| What must every agent know here that the plugin cannot? Which shipped file does each rule belong on top of? | no declaration — these are **bodies**, recorded in Phase 3 and emitted in Phase 5 |
```

Then add directly below the table:

```markdown
The last row is the exception that proves the rule, and it is marked as one: it collects
bodies rather than declarations. Every other row names exactly one `policy.*` key, and a
question that named none would produce prose nothing consults.
```

In `plugins/virtuoso/references/registry-contract.md`, add `policy-set` to the explicit-writer list wherever `create-item` is named.

- [ ] **Step 8: Run everything**

```bash
python -m pytest plugins/virtuoso -q 2>&1 | tail -8
python plugins/virtuoso/scripts/validate.py 2>&1 | tail -3
```

Expected: no failures; `All checks passed.`

- [ ] **Step 9: Walk the loop by hand**

```bash
python - <<'PY'
import json, os, subprocess, sys, tempfile
plugin = os.path.abspath("plugins/virtuoso")
sys.path.insert(0, plugin)
from tools.governance import schema
pre = os.path.join(plugin, "scripts", "virtuoso_preflight.py")
cli = os.path.join(plugin, "scripts", "virtuoso_registry.py")
proj = tempfile.mkdtemp()
run = lambda *a: subprocess.run([sys.executable, *a], capture_output=True, text=True)
run(pre, "--root", proj, "--mode", "create", "--authorize")
man = os.path.join(proj, "Virtuoso", "workspace-layout.json")
d = json.load(open(man, encoding="utf-8"))
d["roles"]["overlays"] = dict(schema.default_role("overlays"), path="Virtuoso/overlays")
json.dump(d, open(man, "w", encoding="utf-8"), indent=2)
print("1. declare:", run(cli, "--root", proj, "--actor", "project-profile", "policy-set",
                         "rubric.extensions", "--value-json", '["deployment"]',
                         "--apply").stdout.splitlines()[0])
print("2. session start:", [l for l in run(pre, "--root", proj, "--mode", "check",
                                           "--quiet").stdout.splitlines()
                            if l.startswith("overlays:")][0])
out = run(cli, "--root", proj, "overlays", "--scaffold", "--for",
          "references/readiness-rubric.md").stdout
t = os.path.join(proj, "Virtuoso", "overlays", "references", "readiness-rubric.md")
os.makedirs(os.path.dirname(t)); open(t, "w", encoding="utf-8").write(out)
print("3. after scaffold:", [l for l in run(pre, "--root", proj, "--mode", "check",
                                            "--quiet").stdout.splitlines()
                             if l.startswith("overlays:")][0])
open(t, "w", encoding="utf-8").write("## Deployment\n\nrollback rehearsed\n")
print("4. after prose:", [l for l in run(pre, "--root", proj, "--mode", "check",
                                         "--quiet").stdout.splitlines()
                          if l.startswith("overlays:")][0])
PY
```

Expected: step 1 prints `policy.rubric.extensions set`; step 2 names `deployment` as undefined; step 3 reports a finding about the stub; step 4 is clean with no suffix.

- [ ] **Step 10: Commit**

```bash
git add plugins/virtuoso/tools/governance/policy.py plugins/virtuoso/tools/governance/repair.py plugins/virtuoso/scripts/virtuoso_registry.py plugins/virtuoso/skills/project-profile/SKILL.md plugins/virtuoso/references/registry-contract.md plugins/virtuoso/scripts/test_overlays.py
git commit -m "feat(policy): policy-set, the write path project-profile documented

The skill's Phase 4 said it writes the machine-readable half 'through the
existing previewed and backed-up repair path'. There was no such path. repair
takes no policy input and carries reg.policy through unchanged, no subcommand
wrote a policy value, and project-profile is in no allowedWriters. The skill
forbade hand-editing the manifest and then prescribed a path that could not
carry the interview's answers -- so its only side-effecting step was
unimplementable as written.

policy-set is that path, built on apply_plan rather than beside it, so a policy
write inherits the same transaction: validate the candidate registry, back up,
write, re-validate, roll back on failure. It refuses a key the defaults do not
document, because a key no ceremony reads is configuration that looks live and
is inert.

The catalogue's eighth row is now marked as what it is -- bodies, not a
declaration -- instead of quietly contradicting the rule it sits under.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Reconcile the shipped record with measured behaviour

**Files:**
- Modify: `RELEASE-NOTES.md`
- Modify: `docs/superpowers/specs/2026-09-17-project-specificity-architecture-design.md`

**Interfaces:**
- Consumes: the behaviour established by Tasks 1-7.
- Produces: nothing code depends on.

The release notes describe a v1.8.0 that was never quite the one on disk, and the spec is marked "implemented" with two done-when items unmet and a Risks table still citing a check that was dropped. The reference documents were corrected inside the tasks that changed their behaviour; this is the narrative layer.

- [ ] **Step 1: Correct the spec's stale Risks row**

In `docs/superpowers/specs/2026-09-17-project-specificity-architecture-design.md`, replace the last Risks-table row, which still names the dropped check:

```markdown
| The pairing convention is too loose or too strict | Documented beside the extension table; a body must be a single-line depth 2–4 heading outside a code fence, matched case-insensitively, with prose under it. The reverse direction is deliberately unchecked — see the implementation notes |
```

- [ ] **Step 2: Annotate the Stage 2 findings table**

That table still lists a finding that was dropped before release, and the document is headed "implemented in v1.8.0", so a reader takes it as a description of what shipped. Annotate rather than delete — the record should show both what was planned and what happened. Replace the `pairing-body-orphan` row and add the one that replaced it:

```markdown
| ~~`pairing-body-orphan`~~ | — | **Not implemented.** Dropped during Stage 3; see the implementation notes |
| `pairing-body-stub` | warning | the section exists but is empty, or still the scaffold's placeholder |
```

- [ ] **Step 3: Correct the Stage 2 and Stage 3 done-when lists**

Replace the Stage 2 "Done when" bullet that names `pairing-body-orphan`:

```markdown
- A project declaring `rubric.extensions: ["db-migration"]` with no body sees
  `pairing-body-missing` named in the session-start overlay line and in `overlays`, in
  every registration state — including with no `overlays` role and with the directory
  absent.
```

Replace the Stage 3 "Done when" bullet about approval:

```markdown
- Approval writes only policy, transactionally, with a backup — through
  `virtuoso_registry.py policy-set <key> --value-json <json> --apply`, which validates the
  resulting policy, backs the manifest up, and rolls back if the registry would not reload.
```

- [ ] **Step 4: Extend the implementation notes**

Append to the "Implementation notes (v1.8.0)" section:

```markdown
### Found by reviewing the release rather than the plan (2026-09-17)

Five things the completion report claimed were not true when measured on Windows, which
is the platform this plugin is maintained from. All five are fixed in the release that
actually shipped.

The suite was green on Linux only. A fixture wrote two overlay paths differing only in
case, which are one file on NTFS and on a default macOS volume, so five tests asserted
against content the fixture had not produced. `windows-latest` had been red since v1.6.0
on an unrelated cross-drive path, so it had stopped working as a gate and absorbed these
without anyone reading it. A red gate is not a gate.

The documented redirect produced an unreadable overlay. `--scaffold --for X > X` is the
whole write, and on Windows it wrote a legacy code page under pwsh and UTF-16 under
PowerShell 5.1. Both made `read_text` return `None`, and the audit then reported
`pairing-body-missing` about a file carrying exactly the right heading. Scaffolds are now
emitted as UTF-8 bytes, a BOM is honoured on read, and genuinely undecodable bytes are
reported as `overlay-unreadable` rather than laundered into a misleading finding.

The status line was silent in two of three states. The finding suffix was computed after
the early returns, so the two states a project is in the moment it declares its first
extension reported a clean line. It now applies everywhere and names the undefined ids.

Body detection passed what is not a body: a heading split across a newline, a heading
inside a fenced code block — including the one this plugin's own rubric shows as an
example — a section with nothing under it, and, in the other direction, rejected
`## Deployment` for `deployment`. The empty-section case mattered most: deleting the
placeholder is the obvious way to clear the stub warning, so the gate still had a second
route its own remedy could satisfy.

`project-profile` Phase 4 had no mechanism. It is now `policy-set`, built on `apply_plan`
so a policy write inherits the same transaction repair has.

A version bump is not a release. 1.8.0 was bumped inside feature commits on a branch while
`origin/main` sat at v1.6.0 and the installed plugin on the maintainer's machine was
v1.6.0. `release.py` exists because two releases once shipped on red CI; it was bypassed.
This release ran it.
```

- [ ] **Step 5: Correct the release notes**

In `RELEASE-NOTES.md`, in the v1.8.0 section's pairing-check table, replace the `pairing-body-stub` row and add the new finding:

```markdown
| `pairing-body-stub` | a section exists but is empty, or still the scaffold's placeholder |
| `overlay-unreadable` | the overlay's bytes are not decodable as text; re-save it as UTF-8 |
```

Replace the sentence beginning "A body is a depth 2–4 heading that **starts with** the id":

```markdown
A body is a depth 2–4 heading that **starts with** the id, on one line, outside any code
fence, with prose under it. Anchoring is the point: `## Why we dropped db-migration`
discusses a check and must not satisfy it, and `## db-migration-rollback` is a different
id. Case is not: `## Deployment` defines `deployment`, because the id is an identifier and
the heading is prose a person writes.
```

Add a subsection before "### `project-profile`, the sixteenth skill":

```markdown
### Writing the declaration half

`virtuoso_registry.py --actor <ceremony> policy-set <key> --value-json <json>` previews a
policy change; `--apply` writes it. It runs on the same transaction `repair` does — the
candidate registry is validated before anything is touched, the manifest is backed up, and
a registry that would not reload cleanly is rolled back. It refuses a key the plugin does
not document, because a key no ceremony reads is configuration that looks live and is
inert.

This is what `project-profile` Phase 4 uses. Before it existed, the only way to set a
policy value was to hand-edit the manifest, which every ceremony is forbidden to do.
```

- [ ] **Step 6: Verify nothing else claims what is no longer true**

```bash
grep -rn "pairing-body-orphan" --include=*.md --include=*.py . | grep -vi "dropped\|not implemented\|deliberately"
```

Expected: no output. Before Step 2 this printed the Stage 2 findings-table row; every surviving mention must now be one that says the check does not exist.

```bash
grep -rn "case-sensitiv\|starts with" plugins/virtuoso/references/readiness-rubric.md
python -m pytest plugins/virtuoso -q 2>&1 | tail -4
python plugins/virtuoso/scripts/validate.py 2>&1 | tail -3
```

Expected: the rubric describes the body rule including case; no test failures; `All checks passed.` `validate.py` reads several of these documents, so a docs edit can break the build.

- [ ] **Step 7: Commit**

```bash
git add RELEASE-NOTES.md docs/superpowers/specs/2026-09-17-project-specificity-architecture-design.md
git commit -m "docs: the record matches the behaviour that shipped

The release notes described a body rule the code does not implement, the spec was
marked implemented with two done-when items unmet, and its Risks table still
cited pairing-body-orphan as the mitigation for a direction that was dropped
before release. The implementation notes now carry what reviewing the release --
rather than the plan -- found.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Merge, release, and record

**Files:**
- Modify: `C:\Users\estra\Projects\Virtuoso\sprint-catalog.csv` (governance workspace, LOCAL-ONLY)
- Create: `C:\Users\estra\Projects\Virtuoso\Close-Outs\CloseOut.V18-READINESS.2026-09-17.md`

**Interfaces:**
- Consumes: green CI on `eb/zealous-einstein-zxvy3w`.
- Produces: v1.8.0 installed and verified on this machine.

`origin/main` is at v1.6.0 and the plugin installed here is v1.6.0, so the SessionStart hook the user runs today has no overlays support at all. The version was bumped inside feature commits, so `release.py 1.8.0` would refuse as "already released"; `--redeploy` is the mode built for exactly this — bump and push done, deploy and verify not.

- [ ] **Step 1: GATE — both CI legs green on the final branch state**

```bash
git push
gh run list --repo gorillabrown/virtuoso --branch eb/zealous-einstein-zxvy3w --limit 1
```

Wait for completion. Expected: both `validate (windows-latest)` and `validate (ubuntu-latest)` green. **Do not merge on a red leg.**

- [ ] **Step 2: Merge to main**

```bash
git checkout main
git merge --ff-only eb/zealous-einstein-zxvy3w
git log --oneline -1
```

Expected: a fast-forward. `origin/eb/zealous-einstein-zxvy3w` was zero commits behind main, so no merge commit is needed. If git refuses the fast-forward, stop: something landed on main since this plan was written, and the reconciliation is a judgement call, not a mechanical one.

- [ ] **Step 3: Push main and confirm CI**

```bash
git push origin main
gh run list --repo gorillabrown/virtuoso --branch main --limit 1
```

Wait for green on both legs. `release.py` re-runs the suite itself, but a red main is worth knowing about before the pipeline tells you.

- [ ] **Step 4: Confirm the pipeline's preconditions**

```bash
python plugins/virtuoso/scripts/release.py --dry-run 2>&1 | tail -20
```

Expected: `DRY-RUN COMPLETE: every gate green against version 1.8.0. Nothing written.` A gate failure here names itself; fix it before Step 5.

- [ ] **Step 5: Release**

```bash
python plugins/virtuoso/scripts/release.py 1.8.0 --redeploy 2>&1 | tail -30
```

Expected: `RELEASE v1.8.0 COMPLETE.` `--redeploy` is required because the version already equals the repo's current version; without it the preflight refuses with "already released? resume an incomplete deploy with --redeploy".

- [ ] **Step 6: Verify the installed copies — both of them**

```bash
python -c "import json,os; d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json'))); print(d['virtuoso@virtuoso-marketplace'][0]['version'], d['virtuoso@virtuoso-marketplace'][0]['installPath'])"
```

Expected: `1.8.0` and a path under `cache/virtuoso-marketplace/virtuoso/1.8.0`.

`installed_plugins.json` is the CLI's install record. **The desktop app runs its own copy**
and is currently on 1.3.6, so a green CLI check here does not mean the app you work in is
running 1.8.0. Confirm the app's copy separately:

```bash
python - <<'PY'
import glob, json, os
for path in glob.glob(os.path.expanduser("~/**/plugins/**/virtuoso/**/plugin.json"),
                      recursive=True):
    try:
        print(json.load(open(path, encoding="utf-8")).get("version"), path)
    except (OSError, ValueError):
        pass
PY
```

If the app does not pick 1.8.0 up, say so in the close-out rather than recording that the
app runs it. An unverified claim about the installed version is the same failure as the
unverified claim about the test suite that produced this plan.

Then, from the governance workspace, confirm session start reports overlays:

```bash
python ~/.claude/plugins/cache/virtuoso-marketplace/virtuoso/1.8.0/scripts/virtuoso_preflight.py --root /c/Users/estra/Projects/Virtuoso --mode check --quiet
```

Expected: three lines, the third beginning `overlays:`. Restart the app afterwards so session snapshots pick the new version up — the release script says so for a reason.

- [ ] **Step 7: Record the work in the governance workspace**

Append a row to `C:\Users\estra\Projects\Virtuoso\sprint-catalog.csv` matching the existing column order, with sprint id `V18-READINESS`, branch `eb/zealous-einstein-zxvy3w`, and a note naming the five blocking concerns closed.

Write `C:\Users\estra\Projects\Virtuoso\Close-Outs\CloseOut.V18-READINESS.2026-09-17.md` covering: what the adversarial review found, which of the fourteen gaps this plan closed, which it deliberately did not (G13 the Codex-manifest publish decision, G14 whether any agent applies an overlay), and the released version.

- [ ] **Step 8: Restore the local spec and clean up**

```bash
cd /c/Users/estra/Projects/Virtuoso/virtuoso.dev
mv ../local-notes/2026-09-16-project-overlays-design.LOCAL-1859-line.md ../local-notes/keep-2026-09-16-project-overlays-design.md
git worktree prune
git worktree list
git status --short
```

The local 1,859-line planning document is *not* restored to `docs/superpowers/specs/` — that path now holds the branch's own 198-line record, and putting the local copy back would recreate the collision. Keep it under `../local-notes/`.

Expected: `git status --short` prints nothing.

- [ ] **Step 9: Commit the governance record**

```bash
cd /c/Users/estra/Projects/Virtuoso
git add sprint-catalog.csv Close-Outs/CloseOut.V18-READINESS.2026-09-17.md audits/Audit.AdversarialReview.v1.8.0-project-specificity.2026-09-17.md
git commit -m "govern: V18-READINESS close-out — v1.8.0 released after adversarial review

The review found the branch red on windows-latest, the documented scaffold
redirect producing an unreadable overlay, session start silent in two of three
states, project-profile Phase 4 with no mechanism, and nothing actually
released. All five closed; 1.8.0 is installed and verified here.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Out of scope

These came out of the review and are deliberately not in this plan. Each warrants its own brainstorm rather than being folded in here.

- **G14 — does any agent actually apply an overlay?** No test, eval, or observation shows a skill reading one. The whole 1.7.0 and 1.8.0 investment is plumbing for prose whose application is, by the spec's own corollary, discretionary and unmeasured. A `claude plugin eval` with a fixture project and an agent overlay would be the first measurement. This is the highest-value follow-up.
- **G13 — the `.codex-plugin` publish decision.** The branch removed `.codex-plugin/` from `.gitignore`, reversing a 2026-06-30 decision recorded as "dev clone only, never published", with no stated reason the decision no longer holds. The manifest's shape has never been validated against that host.
- **A role-sourced `Pairing` variant** for `policy.standingRules`, which pairs ids to a role rather than an overlay and would mean parsing a project's own roadmap.
