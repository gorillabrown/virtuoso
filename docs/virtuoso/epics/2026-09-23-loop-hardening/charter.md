---
epic: loop-hardening
created: 2026-09-23
status: active   # active | complete | aborted — set complete only per launch.md Completion protocol
---

# Epic Charter — Loop hardening: every prose link a check, every output a reader

<!-- FROZEN after launch. Only the user amends this file; the executor treats it as the
     contract. If reality proves the contract wrong, that is a BLOCKER(USER), not an edit. -->

## Outcome

The perpetual improvement loop graded in *Virtuoso Loop: SWOT and Gap Analysis*
(21 hand-offs: 6 mechanical, 5 partly, 8 prose, 2 missing) is hardened: every High
and Medium gap is closed by a command, a check, a role, or a metric with provenance;
every Low gap is closed or holds a recorded owner decision; and the plugin describes
itself identically on both hosts it ships to (Claude Code and the alternate host).
The plugin stays additive — registry schema v2, rubric v1.1, no project identifiers,
findings about project-owned things never at error severity — and every commit on the
way is green.

## Definition of Done — all rows must pass

| # | Condition | Verify by | Expected evidence |
|---|-----------|-----------|-------------------|
| D1 | Plugin metadata is brought forward and agrees across both manifests and the marketplace entry | `python -m pytest plugins/virtuoso/scripts/test_overlays.py -q -k "manifest or marketplace"`; `python plugins/virtuoso/scripts/bump_version.py --check` | the Codex `interface` test and a parity test pass; all declared files in sync |
| D2 | The preflight prints `roadmap-integrity:` and the four skills that read it match what it prints | `python -m pytest plugins/virtuoso -q -k integrity`; `grep -c "roadmap-integrity:" plugins/virtuoso/scripts/virtuoso_preflight.py` | tests pass; count ≥ 1; the contract lists five machine lines |
| D3 | Hand-edited invalid policy is reported at preflight as warnings | `python -m pytest plugins/virtuoso -q -k "policy and preflight"` | a fixture with a wrong-typed key yields a `policy-invalid` warning; exit code unchanged |
| D4 | Default writer lists match the skill bodies | `python -m pytest plugins/virtuoso -q -k writers` | `virtuoso` in `issues` and `closeOuts`; `3rd-party-audit` in `lessons` and `roadmap` |
| D5 | The `## Decision` block has a step and issue files have a reader | `grep -n "## Decision" plugins/virtuoso/skills/mid-dispatch-decision/SKILL.md`; docs test | a numbered step 6 sub-step writes it; pointer-closeout reads the item's issue files |
| D6 | No shipped file names a skill, agent, or case that does not exist | `python plugins/virtuoso/scripts/validate.py`; `grep -rlE "\b(athena\|solon\|herodotus)\b\|write-spec\|Case C\b" plugins/virtuoso/skills plugins/virtuoso/agents` | validator passes with a ghost-name check; grep empty; a fixture with a ghost name fails the validator (test) |
| D7 | The epic skill resolves the `epics` role and never a conventional path | `grep -cE "2 operational/Epics\|epics/. at the project root" plugins/virtuoso/skills/epic/SKILL.md` | 0; the contract documents the role |
| D8 | Sprint guards and the virtuoso skill read v2 roles | `python -m pytest plugins/virtuoso/scripts/test_sprint_guards.py -q`; `grep -c "registry:scripts" plugins/virtuoso/skills/virtuoso/SKILL.md` | a v2-manifest test passes; count 0 |
| D9 | `record-completion` performs the ledger crossing for a local register | `python -m pytest plugins/virtuoso -q -k record_completion` | ledger append, register status, refusal for external providers, recovery record on partial failure; `test_crossing.py` runs the command |
| D10 | Standing rules are paired and have one source | `python -m pytest plugins/virtuoso -q -k standing`; `grep -n "standingRules" plugins/virtuoso/skills/virtuoso/zeus.md` | an id without a heading in `standingRules.source` yields `standing-rule-unpaired` (warning) at preflight; Zeus reads the same source |
| D11 | Promotion candidates are computed from close-out outcomes | `python -m pytest plugins/virtuoso -q -k candidates`; docs test | `lessons --candidates` lists lessons applied by two or more close-outs with held / did-not-hold counts; roadmap-review D.4 runs it |
| D12 | A no-lesson reason names what was examined; lesson yield is a figure | `python -m pytest plugins/virtuoso -q -k "reason or lesson_yield"` | a reason citing no lesson, rule, or item fails when any exist, passes when none do; `kpis` carries `lesson-yield` |
| D13 | Sweep, adversarial and agent findings have a role and a reader | `python -m pytest plugins/virtuoso -q -k findings_role`; docs test | `findings` in the default roles with its writers; `create` scaffolds it; roadmap-review B.3 reads the previous lessons-applied |
| D14 | Effort calibration is measured per project | `python -m pytest plugins/virtuoso -q -k effort` | ledger accepts `effortEstimate` / `effortActual`; `kpis effort-calibration` with provenance, *not computable* below three paired records; `effort-levels` prefers the project's figure |
| D15 | Six loop-health metrics with provenance | `python -m pytest plugins/virtuoso -q -k learning`; `kpis --json` on the fixture | a `learning` group: lesson-yield, time-to-apply, held-rate, promotion-rate, live-count, repeated-trap-rate, each computed or *not computable* with its inputs named |
| D16 | No project's residue in shipped agents | `python plugins/virtuoso/scripts/validate.py`; `grep -rnE "2 operational\|Session 116\|\bAR-[1-7]\b\|\bDC-4\b\|origin/main" plugins/virtuoso/agents` | validator passes with the extended scan; grep empty |
| D17 | Agent memory's boundary is stated once and agents speak the project's vocabulary | test; `grep -c "feedback.log" plugins/virtuoso/agents/Plato.md` | the memory guide states the boundary; count 0; agents cite `<prefix>`, never a fixed one |
| D18 | Anchors prove rule text; the buffer counts readiness | `python -m pytest plugins/virtuoso -q -k "anchor or buffer_ready"` | `skill_rules.py` entries carry a rule-text hash the validator checks (a changed rule fails); `kpis` carries `dispatch-buffer-ready` |
| D19 | The stranded branches have an owner decision | `state.md` → Blockers | a BLOCKER(USER) with the inspection and a recommendation per branch; nothing merged without an `Answer:` |
| D20 | Contract and notes carry everything new | `python -m pytest plugins/virtuoso/scripts/test_docs_contract.py -q`; `grep -n "^## v1.10.0" RELEASE-NOTES.md` | every new command, finding, role and metric in `references/registry-contract.md` with a docs test; a v1.10.0 section |
| D21 | Green on both legs | the CI run of the final commit | ubuntu and windows both `success` |

