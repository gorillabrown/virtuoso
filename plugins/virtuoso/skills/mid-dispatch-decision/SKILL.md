---
name: mid-dispatch-decision
description: "Decision protocol for when a Virtuoso execution (Zeus) pauses mid-dispatch and routes a structured issue. Primary input: a path to an issue file under the manifest `issues` directory — the 7-field issue document produced by the virtuoso skill. Reads the issue, produces a recommendation and a worker-pasteable instruction block, appends a Decision block to the issue file, and amends the dispatch spec. Trigger on: \"mid-dispatch decision\", \"decision needed\", \"escalation decision\", \"what should I tell the implementation agent\", \"the implementation agent is stuck\", a virtuoso issue path, or any pasted execution output showing a paused dispatch awaiting direction."
---

<!-- virtuoso-shared-contract v2 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — `Virtuoso/workspace-layout.json` is the authority; `Virtuoso.Governance.Readme.md` is its synchronized human view. Resolve every document, work item, and permission through the registry. Never hardcode a path, never fall back to a conventional one, and never infer authority from a role's name. Full contract: the plugin's `references/registry-contract.md`.
- **Read-only preflight** — session start and any "where am I" check runs `--mode check`, which performs **zero project writes**. Adoption, creation, and repair are separate operations, each explicitly invoked.
- **Providers** — work items come from the configured work-register provider (local file, spreadsheet, connector-backed task manager, issue tracker, database, or read-only snapshot). Negotiate capabilities before planning work; never open a register file directly. The live work register, the append-only terminal ledger, and any compatibility export are three different roles.
- **Provenance** — every derived figure cites its provider, source, and snapshot time. A figure whose inputs are missing is reported as *not computable* with the missing inputs named, never approximated.
- **Git** — behaviour is `policy.git`, not a fixed rule of this plugin. See `references/git-policy.md`. Under every policy: inspect first, stage exact paths, preserve unrelated work, no destructive flags, no force-push without explicit authorization.
- **Readiness** — one shared, versioned rubric: `references/readiness-rubric.md` (its universal checks, at the version it declares, plus the project's declared extensions). No skill restates it in its own words.
- **Actors** — roles from `policy.actors`: planner, implementation agent, reviewer, repository operator. Never a product, vendor, or model name. See `references/actors-and-interaction.md`.
- **Issue contract** — any stop, hold, block, or elevation becomes an issue document, routed per `policy.issues.targets` (local file, external tracker, or both).
- **Effort levels** — low / medium / high / xhigh / max. A property of the task's difficulty, never a ranking of whoever performs it.

<!-- virtuoso-overlay-clause v2 -->
**Project overlay.** If the registry declares an `overlays` role, read the overlay mirroring
every shipped file you read beneath it — this file at its own path (`skills/<skill>/SKILL.md`,
`agents/<Agent>.md`) and any `references/<file>.md` this one sends you to — and apply each on
top of the file it mirrors. Resolve them with the registry helper's `overlays` subcommand;
never fork or edit a shipped file to carry a project's rules. An overlay is additive and
wins on conflict, with one exception: it may not loosen a shared-contract safety rule
(registry resolution, read-only preflight, write permission, git safety, provenance, the
issue contract), and `references/registry-contract.md` may not be overlaid at all. No
`overlays` role, an absent overlays directory, and no matching overlay file all mean the
same thing — proceed on the shipped file alone.

# Mid-Dispatch Decision

## Preflight — read-only registry check (run first)

Resolve the plugin through its launcher, then run the **read-only** check. It performs
discovery and validation with zero project writes.

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check

Add `--json` when you want the structured result (status, writes, findings, and the full
resolved role table). Read the `virtuoso-status:` line and branch:

- `ready` — the registry is valid. Continue.
- `warning` — usable; surface the findings to the user and continue. Warnings are not blockers.
- `repair-needed` — **STOP.** Run `--mode repair` to produce the preview, show the user the
  proposed paths, semantic changes, files affected, and backup location, and apply it only
  with `--apply` after they approve.
- `adoptable` — the project has governance documents but is not registered. Offer
  `--mode adopt`: it registers what exists, in place. Nothing is moved, duplicated, or rewritten.
- `none` — no registry and nothing to adopt. Route the user to `/virtuoso-init`.
- `failed` — report the error verbatim and stop.

If neither launcher resolves, report that the plugin could not be located and stop. Do not
guess a path.

**Governance authority.** Resolve every document you need through the registry
(`references/registry-contract.md`). Never create a parallel document for a registered role;
never write to a role whose `allowedWriters` does not name this ceremony; never treat a
`mirror`, `report`, `archive`, or `unknown` role as truth.

A Virtuoso execution (Zeus) has paused mid-dispatch and routed a structured issue. **Your
primary input is a path to an `Issue.*.md` file under the manifest `issues` directory** — the
7-field issue document the virtuoso skill produced. Read it first, bring the planner's
context to the execution state, and recommend a path; after user confirmation, print a
worker-pasteable block, append a `## Decision` block to the issue file, and amend the
dispatch spec and lessons. (Given raw pasted output instead — legacy fallback — reconstruct
the 7 fields first.)

**Announce at start:** "Mid-dispatch decision engaged — loading context for [dispatch ID]."

**Why.** The implementation agent has execution context but lacks planning context
(adjacent dispatches, lessons); the planner has the inverse. This skill bridges them.
Advancing when you should pivot wastes budget and propagates bad baselines; stopping when
you should advance abandons 80%-done work.

**The pause is a wait on the owner.** The paused row's clock waits with the reason `owner`
(`timing --dispatch <dispatch-id> --wait N --reason owner`), so the decision's time stays out
of its working time. The instruction block opens with
`timing --dispatch <dispatch-id> --resume N` before the first action it directs.

---

## Brevity and Plain Language

**Be succinct.** Read everything, reason thoroughly, present in the fewest accurate words —
the implementation agent is waiting. Step 5 fits one screen (drop any justification point
that doesn't change the decision); Step 6 is as short as the implementation agent needs.
Under ULTRATHINK too: deep *thinking*, not deep *output*. Don't rush, don't pad: five minutes
of context loading prevents thirty of wrong-direction work; then earn agreement with
clarity, not volume.

**Step 5 is plain language.** The user, under time pressure, must follow the situation,
levers, risks, and decision **without opening any other document**; if they must look
something up, the recommendation has failed.

- **No acronyms, no identifiers as proxies for ideas** — no rule or lesson numbers
  (SRL-XXX), run IDs (CAL-XXX), dispatch IDs (SK-01B, FAS-1, IFG), FP-XX, or codenames.
  Not "Rule 100 supports re-banding" but "when the underlying behaviour changes, the targets
  we tuned against the old behaviour are no longer the right targets — that argues for
  re-banding."
- **Self-contained, succinct, complete.** Paraphrase any decision-relevant reference; cut
  every paragraph that doesn't change the decision — but every decision-relevant lever,
  touch-point, risk, or downstream effect keeps one tight sentence.
- **Identifiers, file paths, line numbers, and agent names go in the instruction block
  (Step 6a)** unless an exact location is load-bearing for the decision itself.

---

## Decision Types

Seven, defined in [references/decision-types.md](references/decision-types.md) (read at
Step 3): **1a** Advance (Pre-Authorized) · **1b** Advance (Planner-Originated) · **2**
Advance with Narrowing · **3** Pivot Advance · **3a** Revise Routing / Effort · **4** Pivot
Stop and Regroup · **5** Verify First.

**Type 4 partial close-out contract.** Type 4 triggers dispatch-closeout immediately with:
(a) completed tasks as the deliverables, (b) cancelled tasks listed with reason
"mid-dispatch pivot," (c) the pause-point finding that triggered the stop in its findings
table, (d) the stopped line of work sent back to `/roadmap-review` to be re-planned
(`/next-dispatch` escalates there when no head is dispatch-ready). Step 2's assessment serves
as the pause summary; no full one is needed.

---

## Workflow

### Step 0 — Depth Selection

Ask the user:

> **How deep should I go?**
> - **Fast** — pause report + dispatch spec only. ~2-3 min.
> - **Deep** — Full context load (roadmap, lessons learned, close-outs). ~5-10 min.

**Default to Deep** when non-trivial (unexpected finding, several viable paths, any Type
3/4/5 candidate). **Fast** only when the dispatch pre-authorized this exact response and the
implementation agent's analysis confirms it applies cleanly; escalate to Deep mid-analysis
if the decision proves more complex.

### Step 1 — Load Context

**Fast:** the **pause report** (what happened, current state, the implementation agent's
analysis and options) and the **dispatch spec** (what was supposed to happen, pre-authorized
paths, scope fences). Never decide without the spec — the answer may already be there.
**Deep** adds the **roadmap** (downstream dependencies; the baseline later dispatches
measure against), the **dispatch queue** (what's next; whether this decision changes its
order), **lessons learned** (prior occurrences; standing rules that apply), and **recent
close-outs** (prior findings; constraints carried forward).

**Search lessons by keyword**, not linearly: calibration drift → "drift", "threshold",
"escalation"; budget → "budget", "overrun", "sizing"; unexpected → "discovery",
"hypothesis"; scope → "scope", "expansion", "pre-authorized". **Pre-authorization lookup:**
don't enumerate patterns here — they go stale. Search the live lessons
(`virtuoso_registry --root . lessons --open`, the registered `lessons` role) for the ones
governing this decision surface (escalation thresholds, pre-committed decision rules,
trip-gate clauses, mechanism-class criteria). The lessons catalog is authoritative.

**Staleness check (Deep only).** Spend thirty seconds comparing modification dates on the
operational docs directory and the registered lessons document
(`virtuoso_registry --root . resolve lessons`) with the last known planner-session timestamp;
surface anything touched since — a new standing rule or roadmap revision could flip the
recommendation. **Do not use git** (no `git log`, `git status`, or any git command against
the project directory); filesystem timestamps are the only freshness signal.

### Step 1.5 — Disambiguation (if needed)

If the pause message does not map cleanly to a decision — three observations without naming
the blocker, or a vague "not sure what to do" — ask the implementation agent (via the user)
to restate: "What specific decision do you need? Which task is blocked and what are the
options?" Do not proceed on a decision you cannot classify.

### Step 2 — First-Principles Situation Assessment

**Read [references/situation-assessment.md](references/situation-assessment.md) now** and
walk all five sub-steps: objective, assumptions, challenge, first principles, reconstruction
— only then compare with the spec's pre-authorization; a divergence is the finding. Never
rubber-stamp a pre-authorization. The output is internal reasoning. If Step 1 surfaced a
trigger listed there, the Step 6a instruction becomes **conditional direction**
(check-then-act).

### Step 3 — Decision Classification

**Read [references/decision-types.md](references/decision-types.md) now** — what each type
means. Then walk this tree. Take the first match.

```
1. Did the dispatch pre-authorize a response for this exact situation?
   ├── YES: Does the pre-authorization still apply given what the implementation agent found?
   │   ├── YES → Type 1a (Advance — Pre-Authorized)
   │   └── NO → Continue to step 2
   └── NO → Continue to step 2

2. Is the measurement itself suspect? (See valid suspicions list below.)
   ├── YES: Is the strategic decision load-bearing on this measurement?
   │   ├── YES → Type 5 (Verify First)
   │   └── NO → Continue to step 3
   └── NO → Continue to step 3

3. Is the fundamental direction still correct?
   ├── YES: Is it an agent-routing or effort-level problem only?
   │   ├── YES → Type 3a (Revise Routing / Effort)
   │   └── NO: Does remaining scope need reduction?
   │       ├── YES → Type 2 (Advance with Narrowing)
   │       └── NO → Type 1b (Advance — Planner-Originated)
   └── NO → Continue to step 4

4. Can the implementation agent productively continue with a revised direction?
   ├── YES → Type 3 (Pivot Advance)
   └── NO → Type 4 (Pivot Stop)
```

**Mandatory alternative-frame test.** Before finalizing, state what the *next type down*
looks like and why you reject it — this stops the comfortable choice (usually Type 1, "just
keep going") when the situation warrants a pivot. 1a/1b: show Type 2 or 3, and why the full
advance is better. 2: why not Type 1; what Type 3 looks like. 3: why Types 1/2 fall short;
what Type 4 looks like. 4: what Type 3 looks like, and why even a pivot isn't productive.
5: what Type 1a (trust the measurement and advance) looks like, and why the gate is worth
the delay.

#### Valid Measurement Suspicions (for Type 5 gating)

Accept the numbers unless one of these applies; "they seem off" is not grounds for Type 5,
and Type 5 is never a comfort move to delay a hard decision.

1. **A single-seed result contradicts a prior close-out** on the same code state.
2. **It violates the spec's declared ESCALATE criteria** in a way suggesting instrumentation
   error (e.g. a metric moves in the impossible direction given the change).
3. **Impossible delta** — larger than the change could plausibly produce.
4. **Cadence doesn't match the mechanism class**, where a standing rule in
   `policy.standingRules` says so — cite it by the project's own identifier (e.g. a
   structural change measured with a constants-only N=200 gate).
5. **It differs from the baseline calibration run on the same code state** — same code,
   different numbers, no intervening change.

### Step 4 — Cost-Benefit Analysis

For each viable type (minimum two — the recommended and the best alternative):

```
Type [N]: [Name]
  What happens next: [Specific actions]
  Cost: [Time, tokens — be concrete]
  Risk: [What goes wrong if this is the wrong call]
  Downstream impact: [Effect on next 2-3 dispatches]
```

If over budget, state the position: budgeted vs. consumed vs. remaining. Over-budget is a
factor, not a veto — marginal work must justify marginal cost.

### Step 5 — Recommendation

**Read [references/recommendation-format.md](references/recommendation-format.md) now** —
the template (Problem / Opportunity, at least two Alternative Solutions, Recommended Way
Forward, Justification). Plain-language rules apply.

Be opinionated; "it depends" is not a recommendation. If the evidence doesn't favor one
option, choose the better cost-of-being-wrong profile and say so. Cite evidence — (a) a
pause-message finding, (b) the spec's pre-authorization or scope fence, (c) the downstream
dependency chain, (d) matching prior patterns or standing rules — paraphrased here,
identified in the instruction block. No evidence means not enough analysis.

**Bundled pauses.** Several decision points at once (e.g. two authorization flags) are NOT
collapsed: each gets its own Problem / Opportunity, Alternatives, Recommended Way Forward,
and alternative-frame test; one instruction block at the end lists all instructions in
execution order. **Independence rule:** if A's outcome changes B's viable options, they are
not independent — handle A, get the implementation agent to the next pause point, then B.

**Before presenting, check the recommendation against
[references/anti-patterns.md](references/anti-patterns.md)** — and check again before
persisting in Step 6.

### Step 5.5 — Cross-Worktree Conflict Surface Check

Skipped for Type 4 (no cross-worktree timing gap) and for a worktree-resident dispatch
(Path A: no main governance edits). **Otherwise, read
[references/conflict-surface-check.md](references/conflict-surface-check.md) before the
instruction block or any persisting** — three conditions; when all hold, the Recommendation
names the conflict and its mitigations, and the user chooses one before anything is
persisted.

### Step 6 — Confirm and Execute

**Produce ONLY after the user confirms** — recommend first, wait for explicit assent. Then,
in order:

#### 6a. Implementation-Agent Instruction Block (print first)

The user pastes it immediately. **Read
[references/instruction-blocks.md](references/instruction-blocks.md) now** — the fields each
type carries, the per-type templates, and the conditional-direction wrapper. First person,
minimal, specific; a Type 3 block always carries the full revised task plan.

#### 6b. Amend the Dispatch Spec (hard execution) — uses virtuoso's governance staging file

Not optional. The planner **must execute an Edit call** and confirm the edit landed; the
workflow does not end until the amendment is persisted. **Read
[references/amendment-paths.md](references/amendment-paths.md) now** — both paths, their
templates, and the Amendment Registry.

- **Path A — worktree-resident dispatch:** a fold-in in the dispatch's staging file
  (`Memo.<dispatch-id>.GovernanceStaging.<YYYY-MM-DD>.md`), never the inline spec — virtuoso
  forbids worktree edits to main governance documents.
- **Path B — planner-side, canonical main:** Step 5.5 first, then the amendment inline in the
  spec, always with its Close-Out Preservation field.
- **When in doubt, Path A.** Every amendment adds an Amendment Registry row.

#### 6c. Update Lessons Learned (hard execution when warranted)

If the decision produced a reusable lesson, the planner **must execute the append** to the
registered `lessons` role — not just describe it. **Update when** the pre-authorization was
wrong or incomplete; the decision was a pivot (Type 3, 4, or 5 — the original plan was off);
a standing rule was invoked and found insufficient; or the same pattern appeared before
(check for promotion). **Skip when** a straightforward Type 1a followed the
pre-authorization exactly, or an existing lesson already captures it.

**If updating:** append an entry under the next identifier
(`virtuoso_registry --root . closeout --item <ID> --date <date>` resolves `nextLessonId`) in
the standard shape — dispatch-closeout's `references/spec-retro-format.md` — and check the
promotion rules. Print: "Added <prefix>-NNN to the lessons: [one-line summary]."
**If skipping:** print "No new lesson — [reason]."

#### 6d. Record the Decision in the Issue File (always)

The issue file is the durable record of what was decided; the chat is not. Append this block
to the end of the issue file you were handed — append-only: a later decision on the same
issue appends another block beneath it, never an edit.

```markdown
## Decision — YYYY-MM-DD

- **Type:** [1a / 1b / 2 / 3 / 3a / 4 / 5] — [name]
- **Decided:** [the recommendation adopted, or the user's override, in one sentence]
- **Instruction:** [the first line of the 6a block]
- **Amendment:** [staging file path, or "inline in the spec", or "none"]
- **Lessons:** [<prefix>-NNN appended in 6c, or "No new lesson — reason"]
```

An issue with no `## Decision` block is an open decision. `dispatch-closeout` reads each of
the item's issue files at close-out and will not treat one without a block as settled.

Print confirmation: "Recorded the decision in [issue file]."

**Decision trail.** The 6a "Why" and "For the close-out" fields, the 6b amendment, and this
block are the permanent record: a future close-out session must be able to reconstruct the
reasoning from them alone.

---

## Integration with Other Skills

- **Dispatch-closeout** — Type 4 triggers a partial close-out at once (contract under
  Decision Types); for Types 1-5, the 6b amendment informs the eventual close-out.
- **Adversarial review** — offer it when the analysis rests on a hypothesis that, if wrong,
  flips the decision type; if it proves fragile, push toward Type 5 or 4, and say what to do
  with the review's output.
- **ULTRATHINK** — Steps 2-5 at maximum depth; Step 6 stays concise.
  Escalate to `/ultrathink` when the decision is genuinely hard, not merely consequential: the
  classification keeps flipping between two candidates, the options trade off on axes with
  no common unit (correctness vs. throughput vs. schedule), or the recommendation rests on an
  assumption nobody has stated (its assumption archaeology surfaces it). A high-stakes but
  structurally obvious decision does not need it — recommend and move.
- **Effort levels / Virtuoso** — see Step 6a (effort, task-plan reprint) and Step 6b Path A
  (virtuoso's Worktree Governance Staging, §Rule 5).

---

## Worked Example

[references/example-sk01b.md](references/example-sk01b.md) walks through the SK-01B
calibration drift decision (Type 1a — advance with pre-authorized full-cal). Its agent names
are project-specific; adapt them to your project's roster.
