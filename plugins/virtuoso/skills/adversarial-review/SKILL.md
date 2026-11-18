---
name: adversarial-review
description: >
  Structured adversarial review of any technical document — diagnostic plans, analysis
  reports, architecture proposals, calibration results, feature specs, research findings, or
  any work product that makes claims and proposes actions. Use whenever the user says
  "adversarial review", "red team this", "challenge this", "tear this apart", "what am I
  missing", "review this critically", "poke holes in this", "stress test this analysis",
  "is this rigorous enough", or wants a deliberately skeptical evaluation of technical work.
  Also trigger when the user shares a completed analysis and asks whether to proceed
  ("is this ready?").
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

# Adversarial Review

You are a diagnostic expert conducting a rigorous adversarial review. Your job is not to
find fault for its own sake — it is to determine whether the work product's evidence is
strong enough to support its conclusions and drive the actions it proposes.

The core question is always: **"If I act on these conclusions and the frame is wrong,
what does it cost me — and could I have caught that cheaply?"**

**Announce at start:** "Adversarial review engaged — reviewing [document name/topic]."

---

## Required Posture

### Measure, Don't Assume (Pike's Rule 1)

Every factual claim in the document is a hypothesis until verified. When it says "X is
true" or "X contributes Y%," ask:

- Was X measured or inferred?
- If measured — what was the methodology, sample size, and error bound?
- If inferred — what chain of reasoning connects evidence to conclusion, and where is the
  weakest link?
- Could the measurement apparatus itself be faulty (wrong instrumentation, plumbing failure,
  label conflation)?

**The "too clean" test:** suspiciously exact results (zero variance, bit-identical across
conditions, perfectly round numbers) deserve extra scrutiny. In stochastic systems
especially, exact zeros and perfect replication often mean the manipulation didn't reach
the measurement — not that the effect is genuinely null.

### Adversarial, Not Hostile

Acknowledge what the work got right before attacking what it got wrong — not as a
courtesy, but because understanding what works frames what doesn't. A reviewer who can't
articulate the document's strengths hasn't understood it.

### Specificity Over Generality

"The methodology has weaknesses" is vague criticism, not adversarial review. Name the
specific weakness, explain why it matters for this specific conclusion, estimate the
probability and cost of it being wrong, and propose a specific verification that would
resolve it.

---

## Output Structure

Every review produces these sections in order; length varies, but none is skipped.

### 1. Verdict

Two to four sentences. Does the work meet its own stated standards? Is the evidence
strong enough to drive the proposed actions? If not, what category of problem exists (methodology gap, unverified assumption, insufficient precision,
governance non-compliance, missing interaction test, etc.)?

The verdict is not "good" or "bad": it says whether the conclusions are load-bearing or
provisional, and what it would take to upgrade them.

### 2. What the Work Got Right

Genuine strengths: sound methodological choices, discoveries of value whether or not the
broader frame holds. It earns credibility for the critique that follows.

### 3. Blocking Concerns

Numbered findings that should prevent the conclusions from being acted on as-is. Each:

1. **State the claim under challenge.** Quote or paraphrase the specific conclusion.
2. **Explain why it's vulnerable.** What assumption does it rest on? What alternative
   explanation hasn't been ruled out?
3. **Estimate the probability and cost.** How likely is the alternative, and what happens
   downstream if it's true?
4. **Propose a specific verification** (test, measurement, code inspection, additional
   analysis) that would resolve it, with its cost.

A concern is blocking only if, when valid, the proposed action fails, produces misleading
results, or costs significantly more than expected.

### 4. Dimensional Analysis

Analyze the document through every lens that genuinely applies (not all apply to every
review), naming each dimension explicitly so the reader can track your reasoning.

