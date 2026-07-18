# Worked Example: SK-01B Calibration Drift

> **Note:** This example uses project-specific agent names (socrates, marcusaurelius,
> hermes) and project-specific artifacts (Roadmap.md, SRL catalog). Adapt
> agent references and file paths to your project's roster.

To illustrate the full workflow, here is how this skill would handle the SK-01B
situation described in the motivating example:

### Step 0 — Depth selection:
Deep. The sprint involves structural engine changes, the drift exceeds a
pre-authorized threshold, and CLI has a hypothesis about root cause. This isn't
a rubber-stamp confirmation.

### Step 1 — Context loaded (Deep mode):
- CLI pause: quick-cal Immediate +3.5pp, Special -5.1pp, both exceed 3pp threshold
- Dispatch spec (roadmap SK-01B): "Escalate to full-cal N=1,200x3 if shift
  exceeds 3pp on any primary metric (per SRL-113)"
- Roadmap: SK-01B is first Stage 1a gate. Every subsequent sprint (SK-18, SK-19,
  SK-02, all of 1b) measures against post-SK-01B baseline
- Lessons learned: SRL-015 (N=200 unreliable for structural changes), SRL-113
  (full-cal escalation threshold)
- Recent close-out: SK-01A clean pass, CLAUDE.md headroom issue flagged

### Step 2 — Situation assessment:
- **Expected:** quick-cal might show drift because SK-01B zeroes profile-class routing
  constants and materializes schema changes — structural changes to engine behavior
- **Actual:** Immediate +3.5pp, Special -5.1pp — both exceed threshold, Immediate/Special swap signature
- **Gap:** Magnitude larger than typical constant-only drift but consistent with
  the *intended* behavioral change (real Special-Finish Rating values replacing
  constant-50 defaults)
- **Known pattern:** SRL-015 warns that N=200 is unreliable for structural changes.
  This is N=400 (better) but still single-seed. SRL-113 pre-authorizes full-cal
  at the 3pp threshold.
- **Downstream:** Every Stage 1a sprint measures against this baseline. If the
  drift is real (correctness, not regression), the baseline should reflect it.
  If it's noise, full-cal will reveal that.

### Step 3 — Classification:
- Dispatch pre-authorizes full-cal at >3pp? **Yes** (per SRL-113).
- Is pre-authorized response still appropriate? **Yes** — the drift is structural,
  not noise, and full-cal confirms the magnitude with statistical power.
- **Type 1a: Advance — Pre-Authorized.**
- Alternative frame test: Type 3 (pivot to investigate CHAIN_ENGAGEMENT_THRESHOLD)
  is tempting because CLI identified a specific mechanism. But the investigation
  is *downstream* of measurement — you need full-cal to establish the actual
  magnitude before deciding whether to tune the threshold. Investigating first
  puts the cart before the horse.

### Step 4 — Cost-benefit:
- Type 1a (full-cal): ~25 min additional compute. Establishes the post-zeroing
  baseline with statistical confidence. Downstream sprints measure against
  a validated number.
- Type 3 (investigate threshold): ~30-40 min code analysis. Produces a hypothesis
  but no validated baseline. Downstream sprints would still need the full-cal.

### Step 5 — Recommendation (presented to user):

