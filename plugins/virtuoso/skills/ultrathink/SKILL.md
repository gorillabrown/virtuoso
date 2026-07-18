---
name: ultrathink
description: >
  Deep-reasoning protocol that overrides default brevity and forces exhaustive, multi-dimensional
  analysis grounded in first principles. Use this skill whenever the user says "ULTRATHINK",
  "ultrathink", "think deeply", "think harder", "maximum depth", "don't simplify", or when a
  problem requires reasoning beyond surface-level logic. This skill suspends conciseness
  preferences, requires mandatory assumption archaeology before dimensional analysis, and mandates
  a validation architecture before concluding. Trigger on: "ULTRATHINK", "ultrathink", "deep
  think", "think step by step", "analyze this thoroughly", "don't be brief", or any signal that
  the user wants exhaustive reasoning over efficient output.
---

<!-- virtuoso-shared-contract v1 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — the project-root governance readme's machine-readable block and `Virtuoso/workspace-layout.json` together form the registry. The manifest wins for any role it already carries a key for; the readme is the carrier for roles the manifest does not yet hold. Resolve every governance path through the registry — never hardcode one.
- **Workspace adopt** — bringing an established project under management is non-destructive: nothing is moved, nothing is duplicated, no parallel document is seeded beside a registered one, and user content is never overwritten.
- **Git ownership** — stage explicitly (`git add <path>`); never `git add .` or `git add -A`. Run a tripwire status check against the expected dirty set before any commit and stop on anything unexpected. No destructive flags, no force-push.
- **Effort levels** — low / medium / high / max. Model tier sets the default (haiku→low, sonnet→medium, opus→high); annotate a task only when overriding its default.
- **Issue contract** — any stop, hold, block, or elevation becomes the 7-field issue document, saved to the registered `issues` directory as `Issue.<SPRINT-ID>.<YYYY-MM-DD>.md`, then routed to `/mid-dispatch-decision` by path.
- **Governance staging** — a worktree-resident run never edits a main governance document directly; the change-intent goes to a staging file as fold-in instructions, applied at close-out.

# ULTRATHINK Protocol

You have been asked to engage in deep, exhaustive reasoning. This protocol overrides normal
output conventions and requires maximum analytical depth, grounded in first principles.

**Announce at start:** "ULTRATHINK engaged — suspending brevity, maximizing depth."

---

## Required Settings

ULTRATHINK performs best at the highest-capability configuration. Framework quality matters
independently of model tier, but stronger models apply the protocol more faithfully.

| Setting | Recommended | Minimum Viable | Compensating Behavior at Minimum |
|---------|-------------|----------------|----------------------------------|
| **Model** | **Opus** | Any | Flag more claims as working assumptions; lower confidence ratings; be more explicit in assumption cataloging |
| **Effort** | **Max** | Medium | Narrow scope to fewer dimensions; invest depth where evidence is thinnest |

**If dispatching to CLI:** Any task tagged ULTRATHINK in a sprint spec should be assigned to
an opus-tier agent with `{max}` effort override. Example:
```
□ 3. athena: Analyze architecture tradeoffs for cache redesign [opus] {max}  ← ULTRATHINK

CLI execution:
  /effort-levels max             ← set before ULTRATHINK task
  dispatch task #3               ← runs at max effort on opus
  /effort-levels [default]       ← revert after task completes
```

**If in Cowork conversation:** Opus + Max effort is recommended. If running at a lower tier,
acknowledge this in your output and apply the compensating behaviors above.

---

## First Principles Protocol

ULTRATHINK tells you **how deep to go**. First principles analysis tells you **where to dig**.
Both are required. Neither is sufficient alone.

The central failure mode of deep reasoning is building well-structured answers on unexamined
foundations. Structural discipline — applying nine lenses rigorously, mapping tradeoffs
explicitly — cannot compensate for analysis that begins from a false or artificial premise.
First principles analysis prevents this by requiring systematic excavation of assumptions
*before* dimensional analysis begins. Every ULTRATHINK execution must open with this protocol.

### Phase 1 — Assumption Archaeology

Before selecting analytical dimensions, catalog every assumption embedded in the problem
framing and your own initial reaction to it.

For each assumption identified, apply the Socratic challenge:
- Is this a **foundational truth** — empirically verifiable, logically necessary, or
  derivable from first principles? (e.g., a physical law, a mathematical constraint, a
  verified resource limit, a contractual obligation)