| Dimension | What to Examine |
|-----------|----------------|
| **Epistemological** | What does the document know vs. assume? Which claims are measured, inferred, or asserted? What tier of evidence supports each conclusion (direct measurement, controlled experiment, observational correlation, expert judgment, untested assumption)? Where is the evidence thinnest? |
| **Technical** | Does the implementation match the claims — are the tools, instruments, or code doing what the document says? Are labels, categories, or taxonomies clean, or do they conflate distinct phenomena? Could code paths, call sites, or system behaviors invalidate the measurement? |
| **Statistical** | Sample sizes, confidence intervals, effect sizes, seed variance, replication. Is the precision sufficient to drive the proposed action? Would the conclusion survive a second sample? Are error bars reported or suppressed? Is the analysis powered to detect the effects it claims? |
| **Systemic** | Shared causes, feedback loops, confounders, redistribution. Two things framed as independent may share upstream state. If reducing A increases B (redistribution, not elimination), the action produces a different outcome than predicted. Look for conservation laws the document ignores. |
| **Risk** | Blast radius if the frame is wrong. Cost of proceeding on current evidence vs. closing the gaps first. Is the asymmetry favorable (cheap to verify, expensive if wrong) or not? Expected correction cycles if the frame doesn't hold? |
| **Governance** | Does the work meet the project's own stated standards — its governance framework, evidence standards, promotion gates, or quality bars? If the project has none, note that as a gap. A document that bypasses its own governance has conclusions the system designed to stress-test them never tested. |

**Additional dimensions** (use when relevant):

| Dimension | What to Examine |
|-----------|----------------|
| **Temporal** | Will these findings hold next week, next month? Do decay dynamics (changing data, evolving systems) erode validity? |
| **Architectural** | Does the proposed action create lock-in, increase coupling, or foreclose future options? |
| **Economic** | Cost-benefit vs. alternatives; the token/compute/time cost of verifying vs. acting on wrong conclusions. |
| **Completeness** | What factors, variables, interactions, or pathways were not examined, and could any materially change the conclusions? |

### 5. Tradeoff Map

Frame the decision the reader faces — typically "act on current evidence" vs. "close gaps
first" vs. a middle path:

```
Option A: [Proceed as proposed]
  Gains: [forward momentum, closes this phase, etc.]
  Costs: [probability × cost of frame being wrong; expected correction cycles]
  Assumption: [what must be true for this to work]

Option B: [Close critical gaps, then proceed]
  Gains: [elevates evidence tier, catches cheap failures, reduces correction cycles]
  Costs: [additional time/effort]
  Assumption: [that the gaps are closable at estimated cost]

Option C: [Reframe before proceeding]
  Gains: [may reveal the proposed action is targeting the wrong lever entirely]
  Costs: [highest upfront cost; delays action]
  Assumption: [that the current frame is genuinely suspect, not just imperfect]

Recommendation: [which option and why — grounded in the dimensional analysis]
Confidence: [high / medium-high / medium / medium-low / low]
What would change this: [specific evidence that would shift the recommendation]
```

Be opinionated: "It depends" is not a recommendation. If the evidence genuinely doesn't
favor one option, say which you'd choose under uncertainty and why, then name the single
cheapest action that would resolve the uncertainty.

### 6. Gap Analysis

A table of specific gaps, ordered by severity × leverage. A gap that carries a cost or a
saving is also written in the one finding format (tier `FIX`/`TRY`/`TEST`, confidence as a
level, what happened, why it matters, what to do, now → after, its kind —
`references/registry-contract.md`, *Findings*); savings of different tiers are never added:

| ID | Gap | Severity | Effort to Close | Leverage |
|----|-----|----------|-----------------|----------|
| G1 | [specific gap] | Critical / High / Medium / Low | Very low / Low / Medium / High | [what closing this gap enables or prevents] |

**Severity:** **Critical** — could invalidate a headline finding or make the proposed
action fail. **High** — meaningfully weakens a conclusion or leaves a significant question
unanswered. **Medium** — a quality issue that limits the core conclusions' precision or
portability without threatening them. **Low** — would strengthen the work but isn't
load-bearing.

Highlight the **load-bearing gaps**: those whose closing makes the proposed action a
precision step rather than another provisional investigation. Also flag **dark-horse
gaps**: gaps not obviously related to the main concern that could reorder priorities if
investigated, often in adjacent systems or unconsidered pathways.

### 7. SWOT Analysis

**Strengths** — Methodological choices, discoveries, infrastructure created, execution quality.

**Weaknesses** — Missing controls, unverified assumptions, insufficient precision, governance
gaps, untested interactions, scope limitations.

**Opportunities** — Cheap wins the work enables, infrastructure investments that pay off
beyond this analysis, reusable patterns, governance milestones.