Rules: the session claiming completion re-runs **every** row fresh and pastes the outputs
into state.md → Evidence. Any row unverified ⇒ the epic is not done. Rows may be tightened
by the user, never loosened by the executor.

## Constraints — hard limits

- All work on branch `eb/zealous-einstein-zxvy3w`; never push another branch; never
  force-push, reset, clean, or restore destructively; stage exact paths.
- Every push is green: `python plugins/virtuoso/scripts/validate.py`,
  `python plugins/virtuoso/scripts/bump_version.py --check`, and
  `python -m pytest plugins/virtuoso/ -q` pass before each commit lands on origin.
- Additive only: registry schema stays v2; rubric stays v1.1 (no new universal check);
  existing ledger rows, close-outs and lessons are never rewritten; existing KPI names
  keep their meaning (new figures get new names).
- Findings about project-owned things (overlays, deadlines, lessons, standing rules,
  policy values) are warnings or information, never errors.
- No project identifiers in shipped or test files (the validator's scan is the gate);
  no model identifiers in any repository artifact.
- Every new key, command, finding, role or metric enters `references/registry-contract.md`
  and its docs-contract test in the same commit that adds it.
- Every new gate ships with a test that holds the plugin's own templates to it.
- Every new metric has a tested *not computable* path before a computed one.
- Session budget: this session plus at most two resumes.

## Non-goals — explicitly out of scope

- Releasing (the owner runs `release.py`); deciding whether 1.9.0 ships separately.
- Merging `eb/gracious-mendel-juqys8` or `eb/charming-pasteur-9rigux` (owner decision, D19).
- New host capability vocabulary beyond the three confirmed strings.
- Changing what any agent is for, or the rubric's universal checks.
- Parsing sweep or review output into structured findings (the role and the reader are
  in scope; a parser is not).
- Touching any live project's data (the owner applies commands in their projects).

## Autonomy grants — the executor decides alone (log each call in state.md → Decision log)

- Names of commands, options, finding codes, metrics and roles.
- Test structure and fixtures; refactors under ~40 lines that enable a test.
- Order of work within a phase; splitting a gap across commits.
- Contract and release-note wording.
- Where the SWOT offers two closures for one gap, choosing the lighter one that still
  closes it — recorded in the Decision log with the alternative named.

## Escalation triggers — STOP and surface to the user

- Any action that is destructive, irreversible, or outward-facing beyond the grants above
- A DoD row that appears unachievable as written
- Reality contradicting this charter or a listed assumption's guard failing
- The session/time budget in Constraints is exhausted with DoD rows still unmet
- A closure that would need registry schema v3 or rubric v1.2
- A closure that would change an existing KPI's meaning or an existing ledger row
- Anything that would merge a stranded branch or act in the owner's live projects

When triggered: write a BLOCKER(USER) in state.md with the exact question and what it
unblocks, advance any unblocked front; if every front is blocked, append a final journal
entry and stop cleanly.

## Assumptions — gaps accepted at launch (unattended launches especially)

| Assumption | Risk if wrong | Guard |
|------------|---------------|-------|
| A1 The alternate host accepts only `Interactive`, `Read`, `Write` as capabilities | a fourth string breaks the plugin page | keep the three; escalation trigger for any addition |
| A2 The marketplace entry accepts `category`, `tags`, `author`, `homepage`, `license`, `keywords` | `/plugin` install fails on an unknown key | keep the manifest itself to documented keys; the marketplace gains only keys its documentation lists; owner confirms after the next install |
| A3 The preflight's existing roadmap read (deadlines, since 1.8.1) is the right place for the integrity line | a second read of the roadmap at session start | reuse that read; a test asserts one read |
| A4 No project relies on `dispatch-buffer-filled` counting written status | a changed figure surprises a cockpit | leave it; add `dispatch-buffer-ready` |
| A5 The registry-governed repositories using this plugin can absorb a new default role (`findings`) without a migration | `create`/`repair` add it; existing manifests without it stay valid | the role is optional in `validate`, scaffolded by `create`, offered by `repair` |
| A6 This repository is not registry-governed, so the epic lives at `docs/virtuoso/epics/` by owner convention rather than an `epics` role | none for the plugin; recorded here so the choice is visible | Decision log #1 |

## Lessons applied — the project's own history, read before the run

<!-- This repository keeps no `lessons` role (it is not registry-governed), so
     `virtuoso_registry lessons --open` has nothing to read: 0 read. The SWOT's gaps and
     the release notes' own findings stand in, and each that bears is applied below. -->

| Lesson | Bears on | Applied as |
|--------|----------|------------|
| SWOT gap 1 — a shipped specification format failed the very gate 1.9.0 added | every new gate (D2, D9–D12) | Constraint: every new gate ships with a test holding the plugin's own templates to it |
| v1.8.2 — the first real run of 1.8.1 reported a silent zero | D12, D14, D15, D18 | Constraint: every new metric has a tested *not computable* path first |
| v1.8.1 — "the docs-contract test missed it" | D20 | Constraint: contract and docs test in the same commit as the change |
| v1.5.0 — "a rule promoted into a project's lessons catalog produces documentation, not enforcement" | D9–D12 | The closures are commands with exit codes, not skill prose |
| v1.7.0 — two contradictory copies of one instruction, whichever is hit first wins | D10, D17 | Constraint: one source per rule (`policy.standingRules.source`); the memory boundary stated once |
| v1.4.0 / v1.6.0 — one authority per fact; never a raw write into a register | D9, D13 | `record-completion` writes through providers and leaves a recovery record; the findings role is registered, never a conventional path |
