---
name: mid-dispatch-decision
description: >
  Decision protocol for when CLI pauses mid-sprint. Produces a recommendation,
  then a CLI-pasteable instruction block and amends the dispatch spec. Trigger on:
  "CLI is stuck", "decision needed", "escalation decision", "what should I tell CLI",
  or any pasted CLI output showing a paused sprint awaiting direction.
---

# Mid-Dispatch Decision

CLI has paused mid-sprint and needs direction. Your job: bring Cowork's planning
context to CLI's execution state, recommend a path, and — after user confirmation —
print a CLI-pasteable block and amend the dispatch spec and lessons learned.

**Announce at start:** "Mid-dispatch decision engaged — loading context for [sprint ID]."

---

## Brevity Rule

**Be succinct.** Deep analysis does not mean long output. Read everything, reason
thoroughly, present in the fewest words that preserve accuracy. CLI is waiting.

- Step 5 (recommendation): one screen. If a justification point doesn't change
  the decision, drop it.
- Step 6 (CLI block): as short as CLI needs to act.
- Applies even when layered with ULTRATHINK. Deep *thinking* required; deep
  *output* is not.

### Plain-Language Rules (Step 5 only)

The recommendation is for the user under time pressure. They must understand the
situation, the levers, the risks, and the decision **without opening any other
document**. If a reader needs to look something up to follow the recommendation,
the recommendation has failed.

- **No acronyms.** No SRL-XXX, no CAL-XXX, no sprint IDs (SK-01B, FAS-1, IFG, etc.),
  no FP-XX, no internal codenames. Any concept currently invoked by acronym must be
  paraphrased in plain terms.
- **No identifiers as proxies for ideas.** "SRL-100 supports re-banding" is wrong.
  "When the engine's underlying behavior changes, the targets we calibrated against
  the old behavior aren't the right targets — that argues for re-banding" is right.
  The idea carries the weight; the identifier doesn't appear in the recommendation.
- **Self-contained.** The user must not have to reference other documents to
  understand the decision.
- **Succinct.** Cut filler. State the crux. No paragraph survives that doesn't
  change the decision.
- **Complete.** Brevity does not waive accuracy. If a lever, touch-point, risk, or
  downstream effect is decision-relevant, it gets one tight sentence. It does not
  get cut for length.
- **File paths and line numbers go in the CLI block, not the recommendation,**
  unless the exact location is load-bearing for the decision itself.

Sprint IDs, SRL numbers, file paths, and agent names belong in the **CLI block**
(Step 6a), not the Recommendation. CLI's audience knows the codes; the user, under
time pressure, should not have to translate them.

---

## Why This Skill Exists

CLI has execution context (what happened, what the numbers say) but lacks planning
context (how this connects to adjacent sprints, what lessons learned say). Cowork
has the inverse. This skill bridges the two. The cost asymmetry is extreme:
advancing when you should pivot wastes budget and propagates bad baselines;
stopping when you should advance abandons 80%-done work.

---

## Decision Types

Seven types across three axes: same direction vs. new direction, continue vs.
stop, and a verification gate that defers the strategic decision entirely.

### Type 1a — Advance (Pre-Authorized)

The dispatch spec pre-authorized a response for this exact situation. CLI's
findings confirm the pre-authorization still applies. Confirm and go.

**CLI block format:** Decision + constraints + why. Minimal — the spec already
said what to do.

### Type 1b — Advance (Cowork-Originated)

No pre-authorization exists, but the direction is right and the remaining scope
is correct. Cowork authors the direction CLI didn't have.

**CLI block format:** Decision + direction + scope + constraints + why. Fuller
than 1a because CLI has no spec language to fall back on.

### Type 2 — Advance with Narrowing

Same direction, reduced scope. Budget, focus, or new information justifies
doing less.

**CLI block format:** Decision + direction + what's narrowed + where deferred
work goes (next sprint, parking lot, dropped) + constraints.

### Type 3 — Pivot Advance

CLI continues but does *different work* than planned. Cowork authors a
mini-dispatch-revision in real time.

**CLI block format:** Decision + what to skip + revised task plan (new task
numbers, agent assignments, model tiers, effort levels, done-when) + constraints.
When Type 3 fires, use the effort-levels Task Type Reference Table to size new
tasks, and flag that virtuoso's execution discipline applies to the revised plan.