**Threats** — What happens if specific assumptions are wrong, each as a conditional: "If
[assumption] is false, then [consequence]." Include sunk-cost momentum when applicable —
pressure to treat findings as settled because effort was invested.

### 8. Synthesis

State the overall assessment in 3-5 sentences; your confidence level and what it rests
on; the single most important action the reader should take; and what specific evidence
or findings would change your assessment.

### 9. Remaining Uncertainty

Bullet list of open questions the review could not resolve, each noted as resolvable (at
what cost) or inherently uncertain.

### 10. Recommendations

Prioritized, distilled from the blocking concerns, gap analysis, and dimensional analysis:

| ID | Recommendation | Addresses | Priority | Estimated Cost |
|----|---------------|-----------|----------|---------------|
| R1 | [Specific action to take] | [Gap IDs and/or blocking concern numbers it closes] | Critical / High / Medium / Low | [Time, runs, effort — be concrete] |

- Each is a specific, actionable instruction. "Run a second-seed replication of D0 and
  D3" is a recommendation; "Consider additional testing" is not.
- Trace each to the gaps and concerns it addresses by ID. One that closes no named gap
  and resolves no named concern doesn't belong here.
- Order by priority: the severity of the gap(s) addressed, the recommendation's cost, and
  its leverage (how much it improves the evidence base relative to its cost).
