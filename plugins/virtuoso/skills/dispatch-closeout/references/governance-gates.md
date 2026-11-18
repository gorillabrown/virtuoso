# Governance Gates

Serves dispatch-closeout SKILL.md, *After the crossing*: the buffer check, the gates to
check once the report is drafted, and the optional adversarial pass.

## Buffer check

Every close-out drains the dispatch buffer by one. Count the remaining
dispatch-ready active items and compare against `policy.roadmap.dispatchBuffer`.
If the count is below target, or the newly elevated head item is a stub,
recommend `/roadmap-review` plainly in the summary.

If `policy.roadmap.dispatchBuffer` is 0 or `policy.roadmap.eagerSpec` is false,
skip this check — the project has deliberately disabled eager specification. Do
not recommend replenishing a buffer the project does not keep. A held plan skips
it too: ad hoc work never drew on the buffer.

Never author a specification here. Flagging depletion is this skill's whole job in
that loop.

## Check These Gates

After the report is drafted, check whether any lesson belongs in a governance
document, and whether one of these should be surfaced:

- **Audit gate**: does this phase boundary require third-party review?
- **Milestone review**: does a stakeholder-facing milestone need a summary?
- **Branch / merge gate**: does the phase close imply merge, tag, or release work?

## Governance Update Rule

Prefer the smallest truthful update set:

- if roadmap status changed, update roadmap
- if queue order changed, update dispatch queue
- if a new trap or lesson surfaced, update the matching governance doc

If nothing changed, say that plainly.

## Optional adversarial pass

Before Wave 2 writes anything, offer `/adversarial-review` over the drafted
report and retrospective **when the close-out carries something the project will
inherit unexamined**: a lesson being promoted to a standing rule, an item declared
complete on partial evidence, or a change that retires scope. Skip the offer for
a routine close-out — a reflexive offer trains the user to decline it. If the pass
runs, fold its blocking concerns into the findings before the crossing begins.

Return to SKILL.md, *After the crossing*.
