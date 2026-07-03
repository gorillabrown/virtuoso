# Epic Skill — Design

**Date:** 2026-07-02
**Status:** Implemented (authored non-interactively in an autonomous session; user review of this
spec is asynchronous — see Review Notes at bottom)
**Deliverable:** `plugins/virtuoso/skills/epic/` (SKILL.md + assets templates)

## Problem

The plugin's dispatch machinery (roadmap-review → next-pointer → virtuoso → pointer-closeout)
assumes a Cowork planner writing fully-specified sprints for an implementer that makes no
judgment calls. Frontier executors (Claude Fable 5 class) invert that premise: give them the
goal, not the steps, and they can plan the path and hold multi-hour or multi-day sessions —
*if* the run is anchored by durable materials. Today nothing in the plugin produces those
materials. Ad-hoc long runs fail in three characteristic ways:

1. **Losing the thread** — context compaction or a fresh session drops the plan; the executor
   re-derives (differently) or stalls.
2. **Premature victory** — "done" is declared on vibes because no verifiable completion
   condition was ever written down.
3. **Drift or overreach** — with no recorded autonomy grants or escalation triggers, the
   executor either stops to ask about trivia or silently makes calls the user wanted to make.

## Goals

- One invocation turns a stated outcome into a complete, self-sufficient **epic packet**.
- An amnesiac future session can resume from the packet alone within minutes.
- Completion is defined by **verifiable conditions** (command + expected evidence), not prose.
- Walk-away safety: autonomy grants and escalation triggers are decided *before* the run.
- Works in any project (bare repo fine); defers to the Virtuoso workspace registry when present.

## Non-goals

- Not an executor. The skill produces materials and a launch pointer; it does not run the epic.
- Not a replacement for sprint machinery. Fully-specified dispatches stay with
  next-pointer/virtuoso; epics are for goal-scale work where the executor plans the path.
- No new hooks, scripts, or runtime dependencies.

## Approaches considered

**A. Materials-generator skill (chosen).** `/virtuoso:epic` sizes the goal, sharpens it into a
charter, and scaffolds a five-file packet from templates; any runner (a long interactive
session, a goal-mode loop, `/loop`, or a sequence of fresh sessions) executes by reading the
packet. Pros: fits the plugin's documents-as-control-plane philosophy; runner-agnostic;
testable; the discipline travels *inside* the packet so the executor doesn't need the skill
loaded. Cons: relies on executor compliance — mitigated by embedding the rules in the files the
executor must read anyway (state.md resume protocol, launch prompt contract).

**B. Executor skill.** One skill that both plans and immediately executes with an in-skill
loop. Rejected: conflates planning with running, cannot hand off to fresh sessions (the whole
point of multi-day work), and duplicates the virtuoso skill's execution-discipline territory.

**C. Extend the roadmap machinery.** Model an epic as a mega-sprint in the sprint catalog with
a full spec. Rejected: "spec every step so a low-judgment implementer cannot fail" is exactly
the premise epics invert; also drags in workspace ceremony that goal-scale work shouldn't need.

## The packet (materials contract)

Location resolution, in order: (1) an `epics` path in `Virtuoso/workspace-layout.json` if one
is registered; (2) `Project Documentation/2 operational/Epics/` when that governance tree
exists; (3) `epics/` at the project root. Directory name: `<yyyy-mm-dd>-<slug>/`.

| File | Role | Mutability during the run |
|------|------|---------------------------|
| `charter.md` | Outcome, Definition of Done (condition / verification / evidence table), constraints, non-goals, autonomy grants, escalation triggers, recorded assumptions | Frozen — only the user amends |
| `plan.md` | 3–7 phases, each = intent + verifiable exit gate + rough size; replanning rules | Executor may replan phases (logged); gates only tighten |
| `state.md` | Resume protocol first, then Now (phase / next action / working set), blockers, decision log, assumption log, gate-evidence index | Rewritten freely; always current truth |
| `journal.md` | Append-only timestamped session log | Append only |
| `launch.md` | Code-boxed kickoff prompt, code-boxed resume prompt, user monitoring guide, completion protocol | Static after scaffold |

The split matters: charter = what "done" means (stable), plan = route (replannable),
state = current truth (rewritten), journal = history (appended). Baseline testing (below)
showed that without the skill these roles collapse into one plan-ish document whose staleness
then poisons resumes.

## Skill flow (recipe)

0. **Size the request.** Epic-scale = multi-phase AND multi-session/walk-away AND goal-stated.
   Not epic-scale → say so and route (single sitting → just do it or virtuoso; fully-specified
   dispatch → sprint machinery; recurring interval → loop/schedule).
1. **Sharpen the goal into the charter.** Interactive: ask up to ~5 targeted questions,
   completion conditions first. Unattended: proceed on stated text, record every assumption in
   the charter's Assumptions section with an escalation trigger guarding the risky ones.
2. **Draft phases + gates** (goal-not-steps inside each phase).
3. **Scaffold the packet** from `assets/` templates.
4. **Hand off:** print walk-away readiness check + the code-boxed launch pointer.

## Integration