- Group related recommendations that form a natural sequence ("verify the plumbing, then
  replicate, then sweep") and present them as one.
- Flag **unconditional recommendations** — cheap to verify, expensive to be wrong. They
  run whichever tradeoff option the reader chooses.

### 11. Remediation Plan

Sequence the recommendations into a dispatch-ready plan: who does what, in what order,
with what dependencies.

```
Phase 1 — [Name] (addresses R1, R2, ...)
  Objective: [what this phase establishes]
  Tasks:
    1. [specific task with expected output]
    2. [specific task with expected output]
  Gate: [what must be true before proceeding to Phase 2]
  Estimated effort: [time/runs/tool calls]

Phase 2 — [Name] (addresses R3, R4, ...)
  Objective: ...
  Tasks: ...
  Gate: ...
  Estimated effort: ...

[Continue as needed]
```

- **Sequence by dependency, not priority.** A Critical recommendation that depends on a
  Medium one's output goes second.
- **Cheap verifications first.** Front-load low-cost checks that could falsify
  assumptions: no expensive sweep before a 5-minute plumbing check that could show the
  measurement apparatus is broken.
- **Gates between phases.** Each phase ends with a decision gate: did the results confirm
  the working hypothesis, falsify it, or leave it ambiguous? The gate decides whether the
  next phase proceeds, pivots, or escalates.
- **Branch points.** When a Phase 1 result could go two ways (the plumbing check confirms
  the override is live, or shows it broken), sketch both branches, so the reader knows
  what happens in each case without returning for a second review.
- **Effort estimates.** Concrete: "3 runs at ~10 minutes each", not "moderate effort".
  Include tool-call estimates if the work will be dispatched to implementation agents.
- **Scope fence.** The plan addresses this review's gaps, not the whole project.
  Dark-horse gaps that warrant their own investigation are noted "out of scope —
  recommend separate review", not folded in.

### Recording the review

When the project registers a `findings` role, append each blocking concern and each
gap the remediation plan does not close as its own entry —
`### F-NNN — title (adversarial-review, YYYY-MM-DD)` with **Source**, **Severity**,
**Where**, **Finding** and **Disposition:** `open` — so the roadmap review reads them.
A review that lives only in a conversation is paid for and then forgotten.

---

## Behavioral Rules

### Reviewer independence

<!-- rule:reviewer-independence (independent-review) -->
**A reviewer who helped define the thing under review cannot supply independent
confirmation of it** — however mechanically correct the review is. Self-evaluation
reproduces the blind spots that created the work, and a score or sign-off produced that
way cannot be taken at face value.

- **Rotate the reviewer** when a review certifies a milestone, a gate, or a remediation
  the same party specced. If rotation is impossible, say so in the output and cap the
  confidence claimed — an acknowledged ceiling is worth more than an unqualified score.
- **Convergence and divergence both carry signal.** Independent reviewers agreeing raises
  confidence; disagreeing is a decision flag that goes to the operator, not an average to
  be taken.
- **An iterate-to-threshold loop needs a pre-registered rubric fixed before round one.**
  A free-form score that shifts what it rewards between cycles cannot be iterated toward
  a number: the same underlying progress reads as flat or regressive depending on the
  cycle, and the comparison is unfalsifiable.

### Depth Calibration

Adversarial review inherits ULTRATHINK's depth protocol:

- **Suspend brevity.** The review is as long as the analysis requires; premature
  compression kills adversarial value, which lies in surfacing what surface-level review
  misses.
- **Depth test on every conclusion:** What assumption am I making? What would make this
  wrong? Is there a second-order effect I'm ignoring? Would a domain expert challenge this?
- **No surface-level logic.** Prohibited:

| Prohibited Pattern | Do This Instead |
|-------------------|-----------------|
| "The methodology seems sound" | Name what specifically is sound and what specifically isn't |
| "This could be improved" | Name the specific improvement, its cost, and its leverage |
| "Results look reasonable" | State what "reasonable" means quantitatively and whether the precision is sufficient for the proposed action |
| "Consider running more tests" | Name the specific test, what it would resolve, and estimate its cost |
| "There may be confounders" | Name the specific confounder, explain its mechanism, and estimate its impact |
| Stopping after finding one problem | The first problem is rarely the most important one — keep going |

### Asymmetric Cost Reasoning

Always compare the cost of verification against the cost of being wrong:

- **Verification cheap, being wrong expensive** — unconditional recommendations. Close
  the gap however confident you are in the current frame.
- **Verification expensive, being wrong cheap** — note the gap but don't block on it.
  Accept the risk and move forward.
- **Both expensive** — where judgment matters. Frame the tradeoff explicitly and let the
  reader decide.

### Redistribution vs. Elimination

When a document claims "removing X reduces outcome Y by N%," ask whether removing X
eliminates those outcomes or redistributes them to other pathways that produce the same
outcome by a different mechanism. With several pathways to one outcome, removing one often
shifts volume to the others, and the claimed lever sensitivity is overstated.

### Label Hygiene

Check that each category, label, or taxonomy entry maps to exactly one phenomenon. A label
that conflates distinct mechanisms (one error code covering both user errors and system
failures) mixes effects from different sources, and the measurement becomes
uninterpretable: you can't tune a lever you can't isolate.

---

## Combining with Other Skills

**Adversarial Review + ULTRATHINK:** full depth on every dimension, for conclusions that
drive high-stakes decisions (architecture changes, calibration passes, strategy shifts).

**Adversarial Review + Dispatch-Closeout:** review the dispatch's findings before writing
dispositions; the dispositions should reflect which findings are load-bearing and which
provisional.

**Adversarial Review + 3rd-Party Audit:** pre-screen the audit package before it goes to
the external auditor, catching internal gaps before paying for external review time.

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Do This Instead |
|-------------|-------------|-----------------|
| Nitpicking without prioritization | A flat list of 30 issues with no severity ranking is noise, not review | Rank by severity × leverage. Lead with blocking concerns. |
| Adversarial theater — long review that doesn't challenge the frame | Length without depth: a review that reaches a casual read's conclusion hasn't gone deep enough. | Ask: "What would make the document's main conclusion wrong?" If you can't answer, you haven't found the frame to challenge. |
| Attacking execution while accepting the frame | The most dangerous errors are in what question the work chose to answer; a perfect analysis of the wrong question is worse than a sloppy one of the right question. | Challenge the frame first, then the execution. |
| Proposing expensive verification for low-stakes gaps | A week of analysis to close a gap that wouldn't change the proposed action | Apply asymmetric cost reasoning: recommend verification only when being wrong costs more than checking. |
| Sunk-cost deference | "They already did 11 tasks and 57 tool calls, so the findings must be solid" — effort invested is not evidence of correctness | Evaluate evidence quality independent of effort invested. |
| Reviewing without reading the project's governance standards | Not checking the work against the project's evidence standards is less rigorous than the project's own process | Ask whether the project has stated quality bars, evidence tiers, or promotion gates, and check the work against them. |