- Or is it a **constructed convention** — a historical default, an industry norm, a
  workflow habit, or a belief that has never been explicitly tested? (e.g., "we always
  do it this way," "that's best practice," "everyone assumes X")

Foundational truths are load-bearing and must be respected. Constructed conventions are
candidates for examination — they may be worth keeping, but they must earn that status
explicitly rather than being inherited uncritically.

**Output of Phase 1:** A catalog of the problem's assumptions, each labeled as
*verified truth* or *working assumption (unverified)*.

### Phase 2 — Constraint Classification

Every constraint on a problem is either:
- **Genuine (unbreakable):** Physical limits, mathematical bounds, hard legal requirements,
  verified resource ceilings. These are not negotiable — reasoning that ignores them
  produces unrealizable conclusions.
- **Artificial (revisable):** Conventions, traditional approaches, regulatory interpretations,
  self-imposed timelines, assumed stakeholder preferences. These should be questioned before
  being accepted as boundaries.

The most powerful insights in any domain come from asking: *does this actually have to be
this way?* Constraint classification is the systematic form of that question.

**Output of Phase 2:** A constraint map with every identified constraint classified as
genuine or artificial. Artificial constraints that survive Socratic challenge become
*provisional boundaries* — held as working limits, not treated as walls.

**Gate:** Dimensional analysis begins only after Phases 1 and 2 are complete. Their outputs
determine which analytical dimensions are actually material and sharpen every tradeoff
mapping that follows.

---

## Behavioral Overrides

When ULTRATHINK is active, the following rules are in effect:

### 1. Suspend Brevity

Immediately override any "Zero Fluff," "be concise," or brevity-first rules from CLAUDE.md,
session bootstrap, or standing instructions. You must not optimize for shortness at the
expense of quality. Length is not a goal — depth is. But when depth requires length, length
is permitted without apology.

This does NOT mean pad with filler. Every sentence must carry analytical weight. The override
is against premature compression — cutting analysis short because "the user probably gets it."
Under ULTRATHINK, do not assume the user gets it. Show the full chain.

### 2. Maximum Reasoning Depth

Engage in exhaustive, step-by-step reasoning. If a conclusion feels obvious or the logic
feels easy, that is the signal to dig deeper — not to stop. Easy logic is usually
incomplete logic.

**Depth test:** For every conclusion you reach, ask:
- What assumption am I making?
- What would make this wrong?
- Is there a second-order effect I'm ignoring?
- Would someone with deep domain expertise challenge this?

If any answer is "yes" or "maybe," continue reasoning.

**Principled termination:** Stop when every load-bearing claim in your conclusion is either:
- (a) A **verified foundational truth** — irreducible, empirically grounded, emerged from
  Phase 1 as a genuine constraint; or
- (b) An **explicitly flagged working assumption** — named, bounded, and paired with a
  defined test that would confirm or refute it.

If you cannot categorize every load-bearing claim this way, you have not gone deep enough.
"I'm not sure which category this falls into" is a signal to keep digging, not a signal
to stop.

### 3. Multi-Dimensional Analysis

Analyze the request through every relevant lens. Dimensions should be **derived from the
Phase 1 and Phase 2 outputs** — the assumptions you've surfaced and the constraints you've
classified will indicate which lenses are actually material. Do not select dimensions by
default; derive them from what you now know about the problem's actual structure.

The following dimensions are available. Use the ones the problem demands:

| Dimension | What to Examine |
|-----------|----------------|
| **Technical** | Implementation complexity, performance costs (rendering, compute, memory), state management, error surfaces, edge cases |
| **Architectural** | Coupling, cohesion, modularity, extensibility, migration paths, dependency chains, blast radius of changes |
| **Psychological** | User cognitive load, decision fatigue, information density, mental model alignment, surprise factor |
| **Scalability** | Long-term maintenance burden, team-size sensitivity, documentation debt, onboarding cost, what happens at 10× current scale |
| **Economic** | Token cost, compute cost, time cost, opportunity cost, cost of being wrong vs. cost of being slow |
| **Temporal** | Short-term vs. long-term tradeoffs, reversibility, lock-in effects, what this decision looks like in 6 months |
| **Risk** | Failure modes, blast radius, recovery cost, probability × impact, what you're implicitly betting on |
| **Systemic** | How this interacts with other parts of the system, second-order effects, feedback loops, emergent behavior |
| **Epistemological** | What do we actually know vs. assume? Where is the evidence thin? What would change our mind? |

For domains outside this standard set (e.g., legal interpretation, materials science,
ethical philosophy), derive additional dimensions from the problem's foundational structure
rather than forcing a fit to the list above. State any added dimension explicitly and
justify its inclusion from Phase 1 findings.

For each dimension you analyze, state it explicitly so the user can track your reasoning
structure.

### 4. Tradeoff Mapping

Every non-trivial decision involves tradeoffs. Under ULTRATHINK, make them explicit. Every
assumption in the template below must trace back to the Phase 1 catalog — label each as
*verified truth* or *working assumption*:

```
Option A: [description]
  Gains: [what you get]
  Costs: [what you lose or risk]
  Assumption: [what must be true — verified truth or working assumption?]

Option B: [description]
  Gains: ...
  Costs: ...
  Assumption: [what must be true — verified truth or working assumption?]

Recommendation: [which option and why — grounded in the dimensional analysis above]
Confidence: [see calibrated scale below — and what would change it]
```

**Calibrated confidence scale (grounded in Phase 1 and 2 outputs):**
- **High:** All load-bearing claims are verified foundational truths. No material working
  assumptions remain unresolved. The conclusion holds under all conditions exposed by
  Phase 1 and Phase 2.
- **Medium:** Most load-bearing claims are verified. One or more working assumptions remain,
  each with a defined test and bounded impact if wrong. The recommendation is sound but
  should be revisited once those tests are run.
- **Low:** Significant load-bearing claims are unverified assumptions. The conclusion is
  directionally useful but should not drive irreversible decisions without validation.

If there are more than two options, map all of them. If the tradeoffs are genuinely balanced,
say so — don't force a recommendation when the evidence doesn't support one.

### 5. Prohibition on Surface-Level Logic

The following patterns are prohibited under ULTRATHINK:

| Prohibited Pattern | Why It Fails | Do This Instead |
|-------------------|-------------|-----------------|
| "Obviously, X" | Nothing is obvious under deep analysis — this is a reasoning shortcut | Prove X from first principles |
| "It's best practice to..." | Best practices are context-dependent generalizations | Explain WHY this practice applies HERE, or whether it doesn't |
| "Simply do X" | "Simply" is a complexity-hiding word | Enumerate the steps, dependencies, and failure modes |
| "This should work" | Confidence without evidence | State what evidence supports the claim and what could falsify it |
| "In most cases..." | Vague probabilistic hedge | Specify which cases, what makes this case different or similar, and what the edge cases are |
| Stopping after the first valid answer | First valid ≠ best. There may be a better answer one level deeper | Generate at least two viable approaches before choosing |
| Treating constraints as given | Constraints are inputs to challenge, not walls | Classify each constraint as genuine or artificial (Phase 2) before accepting it |

---

## Execution Flow

When ULTRATHINK is triggered:

1. **Acknowledge the protocol.** State that ULTRATHINK is active and brevity is suspended.

2. **Frame the problem.** Restate the question or task in your own words to confirm
   understanding. Identify what type of problem this is (design decision, debugging,
   architecture, strategy, tradeoff evaluation, etc.).

3. **Assumption Archaeology (Phase 1).** Catalog every assumption embedded in the problem
   framing and your initial reaction to it. Apply the Socratic challenge to each: is this
   a foundational truth or a constructed convention? Label every assumption as *verified
   truth* or *working assumption (unverified)*. This step gates everything that follows —
   do not proceed to step 4 until every material assumption has been surfaced and labeled.

4. **Constraint Classification (Phase 2).** Map every identified constraint as genuine
   (unbreakable) or artificial (revisable). Flag artificial constraints that survive
   challenge as provisional boundaries. Note which artificial constraints, if revised,
   would open meaningfully different solution paths.

5. **Derive relevant dimensions.** From the outputs of steps 3 and 4, identify which
   analytical lenses are material to this specific problem. State your derivation — why
   each selected dimension is relevant given what you now know about the problem's actual
   structure.

6. **Analyze each dimension.** Work through each selected dimension in sequence. Show
   your reasoning chain — don't jump to conclusions.

7. **Map tradeoffs.** If the problem involves a decision, use the tradeoff template above.
   Trace every stated assumption back to the Phase 1 catalog.

8. **Synthesize.** Pull the dimensional analyses together into a coherent recommendation
   or conclusion. Apply the calibrated confidence scale. State what would change your mind.

9. **Validation Architecture.** Before concluding, state:
   - The **minimal testable proposition**: what single observation would confirm or refute
     the central conclusion?
   - The **validation cost-benefit**: what is the cost of testing before acting, versus the
     cost of acting on the current conclusion if it turns out to be wrong?
   - For each remaining working assumption: what is the cheapest, fastest test that would
     resolve it?

10. **Identify remaining uncertainty.** What don't you know? What would you investigate
    further if you had more time? (Distinct from step 9 — step 9 is about your conclusion;
    step 10 is about the broader problem space.)

---

## Combining with Other Skills

ULTRATHINK is a reasoning modifier — it layers on top of whatever skill is already active.
When ULTRATHINK's behavioral directives conflict with another skill's requirements:
- **ULTRATHINK takes precedence** on reasoning depth, assumption surfacing, and constraint
  classification.
- **The other skill takes precedence** on output format, structure, and domain-specific
  workflow steps.

Specific combinations:

- **ULTRATHINK + pointer-closeout:** Deeper interpretation of findings, more thorough
  tradeoff analysis on dispositions, Phase 1 assumption archaeology applied to sprint
  conclusions before the phase is closed.
- **ULTRATHINK + effort-levels:** Deeper analysis of task complexity, more careful
  effort-tier selection with explicit reasoning for borderline cases, constraint
  classification applied to effort constraints themselves.
- **ULTRATHINK + 3rd-party-audit:** More thorough remediation plan, deeper disposition
  reasoning, Phase 2 constraint classification applied to audit findings to distinguish
  genuine vulnerabilities from conventional remediation paths.
- **ULTRATHINK + dispatch authoring:** More thorough failure mode analysis, Phase 1
  archaeology applied to task dependencies before dispatch, deeper agent-routing
  justification.
- **ULTRATHINK + adversarial-review:** First principles protocol runs before adversarial
  challenges are formulated — assumption archaeology ensures the adversarial critique
  attacks actual foundations, not surface-level positions.

When combined with another skill, ULTRATHINK's behavioral overrides (suspend brevity,
maximum depth, first principles protocol, multi-dimensional analysis) apply to every step
of the other skill's execution — not just the final output.

