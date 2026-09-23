# v1.8.1 Deadline Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A project declares a dated deadline once, in the manifest. Every ceremony then computes pace against it: the rate the date requires against the rate the project delivers, in items and in points, with a verdict. Today an operator derives that by hand and copies the date into six documents.

**Architecture:** A deadline has two halves. The *value* is a typed `policy.roadmap.deadlines.<id>` entry written by `policy-set`. The *body* is the roadmap heading that defines the finish line it dates. A pure pace engine reads the snapshot `kpis` already reads, plus dated completions from the terminal ledger. It returns each figure, or the inputs that figure lacks. `kpis`, the cockpit and a fourth session-start line surface the result, and four ceremonies read it instead of deriving it. Nine tasks on one branch, in dependency order.

**Tech Stack:** Python 3.12 (CI) / 3.14 (dev machine), pytest, GitHub Actions (`ubuntu-latest` + `windows-latest`), the plugin's own `validate.py`, `bump_version.py` and `release.py`.

**Evidence:** the Gloves of Glory roadmap review of 2026-09-22. The owner set 2027-01-01 for "the overall game build", and the session found nowhere in the plugin to put it. Its figures are Task 3's acceptance fixture.

---

## What the 2026-09-22 session hit

| # | Observed | Cause in the plugin | 1.8.1 answer | Task |
|---|---|---|---|---|
| 1 | No deadline or target-date policy key | `policy.DEFAULTS` has none | `policy.roadmap.deadlines.<id>`: typed, validated, written by `policy-set` | 2 |
| 2 | `finish_line:` looked like a place for a date | It is a roadmap-detection marker in `discovery.py`. Nothing reads a value from it | Unchanged, and the contract says so. What a finish line *means* is the deadline's `finishLine` body | 5, 8 |
| 3 | Pace computed by hand: 60 items / 235.5 points remaining; 2.50 (3.00 with qualified) completions a week; 4.16 items and 16.32 points a week required | `kpi.compute` takes no date and reads no completion date | A pace engine, surfaced by `kpis` | 3, 4 |
| 4 | "Pace against a deadline remains not computable: no dated deadline exists" | `roadmap-review` B.2 names pace, but nothing computes it | B.2 reads the `pace` block | 8 |
| 5 | Which finish line is "the overall game build": B1, B2, B3, C, or all of them? | Nothing asks | `scope` says which items count (mechanical). `finishLine` says what done means (the body). The output always prints the scope, and an unanchored deadline is a finding | 2, 5 |
| 6 | Would a registry guard revert a `policy-set`? | It would not. `apply_plan` restores only when the write or its re-validation fails, and no plugin hook writes | `policy-set` reads the value back from disk and says so. The contract states the guarantee. The session-start line makes any later revert visible at the next session | 2, 6, 8 |
| 7 | The date was headed for the roadmap, assessment, phase brief, memory, charters and board | No single authority existed | The manifest is the authority. Every surface reads and cites it, and ceremonies are told not to copy it | 6, 8 |
| 8 | 85.4% of remaining points held or blocked: the real constraint on pace | No figure for blocked effort | The blocked share of remaining scope, reported beside the verdict | 3 |

**Found while tracing row 3, in scope because pace in points depends on it (Task 1).** `roadmap-review`'s policy table documents `roadmap.effortScale`, and `kpis` reads it. It is not in `DEFAULTS`, so `policy-set roadmap.effortScale` is refused as "not a documented key". The docs-contract test missed this because it matches only keys spelled `policy.x.y`, and that table spells them `x.y`.

---

## Decisions: approve or redirect before Task 1

**D1. Deadlines are a mapping keyed by id, not a list.**
- `policy-set roadmap.deadlines.game-build` adds or replaces one deadline.
- `policy-set roadmap.deadlines.game-build.date` moves one date.
- `--value-json null` on an id withdraws it.

A list could only be replaced whole, so adding a second deadline would mean restating the first, which is how one gets dropped. The cost: `policy.py` learns *open mappings*, documented keys whose children the project names.

**D2. `date` and `owner` are required. `finishLine` and `scope` are optional and reported.** A date nobody owns is not a ruling. A deadline without `finishLine` still computes pace, but it is reported `deadline-unanchored` (info). A `finishLine` the roadmap does not define is `deadline-finish-line-missing` (warning). Neither is ever error severity. As with overlay findings, the project fixes these, and `repair` has nothing to propose.

**D3. Scope defaults to every item in the register, and the output always prints the scope.** This matches GoG's own reading ("all remaining work"). Because the scope is printed, a wrong assumption is visible.
- A narrower scope selects on one register field, for example `{"field": "group", "values": ["B3", "C"]}`. The field can be canonical `lane`, `group` or `id`, or a register column the provider exposes verbatim.
- A scope that matches no item is **not computable**, never "met".

