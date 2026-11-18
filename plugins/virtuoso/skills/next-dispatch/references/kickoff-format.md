# Kickoff Output Format

Serves next-dispatch Phase 1.4 (*Pipeline figures*) and Phase 4, §4.2 *Output format*: the figures the Pipeline table reports, and the three-section print, with the kickoff and its reconciliation recipe in one code block.

## Pipeline figures (Phase 1.4)

All of these come from `virtuoso_registry --root . kpis --json`, with provenance; a
generated artifact is a presentation output, never the source.

- **Effort.** Effort-weighted figures are in hours when `kpis` reports `effort-basis`
  hours, else in points. They need hours or a scaled size word on every item; if an item
  has neither, the figure is not computable and the message says which items. Name the
  unit, and say *inferred* when size words stood in for hours.
- **Buffer health** compares the count of dispatch-ready active items against
  `policy.roadmap.dispatchBuffer`. If the buffer is 0, report "eager specification
  disabled" rather than a ratio.
- **Last review** is the date of the review `virtuoso_registry --root . review` names as
  `previousComplete` (latest by date, then run; an interrupted review does not count).
- **Pace** comes from the `pace` block of the same `kpis --json` call — computed live
  against each date in `policy.roadmap.deadlines`, never read from an assessment. With no
  deadline declared, the Pace row says so.

Return to SKILL.md Phase 1.5 when this is filled in.

## 4.2 Output format

Apply the §4.1 plain-language rules to every line.

```
# Dispatch Kickoff — [Item title]

## What's next

**[One-to-two-sentence plain-language summary: what the work does and why it
matters.]** *(item [ITEM-ID])*
- *Optional sub-bullet: adaptation, risk, or upstream consideration.*

## Readiness

| Finding | Result | Reason |
|---|---|---|
| Specification | PASS / GAP / BLOCKED | … |
| Prerequisites | … | … |
| Repository | … | … |
| External register | … | … |
| Execution environment | … | … |

## Pipeline

| Metric | Value |
|---|---|
| Dispatch-ready items remaining (incl. this one) | N / [policy buffer] — [healthy / low / critical / empty / eager spec disabled] |
| Items to end of current group | X *(omit if the project uses no grouping)* |
| Items to finish line | Y — ~Z% remaining by effort, in [hours \| points] *(or: not computable — [missing inputs])* |
| Prerequisites for this item | all met / pending: [descriptive names] |
| Last review | N days ago |
| Deadline | [label] YYYY-MM-DD — N days *(or: none declared)* |
| Pace | Ahead / On track / Behind / Overdue — required X vs trailing Y per week ([unit]) *(or: not computable — [missing inputs]; or: no deadline declared)* |

*Source: [register] via [provider], snapshot [timestamp][ — STALE: reason].*

## Kickoff

\```
[Item title]  ([ITEM-ID])
Session: [ITEM-ID] — [short name] · Remote Control: [on | off — <the step to turn it on> | not offered by this host]
Origin: roadmap — [ITEM-ID]
[Group / workstream, if the project uses them]
Effort: [size][ — N h, where the register carries hours]
Branch: [branch-name] from [default branch] @ [sha carrying the specification]
Specification: [resolved location]
Status: next up (not in flight) | Prerequisites: [descriptive names, met/pending]
Readiness: specification ✓ · prerequisites ✓ · repository ✓ · register ✓ · environment ✓

REPOSITORY RECONCILIATION — run this FIRST, before any edit, in [PowerShell | bash]
  [the filled recipe, every line indented two spaces: detected remote and default
   branch, no placeholders, only steps this project's git policy permits]

Halt on any STOP and report the git output — a halt is a dispatch blocker, not something to improvise around.
\```

## Standing rules that apply
- **[project rule id] — [short title].** [One-sentence statement.]

## Lessons applied
- **[<prefix>-NNN — title].** [How this specification applies it.]
*(or: No live lesson applies — [N] live lesson(s) read.)*

## Pre-flight

- [resolved] Readiness rubric ([universal + extensions]) re-confirmed against current state
- [resolved] Lessons applied (U9) — `lessons --check` passes
- [resolved] Prerequisites
- [resolved] Specification reachable from the execution base
- [resolved] Figures computed through the provider, with provenance
- [resolved] Register reflects reality
- [resolved] Serialization — no in-flight branch or worktree for this item
- [resolved] Reconciliation recipe embedded and filled
- [resolved] Execution environment

[Ready to dispatch — all five readiness findings pass.]
| [Not ready — [the named open item].]
```

## 4.3 Pre-print verification

Print only when every answer is yes:

1. Does the summary pass the stranger test, and lead with the descriptive name?
2. Are all five readiness findings reported separately?
3. Is every figure either a value with provenance, or explicitly *not computable*
   with its missing inputs named?
4. Are met/pending markers consistent across the table, the kickoff, and pre-flight?
5. Does the verdict match the findings?
6. If enrichment ran, did the re-audit pass?
7. Is the recipe inside the kickoff's one block — after the `REPOSITORY RECONCILIATION`
   label, indented two spaces, halt line last, with no here-string, heredoc or triple
   backtick — filled with real detected values (remote, default branch, branch name),
   and does it contain only steps `policy.git` permits?
8. If a specification edit is still unreachable from the execution base, is
   repository readiness BLOCKED and the verdict "Not ready"?
9. Is every pre-flight item resolved? Under a Ready verdict there are no open
   items at all.
10. Is the kickoff's Session line present — `[ITEM-ID] — [short name]`, the short name
    being the item's title trimmed to a few words, never blank, and the line naming
    ` · Remote Control:` with its state — so the session is titled before it starts?

Any "no" → fix it before printing. Return to SKILL.md §4.3 and print.
