Serves `mid-dispatch-decision` Step 2: the first-principles situation assessment and the conditional-direction rule.

# First-Principles Situation Assessment

Reason from foundations, not from analogy. The dispatch spec, the pre-authorization, and the
implementation agent's own framing all carry assumptions; strip them and rebuild. This step
prevents the most dangerous failure mode: rubber-stamping a pre-authorized response because
pattern-matching is comfortable. The spec's framing is the starting point for analysis, never
its conclusion. Walk all five sub-steps.

1. **Define the objective.** State what the dispatch is actually trying to achieve in goal
   terms — the underlying engineering or product outcome, not "what the spec says to do."
   If the goal is unclear from the spec, infer it from the roadmap or ask the user.
2. **Catalog assumptions.** List what the spec, the pre-authorization, and the implementation
   agent's analysis take for granted. Common categories: the measurement apparatus is
   correct; the pre-authorization's threshold is the right gate; the implementation agent's
   hypothesis about cause is correct; the downstream baseline is what we think it is; the
   spec's scope fence still holds.
3. **Challenge each assumption.** Mark each *foundational* (irreducible — measurements are
   what they are, the goal is what it is, the code does what it does) or *conventional* (we
   usually handle this kind of thing this way). Foundational ones are not negotiable;
   question every conventional one Socratically: is it true here, or is it inertia?
4. **Identify the first principles.** With conventions stripped away, what is actually true —
   the real levers, constraints, and signals, independent of how the spec or the
   implementation agent framed them? In engineering this often reduces to: what does the
   code do, what does the data say, what does the user actually want.
5. **Reconstruct the optimal response** ground-up from the foundational truths. Only then
   compare it against the spec's pre-authorization, which passes only if it matches what the
   reconstruction produced. If they diverge, the divergence is the finding, and Step 3's
   classification turns on it.

**The output is internal reasoning, not user-facing.** Step 5's Recommendation presents the
*conclusion* in plain language, not the analysis. Show your work to yourself, not the user.

## Conditional direction for the implementation agent

If Step 1's context load surfaced something that could change the analysis, the
reconstruction must carry that uncertainty into the instruction (Step 6a) as an if/then
guard: the direction stops being a single directive and becomes check-then-act.

**Triggers (any one fires it):**

- A new standing rule appeared since the last session that *might* apply but requires
  implementation-agent-side verification of state the planner didn't load.
- The roadmap was revised in a way that affects downstream baselines, but the revision's
  exact scope depends on which file or branch the implementation agent is touching.
- A measurement assumption can only be verified by reading state mid-execution.
- The dispatch's pre-authorization rests on a property of the current code state that may
  have changed since the spec was written.
- The planner's planning context is more than one session stale on a load-bearing document.

The instruction block then enumerates the branches and the verification step that selects
among them (shape: [instruction-blocks.md](instruction-blocks.md) §Conditional direction,
read at Step 6a). The branches must be exhaustive enough that the implementation agent does
not have to invent a third option; if the situation space is not enumerable, escalate to
Type 5 instead.

**This is not Type 5.** Type 5 defers the whole strategic decision until a verification task
reports back, and the remaining plan pauses. Conditional direction makes the action
*contingent*: the implementation agent proceeds immediately and selects the action from what
it observes when it gets there. Use conditional direction when the planner can enumerate the
branches but not choose between them; use Type 5 when even the branches can't be enumerated
without verification.

Return to SKILL.md Step 3.
