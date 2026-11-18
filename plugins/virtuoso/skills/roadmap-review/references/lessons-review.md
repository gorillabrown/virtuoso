# Roadmap review — the lessons-learned review

Serves `roadmap-review` SKILL.md Phase D, step D.4 (D.4.1–D.4.6). Run it after D.3 has
written this review's specifications.

## D.4 Lessons-learned review

**D.4.1 Gather.** Read the registered `lessons` role (`lessons --open`), the
close-outs since the last review, audits, and decision records. Resolve each
through the registry; do not scan the filesystem for lookalike names. Include the
close-outs A.1 found without a Lessons section.

**D.4.2 Build the checklist.** Deduped, grouped by theme. The promotion candidates are
computed, not remembered:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --candidates

It lists every pattern that recurred (a second close-out reported it) and every lesson
applied and held in two close-outs — **promote** — and every lesson that did not hold
twice — **revise or retire**. Decide each; a candidate left undecided is carried into
D.4.6 by name. Decide too the candidates the previous review left undecided (B.3).

**D.4.3 Update the standing rules.** Rules live where
`policy.standingRules.source` says, and their identifiers come from
`policy.standingRules.ids`. Present rules get their wording verified; missing ones
are added with a source; superseded ones are updated or removed. A lesson promoted
here gets a status record appended under its identifier in the `lessons` role —
`Promoted -> <rule id>` — never an edit to its original entry:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --record-status <ID> --status "Promoted -> <rule id>" --actor roadmap-review --item <review date> --apply

**D.4.4 Confirm the new specifications** applied the lessons: U9 passed for each in
D.3. Note any live lesson every one of them declined, and whether that is right.

**D.4.5 Review the existing specifications** — every dispatch-ready item this
review did not write — against the live lessons:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --check <spec> --item <ITEM-ID>

One that fails is no longer dispatch-ready: enrich it in place, or flag it as a
buffer gap in D.6. A lesson recorded after a specification was written is exactly
what this step exists to catch.

**D.4.6 Render** `YYYY-MM-DD-lessons-applied.md`: the live lessons; which
specification applied which; the promotions and retirements recorded; the candidates
left undecided; the `learning` figures from `kpis` beside the previous review's (the
resolver's `previous`, or `previousComplete` when `previous` has no lessons-applied); and
the close-outs since the last review that recorded no lesson and gave no reason.

Return to SKILL.md D.5.