```
## Mid-Dispatch Decision: SK-01B

### Problem / Opportunity

CLI's quick-cal found that the Immediate-outcome rate rose 3.5 percentage points
and the Special-outcome rate dropped 5.1 points after the profile-class-routing
zeroing changes. Both exceed the 3-point threshold that triggers a full
calibration run. The sprint is already over its time budget.

The drift appears to be real — it's the expected consequence of participants
now using their actual Special-Finish Rating values instead of the old
constant-50 defaults. Participants with a low Special-Finish Rating can no
longer chain Special-outcome attempts, so simulated matches run longer before
resolving, and more of them resolve via the Immediate-outcome category. This
is correctness, not a bug.

Every subsequent Stage 1a sprint (SK-18, SK-19, SK-02, and all of Stage 1b)
measures against whatever baseline we establish here. If we don't validate the
numbers with full-cal, those sprints measure against an uncertain baseline.

### Alternative Solutions

**Option A: Run full-cal as the dispatch pre-authorized (Type 1a — Advance)**
Run the full calibration (N=1,200 x 3 seeds, ~25 additional minutes). This
confirms the drift magnitude with statistical confidence and gives downstream
sprints a validated baseline. The cost is time on an already over-budget sprint.

**Option B: Skip full-cal, investigate CHAIN_ENGAGEMENT_THRESHOLD instead (Type 3 — Pivot)**
CLI identified the engagement threshold as the likely mechanism for the Special-outcome drop.
Investigating it now (~30-40 min code analysis) would explain *why* the drift
happened. But it doesn't validate the magnitude, and downstream sprints would
still need the full-cal eventually.

### Recommended Way Forward

Option A — run full-cal as the dispatch pre-authorized (Type 1a).

### Justification

- **What the dispatch planned for:** The spec explicitly says "Escalate to
  full-cal N=1,200x3 if shift exceeds 3pp on any primary metric (per SRL-113)."
  Both metrics exceed 3pp. This follows the pre-authorized path.
- **What history says:** SRL-015 warns that quick-cal at N=200 is unreliable
  for structural changes. We're at N=400 (better), but still single-seed.
  SRL-113 established the 3pp escalation threshold as a standing rule.
  Both support running full-cal.
- **What's downstream:** SK-18, SK-19, SK-02, and all Stage 1b sprints measure
  against post-SK-01B baseline. A validated 3-seed baseline is worth the 25
  minutes. Without it, every downstream sprint's drift measurements are
  relative to an uncertain number.
- **What would change my mind:** If the drift were noise rather than the
  expected behavioral change — but CLI's analysis of CAL-079 seed-42's own
  values (+3.0pp Immediate, -4.8pp Special vs. its own prior) rules that out. The
  Immediate/Special swap signature is too clean to be variance.
```

### Step 6 — (After user confirms):

**6a. CLI block (printed first — user pastes immediately):**

```
Here's my decision on the quick-cal escalation:

**Decision:** Type 1a — Advance (Pre-Authorized)

Proceed with full-cal N=1,200x3 seeds as pre-authorized. The drift is expected
behavioral change from real Special-Finish Rating values replacing constant-50
defaults.

**Scope:** All primary metrics. No narrowing.

**Constraints:** If any band drifts >5pp from CAL-079 baseline, note it in the
close-out but do not tune thresholds. I'll scope that from Cowork.

**Updated task plan:**
  ✓ 12. socrates: quick-cal N=400x1 — DONE, escalation triggered
  → 12a. socrates: full-cal N=1,200x3 seeds — proceed
  □ 13. marcusaurelius: update CLAUDE.md + write close-out
  □ 14. hermes: commit, merge, push

**For the close-out:** Full-cal approved over budget — baseline validation
outweighs 25-min cost. Flag CHAIN_ENGAGEMENT_THRESHOLD as Cowork follow-up.

**Why:** Correctness, not regression. Downstream sprints need a validated baseline.
```

**6b. Amend dispatch spec** — Cowork edits Roadmap.md SK-01B entry, appending:

```markdown
#### Mid-Dispatch Amendment — 2026-04-24

**Pause point:** Quick-cal Immediate +3.5pp / Special -5.1pp exceeded 3pp threshold
**Decision:** Type 1a — Advance (Pre-Authorized, full-cal as pre-authorized)
**Rationale:** Drift is expected behavioral change from redirect implementation;
full-cal validates magnitude for downstream baseline.
**Scope change:** None
**Follow-up items:** CHAIN_ENGAGEMENT_THRESHOLD investigation (Cowork to scope)
```

**6c. Lessons learned** — No new SRL. Decision followed SRL-113 pre-authorization
exactly as designed. System worked. Noted: "Amended SK-01B spec. No new lesson —
SRL-113 covers this pattern."
