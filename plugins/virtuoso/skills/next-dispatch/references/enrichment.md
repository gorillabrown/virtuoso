# Enrichment: Gap Table and Change Verification

Serves next-dispatch Phase 3 *Enrichment* (how to close each closable gap Phase 2 flagged; roadmap-review and write-plan close gaps with the same table) and Phase 3.5 *The enrichment change* (separation of duties, and verifying the edit from primary evidence).

## Phase 3 — the gap table

Close each gap by investigation and update the specification in place. Be surgical: do not
rewrite sections that do not need it; preserve existing structure and formatting.

| Gap | How to close |
|---|---|
| Stale location reference | Search for the symbol; read the file; correct the reference. |
| Vague test reference | Read the test file; insert the exact name and assertion. |
| Unverified constant | Search; record the current value and its location. If it does not exist, this is a structural gap. |
| Non-mechanical acceptance criterion | Rewrite it as a command or assertion. |
| Missing branch plan | Apply `policy.git.branchNameTemplate`. |
| Missing failure handling | Enumerate known failure modes; add "if X, do Y". |
| Missing rollback | State the revert path this project's git policy permits. |
| Missing source citation | Find it; link it with an anchor. |
| Missing project-extension detail | Consult the project's own precedent, not another project's. |
| Missing reconciliation recipe | Fill the template in `references/reconciliation-recipe.md` (this skill's folder) from `policy.git` and detected repository state. Pure text; no git mutation. |
| Missing lessons applied | From 1.6: name each live lesson that bears on the item and the change it makes here, or state that none applies; re-run `lessons --check`. |
| Missing task list | Write the `##### Task list` per `references/task-rows.md`: one row per outcome-level task with its class, and an estimate or a frontier timebox. Price it and take the total line from `timing --rows-from-spec <spec> --item <ITEM-ID>`, then re-run it until it exits 0. Always closable, never structural. |
| Missing milestones | Write the `##### Milestones` table per the rubric's U11: a few named stages, each the task-list rows that make it up and a *Done when*, every row in one milestone. Re-run `progress --check-milestones <spec> --item <ITEM-ID>` until it exits 0. Always closable, never structural; a specification that still lacks them gets them derived at kickoff by the virtuoso skill. |

Return to SKILL.md Phase 3.1 *Re-audit*.

## Phase 3.5 — separation of duties

If `policy.git.separationOfDuties` is true, the actor that authored the edit does
not commit it: emit the commit as a hand-off to another actor, with explicit
paths only. This is an *optional project policy* — it is not implied by which
product or model is running the ceremony, and it never applies unless the project
declares it.

## Phase 3.5 — verify from primary evidence

```
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks status -sb
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks diff --stat
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks show HEAD:"<spec path>" | grep -c "<distinctive token>"
```

Confirm the only dirty paths are the ones you edited, and that the enrichment is
actually present where you claim it is. If a report says "clean" but the
enrichment is not on `HEAD`, state the contradiction: nothing was lost — the edit
is still in the working tree — it simply has not been committed yet.

Return to SKILL.md Phase 3.5 *Gate consequence*.
