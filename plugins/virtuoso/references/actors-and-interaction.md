# Actors and Interaction

## Actors are roles, not products

Every ceremony refers to actors by **role**, never by the name of a product,
vendor, CLI, or model (redesign item 74). The roles, and their default labels:

| Role key | Default label | What it does |
|---|---|---|
| `planner` | planner | authors specifications, runs planning ceremonies, makes decisions |
| `implementer` | implementation agent | executes a dispatch-ready specification |
| `reviewer` | reviewer | reviews work against the specification |
| `operator` | repository operator | performs repository mutations permitted by git policy |

A project renames them in `policy.actors`:

```jsonc
"actors": {
  "planner": "tech lead",
  "implementer": "build agent",
  "reviewer": "second pair of eyes",
  "operator": "release engineer"
}
```

The same human, agent, or session may hold several roles at once. Whether roles
must be held by *different* actors is `policy.git.separationOfDuties` — an
optional project choice (item 65).

## No model hierarchy

Readiness depends on the quality of the specification, never on a claim that one
host or model is inherently more capable than another (item 75). Do not write —
and do not act on — statements of the form "this must be fully specified because
the implementer is a weaker model". The correct reason is: *a specification with
unresolved decisions cannot be executed without inventing them, by anyone.*

The `effort-levels` vocabulary (low / medium / high / max) describes how much
deliberation a task warrants. It is a property of the task, not a ranking of
whoever performs it.

## Interaction adapter

Hosts differ in what they can render (item 76). Adapt, and never let the host's
capabilities change the *content* of a question.

**When the host offers structured questions** (option lists, multi-select):
ask with 2–4 concrete options, exactly one marked *(recommended)*, and an escape
hatch on consequential decisions.

**When it does not**: ask the same question in plain text — a one-line question,
then the options as a short lettered list, then the recommendation:

```
Which register should be authoritative for this project?
  a) the local CSV at docs/work-register.csv   (recommended — it is the file you
     already maintain)
  b) the external board monday:board/1234567890
  c) something else — tell me where it lives
```

Rules that hold in both modes:

- Never ask an open-ended free-text question when a bounded set of options exists.
- Never ask a question whose answer is discoverable from the registry, the
  repository, or the work register — look first.
- Batch related questions rather than interrogating one at a time.
- State the recommendation and *why* in one clause, not a paragraph.

`policy.interaction.mode` may pin this to `structured` or `plain`; the default,
`auto`, uses structured questions when the host offers them.
