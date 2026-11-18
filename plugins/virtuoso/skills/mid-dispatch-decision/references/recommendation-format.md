Serves `mid-dispatch-decision` Step 5: the recommendation template presented to the user.

# Recommendation Format

The plain-language rules in SKILL.md (§Brevity and Plain Language) apply to every line: no
acronyms, no identifiers as proxies for ideas, self-contained, succinct, complete, one screen.

```
## Mid-Dispatch Decision: [Dispatch name in plain language]

### Problem / Opportunity

[2-4 sentences. What the implementation agent found, why it triggered a pause, what's at stake if the
decision goes wrong. Connect to downstream work in plain terms — "the next four
dispatches all measure against the baseline we set here," not dispatch IDs.]

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
  terms. Do not cite by lesson or rule ID. If no relevant pattern exists, say so.]
- **What's downstream:** [Name the next 2-3 affected pieces of work in functional
  terms ("the calibration baseline for the next four dispatches," not "SK-18, SK-19,
  SK-02").]
- **What would change my mind:** [Specific evidence or conditions that would flip
  the recommendation to a different option.]
```

When Step 5.5 found a foreseeable close-out conflict, the Recommendation states it and its
mitigation options (Step 5.5's wording) so the user chooses the mitigation before anything
is persisted.

**Bundled pauses** repeat the Problem / Opportunity, Alternative Solutions, Recommended Way
Forward, and alternative-frame test once per decision; the single instruction block comes
at the end (see [instruction-blocks.md](instruction-blocks.md), read at Step 6a).

Return to SKILL.md Step 5 (bundled pauses), then Step 5.5.