---

## Deactivation

ULTRATHINK remains active until:
- The user says "stop ultrathink," "normal mode," "be brief again," or similar
- The specific question or analysis is complete and the user moves to a new topic
- The user signals satisfaction with the analysis

When deactivating, revert to the normal brevity and conciseness preferences from the
project's standing rules.

---

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Do This Instead |
|-------------|---------------|-----------------|
| Using ULTRATHINK formatting but shallow reasoning | Length ≠ depth. Padding with headers and bullets while skimming the analysis | Every sentence must carry analytical weight. If you can delete it without losing insight, delete it |
| Skipping Assumption Archaeology | Structural analysis of a problem with unexamined assumptions produces well-organized wrong conclusions | Phase 1 gates everything. Skipping it means you're building on sand |
| Treating artificial constraints as genuine | Accepting conventional limits without classification causes you to solve a restricted version of the real problem | Phase 2: classify every constraint before accepting it as a boundary |
| Analyzing irrelevant dimensions | Not every lens applies to every problem — applying a dimension without grounding it in Phase 1 findings is waste | Derive dimensions from Phase 1 and 2 outputs, not by default inclusion |
| Reaching the same conclusion you would have without ULTRATHINK | If deep analysis produces the same answer as surface analysis, either the problem didn't need ULTRATHINK or you didn't actually go deeper | Check: did assumption archaeology surface anything that changed the problem framing? If not, push harder |
| Presenting analysis without a clear conclusion | Exhaustive reasoning that doesn't converge is just noise | Always synthesize into a recommendation with stated confidence |
| Concluding without a validation architecture | Analysis without a testable proposition is philosophy, not engineering | Step 9 is mandatory: state the minimal falsifiable test and its cost-benefit before closing |
| Using ULTRATHINK on trivial tasks | "Rename this variable" doesn't need multi-dimensional analysis | ULTRATHINK is for problems where being wrong is expensive or the solution space is genuinely complex |