**D4. The trailing rate is project-wide delivery capacity.** It is counted from the terminal ledger. When no ledger is registered, it falls back to the register's completion dates. A per-scope trailing rate would need every completed item's scope, and a register that drops finished items (GoG's board) cannot supply it. The output labels the rate project-wide.

**D5. A completion is a record whose result maps to canonical `completed`, shown with a per-word breakdown.**
- The status mapper's prefix rule maps "completed (qualified)" to `completed`. GoG's figure is therefore 3.00 a week, printed as "completed ×10, completed (qualified) ×2", so the strict 2.50 stays readable.
- Dissolved and superseded results take work out of scope. They are not delivery, and are listed as excluded.

**D6. A verdict per unit; the headline is the worse of the two.**
- The verdicts are `ahead`, `on track` and `behind`. `policy.roadmap.pace.tolerance` (default 0.10) sets the band: within ±10% of the required rate is on track.
- `met` means nothing in scope remains. `overdue` means the date has arrived with work remaining.
- The headline names the unit that drove it. It keeps the vocabulary `next-pointer` already documents (On track / Behind / Ahead).

**D7. A fourth session-start line, `deadlines:`.** It carries the date and days remaining only, read from the manifest. It never carries pace, because session start must not read a register that may be external. It follows the `overlays:` precedent: always printed, survives `--quiet`, always states a result, including `none declared`.

**D8. Version 1.8.1, released by `release.py` from `main`.**
- The change is additive and needs no registry schema change: `policy` is free-form and `create` writes `policy: {}`.
- Writer output is therefore unchanged, and the regen-diff gate should pass without `--allow-regen-diff`.
- The branch keeps `1.8.0` in its manifests. `release.py 1.8.1` performs the bump, as designed, so no `--redeploy` is needed.

---

## Design

### The declaration

```json
"policy": {
  "roadmap": {
    "deadlines": {
      "game-build": {
        "date": "2027-01-01",
        "owner": "Evan",
        "label": "Overall game build",
        "finishLine": "Finish Line C",
        "scope": {"field": "group", "values": ["B1", "B2", "B3", "C"]},
        "recorded": "2026-09-22"
      }
    },
    "pace": {"trailingWeeks": 4, "tolerance": 0.1}
  }
}
```

| Field | Required | Rule |
|---|---|---|
| the id (key) | yes | `[A-Za-z0-9][A-Za-z0-9_-]*`, with no dots, so it is exactly one dotted-path segment |
| `date` | yes | ISO `YYYY-MM-DD`, a real calendar date. Due by the end of that day |
| `owner` | yes | Non-empty string: who ruled |
| `label` | no | String. The output uses the id when absent |
| `finishLine` | no | Heading text in the registered roadmap that defines done: the body |
| `scope` | no | `{"field": str, "values": [str, …]}`, both non-empty. Absent or `{}` means every item |
| `recorded` | no | ISO date the deadline was set or last moved |
| anything else | — | Refused. A misspelled field is stored and ignored, which reads as configured and is not |

`roadmap.pace.trailingWeeks` is an integer from 1 to 52 (default 4). `roadmap.pace.tolerance` is a number with 0 ≤ t < 1 (default 0.1). Booleans are refused for both, because `isinstance(True, int)` is true.

### The body

`finishLine` is matched the way the pairing rule matches a body, with `overlays.body_heading`. The match runs against the registered `roadmap` document, with fenced blocks blanked by `overlays.without_fenced_blocks`. A match is a depth 2–4 heading that starts with the text, in any case, and is not followed by a word character or hyphen.

With GoG's roadmap:
- "Finish Line B3" matches `### Finish Line B3 — Engine + full strategic layer…`.
- "Finish Line B" matches `## Finish Line B — Target…` and not `### Finish Line B1 — …`.

| Finding | Severity | When |
|---|---|---|
| `deadline-unanchored` | info | The deadline names no `finishLine`. Pace is computed over its scope, but nothing defines done |
| `deadline-finish-line-missing` | warning | `finishLine` names a heading the registered roadmap does not have, or no roadmap is registered |
| `deadline-invalid` | warning | A hand-edited entry fails validation. `policy-set` refuses such an entry outright, so this only reports edits made around it |

### The computation: `tools/governance/providers/pace.py`, pure

The engine has no I/O and no clock. "As of" is the snapshot's date, so a stale snapshot yields pace as of its own date, flagged stale.

1. **As of.** `asOf = date(snapshot.taken_at)`, `daysRemaining = (deadline − asOf).days`, `weeksRemaining = daysRemaining / 7`.
2. **Scope.** Select every item, or the items whose field is one of the values. The canonical attribute is checked first, then the item's verbatim `extra` columns. Zero selected is **not computable**, naming why: "no work item carries group ∈ {B3}" or "the register has no work items".
3. **Remaining.** The non-terminal items in scope. Points use the effort scale; an item with no effort or no scale entry makes points not computable and is named. This is the rule `total-effort` already uses.
4. **Blocked.** Canonical `blocked` items and points within remaining, with the blocked share of remaining points and of remaining items.
5. **Required.** Remaining ÷ `weeksRemaining`, per unit. Remaining 0 is `met`. `daysRemaining ≤ 0` with work remaining is `overdue`, with no rate.
6. **Completions.**
   - When a `terminalLedger` role is registered, completions come from the ledger. Corrections apply: a record whose `corrects` names another record replaces it (last one wins), and is not itself counted.
   - A registered ledger whose file is missing makes the rate not computable, with the file named.
   - With no ledger registered, completions are register items that are canonical `completed` and carry a `completed` date.
   - If neither is available, the rate is not computable: "completion dates: no terminal ledger is registered and the register carries no completion date".
7. **Trailing window.** `(asOf − 7·trailingWeeks days, asOf]`, which for GoG is 2026-08-26 … 2026-09-22.
   - It counts distinct items whose effective record maps to `completed`, dated inside the window.
   - A record whose date does not start `YYYY-MM-DD` makes the trailing rate not computable, naming up to five records. A count that might be wrong is not reported.
   - If the earliest dated record is later than the window start, a note says the rate may understate delivery from before the record began.
8. **Trailing points.** Each counted item's effort, joined by id to the register. A counted item that is absent from the register or unsized makes trailing points not computable, and it is named. Items still stand.
9. **Verdict per unit.** `ahead` if T > R·(1+tol); `on track` if T ≥ R·(1−tol); otherwise `behind`. The headline is the worst computable unit verdict in the order overdue < behind < on track < ahead < met, and names its unit or units. If neither unit is computable, the verdict is `not computable`, with every missing input.
10. **Projection.** When T > 0, `asOf + ceil(7 · remaining / T)` days, per unit. When T = 0: "no completions in the trailing window; no projection".

Rates and weeks round to 2 dp, shares to 1 dp, and days are integers. Every figure is computed unrounded and rounded only for output.

### Output

`kpis --json` gains `"pace"`: one object per deadline, sorted by date. The existing `metrics` and `provenance` keys are unchanged.

```json
{"deadline": {"id": "game-build", "label": "Overall game build", "date": "2027-01-01",
              "owner": "Evan", "finishLine": "", "scope": "every item in the register",
              "recorded": "2026-09-22"},
 "asOf": "2026-09-22", "stale": false, "daysRemaining": 101, "weeksRemaining": 14.43,
 "remaining": {"items": 60, "points": 235.5},
 "blocked": {"items": 20, "points": 201.0, "shareOfPoints": 85.4, "shareOfItems": 33.3},
 "required": {"items": 4.16, "points": 16.32},
 "trailing": {"items": 3.0, "points": null, "projectWide": true,
              "window": {"from": "2026-08-26", "to": "2026-09-22", "weeks": 4},
              "completions": 12,
              "byResult": {"completed": 10, "completed (qualified)": 2},
              "excluded": {"dissolved": 1},
              "source": "terminalLedger: <registered path>"},
 "verdict": "behind", "basis": ["items"],
 "reason": "trailing 3.00 items/week is 72% of the 4.16 required",
 "projectedFinish": {"items": "2027-02-09", "points": null},
 "missingInputs": {"trailing.points": ["effort for 12 completed item(s) absent from the register: …"]},
 "findings": [{"code": "deadline-unanchored", "severity": "info", "message": "…"}],
 "notes": []}
```

The text form, added to `MetricSet.render()`, looks like this with GoG's figures:

```
pace
  game-build  Overall game build: due 2027-01-01, owner Evan
    as of 2026-09-22 (snapshot): 101 days, 14.43 weeks remain
    scope:    every item in the register: 60 items, 235.5 points remain
              blocked: 20 items, 201.0 points (85.4% of remaining points)
    required: 4.16 items/week, 16.32 points/week
    trailing: 3.00 items/week over 2026-08-26..2026-09-22, project-wide
              12 completions: completed ×10, completed (qualified) ×2; excluded: dissolved ×1
              points/week not computable (missing: effort for 12 completed item(s) absent from the register: …)
    verdict:  BEHIND on items: 3.00/week is 72% of the 4.16 required
    projected finish at the trailing rate: 2027-02-09, 39 days after the deadline
    finding:  deadline-unanchored: no finishLine names the roadmap heading that defines done
```

The session-start line, on 2026-09-23: `deadlines: game-build 2027-01-01 (100 days); 1 finding`.

### One authority

- The date lives in `policy.roadmap.deadlines` and nowhere else.
- The roadmap's finish-line section *defines* what done means and points at the policy for the date.
- Reviews, briefings and assessments cite the computed pace *as of* their own date. That is history, not a second authority.
- Memory, charters and boards point at the policy rather than repeat the date.

The plugin never reverts a successful `policy-set`. `apply_plan` restores from the backup only when the write itself or the post-write re-validation fails, and it says so. A project that runs its own guard over the manifest should let `policy-set` writes through. Each one leaves a backup set labelled `policy-set` that names the ceremony which asked.

---

## Touchpoints

| File (under `plugins/virtuoso/` unless rooted) | Change | Task |
|---|---|---|
| `tools/governance/policy.py` | `DEFAULTS`: `roadmap.effortScale`, `roadmap.deadlines`, `roadmap.pace`. `DEADLINE_TEMPLATE`, `OPEN_MAPPINGS`, open-mapping walk in `documented_default`, `open_child`, `withdraw`, `iso_date`, `deadline_problems`, `pace_problems`. `validate()` calls both | 1, 2 |
| `scripts/virtuoso_registry.py` | `policy-set`: withdraw with `null`; read-back verification. `kpis`: attaches pace | 2, 4 |
| `tools/governance/deadlines.py` (new) | `Deadline` parsing, `anchor_findings`, `summary` for the session line | 5, 6 |
| `tools/governance/providers/pace.py` (new) | The pure engine: `Completion`, `PaceReport`, `compute`, `compute_all` | 3 |
| `tools/governance/providers/__init__.py` | `completion_source(reg, snapshot)`: read-only, ledger first, register second | 3 |
| `tools/governance/providers/kpi.py` | `MetricSet.pace`, `as_dict()["pace"]`, and the `render()` block | 4 |
| `tools/governance/result.py` | `deadlines` / `deadlines_detail`, `deadline_line()`, the JSON key, and the docstring's line contract | 6 |
| `scripts/virtuoso_preflight.py` | `_deadline_status`, `_attach_deadlines`; `emit` prints the line in every mode | 6 |
| `tools/roadmap_visualizer/generate.py`, `render.py`, `health.py` | Pace in the model; Deadline and Pace tiles; a behind or overdue verdict in the recommendation | 7 |
| `skills/roadmap-review/SKILL.md` | Policy-table rows; B.2 reads the `pace` block; recording a set or moved deadline; Phase C's response to behind/overdue | 8 |
| `skills/roadmap-status/SKILL.md` | 1.3 figures; 1.4 pace signal; the Health pace line; the "Where we stand" finish-line line | 8 |
| `skills/next-pointer/SKILL.md` | Pace comes from `kpis`, not the last assessment; Pipeline rows Deadline and Pace | 8 |
| `skills/project-profile/SKILL.md` | Catalogue row; Phase 3 preview line; Phase 4 command | 8 |
| `references/registry-contract.md` | New "Deadlines and pace" section; the preflight contract's fourth line; the JSON key | 6, 8 |
| `scripts/test_deadlines.py` (new) | Declaration, validation, `policy-set`, anchoring, the session line | 1, 2, 5, 6 |
| `scripts/test_pace.py` (new) | The engine including the GoG fixture; `kpis`; the cockpit | 3, 4, 7 |
| `scripts/test_docs_contract.py` | Policy tables checked; `policy-set` in the subcommand check; verdicts and findings documented | 1, 8 |
| `scripts/test_status_contract.py` | The fourth line, in every mode | 6 |
| `scripts/release.py` | Docstring only: step 3 and step 4 still say "two files"; the set is derived from `.version-bump.json` (three) | 9 |
| `RELEASE-NOTES.md`, `docs/superpowers/specs/2026-09-17-project-specificity-architecture-design.md` (repo root) | v1.8.1 section; the v1.8.0 record corrected to "released" | 9 |

**Deliberately unchanged:**
- `discovery.py`: `finish_line:` stays a detection marker.
- `schema.py`: no schema change.
- Everything `create`, `adopt` and `repair` write.
- `build_register_report.py`: a presentation output, deferred.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **Branch:** `eb/zealous-einstein-zxvy3w`, level with `origin/main` at `fcf907c`. Never push `main` without the owner's explicit go-ahead. The 1.8.0 permission covered 1.8.0 only.
- **Green after every task.** `validate.py` prints `All checks passed.`, `pytest plugins/virtuoso/ -q` passes, and after every push **both CI legs are read**, not assumed.
- **Pace never approximates.**
  - A figure with a missing input is `not computable`, with the input named.
  - No figure silently becomes zero.
  - An empty scope never reads as `met`.
  - An undatable completion never drops out of a count.
- **No clock in the engine.** "As of" is the snapshot date. The session line uses today's local date through one injectable function.
- **Deadline findings are never `error` severity.** A deadline problem must not flip a usable registry to `repair-needed`.
- **Writer output does not change.** The regen-diff gate must stay byte-identical. If any task changes what `create`, `adopt` or `repair` writes, stop and flag it.
- **The manifest version stays `1.8.0` on the branch.** `release.py 1.8.1` performs the bump.
- **Windows.** Fixtures write bytes with explicit newlines. Nothing assumes `/`. CLI tests pass JSON as a list argument, never through a shell.
- **Stage exact paths.** No `git add -A`, force-push, reset, clean or destructive restore.

---

## Before you start

The branch head `fcf907c` equals `origin/main`, and the working tree is clean. Confirm both before Task 1:

```bash
cd /home/user/virtuoso
git fetch origin main && git rev-list --left-right --count HEAD...origin/main   # expect 0 0
git status --short                                                                # expect nothing
python plugins/virtuoso/scripts/validate.py && python -m pytest plugins/virtuoso/ -q
```

---

### Task 1: `roadmap.effortScale` becomes a real key; policy tables are contract-checked

**Files:** modify `tools/governance/policy.py`, `scripts/test_docs_contract.py`; create `scripts/test_deadlines.py`.

- [ ] **Step 1: Write the failing tests.**
  - `test_every_policy_table_key_exists` (docs contract). Scan every markdown table whose header's first cell is `Policy` and collect the backticked first cell of each row. Every key must be in `DEFAULTS`. **This fails today on `roadmap.effortScale`.**
  - `test_effort_scale_is_settable`. `policy-set roadmap.effortScale --value-json '{"s": 1, "m": 3}'` previews without refusal, and `--apply` writes it.
  - `test_an_empty_effort_scale_means_the_generic_scale`. `kpi.compute` gives identical metrics for `effort_scale=None` and `effort_scale={}`.
- [ ] **Step 2: Run them and see them fail** for the stated reason.
- [ ] **Step 3: Add the key.** In `DEFAULTS["roadmap"]`, add `"effortScale": {}` with the comment `# size -> points; {} means the generic t-shirt scale in providers/kpi.py`. `_deep_merge` over `{}` yields the project's own scale, and never a union with the generic one. A union would silently price a mistyped size.
- [ ] **Step 4:** Tests pass; run `validate.py`.
- [ ] **Step 5: Commit.** `fix(policy): roadmap.effortScale is a documented key, and policy tables are checked`.

### Task 2: The declaration: `policy.roadmap.deadlines` and `policy.roadmap.pace`

**Files:** modify `tools/governance/policy.py` and `scripts/virtuoso_registry.py`; extend `scripts/test_deadlines.py`.

- [ ] **Step 1: Write the failing tests.**
  - `test_deadlines_and_pace_are_documented`: `is_documented` holds for `roadmap.deadlines`, `roadmap.pace.trailingWeeks` and `roadmap.pace.tolerance`.
  - `test_a_project_named_deadline_is_documented`: `is_documented` holds for `roadmap.deadlines.game-build` and `roadmap.deadlines.game-build.date`, and fails for `roadmap.deadlines.game-build.dat`.
  - `test_deadline_validation_names_each_problem`, parametrized over:
    - date `"2027-13-01"`
    - date `"01/01/2027"`
    - a missing date
    - a missing owner
    - an empty owner
    - an unknown field `dat`
    - the id `"b3.final"`
    - `scope` with empty `values`
    - `scope` with an extra key
    - `recorded` `"yesterday"`
    - an entry that is a string

    Each yields one problem naming the field.
  - `test_pace_validation`: rejects `trailingWeeks` of 0, 53, `true` and `"4"`, and `tolerance` of 1, -0.1 and `true`.
  - `test_policy_set_adds_a_deadline_beside_another`. With `alpha` declared, setting `beta` leaves `alpha` byte-for-byte in the manifest.
  - `test_policy_set_moves_one_date`. Setting `roadmap.deadlines.alpha.date` changes only the date.
  - `test_setting_a_field_of_an_undeclared_deadline_is_refused`. Setting `roadmap.deadlines.nope.date` is refused because `owner` is required, and nothing is written.
  - `test_null_withdraws_a_deadline`. `--value-json null` on `alpha` removes it and `beta` survives.
  - `test_null_on_an_undeclared_deadline_is_refused`: "nothing to withdraw".
  - `test_null_is_still_refused_where_it_withdraws_nothing`. `null` on `rubric.extensions` is still the type error it is today.
  - `test_policy_set_reads_the_value_back`. The `--apply` output carries `verified: read back from disk`, and the JSON carries `"verified": true`.
- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Extend `policy.py`.** The sketch below is binding in behaviour and free in wording:

```python
import datetime as _dt
import re

DEFAULTS["roadmap"] gains:
    "effortScale": {},                    # Task 1
    "deadlines": {},                      # id -> DEADLINE_TEMPLATE-shaped entry; none by default
    "pace": {"trailingWeeks": 4, "tolerance": 0.1},

#: What one deadline holds. The project names the children of ``roadmap.deadlines``,
#: so the defaults cannot list them; this documents their fields and types.
DEADLINE_TEMPLATE: dict = {
    "date": "",                               # required: YYYY-MM-DD; due by the end of that day
    "owner": "",                              # required: who ruled
    "label": "",
    "finishLine": "",                         # the roadmap heading that defines done
    "scope": {"field": "", "values": []},     # absent or {} => every item in the register
    "recorded": "",                           # YYYY-MM-DD it was set or last moved
}

#: Documented mappings whose keys a project names.
OPEN_MAPPINGS: dict = {"roadmap.deadlines": DEADLINE_TEMPLATE}

_DEADLINE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def documented_default(path: str):
    cursor = DEFAULTS
    walked: list[str] = []
    for part in path.split("."):
        template = OPEN_MAPPINGS.get(".".join(walked))
        if template is not None and part:
            cursor = template            # a project-named entry: documented by its template
        elif not isinstance(cursor, dict) or part not in cursor:
            return _MISSING
        else:
            cursor = cursor[part]
        walked.append(part)
    return cursor


def open_child(path: str) -> bool:
    parent, _, leaf = path.rpartition(".")
    return bool(leaf) and parent in OPEN_MAPPINGS


def withdraw(raw: dict | None, path: str) -> dict:
    """``raw`` without the open-mapping entry at ``path``. Pure; siblings survive."""


def iso_date(value) -> _dt.date | None:
    """A strict ``YYYY-MM-DD`` calendar date, or None. ``fromisoformat`` alone is not
    strict enough: 3.11+ also accepts ``20270101`` and week dates."""


def deadline_problems(deadlines) -> list[str]: ...   # every rule in the declaration table
def pace_problems(pace) -> list[str]: ...
```

  `Policy.validate()` appends both problem lists. `policy-set` already validates the whole candidate policy, so a malformed deadline is refused before anything is written.

- [ ] **Step 4: Extend `cmd_policy_set`.**
  - **Withdraw.** When `value is None and policy_mod.open_child(args.key)`, skip `type_problem` and build the candidate with `withdraw`. An absent entry is refused with "nothing to withdraw".
  - **Read back after `--apply`.** Re-load the registry from disk and compare `policy_mod.load(reloaded.policy).get(args.key)` with the value. A withdrawal compares with `None`.
    - If they differ, raise a `GovernanceError` that names both values and the backup set.
    - Otherwise print `  verified: read back from disk` and add `"verified": true` to the JSON.
- [ ] **Step 5:** Tests pass; `validate.py`; the full suite.
- [ ] **Step 6: Commit.** `feat(policy): dated deadlines, declared once and written through policy-set`.

### Task 3: The pace engine

**Files:** create `tools/governance/providers/pace.py` and `scripts/test_pace.py`; modify `tools/governance/providers/__init__.py`.

- [ ] **Step 1: Build the GoG acceptance fixture** in `test_pace.py`. It is synthetic, but its totals are the 2026-09-22 review's.
  - **Snapshot** taken `2026-09-22T12:00:00Z`, using the generic effort scale.
    - 40 unblocked items: 30 `xs`, 6 `s-m`, 2 `m`, 2 `xs-s`, totalling 34.5 points.
    - 20 blocked items: 5 `xl`, 11 `l`, 2 `m-l`, 1 `s`, 1 `s-m`, totalling 201.0 points.
    - 60 items and 235.5 points in all.
  - **Ledger** (markdown, the documented six columns), inside the window:
    - 10 records with result `completed`
    - 2 with `completed (qualified)`
    - 1 with `dissolved`
  - **Ledger**, outside it: one `completed` record dated `2026-08-25`, the day before the window opens.
  - **Deadline:** `game-build`, `2027-01-01`, owner `Evan`, no scope, no finishLine.
- [ ] **Step 2: Write the failing tests.**
  - `test_gog_figures`. Assert `daysRemaining` 101, `weeksRemaining` 14.43, required 4.16 items and 16.32 points, trailing 3.00 items, completions 12, `byResult` {completed: 10, completed (qualified): 2}, `excluded` {dissolved: 1}, verdict `behind` on `["items"]`, projected items finish `2027-02-09`, and blocked share of points 85.4.
  - `test_gog_trailing_points_are_not_computable_when_finished_items_left_the_register`. The completed items are absent from the snapshot, as on GoG's board, so trailing points are not computable, the items are named, and the verdict still stands on items.
  - `test_trailing_points_when_the_register_keeps_finished_items`. With the completed items present and sized, points are computed and the headline is the worse unit.
  - `test_the_window_is_half_open`. Dated `asOf − 28 days` is excluded, `asOf − 27 days` is included, and `asOf` is included.
  - `test_an_undatable_record_makes_trailing_not_computable`. The record is named, and no count is reported.
  - `test_a_correction_replaces_what_it_corrects`. A `completed` record corrected to `dissolved` leaves the count.
  - `test_register_completion_dates_when_no_ledger_is_registered`.
  - `test_no_completion_source_is_not_computable_and_says_why`.
  - `test_a_registered_ledger_whose_file_is_missing_is_named`.
  - `test_scope_by_group`, `test_scope_by_extra_column`, `test_scope_by_id`.
  - `test_a_scope_matching_nothing_is_not_computable_never_met`, and the same for an empty register.
  - `test_every_scoped_item_terminal_is_met`.
  - `test_a_passed_date_with_work_remaining_is_overdue`, including the deadline day itself (`daysRemaining` 0).
  - `test_no_completions_in_the_window_is_behind_with_no_projection`.
  - `test_tolerance_bands`, parametrized. With R = 4 and tol = 0.1: T = 3.5 is behind, T = 3.6 is on track, T = 4.4 is on track, T = 4.41 is ahead.
  - `test_ties_name_both_units`.
  - `test_a_stale_snapshot_is_flagged_and_measured_as_of_its_own_date`.
  - `test_ledger_history_shorter_than_the_window_is_noted`.
  - `test_deadlines_are_reported_in_date_order`.
- [ ] **Step 3: Implement `pace.py`.** Define `Completion(item_id, date, raw_date, result, canonical, record)` and `PaceReport` with `as_dict()` / `render()`. `compute(deadline, snapshot, source, *, effort_scale, trailing_weeks, tolerance)` implements steps 1–10 of *The computation*. `compute_all` handles every declared deadline. The verdict core:

```python
#: Worst first. The headline is the worst verdict among the units that computed.
VERDICTS = ("overdue", "behind", "on track", "ahead", "met")


def unit_verdict(required: float, trailing: float, tolerance: float) -> str:
    if trailing > required * (1 + tolerance):
        return "ahead"
    if trailing >= required * (1 - tolerance):
        return "on track"
    return "behind"
```

- [ ] **Step 4: Add `providers.completion_source(reg, snapshot)`.** It returns `(completions, source_label, missing)`.
  - It is read-only and takes no actor, because reading the ledger mutates nothing.
  - The ledger comes first when its role is registered, with the format from `policy.terminalLedger.format`.
  - Otherwise it reads the snapshot's `completed` field.
  - Results are canonicalised through `mapping.StatusMapping.to_canonical`, the same vocabulary `kpis` uses.
- [ ] **Step 5:** Tests pass; `validate.py`; the full suite.
- [ ] **Step 6: Commit.** `feat(pace): required against trailing rate, in items and points, never approximated`.

### Task 4: `kpis` carries pace

**Files:** modify `tools/governance/providers/kpi.py` and `scripts/virtuoso_registry.py`; extend `scripts/test_pace.py`.

- [ ] **Step 1: Write the failing tests.**
  - `test_kpis_json_carries_a_pace_block`. On a workspace fixture with one deadline, the `pace` list has one object with the keys shown under *Output*. `metrics` and `provenance` are unchanged.
  - `test_kpis_json_pace_is_empty_without_deadlines`. With no deadlines, `pace` is `[]`.
  - `test_kpis_text_renders_the_verdict_and_the_missing_inputs`.
  - `test_kpis_reports_a_hand_edited_invalid_deadline`. It appears as `deadline-invalid` with pace not computable, rather than as a crash.
- [ ] **Step 2: Implement.**
  - Add `MetricSet.pace: list` (default empty). `as_dict()` adds `"pace"`, and `render()` appends the block.
  - `cmd_kpis` builds the source with `completion_source`, then calls `pace.compute_all` with `roadmap.pace` and `roadmap.effortScale`.
  - `kpi.compute` keeps its signature. Pace is attached by the callers that have a registry.
- [ ] **Step 3:** Tests pass; `validate.py`.
- [ ] **Step 4: Commit.** `feat(kpis): pace against every declared deadline`.

### Task 5: The body: `finishLine` resolves to a roadmap heading

**Files:** create `tools/governance/deadlines.py`; extend `scripts/test_deadlines.py`.

- [ ] **Step 1: Write the failing tests** against a roadmap written as GoG's is.
  - `test_finish_line_matches_its_heading` for B3, C and B.
  - `test_a_shorter_finish_line_does_not_match_a_longer_heading`. B must not match B1.
  - `test_a_heading_inside_a_fence_does_not_count`, with LF and CRLF.
  - `test_an_unanchored_deadline_is_info` and `test_a_missing_heading_is_a_warning`.
  - `test_no_registered_roadmap_is_a_missing_heading`.
  - `test_deadline_findings_are_never_errors`. The registry status stays `ready` or `warning`.
- [ ] **Step 2: Implement `deadlines.py`.**
  - `Deadline` is the parsed entry.
  - `declared(policy) -> (list[Deadline], problems)` skips invalid entries and reports them.
  - `anchor_findings(reg, deadlines) -> list[registry.Finding]` reuses `overlays.body_heading` and `overlays.without_fenced_blocks`.
  - The engine's `findings` come from here.
- [ ] **Step 3:** Tests pass; `validate.py`.
- [ ] **Step 4: Commit.** `feat(deadlines): a deadline names the finish line that defines done`.

### Task 6: The session-start line `deadlines:`

**Files:** modify `tools/governance/result.py`, `scripts/virtuoso_preflight.py`, `scripts/test_status_contract.py` and `references/registry-contract.md` (the preflight contract section); extend `scripts/test_deadlines.py`.

The line has one form per state:

| State | Line |
|---|---|
| unregistered or unreadable | `deadlines: not registered` |
| none declared | `deadlines: none declared` |
| one | `deadlines: game-build 2027-01-01 (100 days)` / `(1 day)` / `(due today)` / `(passed 3 days ago)` |
| several | `deadlines: 2 declared; next game-build 2027-01-01 (100 days)`. "Next" is the earliest not yet passed; if every date has passed, it is the most recent |
| findings | the suffix `; N finding(s)`, as the `overlays:` line does |
| hand-edited and invalid | `deadlines: invalid (<first problem>)` |

- [ ] **Step 1: Write the failing tests.**
  - `test_summary_forms`. A pure `deadlines.summary(declared, problems, findings, today)` covers every row of the table, including singular "1 day".
  - `test_the_deadline_line_is_printed_in_every_mode_and_survives_quiet`. This runs as a subprocess in every mode `test_status_contract` already exercises. It asserts the line's *shape* by regex against a `2099-01-01` deadline, so the test does not depend on the calendar.
  - `test_the_two_line_contract_is_unchanged`. `parse_contract` still reads the status and the write count.
  - `test_preflight_json_carries_deadlines`.
  - `test_a_deadline_problem_never_fails_preflight`. The line is a side observation and is total, as `_overlay_status` is.
- [ ] **Step 2: Implement.**
  - `result.Result` gains `deadlines: str = "not registered"`, `deadlines_detail`, and `deadline_line()`.
  - `emit` prints the line after the overlay line.
  - `_attach_deadlines` is attached at the one place `_attach_overlays` is.
  - "Today" comes from a single module-level `_today()`, which in-process tests patch.
- [ ] **Step 3: Document it.** The result docstring and the registry contract's *Preflight status contract* gain the fourth line, stating that it is not part of `contract_lines()`.
- [ ] **Step 4:** Tests pass; `validate.py`; the full suite. The status-contract and docs-contract tests catch an undocumented JSON key.
- [ ] **Step 5: Commit.** `feat(preflight): every session starts knowing its deadlines`.

### Task 7: The cockpit

**Files:** modify `tools/roadmap_visualizer/generate.py`, `render.py` and `health.py`; extend `scripts/test_pace.py`.

- [ ] **Step 1: Write the failing tests.**
  - `test_the_cockpit_model_carries_pace`.
  - `test_the_cockpit_renders_deadline_and_pace_tiles`. This is a string check on the rendered HTML: the verdict text, the date, and "not computable" with missing inputs where applicable.
  - `test_behind_or_overdue_becomes_the_recommendation_after_drift_and_buffer`. Stale, drift, all-blocked and buffer keep their priority. Pace replaces "Proceed" only.
- [ ] **Step 2: Implement.**
  - `build_model` computes pace through the same `completion_source` and `compute_all`, and puts `"pace"` into `metrics`.
  - The `render.py` tiles are "Deadline" (`label date (N days)` or `none declared`) and "Pace" (the verdict, plus "X vs Y /week").
  - `_recommendation` takes the headline verdict.
- [ ] **Step 3:** Tests pass; `validate.py`.
- [ ] **Step 4: Commit.** `feat(cockpit): deadline and pace tiles`.

### Task 8: The ceremonies and the contract read pace instead of deriving it

**Files:** modify `skills/roadmap-review/SKILL.md`, `skills/roadmap-status/SKILL.md`, `skills/next-pointer/SKILL.md`, `skills/project-profile/SKILL.md`, `references/registry-contract.md` and `scripts/test_docs_contract.py`.

- [ ] **Step 1: Write the failing docs-contract tests.**
  - `test_the_registry_contract_documents_every_pace_verdict`, over `pace.VERDICTS`.
  - `test_the_registry_contract_documents_every_deadline_finding`.
  - Extend `test_every_documented_registry_subcommand_exists` so its pattern includes `policy-set`.
- [ ] **Step 2: `registry-contract.md` gains a section, "Deadlines and pace".** It covers:
  - the key and its fields
  - one authority, and what must not hold a copy
  - scope, and why an empty scope is not computable
  - the completion source order
  - the window
  - the verdicts and the tolerance
  - the not-computable rules
  - the findings table
  - `finish_line:` is a detection marker, not a date
  - the guarantee: a successful `policy-set` is never reverted by the plugin, and guidance for project-side guards
- [ ] **Step 3: `roadmap-review`.**
  - The policy table gains `roadmap.deadlines`, `roadmap.pace.trailingWeeks` and `roadmap.pace.tolerance`.
  - **B.2 Pace** reads the `pace` block of the same `kpis --json` call. It reports:
    - the verdict and its reason
    - the scope
    - the projected finish
    - the blocked share
    - each not-computable figure, with its missing inputs
  - With no deadline declared, B.2 says so. "Pace against a date is not computable" then has a stated cause.
  - **Recording a deadline the owner sets or moves.**
    - First ask which finish line the date is for and which items count; the answers are `finishLine` and `scope`.
    - Then preview with `policy-set roadmap.deadlines.<id> --actor roadmap-review` and apply on approval.
    - Record the ruling in the roadmap's finish-line section as prose that points at the policy.
    - Never copy the date into memory, charters or the board.
  - **Phase C.** A `behind` or `overdue` verdict gets a stated response: reduce scope with the owner, resequence toward the dated finish line, release blocked work (naming the rulings), or take a moved date to the owner. A plan that leaves it unaddressed says so.
- [ ] **Step 4: `roadmap-status`.**
  - 1.3 lists the pace figures.
  - 1.4's pace signal reads the `pace` block.
  - The Health template's pace line becomes: "Pace: <verdict> against <label> (<date>, N days): required X vs trailing Y per week (<unit>)". Otherwise it reads "no deadline is declared", or "not computable: <missing inputs>".
  - "Where we stand" gains the deadline's remaining work and projected finish.
- [ ] **Step 5: `next-pointer`.**
  - Replace "Pace comes from the most recent assessment; if none exists, pace is not computable" with: pace comes from the `pace` block of `kpis --json`, computed live and never read from an assessment.
  - The Pipeline table gains a **Deadline** row and a **Pace** row, the latter with the Overdue verdict added.
- [ ] **Step 6: `project-profile`.**
  - Add a catalogue row. The question: "Is there a date the work must be done by? Who set it, which finish line does it date, and which items count toward it?" It declares `policy.roadmap.deadlines` **and its finish-line heading**.
  - Add a Phase 3 preview line for a deadline.
  - Add Phase 4's `policy-set roadmap.deadlines.<id>` command.
- [ ] **Step 7:** Tests pass; `validate.py`; the full suite. Every new doc key must resolve under `test_every_documented_policy_key_exists` and the Task 1 table check.
- [ ] **Step 8: Commit.** `docs(ceremonies): pace is read from kpis, and a deadline has one home`.

### Task 9: Record and release

**Files:** modify `RELEASE-NOTES.md`, `docs/superpowers/specs/2026-09-17-project-specificity-architecture-design.md` and `plugins/virtuoso/scripts/release.py` (docstring only).

- [ ] **Step 1: Correct the v1.8.0 record.**
  - The notes and the spec still say the release step is outstanding. Record what the owner's machine reported:
    - `RELEASE v1.8.0 COMPLETE`
    - 556 passed, 5 skipped on Windows
    - regen-diff byte-identical
    - sweep hashes equal
    - the registry at 1.8.0
  - Leave the desktop app's running version as the one unverified item, until the owner reports the post-restart checks.
- [ ] **Step 2: Write `RELEASE-NOTES.md` v1.8.1.** Cover:
  - what a deadline is, and the pairing: date plus owner in policy, the finish line in the roadmap
  - the pace block and the verdicts
  - the session line
  - the `effortScale` fix
  - the policy-set read-back and `null` withdrawal
  - the not-computable rules, stated plainly
- [ ] **Step 3: Fix `release.py`'s docstring**, where steps 3 and 4 still say "two files". Then run the full suite and `validate.py`, and confirm `bump_version.py --check` passes at 1.8.0.
- [ ] **Step 4: Push the branch.** Read both CI legs; red is work, never a wait.
- [ ] **Step 5: Ask the owner for the go-ahead to update `main`.** With it, `main` fast-forwards to the branch.
- [ ] **Step 6: Release on the owner's machine** (PowerShell):

```powershell
cd C:\Users\estra\Projects\Virtuoso\virtuoso.dev
git fetch origin
git switch main
git pull --ff-only origin main
python plugins\virtuoso\scripts\release.py --dry-run
python plugins\virtuoso\scripts\release.py 1.8.1 --notes "Deadline support: declared once, paced everywhere"
```

  `release.py` bumps the three manifests, commits, pushes `main`, deploys, sweeps, verifies and updates the registry. Then restart Claude Code; the `deadlines:` line appears at session start.

---

## Applying it to Gloves of Glory, after the release

The owner's open question from 2026-09-22 (which finish line "the overall game build" is) becomes a field.

- **Until it is answered,** leave `finishLine` out. Pace computes over every item, which matches reading A, and the review reports `deadline-unanchored`, which is the truth.
- **Once it is answered,** set `finishLine` to the heading that defines done. If no single heading does, add a short one to the roadmap. Set `scope` if the answer is narrower than everything.

Run from the GoG root, as the ceremony does, under bash:

```bash
V="$HOME/.virtuoso/bin/virtuoso"
"$V" virtuoso_registry --root . --actor roadmap-review policy-set roadmap.deadlines.game-build \
  --value-json '{"date": "2027-01-01", "owner": "Evan", "label": "Overall game build", "recorded": "2026-09-22"}'
# read the preview, then repeat with --apply; the output ends "verified: read back from disk"
"$V" virtuoso_registry --root . kpis
```

If GoG's frozen ledger does not follow the documented six-column format, `kpis` reports the trailing rate as not computable and names the records it could not date. That is a finding about the ledger's format (`policy.terminalLedger.format`), not a reason to estimate.

---

## Out of scope

- **Pace in the XLSX register report** (`build_register_report.py`). It is a presentation output, and it can follow once the block's shape has settled.
- **Deadlines in the generated governance README.** The session line already puts the date in front of every session, and a README change is a writer-output change that would trip regen-diff.
- **Validating all policy at session start.** `Policy.validate()` runs only inside `policy-set`, so a hand-edited invalid `git.policy` is never reported by preflight. Deadlines get their own validation on their own line; the general gap is pre-existing and deserves its own change.
- **Per-scope trailing rates and velocity multipliers.** GoG's 1.5×–4× over spec-floor is one example. A multiplier would be a policy value, and a separate decision.
- **`policy-set --value-file`.** Windows PowerShell 5.1 strips embedded double quotes from native-command arguments. Ceremonies run under bash, so only hand use from PowerShell is affected.
- **Checking roadmap prose dates against the policy date.** Fuzzy prose parsing buys little over "the roadmap points at the policy".