### Type 3a — Revise Routing / Effort (Same Plan)

The remaining work is valid and the direction is correct, but agent routing or
effort allocation is wrong (e.g., a task dispatched to sonnet/medium needs
opus/high). Revise annotations, continue.

**CLI block format:** Decision + which tasks change + new `[agent] {effort}`
annotations. Keep task IDs and done-when unchanged.

### Type 4 — Pivot Stop and Regroup

CLI stops. Completed work preserved; remaining tasks cancelled. Cowork runs a
partial phase-closeout, then authors a new dispatch.

**CLI block format:** "Stop the dispatch. Preserve completed work from tasks
#1-N. Cancel remaining tasks. I'll send a new dispatch from Cowork."

**Partial close-out contract:** When Type 4 fires, Cowork invokes phase-closeout
with these inputs: (a) completed tasks treated as the sprint's deliverables,
(b) cancelled tasks listed with reason "mid-dispatch pivot," (c) the close-out's
findings table includes the pause-point finding that triggered the stop,
(d) the next pointer enters Case C (brainstorm). Phase-closeout does not need
a full CLI summary — the mid-dispatch decision's Step 2 assessment serves as
the summary input.

### Type 5 — Verify First

CLI's findings are surprising and the correct strategic decision depends on
whether the measurement is real. Instead of choosing a direction now, dispatch
a narrow verification task, defer the decision until results land.

This is distinct from Type 3 — you aren't pivoting strategy; you're gating
strategy on verification. The remaining plan pauses (not cancelled) while
verification runs.

**CLI block format:** Decision + verification task (agent, what to check,
done-when) + "pause remaining plan until verification lands, then come back
for direction."

**When to use:** The measurement is load-bearing for the decision AND at least
one of the valid measurement suspicions (below) applies.

---

## Workflow

### Step 0 — Depth Selection

Ask the user:

> **How deep should I go?**
> - **Fast** — CLI pause message + dispatch spec only. ~2-3 min.
> - **Deep** — Full context load (roadmap, lessons learned, close-outs). ~5-10 min.

**Default to Deep** if the situation is non-trivial (unexpected finding, multiple
viable paths, any Type 3/4/5 candidate). **Fast** only when the dispatch
pre-authorized this exact response and CLI's analysis confirms it applies cleanly.
Fast can escalate to Deep mid-analysis if the decision turns out more complex.

### Step 1 — Load Context

#### Fast Mode

| Source | What to Extract |
|--------|----------------|
| **CLI pause message** | What happened, current state, CLI's analysis, options CLI sees |
| **Dispatch spec** | What was supposed to happen; pre-authorized paths; scope fences |

#### Deep Mode

All of Fast, plus:

| Source | What to Extract |
|--------|----------------|
| **Roadmap** | Downstream dependencies; what baseline subsequent sprints measure against |
| **Sprint queue** | What's queued next; whether this decision affects queue order |
| **Lessons learned** | Prior occurrences of this pattern; standing rules that apply |
| **Recent close-outs** | Prior sprint's findings; constraints carried forward |

