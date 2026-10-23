# Task rows — the task list every specification carries

**One row format, one home.** Every specification writer — `roadmap-review` D.5.2,
`write-plan` Step 2, and the `epic` plan template's *Current-phase worklist* — writes its
tasks in the table below, and the virtuoso skill opens its time log from it. Rubric check
U10 (`references/readiness-rubric.md`) asks for it. No writer restates the columns in its
own words.

## The table

A specification carries its tasks under a `##### Task list` heading, after
*Implementation detail* and before *Lessons applied*:

```markdown
##### Task list

| # | Task | Class | Kind | Tier | Effort | Estimate | Timebox | Group |
|---|---|---|---|---|---|---|---|---|
| 1 | The rows-from-spec subcommand | repeat | registry subcommand + tests | bounded | medium | 35m (median of 9 runs) | — | — |
| 2 | The task-rows reference | calculable | reference page | bounded | low | 40m | — | — |
| 3 | Class-aware pricing spike | frontier | | cross-cutting | high | — | ≤2h — stop and file an issue | — |

**Total:** chain 1h15m · sum 1h15m + 1 timeboxed ≤2h; 1 of 2 estimated tasks calibrated
```

Rows are outcomes a reviewer can see, at the altitude of the specification — never code
steps. Columns, every one present; `—` or an empty cell means none:

| Column | Holds |
|---|---|
| `#` | The task's number, a positive whole number used once. The time log keeps it from launch to close-out. |
| `Task` | The outcome, in words. |
| `Class` | `calculable` (a formula over cited inputs), `repeat` (the history of its kind prices it) or `frontier` (not estimated: timeboxed). |
| `Kind` | Optional, except on a `repeat` row: the time log warns on one with none. A name for work that recurs across dispatches; reuse one `timing --kinds` lists. |
| `Tier` | Optional. `mechanical`, `bounded` or `cross-cutting`. |
| `Effort` | Optional. The difficulty level — `low`, `medium`, `high`, `xhigh` or `max` — and never a duration. A list written with four levels stays valid. |
| `Estimate` | Every task but a frontier one: its price as a duration — `45m`, `1h30m`, `2h` — with its basis in brackets: `35m (median of 9 runs)`. No bracket reads `estimated`. A frontier task has none: **a frontier task receives no single-number estimate.** |
| `Timebox` | A frontier task only: its budget and the action when the budget runs out, `≤2h — stop and file an issue`. |
| `Group` | Optional. Tasks sharing a group id run side by side. |

Durations live in `Estimate` and `Timebox` only. `Effort` keeps meaning the level.

## The total line

Under the table, one line in this form, as `timing --rows-from-spec` prints it (the
`+ <N> timeboxed` part only when there are frontier tasks; the line ends by naming how
the tasks were priced):

    chain <duration> · sum <duration> + <N> timeboxed ≤<duration>; <n> of <m> estimated tasks calibrated (priced by …)

- **chain** — the longest path through the tasks: a group counts only its longest task.
  The clock forecasts ("done by", "fills the night") read it.
- **sum** — every estimated task. Calibration and the usage limit read it, since tasks
  run side by side spend the limit together. Neither total stands in for the other.
- **timeboxed** — frontier tasks are kept apart, never added to either total.
- **calibrated** — the estimated tasks whose price is a median of measured runs.

## Pricing it

Price the rows, and get the total line, from the measured history with:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . timing --rows-from-spec <spec> --item <ITEM-ID>

It prices each task as `timing --open` would — the median of its kind's runs, else of its
tier and effort, else its own `Estimate`, labelled `estimated` — and prints the rows and the
total line. Exit 1 names what the task list is missing; that is U10's mechanical check.
`--item` locates a specification stored inline in the roadmap.

At launch, the virtuoso skill opens the log from the table:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor virtuoso timing --dispatch <DISPATCH-ID> --open --from-spec <spec> --item <ITEM-ID>

The rows keep their numbers. Each is priced again from the freshest history
(`predicted`, `basis`), and the specification's own price is kept beside it
(`writtenPredicted`, `writtenBasis`).
