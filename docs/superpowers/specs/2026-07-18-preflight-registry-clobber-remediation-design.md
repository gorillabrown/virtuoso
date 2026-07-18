# PRD — Registry-Authoritative Preflight (Option D)

**Remediation of the Virtuoso governance-registry clobber · target release v1.3.1 · 2026-07-18**

| | |
|---|---|
| **Status** | Draft for approval. Implementation is unblocked — the background-task chip `task_2d3ea410` ("Patch Virtuoso preflight registry clobber (1.3.1)") carries a dispatch-ready build prompt. |
| **Owner** | Evan owns the release decision (version bump + marketplace update, per standing rule). Implementation is dispatchable as a single sonnet-tier sprint with this spec. |
| **Change surface** | `plugins/virtuoso/scripts/virtuoso_preflight.py` — verified as the plugin's **sole** registry writer — plus its test files. No SKILL.md, hook-config, or skill-behavior changes. |
| **Branch** | `fix/registry-authoritative-preflight`, cut from `main` @ v1.3.0 (`343e6dd`). Repo root is the `virtuoso.dev\` subdirectory, not the session cwd. |
| **Evidence base** | Verified diagnosis of 2026-07-18: sandboxed reproduction showed the documented-non-writing SessionStart hook command changing **7 files and creating 5** (including the 3-line lessons stub) on a curated fixture; a live clobber→repair oscillation was observed in Gloves_Of_Glory_fresh during the investigation. Durable record: memory `virtuoso-preflight-registry-clobber`. |

---

## Problem Statement

Every session start, `/clear`, and context **compaction** in any `Virtuoso/`-markered project fires a preflight that silently regenerates the governance registry (`Virtuoso.Governance.Readme.md` + `Virtuoso/workspace-layout.json`) from discovery heuristics instead of honoring the curated registry — repointing the roadmap to a dead archive (structural-marker score beats recency), resetting the lessons pointer to a freshly seeded empty stub, resetting close-outs, and deleting project-custom roles (`epics`, `roadmapArchives`). The same code path runs from every governance skill's `--mode adopt` preamble, and `_refresh_copy` re-churns vendored scripts on every repair cycle (CRLF-committed blobs vs LF plugin bytes).

Nine occurrences have been *noticed* in GoG since 2026-07-10; in reality the trigger fires per lifecycle event across all active sessions, and containment (post-invocation checks, pre-gate checks, worker tripwires) repairs it continuously. Left uncaught once, the next governance skill would edit a dead archive as "the roadmap," append lessons to an empty stub while the real ~1.4 MB catalog stops accumulating, and write close-outs into a void — and a compaction firing **during** a close-out can race a real lessons append into the stub. The containment also imposes a permanent attention/token tax on every worker prompt and trips every clean-tree gate until repaired.

## Goals

1. **Zero unsolicited mutations:** the exact SessionStart hook command (`--mode detect --quiet`) mutates **0 bytes** on any project, curated or not — restoring the behavior the plugin's own contract test documents ("the unattended SessionStart hook must stay non-writing").
2. **Registry authority honored end-to-end:** `adopt`/heal on a healthy curated project converges **byte-identical**, custom roles included — the registry's own charter ("never create a parallel or competing document for a role already registered") enforced on its generator.
3. **Phantom-modified class eliminated:** no EOL-only rewrites of vendored scripts; GoG `git status` stays clean across repair→run cycles.
4. **Containment retired:** post-invocation checks and worker-prompt tripwires stood down after a clean 5-day soak, recovering the standing per-prompt overhead.
5. **Durable beyond this machine:** fix released at source as **v1.3.1** so cache refreshes and any other marketplace consumer inherit it.

## Non-Goals

1. **No redesign of discovery ranking** (`_roadmap_score` ordering stays). Registry authority makes ranking irrelevant for registered roles; re-tuning heuristics is speculative scope. (P1 adds two missing archive segments only.)
2. **No SKILL.md or contract-test-string changes.** The `--mode adopt` preambles stay and become true no-ops on healthy projects; all existing contract tests remain green unmodified.
3. **No hook removal or re-architecture.** The SessionStart hook keeps firing detect; the defect is that detect writes, not that it runs.
4. **No governance-content restoration in GoG.** Evidence says no content was ever lost; R13 audits that cheaply, but content repair is out of scope.
5. **No GoG repo EOL renormalization mandate.** The primary EOL fix lives in the plugin; a `.gitattributes` line is optional hardening (P1), not a requirement.
6. **No proactive migration of sibling markered trees** (`Blurby`, `.rem-*` copies). One status check each after deploy; further work only if drift is found.

## User Stories

Ordered by priority. "Skills" and "workers" are first-class users in this ecosystem — they read and write through the registry.

1. As the **plugin operator**, I want session lifecycle events (start / clear / compact) to never write to my project trees, so that clean-tree gates pass without pre-repair and mid-sprint state stays mine.
2. As a **governance skill run** (roadmap-review, pointer-closeout, …), I want the adopt preflight to treat the curated registry as authoritative, so that roadmap edits, lessons appends, and close-outs land in the real registered documents.
3. As a **project with custom governance roles** (epics, roadmapArchives), I want unknown registry keys round-tripped through every regeneration, so that project-specific rows survive any plugin run.
4. As a **git/merge worker**, I want my expected dirty set to contain only my sprint's files, so that my prompt carries no standing clobber-repair instructions.
5. As the **plugin owner**, I want behavioral regression tests (not command-string assertions), so that a future refactor cannot silently reintroduce registry regeneration.
6. *Edge:* As an operator with a **corrupt or missing manifest**, I want the preflight to fall back to the readme's machine block before resorting to regeneration, so that a half-clobbered project can still self-heal toward the curated state.
7. *Edge:* As an operator whose **registered path is missing on disk**, I want the path kept and marked `⬜ not present` rather than re-guessed, so that a temporarily absent file never causes a silent repoint.

## Requirements

### Must-Have (P0)

**R1 — Detect mode writes nothing, ever.**
Includes fixing the `created = _heal(root, created=[])` misbinding in `preflight()` (~line 744) that returns the paths dict and corrupts detect's reporting.
- Given a markered project with a curated registry, When `virtuoso_preflight.py --root <p> --mode detect --quiet` runs, Then a before/after hash-walk of the tree is identical and exit code is 0.
- Given the same run without `--quiet`, Then a correct status line is printed and no "created/updated" items are reported.

**R2 — Registry-authoritative overlay in `_build_full` and `_build_thin`.**
Resolution order: parse `Virtuoso/workspace-layout.json` → else parse the `virtuoso-governance-registry` machine block in `Virtuoso.Governance.Readme.md` → else (neither parses) current regeneration behavior as last resort. When a registry parses: overlay **all** its path keys — known and unknown — over computed defaults; run discovery only for roles the registry lacks; round-trip unknown keys into both regenerated outputs (manifest keys verbatim; readme rows with a derived label), deterministic ordering (known roles first, then custom keys).
- [ ] Adopt/heal on the curated fixture leaves both registry files byte-identical.
- [ ] `epics` and `roadmapArchives` survive in manifest and readme.
- [ ] Roadmap pointer remains `2 operational/GoG_Roadmap.md` even though `archives/GoG_Roadmap_Archive_2026-07-10.md` outscores it structurally (3 vs 2 markers).
- [ ] With manifest deleted but readme intact, heal reconstructs the manifest from the machine block — curated paths, not defaults.

**R3 — Seeding restricted to create mode.**
Seeds (roadmap seed, lessons stub, workflow reference, sprint-queue template) are written only in `create` mode and only for roles whose path came from defaults. Heal/adopt report missing roles instead of seeding.
- [ ] After adopt on the curated fixture, no file exists at `1 governance/SpecRetro.Lessons_Learned.md`.
- [ ] `--mode create` on a bare tree still scaffolds the full workspace (no regression vs current behavior).

**R4 — Registered-but-missing paths are kept.**
A registered path absent on disk stays registered, renders as `⬜ not present`, and is never re-guessed or re-anchored.

**R5 — EOL-insensitive `_refresh_copy`.**
Compare with `\r\n`→`\n` normalization on both sides; skip when normalized-equal.
- [ ] A vendored script whose project copy differs from the plugin copy only by CRLF is not rewritten.

**R6 — Behavioral regression tests** in `scripts/test_virtuoso_preflight.py` (port the session's repro fixture: markered `Virtuoso/`, curated manifest with custom keys, live roadmap with 2 structural markers, archive with 3): `test_detect_mode_mutates_nothing_on_markered_project`, `test_heal_preserves_curated_registry_and_custom_roles`, `test_vendor_refresh_skips_eol_only_differences`, `test_create_mode_still_scaffolds_bare_tree`. Existing contract tests stay green unmodified.

**R7 — Cache hot-patch deployment.** After the suite passes, copy the patched file byte-identical over `~/.claude/plugins/cache/virtuoso-marketplace/virtuoso/1.3.0/scripts/virtuoso_preflight.py`. Hooks re-execute the file per event, so this takes effect machine-wide immediately, no restarts. Verify: rerun the repro harness (expect 0 changed / 0 created) and confirm GoG `git status --porcelain` is empty across a fresh session start.

**R8 — Release v1.3.1.** Commit on a branch per virtuoso.dev flow; version bump via `scripts/bump_version.py` and marketplace update are **Evan's release actions** (standing rule — never unilateral). Post-update verification: cache shows `1.3.1` and the hook path resolves into it. *Dependency, not a blocker: R1–R7 deliver full local protection while R8 waits.*

### Nice-to-Have (P1)

- **R9 — Discovery hardening:** add `"archives"` and `"0 archive"` to `_ARCHIVE_SEGMENTS` (protects the unregistered-project discovery path; GoG uses the plural, the list has only the singular).
- **R10 — GoG reconciliation commit:** add the missing `roadmapReviews` key to the curated manifest (readme has the row; manifest lacks the key — mirror drift); delete the empty `2 operational/Close-Outs` debris directory; optionally add a `.gitattributes` line for `Virtuoso/scripts/*.py`.
- **R11 — Correct the GoG standing memory:** strike the refuted `prepare_closeout_files.py` vector; record the SessionStart/compact hook vector and the fix version; keep the signature description for post-fix falsification.
- **R12 — Containment stand-down protocol:** after the soak (Success Metrics), retire post-invocation checks first, then worker tripwires; optionally keep one cheap pre-gate assertion permanently.
- **R13 — One-time race audit:** `git log -p` over the stub path plus a scan for post-2026-07-10 modifications inside `archives/`, to upgrade "no content was ever lost" from strong inference to verified fact.

### Future Considerations (P2)

- **R14 — Registry schema version key** (`registryVersion`) so future role additions migrate explicitly instead of via regeneration.
- **R15 — Non-writing drift advisory in detect** (a "registry vs disk" report line) — keep detect's read path structured so this bolts on cleanly.
- **R16 — Sibling-project sweep tooling** if the post-deploy status checks on `Blurby` / `.rem-*` trees reveal drift worth automating.

## Success Metrics

**Leading (hours–days):**
- Repro harness on the curated fixture: **0 files changed / 0 created** (was 7/5). Measured immediately post-R7 via the ported test + harness. Target: 100% of runs.
- Plugin pytest suite: green, including the four new behavioral tests.
- GoG occurrence count during a **5-day soak** with containment still armed: **0** registry-signature events across every pre-gate check, covering ≥10 session lifecycle events including ≥1 compaction and ≥1 governance skill run. Success threshold: zero. Any occurrence = falsification → capture `git diff` before repairing (single-cause conclusion is then wrong).

**Lagging (weeks):**
- Containment retired: worker prompts carry no clobber tripwires within ~1 week post-soak (R12).
- Zero new occurrence entries in the standing memory over 30 days.
- Post-release durability: after the next marketplace/cache refresh (1.3.1), the repro harness still reports 0/0 — confirming the fix survived the cache lifecycle that would have reverted a hot-patch-only approach.

## Open Questions

*None blocking — implementation can start now.*

1. **Other marketplace consumers?** Does anyone else install `gorillabrown/virtuoso`? Affects release-notes urgency for 1.3.1, nothing else. *(Evan · non-blocking)*
2. **Race-audit outcome (R13):** did any historical occurrence land content in the stub or archive? Determines whether any one-time content recovery is needed (expected: no). *(Audit · non-blocking)*
3. **Soak length:** 5 days proposed; acceptable to end early once the event-count target (≥10 lifecycle events incl. compact + skill run) is hit? Default: 5 days stands. *(Evan · non-blocking)*
4. **Pull R15 forward?** Should detect emit the drift-advisory line in 1.3.1, or stay pure-status for a minimal diff? Default: pure status. *(Evan · non-blocking)*

## Timeline Considerations

No external hard deadline. The forcing function is the **live race window**: every unpatched hour includes hook firings across active GoG sessions, and containment wins by racing, not by prevention.

- **Phase A — same day (~1 focused hour):** R1–R7. Branch patch + tests + cache sync + verification. Fully protective locally the moment R7 lands. Not blocked on anything.
- **Phase B — Evan's release schedule (minutes of work):** R8. Blocked only on the bump decision (standing rule).
- **Phase C — days 1–5 post-A:** soak with containment armed; then R10–R13 reconciliation and stand-down. R9 rides along with Phase A or B, whichever is convenient.

Scope guard: any addition to this spec should displace something or extend the soak — the P0 set is the minimum that ends the clobber class; everything else is hygiene layered behind it.

## Amendment — 2026-07-18

**Status:** Implemented and released (v1.3.1, commits `09f59d1` and `c47c23a`). Recorded here for the historical record; this amendment supersedes the R2 and R8 text above, which predates the owner's mid-sprint removal decision.

**What changed, verbatim (commit `09f59d1`, "Scope amendment (owner decision, mid-sprint)"):**

> Scope amendment (owner decision, mid-sprint): canonical layout and its migration subsystem removed entirely; detect now auto-scaffolds only a new project root (empty or .git-only directory). Stored legacy "canonical" manifests degrade gracefully to plugin-only semantics.

**Effect on R2 (Registry-authoritative overlay in `_build_full` and `_build_thin`):** the resolution order in R2 (manifest → readme machine block → regenerate-as-last-resort) stands, but the "regenerate" fallback no longer has a `canonical` layout to resolve into — `plugin-only` is the only layout `_resolve_layout` can produce. A workspace whose stored manifest still carries `"layout": "canonical"` (written before this amendment) is treated as unset and falls back to `plugin-only` rather than erroring or attempting migration. `--layout canonical` is no longer an accepted CLI value; the script hard-rejects it at argparse (`LAYOUTS = ("auto", "plugin-only")`).

**Effect on R8 (Release v1.3.1):** the release R8 describes is the same release that shipped this scope amendment — the canonical-layout removal and the empty-dir-only auto-scaffold behavior went out under v1.3.1, not a later version. R8's text, written before the mid-sprint amendment, should be read as covering this expanded scope.

**Downstream consequence (SK-04):** the ~10 `SKILL.md` files that documented the removed "canonical layout" choice (e.g., `/virtuoso-init`'s former two-option layout prompt) were cleaned up under sprint SK-04, dispatched separately from this PRD's implementation sprint.