**Keyword search for lessons learned** (don't read linearly):
calibration drift → "drift", "threshold", "escalation";
budget → "budget", "overrun", "sizing";
unexpected → "discovery", "hypothesis";
scope → "scope", "expansion", "pre-authorized".

**Pre-authorization lookup:** Don't enumerate patterns here — they go stale.
Instead, search the live `SpecRetro.Lessons_Learned.md` for SRLs that govern
the specific decision surface (escalation thresholds, pre-committed decision
rules, trip-gate clauses, mechanism-class criteria). The SRL catalog is
authoritative; this skill defers to it.

#### Staleness Check (Deep mode only)

Before analyzing, run a 30-second freshness check: compare file modification
dates on the operational docs directory and `SpecRetro.Lessons_Learned.md`
against the last known Cowork session timestamp. If anything was touched since
the last session, surface it — a new standing rule or roadmap revision could
flip the recommendation.

**Do not use git.** This skill does not invoke `git log`, `git status`, or any
other git command against the project directory. Filesystem timestamps are the
only freshness signal.

### Step 1.5 — Disambiguation (if needed)

If CLI's pause message does not map cleanly to a decision — e.g., three
observations without identifying which is the blocker, or a vague "not sure
what to do" — produce a short response asking CLI (via the user) to restate:
"What specific decision do you need? Which task is blocked and what are the
options?" Do not proceed on a decision you cannot classify.

### Step 2 — First-Principles Situation Assessment

Reason from foundations, not from analogy. The dispatch spec, the pre-authorization,
and even CLI's own framing carry assumptions. Strip them and rebuild. This step
prevents the most dangerous failure mode: rubber-stamping a pre-authorized response
because pattern-matching is comfortable. The spec's framing is the starting point
for analysis, never its conclusion.

**1. Define the objective.** State what the sprint is actually trying to achieve in
goal terms — independent of how the spec framed the work. Not "what the spec says
to do," but the underlying engineering or product outcome the work is supposed to
produce. If the goal is unclear from the spec, infer it from the roadmap or ask
the user.

**2. Catalog assumptions.** List what the dispatch spec, the pre-authorization, and
CLI's own analysis are taking for granted. Surface them explicitly. Common
categories: the measurement apparatus is correct; the pre-authorization's threshold
is the right gate; CLI's hypothesis about cause is correct; the downstream baseline
is what we think it is; the spec's scope fence still holds.

**3. Challenge each assumption.** For each item in the catalog, mark it as
*foundational* (irreducible — measurements are what they are, the goal is what it
is, the code does what it does) or *conventional* (we usually handle this kind of
thing this way). Conventional assumptions are negotiable; foundational ones are
not. Apply Socratic questioning to every conventional assumption: is it true here,
or is it inertia?

**4. Identify the first principles.** With conventions stripped away, what is
actually true about the situation? What are the real levers, real constraints,
real signals — independent of how the spec or CLI framed them? In an engineering
context, this often reduces to: what does the code do, what does the data say,
what does the user actually want.

**5. Reconstruct the optimal response.** Build the response ground-up from the
foundational truths. Then — and only then — compare that reconstruction against
the spec's pre-authorization. The pre-authorization passes the test only if it
matches what first-principles construction produced. If they diverge, the
divergence is the finding, and Step 3's classification turns on it.

**Output of Step 2 is internal reasoning, not user-facing.** The user-facing
output is Step 5's Recommendation, which presents the *conclusion* of this
analysis in plain language — not the analysis itself. Show your work to yourself,
not the user.

#### Conditional CLI Direction (when Step 1 surfaces analysis-affecting context)

If Step 1's context load surfaced something that could change the analysis — a
recently-added standing rule, a roadmap revision since the last session, a
constraint introduced by a recent close-out, an assumption that depends on
state Cowork cannot directly verify — Step 2's reconstruction must propagate
that uncertainty into the eventual CLI instruction (Step 6a) as an if/then
guard. The CLI direction stops being a single directive and becomes
check-then-act.

**Triggers (any of these in Step 1 → conditional direction in Step 6a):**

- A new standing rule appeared since the last session that *might* apply but
  requires CLI-side verification of state Cowork didn't load.
- The roadmap was revised in a way that affects downstream baselines, but the
  revision's exact scope depends on which file or branch CLI is touching.
- A measurement assumption can only be verified by reading state mid-execution.
- The dispatch's pre-authorization rests on a property of the current code
  state that may have changed since the spec was written.
- Cowork's planning context is more than one session stale on a load-bearing
  document.

**Direction shape.** When a trigger fires, the CLI block enumerates the
branches and the verification step that selects among them:

```
**Decision:** Type [N] — [Name]

Before acting, verify [specific check]:
  - If [condition A]: proceed with [action A].
  - If [condition B]: proceed with [action B].
  - If neither / unclear: pause and report — I'll route the next decision
    from Cowork.

[remaining CLI block fields...]
```

The branches must be exhaustive enough that CLI does not have to invent a
third option. If the situation space isn't enumerable, escalate to Type 5
(Verify First) instead.

**This is not Type 5.** Type 5 defers the entire strategic decision until a
verification task runs and reports back; the remaining plan pauses. Conditional
direction makes the action *contingent* — CLI proceeds immediately and selects
which action to take based on what it observes when it gets there. Use
conditional direction when Cowork has enough context to enumerate the branches
but not enough to choose between them; use Type 5 when even the branches can't
be enumerated without verification.

### Step 3 — Decision Classification

Walk this tree. Take the first match.

```
1. Did the dispatch pre-authorize a response for this exact situation?
   ├── YES: Does the pre-authorization still apply given what CLI found?
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
   │       └── NO → Type 1b (Advance — Cowork-Originated)
   └── NO → Continue to step 4

4. Can CLI productively continue with a revised direction?
   ├── YES → Type 3 (Pivot Advance)
   └── NO → Type 4 (Pivot Stop)
```

**Mandatory alternative-frame test:** Before finalizing the type, explicitly state
what the *next type down* would look like and why you're rejecting it:

- If recommending Type 1a/1b, state what Type 2 (narrowing) or Type 3 (pivot)
  would look like and why the full advance is better.
- If recommending Type 2, state why Type 1 isn't justified and what Type 3
  would look like.
- If recommending Type 3, state why Types 1/2 aren't sufficient and what Type 4
  (full stop) would look like.
- If recommending Type 4, state what Type 3 (pivot advance) would look like
  and why even a pivot isn't productive.
- If recommending Type 5, state what Type 1a (just trust the measurement and
  advance) would look like and why the verification gate is worth the delay.

This test prevents the most dangerous failure mode: choosing a comfortable type
(usually Type 1 — "just keep going") when the situation actually warrants a pivot.

#### Valid Measurement Suspicions (for Type 5 gating)

Only these qualify as reasons to suspect CLI's measurement. If none apply,
accept the numbers and decide:

1. **Single-seed result contradicts prior close-out** on the same code state
2. **Measurement violates the spec's declared ESCALATE criteria** in a way
   that suggests instrumentation error (e.g., a metric moves in the impossible
   direction given the change that was made)
3. **Impossible delta** — magnitude exceeds what the change could plausibly produce
4. **Measurement cadence doesn't match the mechanism class** per SRL-091
   (e.g., structural change measured with a constants-only N=200 gate)
5. **Measurement differs from baseline CAL on the same code state** — same
   code, different numbers, no intervening change

If none of the five applies, the numbers stand. Don't use "verify first" as a
comfort move to delay a hard decision.

### Step 4 — Cost-Benefit Analysis

For each viable type (minimum two — recommended + best alternative):

```
Type [N]: [Name]
  What happens next: [Specific actions]
  Cost: [Time, tokens — be concrete]
  Risk: [What goes wrong if this is the wrong call]
  Downstream impact: [Effect on next 2-3 sprints]
```

If the sprint is over budget, state the position explicitly.

### Step 5 — Recommendation

Present using this structure. **Plain-language rules apply** — no acronyms, no IDs
as proxies, self-contained, succinct, complete (see Brevity Rule above).

```
## Mid-Dispatch Decision: [Sprint name in plain language]

### Problem / Opportunity

[2-4 sentences. What CLI found, why it triggered a pause, what's at stake if the
decision goes wrong. Connect to downstream work in plain terms — "the next four
sprints all measure against the baseline we set here," not sprint IDs.]

### Alternative Solutions

**Option A: [Plain-language name] (Type [N])**
[2-3 sentences. What we'd do, what it costs, what we gain, what we risk.]

**Option B: [Plain-language name] (Type [N])**
[2-3 sentences. Same shape.]

[Option C if a third is genuinely viable. Minimum two alternatives required.]

### Recommended Way Forward

[Which option and the decision type. 1-2 sentences stating the recommendation
plainly.]

### Justification

- **What the dispatch planned for:** [Paraphrase the pre-authorization or scope
  fence in plain terms. State whether the recommendation follows or deviates from
  it, and why. Do not cite by ID.]
- **What history says:** [Paraphrase the relevant pattern or precedent in plain
  terms. Do not cite by SRL ID. If no relevant pattern exists, say so.]
- **What's downstream:** [Name the next 2-3 affected pieces of work in functional
  terms ("the calibration baseline for the next four sprints," not "SK-18, SK-19,
  SK-02").]
- **What would change my mind:** [Specific evidence or conditions that would flip
  the recommendation to a different option.]
```

The recommendation must be opinionated. "It depends" is not a recommendation. If
the evidence genuinely doesn't favor one option, choose the option with the better
cost-of-being-wrong profile and say so.

### Bundled Pauses

When CLI surfaces multiple decision points simultaneously (e.g., two
authorization flags triggered at once), do NOT collapse them into a single
recommendation. Instead:

- **One Problem/Opportunity block per decision,** stated separately.
- **Separate Alternative Solutions and Recommended Way Forward per decision.**
- **Separate alternative-frame test per decision.**
- **Single CLI block at the end** listing all instructions in execution order.
- **Independence rule:** If decision A's outcome changes decision B's viable
  options, they are NOT independent — separate the pauses. Handle A, get CLI
  to the next pause point, then handle B.

### Step 5.5 — Cross-Worktree Conflict Surface Check

**Exemption: Type 4 (Pivot Stop) skips this step entirely.** Type 4 triggers
partial phase-closeout immediately, so the amendment authoring and the close-out
integration happen in the same workflow — no cross-worktree timing gap exists.
Steps 5.5 and the staging-file branching in Step 6b apply only to Types 1a, 1b,
2, 3, 3a, and 5, where the dispatch continues and the close-out happens later.

For all non-Type-4 decisions, before producing the CLI block and persisting
amendments, scan for foreseeable merge conflicts at close-out. Three conditions:

1. The dispatch spec lives in a document subject to archive-forward collapse
   (e.g., a Roadmap §Active Skeletons section that converts to a one-paragraph
   Completed Work Summary row at close-out).
2. An active CLI worktree exists on the sprint's feature branch.
3. The close-out edit will modify the same section the amendment is being
   appended to.

If all three hold, the rebase at close-out will produce a conflict on this
file — or worse, a silent revert if pre-merge rebase isn't strict. Surface the
foreseeable conflict in the Recommendation (Step 5), not after the fact:

> "Foreseeable conflict at close-out — [file] §[section]. Mitigation options:
> (1) push amendment inline + Close-Out Preservation note,
> (2) push only the lessons-learned append, hold the spec amendment,
> (3) stage both for close-out integration via the decision-trail staging file."

Let the user choose the mitigation before persisting. The default for projects
that practice archive-forward discipline is the staging-file path (Step 6b's
IF branch); the user can override.

### Step 6 — Confirm and Execute

**Produce ONLY after user confirms.** Wait for explicit confirmation.

Once confirmed, produce three outputs in this order:

#### 6a. CLI Instruction Block (print first)

User pastes this immediately. **Write in first person.** Keep it minimal.

**If Step 2's conditional-direction rule fired,** any of the per-type formats
below is wrapped in a check-then-act structure: the type's direction becomes
the action under the matching branch, and additional branches enumerate the
alternatives. See Step 2's "Conditional CLI Direction" subsection for the
shape.

**Per-type format:**

**Types 1a/1b/2:** Decision + direction + scope + constraints + why.

```
Here's my decision on the [pause point]:

**Decision:** Type [N] — [Name]

[Direction — 1-3 sentences. Name task numbers, agents, metrics.]

**Scope:** [Unchanged / narrowed — what and where deferred work goes]
**Constraints:** [Guardrails. "Do not X." "If Y, stop and ask."]
**Updated task plan:** [only if tasks changed]
**For the close-out:** [What to note]
**Why:** [1-2 sentences]
```

**Type 3 (Pivot Advance):**

```
Here's my decision — pivoting remaining work:

**Decision:** Type 3 — Pivot Advance

Replace remaining tasks with these:
  □ [N]. [agent]: [task] [model] {effort}
  □ [N+1]. [agent]: [task] [model] {effort}
  ...
**Done-when:** [revised criteria]
**Constraints:** [guardrails]
**For the close-out:** [scope change from original dispatch]
**Why:** [1-2 sentences]
```

**Type 3a (Revise Routing/Effort):**

```
Here's my decision — revising agent assignments:

**Decision:** Type 3a — Revise Routing

Change these task annotations (plan and done-when unchanged):
  Task #N: [old agent/effort] → [new agent/effort]
  Task #M: [old agent/effort] → [new agent/effort]
**Why:** [1-2 sentences]
```

**Type 4 (Pivot Stop):**

```
Stop the dispatch. Preserve completed work from tasks #1-N.
Cancel remaining tasks. I'll send a new dispatch from Cowork.

**For the close-out:** [what the partial close-out should capture]
**Why:** [1-2 sentences]
```

**Type 5 (Verify First):**

```
Here's my decision — verify before committing to a direction:

**Decision:** Type 5 — Verify First

Run this verification task:
  □ [agent]: [what to check] [model] {effort}
  **Done-when:** [verification criteria]

Pause remaining tasks until verification lands. Then come back for direction
on the strategic decision.

**Why:** [1-2 sentences explaining the measurement suspicion]
```

#### 6b. Amend the Dispatch Spec (hard execution) — uses virtuoso's governance staging file

This is not optional. Cowork **must execute an Edit call** and confirm the edit
landed. The workflow does not terminate until the amendment is persisted.

**Where the amendment lands** depends on the sprint's execution context:

**PATH A — Worktree-resident sprint (mandatory staging file):**

Per virtuoso's Worktree Governance Staging rules, worktree-resident sprints MUST
NOT edit main governance documents. All governance-change intent goes to the
sprint's staging file. Mid-dispatch amendments are governance changes — they go
to the staging file.

1. Identify the sprint's staging file:
   `<close-out-folder>/Memo.<sprint-id>.GovernanceStaging.<YYYY-MM-DD>.md`
   (where `<close-out-folder>` is wherever the project's close-out memos live).
2. If the staging file does not exist, create it with virtuoso's staging file
   header (see virtuoso skill §Rule 3) and the Amendment Registry (below).
3. Append a fold-in entry under `## Target: <roadmap-document>`:
   ```markdown
   ### Fold-in N — Mid-Dispatch Amendment (<title>)
   Section: §<sprint-id> (inline full spec)
   Action: Migrate
   Source: This amendment block (below)
   Destination: Close-out memo §Mid-Dispatch Decisions
   Content:
   #### Mid-Dispatch Amendment — [date]
   **Pause point:** [1 sentence]
   **Decision:** Type [N] — [Name]
   **Rationale:** [1-2 sentences]
   **Scope change:** [What changed, or "None"]
   **Follow-up items:** [Deferred work, or "None"]
   ```
4. Update the Amendment Registry table with a new row.
5. Print confirmation: "Staged mid-dispatch amendment in
   `Memo.<sprint-id>.GovernanceStaging.<YYYY-MM-DD>.md` (fold-in N).
   Registry shows [N] decisions for this sprint."

At close-out, phase-closeout processes the staging file as Wave 2 Step 0 —
it migrates the amendment content to the close-out memo's §Mid-Dispatch
Decisions section and deletes the staging file. The fold-in instruction's
Action: Migrate tells the handler exactly what to do.

**No Close-Out Preservation field needed.** Under the staging-file pattern,
the fold-in instruction IS the preservation contract. The Destination field
in the fold-in entry serves the same function more directly.

**No conflict-surface check (Step 5.5) needed.** The worktree never touches
the main governance document, so cross-worktree conflicts on governance files
are structurally impossible.

**PATH B — Cowork-side session (no worktree boundary):**

When Cowork is making a mid-dispatch decision outside a worktree context (e.g.,
the sprint is running in the same session or the user is manually operating CLI):

1. Identify the spec location (roadmap entry, sprint-queue entry, or standalone
   file). If ambiguous, resolve **before** printing the CLI block in 6a.
2. Read the file.
3. Append the amendment block (template below) inline to the dispatch spec.
4. Print confirmation: "Amended `[filename]`: added mid-dispatch amendment
   for [pause point description]."

**Amendment block template (Path B — inline path only):**

```markdown
#### Mid-Dispatch Amendment — [date]

**Pause point:** [1 sentence]
**Decision:** Type [N] — [Name]
**Rationale:** [1-2 sentences]
**Scope change:** [What changed, or "None"]
**Follow-up items:** [Deferred work, or "None"]
**Close-Out Preservation:** [Where this amendment migrates at close-out
(close-out memo path + section), what the integration action is
("migrate verbatim under §Mid-Dispatch Decisions"), the timing ("before
collapsing the inline spec to a Completed Work Summary row"), and the
silent-loss risk if skipped ("this decision evaporates and downstream
sprints cannot reconstruct why the spec was amended"). Required field
for Path B only — Path A uses fold-in instructions instead.]
```

**How to decide which path:** If the sprint is running in a git worktree
(check the dispatch spec or project configuration), use Path A. If Cowork is
operating on canonical main directly, use Path B. When in doubt, use Path A —
it's always safe and the staging file is deleted at close-out regardless.

**Amendment Registry (both paths).** The staging file (Path A) or a standalone
decision-trail file (Path B, for projects that want a registry even without a
worktree) carries a registry table tracking every mid-dispatch decision for the
sprint in chronological order:

```markdown
## Mid-Dispatch Decisions Registry — <sprint-id>

| # | Date | Pause point | Decision type | Disposition |
|---|------|-------------|---------------|-------------|
| 1 | YYYY-MM-DD | [pause point in plain language] | Type [N] | [Resolved — one-line summary] |
| 2 | YYYY-MM-DD | [pause point] | Type [N] | [Resolved — one-line summary] |
```

Every amendment adds a row. The close-out handler reads the registry first,
then walks each amendment/fold-in below and processes it.

#### 6c. Update Lessons Learned (hard execution when warranted)

Check whether the decision produced a reusable lesson. If yes, Cowork **must
execute the append** to `SpecRetro.Lessons_Learned.md` — not just describe it.

**Update triggers:**
- Pre-authorization was wrong or incomplete
- Decision was a pivot (Type 3, 4, or 5) — original plan was off
- A standing rule was invoked and found insufficient
- Same pattern appeared before (check for promotion)

**Skip triggers:**
- Straightforward Type 1a following the pre-authorization exactly
- Lesson already captured by existing SRL

**If updating:** Append with sequential SRL-NNN ID, check promotion rules.
Print confirmation: "Added SRL-NNN to lessons learned: [one-line summary]."

**If skipping:** Print: "No new lesson — [reason]."

---

## Integration with Other Skills

### + Phase-Closeout

**Type 4 triggers partial phase-closeout immediately.** Inputs: (a) completed
tasks as deliverables, (b) cancelled tasks with reason "mid-dispatch pivot,"
(c) pause-point finding in the findings table, (d) next pointer enters Case C.
Step 2's situation assessment serves as the CLI summary input.

**Types 1-5 inform eventual close-out.** The amendment block (6b) ensures the
close-out compares results against the *amended* spec, not the original.

### + Adversarial Review

Offer when CLI's analysis rests on a hypothesis that, if wrong, flips the
decision type. If adversarial review finds the hypothesis fragile, push toward
Type 5 (verify first) or Type 4 (stop). Don't just name the option — specify
what to do with the output.

### + ULTRATHINK

Applies Steps 2-5 at maximum depth. Step 6 remains concise regardless.

### + Effort Levels

If the decision changes scope (Types 2, 3, 3a), reassess effort allocations
using the effort-levels Task Type Reference Table. State changes explicitly in
the task plan update.

### + Virtuoso

If the decision changes what CLI executes next (Types 3, 3a, 5), virtuoso's
execution discipline applies to the revised plan. The CLI block should flag
this: "Virtuoso task-plan reprint required after this change."

**Governance Staging integration:** For worktree-resident sprints, virtuoso's
Worktree Governance Staging rules (§Rule 5) mandate that mid-dispatch amendments
go to the sprint's staging file — not to the inline spec. This skill's Step 6b
Path A implements that mandate. The conflict-surface check (Step 5.5) becomes
unnecessary for worktree-resident work because the conflict surface is
structurally eliminated. Step 5.5 still applies for Cowork-side (Path B) sessions.

---

## Behavioral Rules

### Cite Specific Evidence (paraphrased in Step 5, identified in CLI block)

Every recommendation must rest on: (a) a finding from CLI's pause message,
(b) the dispatch spec's pre-authorization or scope fence, (c) the downstream
dependency chain, (d) prior patterns or standing rules if any match. If you
can't cite evidence, you haven't done enough analysis.

**In Step 5 (Recommendation):** Paraphrase the evidence in plain terms. Do not
name SRLs or sprint IDs by identifier. The user must follow the reasoning
without lookups.

**In Step 6a (CLI block):** Identifiers are appropriate and efficient. CLI knows
the codes. Cite SRL-NNN, sprint IDs, and file paths directly.

### Budget Awareness

If over budget, state the position: budgeted vs. consumed vs. remaining.
Over-budget is a factor, not a veto — marginal work must justify marginal cost.

### Measurement Trust with Enumerated Exceptions

Accept CLI's numbers unless one of the five valid measurement suspicions
(listed under the decision tree) applies. "The numbers seem off" without
matching a listed suspicion is not grounds for Type 5.

### Decision Trail

The CLI block's "Why" and "For the close-out" fields, plus the 6b amendment,
are the permanent record. A future Cowork session doing the close-out must be
able to reconstruct the reasoning from these artifacts alone.

### Don't Rush, Don't Pad

5 minutes of context loading prevents 30 minutes of wrong-direction work.
But once the analysis is done, present concisely. The user is the decision-maker
under time pressure — earn agreement with clarity, not volume.

### Cowork-side Edits During In-Flight CLI Dispatch

When a CLI sprint is in flight (worktree exists, feature branch is active, work
is in progress), Cowork-side governance edits to canonical main require explicit
conflict-surface awareness. Two risk classes apply:

1. **Shared-file conflict (visible at rebase).** Both Cowork's edit on main and
   the worktree's edits modify the same file. The conflict surfaces at the
   pre-merge rebase per the project's worktree-complete discipline. Manageable
   but adds friction, especially if the conflicted section is structurally
   complex (e.g., a Roadmap §Active Skeletons row).
2. **Silent-revert risk (invisible at merge if pre-merge rebase isn't strict).**
   Cowork's edit lands on main. The worktree's bootstrap snapshot pre-dates
   that edit. At merge, if the rebase step is skipped or the conflict resolver
   accepts the worktree's older view, Cowork's edit is silently discarded. This
   is the more dangerous failure mode — there is no error, just missing content.

**Rule.** For worktree-resident sprints, this conflict surface is structurally
eliminated by virtuoso's Worktree Governance Staging rules: the worktree never
edits main governance documents, so conflicts are impossible. Step 6b Path A
(staging file) is mandatory for all worktree-resident sprints. For Cowork-side
sessions (Path B), the conflict surface still applies — run Step 5.5 before
any inline edit to a file the in-flight worktree might also touch at close-out.

---

## Anti-Patterns

| Anti-Pattern | Do This Instead |
|-------------|-----------------|
| Deciding without reading the dispatch spec | The answer may already be there |
| Rubber-stamping the pre-authorization | Verify its assumptions against what CLI actually found |
| Choosing Type 1 because it's comfortable | Run the alternative-frame test — state what Type 3 looks like |
| Producing the CLI block before confirmation | Two-step: recommend first, execute after explicit assent |
| Vague CLI block ("continue as you see fit") | Name tasks, agents, files, metrics, thresholds |
| Type 3 without a revised task plan | CLI can't execute "do something different" without specifics |
| Skipping 6b (spec amendment) | The amendment is not optional. For worktree sprints: append to the staging file. For Cowork-side: edit the spec inline. Confirm the edit either way. |
| Using inline-spec amendments for a worktree-resident sprint | Always use Path A (staging file). Virtuoso forbids worktree edits to main governance docs — the staging file is the only valid target. |
| Using Type 5 to avoid a hard decision | Only valid with a listed measurement suspicion |
| Collapsing bundled pauses into one decision | One Problem/Alternatives/Recommendation per decision point |
| Acronyms, sprint IDs, or SRL numbers in the Recommendation | Step 5 is plain language only. Paraphrase the idea; identifiers go in the CLI block. |
| User has to open another document to follow the recommendation | Recommendation must be self-contained. If a reference is decision-relevant, paraphrase it in plain terms. |
| Skipping Step 2's first-principles assessment | Walk all five sub-steps. Pattern-matching to the spec's framing is the failure mode this step exists to prevent. |
| Appending amendment without a Close-Out Preservation field | Always include the field — it's the contract that prevents silent loss at close-out. The close-out handler needs to know where to migrate the amendment, how, when, and what's at risk if skipped. |
| Persisting amendment without checking execution context | For worktree-resident sprints, always use Path A (staging file) — no conflict check needed because the surface is eliminated. For Cowork-side (Path B), run Step 5.5 first. |
| Using inline-spec amendments for a sprint running in a worktree | Virtuoso's staging-file pattern makes this a hard prohibition. Use Path A unconditionally for worktree-resident work. |

---

## Worked Example

See [references/example-sk01b.md](references/example-sk01b.md) for a full
walkthrough of the SK-01B calibration drift decision (Type 1a — advance with
pre-authorized full-cal). The example uses GoG-specific agent names; adapt
agent references to your project's roster.
