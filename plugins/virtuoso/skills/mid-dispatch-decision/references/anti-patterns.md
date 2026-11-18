Serves `mid-dispatch-decision` Steps 5 and 6: the self-check run before presenting the recommendation and again before persisting.

# Anti-Patterns

| Anti-Pattern | Do This Instead |
|-------------|-----------------|
| Deciding without reading the dispatch spec | The answer may already be there |
| Rubber-stamping the pre-authorization | Verify its assumptions against what the implementation agent actually found |
| Skipping Step 2's first-principles assessment | Walk all five sub-steps. Pattern-matching to the spec's framing is the failure mode that step exists to prevent. |
| Choosing Type 1 because it's comfortable | Run the alternative-frame test — state what Type 3 looks like |
| Using Type 5 to avoid a hard decision | Only valid with a listed measurement suspicion |
| Producing the instruction block before confirmation | Two-step: recommend first, execute after explicit assent |
| Vague instruction block ("continue as you see fit") | Name tasks, agents, files, metrics, thresholds |
| Type 3 without a revised task plan | The implementation agent can't execute "do something different" without specifics |
| Collapsing bundled pauses into one decision | One Problem/Alternatives/Recommendation per decision point |
| Acronyms, dispatch IDs, or rule numbers in the Recommendation | Step 5 is plain language only. Paraphrase the idea; identifiers go in the instruction block. |
| User has to open another document to follow the recommendation | The recommendation must be self-contained. If a reference is decision-relevant, paraphrase it in plain terms. |
| Skipping 6b (spec amendment) | The amendment is not optional. Worktree dispatches: append to the staging file. Planner-side: edit the spec inline. Confirm the edit either way. |
| Inline-spec amendment for a dispatch running in a worktree | Virtuoso forbids worktree edits to main governance documents — a hard prohibition. Use Path A (staging file) unconditionally. |
| Persisting an amendment without checking the execution context | Worktree-resident: Path A, no conflict check needed because the surface is eliminated. Planner-side (Path B): run Step 5.5 first. |
| Path B amendment without a Close-Out Preservation field | Always include it — it is the contract that prevents silent loss at close-out, telling the handler where to migrate the amendment, how, when, and what is at risk if skipped. |

Return to the SKILL.md step you came from.