- README skills table gains an `epic` row; marketplace.json "14 skills" count → 15.
  Version bump / release left to the user's release flow.
- Cross-references (all optional, no hard dependency): virtuoso (per-burst execution
  discipline), mid-dispatch-decision (structured escalation), adversarial-review (red-team the
  charter before a very long run).
- Deliberately **no** preflight/workspace requirement, unlike governance skills — epics must
  work in projects that have never seen `/virtuoso-init`.

## Testing plan and results (TDD for skills)

- **RED:** two baseline subagents given the natural task ("produce the materials for an
  autonomous multi-day run; files are all that survive between sessions") with **no** skill —
  one code goal (test-coverage/CI/release epic), one non-code goal (Confluence→MkDocs
  migration). Findings recorded in the Baseline Findings appendix of this spec.
- **GREEN:** same scenario re-run with the authored skill on disk; output audited against the
  materials-contract checklist (verifiable DoD, resume-first state, state/journal split,
  phase gates without step prescription, autonomy grants + escalation triggers, code-boxed
  launch/resume prompts, completion protocol).
- **REFACTOR:** close observed gaps; re-test when changes are substantive.

## Risks

- **Skill bloat** → SKILL.md stays a lean recipe; the discipline lives in the templates.
- **Confusion with sprint machinery** → explicit "When NOT to use" section with routing.
- **Registry conflict** → packet location defers to `workspace-layout.json` when present; the
  skill never seeds a rival governance document.

## Literature review & ingestion decisions (2026-07-02)

Evaluated: *"Engineering Blueprint for Context-Preserving, Long-Horizon Autonomous Agents"*
(user-supplied synthesis document). **Provenance:** an AI-generated research digest of uneven
sourcing — its two load-bearing arXiv papers were verified real and accurately represented
(CMA, arXiv:2601.09913; MAGE execution-state memory, arXiv:2606.06090; CoALA is likewise
real), while its implementation blueprints cite mostly vendor/blog content. Mechanisms were
therefore judged on fit against this skill's tested design, not on source authority.

**Tier boundary (the key finding):** the document targets weeks-to-months agent *platforms*
(PostgreSQL+pgvector memory tiers, nightly consolidation jobs, Docker sandboxes, webhook HITL
portals, RL credit assignment). The epic packet is a zero-infrastructure, hours-to-days
*artifact*. Mechanisms translate; infrastructure does not. The packet's file-tier memory is
the right instrument up to roughly days-scale/dozens-of-sessions; past that, the document's
database tier becomes the right answer. That boundary is now explicit.

**Validates the existing design (no change):** execution-state memory over semantic retrieval
(structured role-separated files + deterministic resume order ≙ MAGE's state-tree reading);
POMDP belief-state correction ≙ distrust-then-verify / files-are-memory-reality-wins; goal
externalization + session re-anchoring ≙ state.md + resume protocol; write-gated facts ≙
curated Working set with HEARSAY marking; temporal validity ≙ "Verified how/when" + freshness
rule; CoALA's four memory classes all have file homes (working→state, episodic→journal,
semantic→working set, procedural→charter). The frozen-charter/mutable-state split *outperforms*
the document's own merged state file against its #1 failure mode (summarization drift diluting
goals held in a mutable file).

**Ingested (document-tier translations; applied after the in-flight GREEN run):**
1. Phase-gate re-anchor — re-read charter at every gate (counter: summarization drift).
2. Context hygiene — distilled results only in durable files; push noisy exploration into
   subagents where available (counter: attention dilution / "projection functions").
3. Session counter + budget in state's Where-we-are block, with a budget-exhausted escalation
   trigger example (their token-budget metadata, right-sized).
4. Working set explicitly includes hard-won gotchas/lessons (counter: memory blindness).
5. Structured BLOCKER(USER) with an `Answer:` slot the user fills inline + monitoring
   instruction — closes the async human loop with zero infrastructure (their inbox/outbox
   pattern, de-platformed).
6. Preflight row: runtime can act unattended — permission mode/allowlist covers the run's
   tool needs so no interactive prompt stalls the walk-away run (their IAM tier, translated;
   a real failure neither baseline could surface).
7. Charter constraints example nudges branch/worktree isolation for code epics.

**Rejected, with reasons:** database/vector/consolidation infrastructure and Letta-style
memory blocks (wrong tier, violates zero-dependency non-goal; day-scale analogs already
present); Docker/egress sandboxing (enforcement belongs to the harness's permission system —
a markdown packet claiming to sandbox would be false security; the charter states *policy*,
the runtime enforces); HiPER/RL credit assignment (training-time concern, inapplicable to an
inference-time artifact); CI golden-dataset gates per epic (the skill itself is tested via the
TDD-for-skills cycle; per-epic eval pipelines are disproportionate); webhook/tokenized-URL HITL
portals (the Answer-slot mechanism achieves the loop file-locally); the "value-alignment slip"
mitigation *as framed* ("frame instructions opposing safety rules as context-specific
exceptions to prevent the model defaulting to standard behavior") — the legitimate kernel
(explicitly record user-authorized exceptions so behavior is consistent) is already the
charter's constraints/autonomy-grants job; language engineered to talk an executor out of
safety defaults is not adopted.

## Verification outcome (2026-07-03)

- **GREEN-A (code goal, pre-ingestion skill):** PASS — exactly the five-file packet at the
  resolved location (`epics/2026-07-02-chronicle-v1-release/`), sizing verdict stated, honest
  preflight (all repo-dependent checks FAIL → charter assumptions A1–A8 with guards),
  launch-blocking questions surfaced before user departure with hard-blocker vs
  proceed-on-default split. ~84k tokens / 13 tool calls; no speculative tooling.
- **GREEN-B (docs-migration goal, post-ingestion skill):** PASS — five files at
  `epics/2026-07-02-confluence-to-mkdocs/`; all ingested mechanisms bound in output
  (`session: 0 of ~8 budgeted`, gotchas clause, HEARSAY marking, Answer slots on Q1–Q5,
  unattended-permissions warning operationalized into a concrete allowlist). 72.6k tokens vs
  its 171k baseline on the same goal (−58%), toolchain correctly deferred to phase 1.
- **Frontmatter:** 951 chars after trim (limit 1024). Plugin integration: README skills-table
  row + marketplace description 14→15 skills. Versions untouched by design.

## Review Notes (async)

Authored while the user was away, per the walk-away request. Decisions the user may want to
revisit: skill name (`epic`), packet location default (`epics/` at project root), and whether
to register epics as a first-class role in `Virtuoso.Governance.Readme.md` (deferred — the
skill only *reads* the registry for now). Version bump intentionally not performed.

## Appendix: Baseline findings (RED)

Two baseline subagents were given the natural task with no skill. Outputs live in the session
scratchpad (`baseline-a/`, `baseline-b/`).

**Baseline A (code goal — coverage/CI/release epic): high quality, with structural gaps.**
Produced 9 files (~48KB): entry-point orientation, mission contract with per-criterion
verification commands and evidence rules, short always-current state with freshness rule,
append-only journal, discovery-generated backlog, facts file with UNKNOWN discipline, decision
log, playbook, runbook. Strong ideas adopted into the skill's templates: completion-marker file
with "if it exists, verify instead of working" semantics; evidence must be re-run fresh in the
claiming session; files-are-memory/repo-is-reality rule; never-idle + BLOCKER(USER)-with-exact-ask
format; crash-safety cadence ("disk handoff-ready at all times").

Verified gaps (what the skill must add):
1. **No user-side materials.** Nothing says what the user should paste to launch or resume a
   session, how to monitor progress at a glance, or when to intervene. Executor-facing only.
2. **No walk-away preflight.** Launch-blocking unknowns were deferred into the run itself —
   the repo's location was left as task T-001 with a mid-run "BLOCKER(USER)" fallback, i.e. the
   first unattended action could dead-end on a question the user could have answered in seconds
   at launch. Ditto credentials (`gh` auth checked reactively, not before the user leaves).
3. **Bespoke shape.** 9 files with invented names/roles; a second epic would produce a
   different layout (confirmed against Baseline B). No cross-epic consistency for the user,
   resume prompts, or downstream tooling.
4. **Role overlap tax.** Binding policies were spread across three files (mission hard
   policies, golden rules, decision log), so "may I do X?" requires consulting all three.
5. **Sizing judgment not exercised** — the scenario was pre-sized as an epic; the skill must
   also decide epic-vs-task and scale the packet accordingly.

**Baseline B (docs-migration goal): equally strong, completely different shape.**
Produced 22 files: prose kit (README/GOAL/PLAN/PLAYBOOK/DECISIONS/JOURNAL) plus a Python
acceptance harness (`verify.py`, exit 0 = done), five more tools, templates, a pre-provisioned
`.venv`, and a paste-ready kickoff prompt — validated end-to-end on a synthetic fixture.
Adopted into the skill: the single kickoff-doubles-as-resume prompt; machine-parseable
state block; "exit 0 = done" thinking folded into the DoD verify column.

Verified gaps B adds to A's list:
6. **Shape divergence confirmed** — A: 9 prose files, `STATE.md`, mission-control style;
   B: 22 files, `STATE.json`, tooling-kit style. Near-zero structural overlap between two runs
   of the same task. Without a contract, every epic invents its own layout.
7. **Scaffold cost unbounded** — B spent ~171k tokens / 28 minutes / 44 tool calls *preparing*,
   including speculative conversion pipelines written for an export it had never seen (the same
   steps-before-knowledge instinct as A's backlog, expressed as code). Packet production should
   be minutes of document writing, not a mini-project.
8. **Walk-away preflight absent in both** — B's `STATE.json` ships `"project_root": null` with
   "locate the export" as Phase 0, and its kickoff prompt forbids asking the user questions
   without defining any escalation contract in exchange.

**RED verdict:** don't spend skill tokens re-teaching what capable executors already do well
(verifiable criteria, amnesia orientation, journaling, decision logs) — pin those structurally
via templates. Spend the skill's prose on the verified gaps: canonical shape, walk-away
preflight, user-side launch/monitor/completion materials, goal-altitude planning, and a
scaffolding budget.
