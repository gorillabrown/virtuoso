# Virtuoso Release Notes

## v1.10.0 (2026-09-23) — the learning loop, hardened

**Upgrading from 1.8.2.** This release ships two bodies of work: the learning loop (the
next section, built as 1.9.0 and never released on its own) and the loop hardening below.
**Additive; registry schema stays at v2. The readiness rubric moves to v1.1** — its new
universal check U9, *Lessons applied*, means a specification that passed under v1.0 may
need one more section before it is dispatch-ready again (the next `/roadmap-review`
re-checks the buffer). New workspaces also get a `findings` role and effort columns in the
ledger; existing manifests stay valid without them.

1.9.0 closed the learning loop at three checked links. The analysis that followed graded
all twenty-one hand-offs in the loop — six mechanical, five partly, eight prose, two
missing — and ranked eighteen gaps. This release closes them. Wherever a person had to
remember, a command now answers; wherever an output had no reader, it has one.

### The catalog tidies itself

- **`lessons --hygiene`** — `governance-sweep`'s new check 21 — proposes what to
  **merge** (live lessons recording one pattern), **retire** (observations older than
  `policy.lessons.staleAfterDays`, default 180, that no close-out ever applied),
  **tidy** (entries missing fields) and **repair** (a reused id).
- **`lessons --candidates`** computes promotion for `roadmap-review` D.4: a pattern that
  recurred, or a lesson applied and held in two close-outs; revision for one that failed
  twice.
- **`lessons --record-status`** is the one write: a Promoted / Retired / Superseded
  record appended for an allowed writer, previewed first, read back after. Nothing is
  ever edited.
- A close-out's **"No new lesson — reason" names what was examined** — a lesson, rule or
  item — whenever there is anything to examine (`lesson-reason-unanchored`).
- **`kpis` has a `learning` group**: live-count, lesson-yield, held-rate, promotion-rate,
  time-to-apply, repeated-trap-rate, effort-calibration — each with its sources, or
  *not computable* naming the missing input.

### Prose links made mechanical

- **`record-completion`** performs the close-out crossing's ledger append and register
  close for a local project, in order, verified, with a recovery record on partial
  failure. Before, those writes were done by hand.
- **Standing rules are paired** with their definitions in `policy.standingRules.source`
  (`standing-rule-unpaired`), checked at session start, and Zeus reads them from that one
  source instead of `CLAUDE.md`.
- **`roadmap-integrity:`** is printed — the fifth machine line, from one read of the
  roadmap — so the four ceremonies that act on it are no longer reading a line that did not
  exist. It decodes before judging, so a UTF-16 roadmap from PowerShell is `ok`.
- **Policy is checked at every load**: a hand-edited value of the wrong type is a
  `policy-invalid` warning, not a silently ignored setting.

### Every output has a reader

- **`findings`** is a default role: the sweep, the adversarial review and the agents record
  there, and `roadmap-review` B.3 reads every open finding — and its own previous
  lessons-applied — into the next plan.
- **Effort calibration** is measured: optional `effortEstimate` / `effortActual` ledger
  fields (`record-completion --estimate --actual`), `kpis effort-calibration`, and
  `effort-levels` sizing by the project's figure instead of a fixed one.
- **`dispatch-buffer-ready`** counts the buffer items a gate would actually pass, beside
  `dispatch-buffer-filled`, which counts what the register says.

### Close-out reviews every file it made

**`sprint_guards created-files --base <ref>`** classifies every file a dispatch created or
left changed — committed, temporary, untracked, uncommitted. `pointer-closeout` drafts
the report's new *Files Created* dispositions from it in Wave 1, removes the confirmed
temporaries, and re-runs it at Step 6. The sprint guards also read v2 registries now; they
had silently needed a v1 `paths` map.

### Said what they do

- Default writers match the skill bodies (`virtuoso` → issues and close-outs,
  `3rd-party-audit` → roadmap and lessons, `governance-sweep` → lessons).
- `mid-dispatch-decision` step 6d writes the `## Decision` block it always promised, and
  the close-out reads it.
- Nothing names a skill, agent or case the plugin does not ship (`write-spec`, "Case C",
  `athena`, `solon`, `herodotus`); the validator checks every reference.
- `epic` resolves an opt-in `epics` role and never a conventional path.
- No other project's residue in the shipped agents; the validator scans for it. The memory
  guide states the memory / lessons / findings boundary once.
- Promoted rules are hashed: an anchor now proves the rule beneath it, not just a marker.

### Close-out: acceptance and evidence reconciliation

Step 1 of the close-out
crossing said to verify completion evidence. It did not say how to read a result that is not
a pass, how much evidence a given integrity property is worth, or which tree the evidence is
about. That left the three misreadings a close-out is most likely to make: applying a
superseded gate, attributing an inherited baseline failure to the candidate — or excusing a
real regression as inherited, by inference rather than evidence — and publishing a tree other
than the one that was tested.

#### One section, not a seventh step

`pointer-closeout` gains **Acceptance and evidence reconciliation**, placed after Step 1. It
governs how the six steps read evidence; the transactional ordering and every confirmation
the crossing requires are unchanged.

Before verifying anything, the ceremony identifies the currently authorized acceptance
contract, published mid-execution amendments included — superseded criteria stay visible in
the history and are not applied as current gates. It never amends those criteria during
close-out: criteria that conflict with superior governance, a known-red baseline, or the
delivered scope stop the crossing and route a concrete amendment for owner approval and
independent review.

#### Failure classification

Every non-pass result is classified before completion evidence is judged to hold:

| Classification | Effect |
|---|---|
| In-scope regression | Completion is blocked |
| Inherited baseline failure | Preserved, routed to a separate bounded issue through the issue contract, covered only by an authorized amendment |
| Admission or custody failure | Completion is blocked even if test assertions passed |
| Infrastructure failure | Repaired or rerun — never recorded as a product failure |
| Authorized exclusion | Reported explicitly; the excluded population is never described as passed |

An inherited failure needs evidence, not inference: reproduce it at the accepted baseline
where practical, compare the candidate's relevant dependency surface, and confirm the
protected inputs did not move.

#### Evidence proportional to the property being proved

Commit and tree identities for tracked-content identity, exact-path diffs for implementation
scope, `virtuoso_registry repo` for checkout drift, `virtuoso_registry protected` for the
protected-file inventory — rather than repeatedly hashing whole repositories, standing up
independent repositories where one identity proves the point, or rerunning an accepted final
test to produce a fresher summary. Evidence reduction is never invented at close-out: a
binding gate changes through the project's amendment and review process first.

#### The tested tree is the published tree

Completion evidence names the exact integrated commit and tree — the candidate diff matches
the authorized manifest, the tested tree equals the tree selected for publication, the local,
tracking and authoritative remote references agree, and nothing unreviewed landed between
acceptance and publication. A later governance-only commit does not retroactively invalidate
a recorded implementation acceptance; the close-out distinguishes the two rather than blurring
them. Where protected inputs exist their integrity properties are recorded either side of the
accepted test session, because a passing test result cannot override protected-state drift.

#### Also

- **Close only what was verified.** A parent epic, program, milestone or release closes on its
  own completion conditions, never on a child's. Remaining dependencies, inherited defects,
  authorized exclusions and unresolved owner decisions are recorded without being converted
  into completion claims.
- **Aggregates leave the close-out vocabulary.** "All tests passed" is not sayable while any
  tested or excluded population carries a known failure; the two populations are named
  separately, alongside what failed, what was excluded under authority, what remained
  unchanged, what was published, and what remains open.
- **Terminal operations are verified through their source** — item retirement, ledger entry,
  worktree completion, lane/lock/merge-slot release, remote publication, recovery state — by
  the exact recorded holder, branch, item and revision identities.
- **Retrospective lessons prefer reconciliation to duplication.** An inefficient or invalid
  gate is sorted into a one-time specification correction, a repeated workflow pattern, an
  existing rule needing reconciliation, or a new candidate standing rule — the last promoted
  only at the project's repetition threshold.
- Seven anchors added to `scripts/skill_rules.py` hold these rules in the skill body, so
  `validate.py` fails if a later edit drops one. **34 rules** are now held this way, and
  `pointer-closeout` joins the skills covered, and each rule's text is hashed like the rest.

### Plugin pages

Both hosts and the marketplace describe the plugin the same way — one description naming
the learning loop, `displayName`, author, keywords; the marketplace entry gains `category`
and `tags`; the alternate host's page gains its `interface` block (tagline, three prompt
chips, information panel, icons). A test holds the three equal.

Tests: 874 passed, 3 skipped (Linux).

## v1.10.0, continued — the learning loop (built as 1.9.0; first released in 1.10.0)

**Additive. Registry schema stays at v2. The readiness rubric moves to v1.1.** The rubric
has one new universal check, U9 *Lessons applied*, so a specification that passed under
v1.0 may need one more section before it is dispatch-ready again.

Virtuoso's ceremonies did new work well and learned from it badly. A close-out could end
with a "Learned" line in prose and nothing appended anywhere; the roadmap review consulted
lessons only after its specifications were drafted and rubric-passed; the dispatch pointer
and the epic charter never consulted them at all; and the ceremonies that did reach for
lessons named a project's file by name, against the registry rule. A lesson recorded at
close-out and never applied was learned once and paid for twice. This release makes the
loop a standard practice with a mechanical half at each link.

### One shape, append-only

A lesson is an entry in the registered `lessons` role under `<prefix>-NNN`
(`policy.lessons.idPrefix`, default `SRL`), with `Verdict`, `Evidence`, `Recommendation`,
`Applies to` — the field the next author matches against new work — and `Status`. A status
is never edited: promoting or retiring a lesson appends a status record under the same
identifier, and the latest one is current. `virtuoso_registry lessons [--open]` lists
lessons and which are live.

### Close-out records, or says why not

Every `pointer-closeout` report carries a *Lessons* section naming the lessons the dispatch
appended, or `No new lesson — <reason>`, plus how each lesson the specification applied
turned out. The crossing's verify step runs `lessons --check <report> --closeout --item
<ID>`; a report that fails is not a finished close-out. An unfilled template fails it too:
`[reason]` is a placeholder, not a reason.

### Specifications apply: rubric U9

`roadmap-review` reads the live lessons before drafting (D.3.0), every new specification
carries *Lessons applied*, and `lessons --check` must pass before it is saved. The lessons
review then re-checks every existing dispatch-ready specification against lessons recorded
since it was written. `next-pointer` reads the live lessons, runs the check, folds them in
as a closable gap, and prints them with the pointer. Live lessons a specification leaves
uncited are listed, so declining one is a judgement rather than an omission. The
specification format the review ships (D.5.2) ends with the `##### Lessons applied`
heading the check reads, so a specification shaped like the template passes the gate
instead of failing it.

### Epics apply too

The charter template carries *Lessons applied*; the epic skill reads the live lessons while
sharpening the Definition of Done, and each that bears becomes a constraint, a guard, or an
escalation trigger. An epic ends through `pointer-closeout`, so what it taught reaches the
role instead of staying in a journal.

### Fixed along the way

- The shared contract block in all sixteen skills, and two ceremonies besides, restated
  the rubric's version and count — the exact thing the rubric forbids. They now point at
  what the rubric declares, and a test keeps it so.
- `SpecRetro.Lessons_Learned.md` and `LESSONS_LEARNED.md` were named by filename in five
  skills and agents. Each now resolves the registered role.
- The promotion rules said to *edit* an earlier entry's status, which the role's
  append-only mutability forbids.

Tests: 775 passed, 3 skipped (Linux).

## v1.8.2 (2026-09-23) — no silent zero in the trailing rate

The first real run of 1.8.1 read Gloves of Glory's live board and reported "0 completions,
BEHIND" against a review that had counted twelve in the same four weeks. The required side
matched the review to the hundredth; the trailing side read a source that held no completion
at all — a board that keeps only live items, or a ledger in another column layout — and turned
that into a rate of zero.

A source with no recorded completion now makes the trailing rate **not computable**, naming the
source and, when it holds records, the result words it found instead. A project whose ledger
has completions, just none in the window, still reads zero and behind, because that is true.
The text form of `kpis` now also prints the trailing rate's source.

### A ledger in the project's own columns

The cause, once traced, was the ledger's layout. The project's terminal ledger is a CSV with its
own columns (`Sprint Code`, `Implementation Status`, `Date Completed`, …); the reader accepted
only `recordId`, `itemId`, `completed`, `result`, so every field read blank.
`policy.terminalLedger.fieldMappings` now names the column for each ledger field, and the
documented human headers (`Record`, `Item`, `Completed`, …) are recognized without one.

The same trace found a write-side defect: an append to such a CSV wrote the six fields in the
plugin's own order under the project's fifteen-column header, which would have shifted a
close-out's values into the wrong columns. An append now lays its row out under the file's own
header, and is refused — naming the missing columns — when the file has no column for the item,
the date or the result.

## v1.8.1 (2026-09-23) — deadline support

**Additive. Registry schema stays at v2, and nothing a project already has changes meaning.**
One behaviour to know: preflight now prints a fourth machine line, so anything that read
`--json` output by skipping a fixed number of lines must read from the first line beginning
`{` instead.

On 2026-09-22 a project owner set a date — 1 January 2027 for "the overall game build" — and
the plugin had nowhere to put it. There was no deadline key. `finish_line:` looked like one
and is only a marker discovery uses to recognize a roadmap. The review's pace line read "not
computable: no dated deadline exists", so the operator derived pace by hand: 60 items and
235.5 points remaining, 4.16 items and 16.32 points a week required, 2.50 to 3.00
completions a week delivered, 85.4% of the remaining points blocked. The date was then
headed for the roadmap, the assessment, the phase brief, memory, the epic charters, and the
board — six copies to keep in step, and nothing to say which one was right.

### A deadline is a declaration with a body

The date lives in one place, `policy.roadmap.deadlines.<id>`, written through `policy-set`:
a `date` and the `owner` who set it, and optionally a `label`, the `finishLine` it dates, the
`scope` of work that counts, and when it was `recorded`. Deadlines are keyed by an id you
choose, so `policy-set roadmap.deadlines.<id>` adds one without restating the others,
`…<id>.date` moves one date, and `--value-json null` withdraws one. A malformed date, a
missing owner, or a misspelled field is refused before anything is written.

The **body** is the roadmap heading `finishLine` names — the section that says what done
means. It is matched the way every pairing body is, and reported when it is missing:
`deadline-unanchored` (info) when a deadline names no finish line, and
`deadline-finish-line-missing` (warning) when it names one the roadmap does not define. That
turns the question the operator had to guess at — *which* finish line is "the overall game
build"? — into a field the owner answers once.

Everything else points at the policy rather than copying it. The roadmap defines; reviews and
briefings cite the computed pace as of their own date; memory, charters and boards do not
carry the date at all.

### Pace, computed rather than derived

`kpis` now reports pace against every declared deadline, from the same snapshot as its other
figures and as of that snapshot's date. For each one:

- **remaining** work in scope, in items and points, and the **blocked** share of it
- the **required** rate — remaining ÷ weeks to the date
- the **trailing** rate — distinct items completed over `policy.roadmap.pace.trailingWeeks`
  (default 4), read from the terminal ledger with corrections applied, broken down by the
  result words the ledger records
- a **verdict** per unit — `ahead`, `on track` or `behind` by `policy.roadmap.pace.tolerance`
  (default ±10%), `met` when nothing remains, `overdue` when the date has arrived — with the
  worse unit as the headline
- the **projected finish** at the trailing rate

A figure the data cannot support is *not computable*, with its missing inputs named: an
undatable completion, an unsized item, a completed item that has left the register (for points
only), a scope that matches nothing. None of these ever becomes a zero, and an empty scope is
never "met".

The 2026-09-22 figures are the acceptance test, reproduced exactly: 101 days, 4.16 items and
16.32 points a week required, 3.00 a week delivered, **behind**, projected finish 9 February
2027, 85.4% of points blocked. The 3.00 includes two "completed (qualified)" records, because
the status vocabulary counts any result beginning "completed" as completed; the breakdown
(`completed ×10, completed (qualified) ×2`) keeps the strict 2.50 readable.

### Every session knows its deadlines

Preflight prints `deadlines:` beside `overlays:`, in every mode and through `--quiet`:
`deadlines: game-build 2027-01-01 (100 days); 1 finding`, or `none declared`, or
`not registered`. It carries dates and days only. Pace needs the work register, which may
be external, and session start never reads one.

### Where it shows

- **`roadmap-review`** reads pace in B.2 instead of deriving it, records a date the owner sets
  or moves through `policy-set`, and must answer a behind or overdue verdict in its plan:
  reduce scope, resequence, release blocked work, or take a moved date to the owner.
- **`roadmap-status`** and **`next-pointer`** read pace live, not from the last assessment.
- **`project-profile`** asks for the date, its owner, its finish line and its scope.
- **The cockpit** shows Deadline and Pace tiles, and a behind or overdue verdict becomes the
  recommendation when nothing more urgent is.

### `policy-set` reads its write back

Every `--apply` now re-reads the manifest from disk and confirms the value landed, printing
`verified: read back from disk`. The plugin never reverts a successful `policy-set` — it
restores its backup only when the write itself or the re-validation after it fails — and the
session-start line would show a deadline that something else later removed.

### Fixed

- **`roadmap.effortScale` could not be set.** `roadmap-review` documents it and `kpis` reads
  it, but it was never a declared key, so `policy-set` refused it as unknown. Points-based pace
  depends on it. The docs-contract test missed it because it only matched keys spelled
  `policy.x.y`; it now also checks every policy table.

### Not in this release

Pace in the XLSX register report; deadlines in the generated governance README; validating
every policy value at session start (today only `policy-set` validates, so a hand-edited
invalid `git.policy` goes unreported — a pre-existing gap); per-scope trailing rates; velocity
multipliers.

Tests: 702 passed, 3 skipped (Linux); CI green on `ubuntu-latest` and `windows-latest`.

## v1.8.0 (2026-09-17) — project specificity

**Additive. No breaking changes; registry schema stays at v2.** v1.7.0 gave projects a place
to put prose. This release establishes the architecture around it, because one mechanism was
not enough and the plugin was already inviting project rules it had nowhere to keep.

Virtuoso has three kinds of project specificity. **Location** — where this project's register,
ledger and issues are — is a registry role. **Value** — dispatch buffer, branch template,
status words, git policy — is a `policy.*` key. **Behavior** — what this project additionally
requires, in prose — is an overlay. The first two were finished; the third was not.

### The pairing rule

Every project-specific thing has two halves. A **declaration** in a role or a `policy.*` key is
typed and validated, so the machinery can count it and gate on it. A **body** in an overlay is
prose only an agent reads. A declaration with no body is an identifier no ceremony can apply;
a body with no declaration is prose no gate consults.

The corollary binds the plugin as much as a project: **if a constraint can be a policy value or
a mechanical check, make it one.** An overlay is applied at the agent's discretion; a policy
value is enforced. A dispatch buffer is a value. "Migrations need a data-loss analysis" is
prose. Shipping the first as the second because prose is easier is how you get a tidy way to
write rules nobody enforces.

### References are overlayable

`policy.rubric.extensions` declared readiness checks by id and gave them nowhere to be
defined. `references/readiness-rubric.md` is the natural home, and 1.7.0 overlays covered only
`skills/` and `agents/`; a skill overlay half-worked, because `roadmap-review` reads the same
policy key and would never have seen it.

`references/` is now a mirror root. One file is excluded — `references/registry-contract.md`,
which defines what an overlay may do, so overlaying it would let a project rewrite the rules
governing its own overlay. That is a bootstrap argument, not a judgement about the file, and it
is the only exclusion. Attempting it reports `overlay-not-overlayable` and says why, rather
than claiming the file mirrors nothing when it plainly exists.

The clause in every skill and agent is **v2**: it now covers the overlay of any shipped file
the reader reads, including a reference it is sent to. Under v1 a reference overlay would have
had nobody to read it.

### Pairing checks

A declared identifier with no prose body is now reported, at session start, on the project that
has it:

| finding | meaning |
|---|---|
| `pairing-body-missing` | the id is declared and nothing defines it |
| `pairing-body-stub` | a section exists but is empty, or still the scaffold's placeholder |
| `overlay-unreadable` | the overlay's bytes are not decodable as text; re-save it as UTF-8 |
| `pairing-mirror-unregistered` | ids are declared with no `overlays` role to hold them |

A body is a depth 2–4 heading that **starts with** the id, on one line, outside any code
fence, with prose under it. Anchoring is the point: `## Why we dropped db-migration`
discusses a check and must not satisfy it, and `## db-migration-rollback` is a different
id. Case is not: `## Deployment` defines `deployment`, because the id is an identifier and
the heading is prose a person writes. Findings are warnings or information, never
errors — an undefined check is the project's to write, and no repair the plugin could run
would write it. `validate.py` rejects a pairing naming a policy key with no documented
default, a file the plugin does not ship, or one the exclusion covers.

### Writing the declaration half

`virtuoso_registry.py --actor <ceremony> policy-set <key> --value-json <json>` previews a
policy change; `--apply` writes it. It runs on the same transaction `repair` does — the
candidate registry is validated before anything is touched, the manifest is backed up, and
a registry that would not reload cleanly is rolled back. It refuses a key the plugin does
not document, because a key no ceremony reads is configuration that looks live and is
inert.

This is what `project-profile` Phase 4 uses. Before it existed, the only way to set a
policy value was to hand-edit the manifest, which every ceremony is forbidden to do.

It refuses a value whose **type** differs from the documented default's, not only an
undocumented key. A string where `rubric.extensions` wants a list was stored happily and
then ignored — the project had declared a readiness check that no ceremony could read and
that session start never mentioned. A declaration that looks live and is inert is the exact
failure the pairing rule exists to prevent, and the key check stopped one field short of it.

**Backup directories are now unique.** They are stamped to the second, so two applies inside
one second shared a directory: the second copied the first apply's output over the pristine
original, and the state before either write was unrecoverable. One key per invocation makes
chaining the normal shape, so this was reliable rather than unlucky. `repair` shared the
defect and is fixed with it. Each set also records the `--actor` that asked, so a restore can
answer who changed something and not only what happened.

### `project-profile`, the sixteenth skill

A front door. It reports what is already specific about a project, interviews from a fixed
catalogue where every question maps to exactly one declaration, previews both halves, and then
writes only the machine-readable one — through the existing previewed, backed-up repair path.

**It never writes a project's overlays.** They are registered read-only precisely so no
ceremony edits what a project authored, and that sentence has no exception clause. The
skeleton is emitted instead: `overlays --scaffold` prints it, and with `--for` the output is
exactly that file's content, so the operator's own redirect is the whole write.

A scaffolded section carries a placeholder and is reported as `pairing-body-stub` until real
prose replaces it. The first end-to-end run showed why: without it, saving the skeleton cleared
the very warning that produced the skeleton, and a project could go green with nothing written.
A gate its own remedy satisfies is not a gate.

Adding the sixteenth skill required **no change to `validate.py`** — the clause check
enumerates the skills folder rather than a list, which is what that design was for.

## v1.7.0 (2026-09-16) — project overlays

**Additive. No breaking changes; registry schema stays at v2.** A project that needed a
shipped skill or agent to behave differently had one option: copy the whole file into its
own tree and edit it. The fork then drifted from the plugin in both directions — the plugin
gained rules the fork never saw, the fork gained rules the plugin never saw — and both
loaded at once, so the agent read two contradictory copies of the same instruction and
followed whichever it hit first. The existing overlay mechanism covered exactly one skill,
by telling the caller to paste extra rules into a dispatch prompt, which saved nothing.

An **overlay** replaces the fork. The project registers one optional, read-only directory;
inside it, a file at the same relative path as a shipped file carries only that project's
additions. The shipped file stays the plugin's. Nothing is duplicated.

### The `overlays` role

```jsonc
"overlays": { "path": "Virtuoso/overlays", "provider": "directory",
              "authority": "reference", "mutability": "read-only", "allowedWriters": [] }
```

- **Opt-in.** `overlays` is deliberately absent from `CREATE_ROLE_ORDER`, so `create`
  neither registers the role nor lays down a directory a project never asked for.
- **Read-only by the machinery already here.** Registering it `read-only` with no
  `allowedWriters` means the guard that already refuses writes to a read-only role refuses
  these too. No new write path was added, because none should exist: overlays are the
  project's files.
- **Case-exact on every filesystem.** Lookup compares each path segment against the names
  the filesystem reports rather than trusting a case-folding existence check, so
  `skills/Epic/SKILL.md` can no longer resolve on Windows and macOS and then silently
  resolve to nothing on Linux. A case-only mismatch is reported everywhere.
- **Only `skills/` and `agents/` are addressable.** An overlay elsewhere mirrors nothing and
  is reported rather than quietly ignored.
- **Bounded.** An overlay adds to a shipped instruction and wins on conflict, with one
  exception: it may not loosen a shared-contract safety rule — registry resolution,
  read-only preflight, write permission, git safety, provenance, or the issue contract.
  Anyone who can write the project folder can write an overlay; without that floor, that is
  also permission to switch off the plugin's own guards. This narrows what an overlay can
  do relative to a plain "the overlay wins" rule, deliberately.

### Reading them

`virtuoso_registry.py overlays` lists what applies, what is inert, and why.
`overlays --for <path>` resolves one shipped file's overlay; "there is no overlay" is an
answer with exit 0, not a failure. Both are queries and neither creates the directory.

Overlay findings are informational or warnings, never errors: an overlay problem is the
project's to fix and must not turn a working registry into one reporting `repair-needed`,
because repair has nothing to propose for a file the project owns.

### The clause, in every skill and agent

All 15 skills and all 10 agents carry the same anchored clause telling them to read their
own overlay. `validate.py` enumerates both rosters **from the folders on disk**, not from a
list kept in the validator — so a sixteenth skill cannot ship without the clause, and the
clause has one home (`tools/governance/overlays.py`) that CI compares shipped bodies
against, so "present" and "still says the same thing" are one check.

### A status line that always says something

Preflight now prints a third parseable line beside `virtuoso-status:` and `writes:`, in
every mode, surviving `--quiet`:

```
overlays: not registered
overlays: registered but absent (<path>)
overlays: registered, none present (<path>)
overlays: 2 applied (<path>); 3 finding(s)
```

It states a result even when there is nothing to report. Printing nothing would have been
indistinguishable from an all-clear — which is exactly how a project ends up believing its
overlays are in force while nothing is reading them. The published two-line contract is
unchanged; callers that parse it keep working.

### Release integrity

- **Every install surface is bumped together.** `plugins/virtuoso/.codex-plugin/plugin.json`
  is a shipped manifest, declared in `.version-bump.json`, so a release advertises one
  version everywhere. A dev clone's repository-root `.codex-plugin/` is a different
  directory — local WIP, never published — and stays ignored; the pattern is anchored so
  the two cannot be confused. `validate.py` fails
  when two install surfaces disagree, and checks every hook file under `hooks/` — again by
  scanning the folder — for a read-only `SessionStart`.
- **The release commit stages what the bumper wrote.** `release.py` derived its dirty-tree
  tripwire from `.version-bump.json` but staged a hand-listed pair, so a newly declared
  manifest would be bumped and then left out of the release commit. Staging now uses the
  same derived set the tripwire checks.
- **Agent memory names are audited against disk *and* git's index.** A memory directory
  spelled with the wrong case reads back as correct on Windows and macOS and resolves to
  nothing on Linux, where the agent then starts every session with an empty memory and says
  so to no one. Git's index records the spelling it was given, so it catches a case-only
  rename the filesystem hides; the filesystem catches what was never added. The audit found
  a live gap: `Hippocrates` declared persistent memory and documented no location for it.

## v1.6.0 (2026-09-08) — governed work-item creation

**Additive. No breaking changes; registry schema stays at v2.** A specification on disk is
not a work item: until the live register carries a row for it, no ceremony can queue,
sequence, or dispatch it. The plugin governed every change to a registered item but not the
act that brings one into existence. A ceremony holding an approved specification for an
unregistered item had no registered operation to promote it, and the only path left was the
host connector's raw create — outside authorization, recovery, evidence, and revision
handling. That is the escape hatch the provider architecture exists to close.

### `create-item`

A tenth provider capability, declared at the interface. Local CSV, Markdown-table, and
spreadsheet registers append a row; a read-only snapshot withdraws it; an external register
plans it through the same handshake as `set-status`.

- **Absence is the concurrency guard.** An external creation is planned only against a
  snapshot that is present and not stale, and only when the id is absent from it — terminal
  items included. The plan carries `expectedAbsent`, `snapshotTakenAt`, the project's own
  column names (`projectFields`), the defaults applied, preconditions for the host, and
  postconditions for the ceremony.
- **Creation is not an update.** An identical re-issue is a no-op that returns the existing
  item; a conflicting one is refused by field name (`duplicate-item`).
- **A new item enters the pipeline.** Status and specification state default to the
  project's spelling of `queued` / `stub`; a status word outside the project's vocabulary is
  refused rather than written as something no ceremony can read.
- **Separately authorized.** `policy.workRegister.creators` names who may create (unset:
  every `allowedWriters` entry). A writer entitled to change items is not thereby entitled
  to add them.
- **Idempotent across the refresh gap.** The recovery trail refuses a second plan under an
  idempotency key whose creation was already confirmed, even before the snapshot shows the
  new item. A failed attempt may be retried with a verify-first precondition; the superseded
  record is resolved with a pointer to its replacement, never deleted. Recovery record ids
  no longer collide when two records for one item land in the same second.
- **The crossing ends readable.** `mutation-confirm --provider-id` records the identifier the
  external system assigned; a successful creation names its next step — refresh the
  canonical snapshot.

### Command-line surface

`virtuoso_registry.py create-item` for local registers (a write, and it says so);
`mutation-plan` and `mutation-confirm` accept `--operation create-item`; `mutation-confirm`
gains `--provider-id`; `provider --json` reports `mayCreate` and, for external registers,
`plannedOperations`.

### Documentation and tests

`references/registry-contract.md` gains *Bringing a new item into existence*; the roadmap
review's D.5.3 distinguishes creating an item from updating one; the
documentation-to-code contract test covers the new subcommand; the provider contract,
crossing, and CLI suites gain creation cases.

## v1.5.1 (2026-08-26) — terminal ledger authority and recoverable external mutations

Shipped without a release-notes entry; recorded here from the commit history. External
mutation contracts became executable — `mutation-plan` / `mutation-confirm` with durable
recovery records and revision checks; a terminal ledger may be registered beneath an
archive directory when its authority is `terminal` and its mutability `append-only`;
registry repair no longer corrupts CRLF registries; the release pipeline accepts either
valid dry-run lineage, negotiates writer authorization, and authorizes fresh workspace
probes.

## v1.5.0 (2026-08-26) — promoted-rule enforcement

**Additive. No breaking changes; registry schema stays at v2.** A rule promoted into a
project's lessons catalog produces documentation, not enforcement — execution paths read skill
bodies at session start, never the catalog. This release gives promoted rules machinery.

### Rule anchors, enforced by CI

`scripts/skill_rules.py` carries a manifest of required rule anchors, and `validate.py` fails
when a registered anchor leaves its skill body. **27 rules** are held this way across
`virtuoso`, `epic`, `adversarial-review`, `effort-levels` and `governance-sweep`. Removing any
one of them turns CI red.

Anchors carry **plugin-neutral identifiers**. A consuming project maps a tag back to its own
catalogue in its own records; no project's rule numbers enter shipped content.

### Sprint guards

`scripts/sprint_guards.py`, 23 tests, three subcommands that exit 0 clean / 1 on a finding /
2 on a resolution error, so a caller branches on the code rather than parsing prose:

| Subcommand | Enforces |
|---|---|
| `staging-sweep` | A resident governance-staging memo is an open obligation, verified against its target documents rather than its own claims |
| `artifacts-exist` | A named deliverable is present on the merged branch — asks the object database, not the filesystem, because a worktree-only artifact looks present until the worktree is removed |
| `unpushed` | Commits not on the upstream at burst end; returns "no upstream" distinctly from "nothing to push" |

### Rules landed in skill bodies

Worker-output validation (a "completed" message is not evidence) · orchestrator owns runs past
the sub-agent timeout · safety rules inlined into worker prompts rather than left behind a
pointer · tier by blast radius, not by cheapness · mechanical acceptance criteria and the
red-base procedure · close-out as an artifact with its own task · staging-memo lifecycle ·
task boundaries are commit boundaries · lane declaration and the merge-slot procedure ·
instrument positive-control · identity-not-counts · cite-a-searchable-anchor · fork-surface ·
re-derive-don't-restate · enforcement-not-disclosure · content-not-presence.

### Also

- The close-out template gains the **Mid-Dispatch Decisions** section that two producer skills
  already named as a migration destination but which did not exist.
- Measurement routing: a run whose output is a distribution routes to an agent permitted to
  interpret, never to the test runner. *The tell is the output shape, not the vocabulary* — a
  detector tuned to retired words will certify a clean bill on an intact defect.
- `bin/` launchers pinned to LF so the byte-for-byte drift check survives checkout on Windows.

### Notes

Two `test_registry_preservation.py` failures (repair path, user-authored readme) remain open
from v1.4.0 and are tracked as follow-on. `validate.py` — the CI gate — is green.

## v1.4.0 (2026-08-25) — source-of-truth redesign

**Breaking changes, despite the minor version number.** Plugin 1.3.6 → 1.4.0; the
**registry schema moves 1 → 2**; several bundled scripts are removed. Migration itself is
non-destructive and previewed — see [`docs/MIGRATION-1.4.md`](docs/MIGRATION-1.4.md) for the
full removed-and-changed tables.

### Release-blocking safety

- **A genuinely read-only preflight.** `--mode check` performs discovery and validation with
  **zero project writes**, in every project state. The SessionStart hook now runs it, so
  starting, clearing, or compacting a session can no longer create, heal, vendor, or rewrite
  a project file.
- **Four separate operations.** `check` (validate), `adopt` (register in place), `create`
  (initialize, requires `--authorize`), `repair` (preview, then `--apply`). Adoption against
  an already-registered project behaves exactly like `check` — it never silently heals.
- **The human registry is never regenerated from a template.** Only the plugin's own
  generated region is refreshed; user prose, tables, labels, comments, ordering, line
  endings, and extension sections are preserved byte-for-byte. A registry with no generated
  region is user-authored: the plugin reads it, reports divergence, and offers only an
  additive append behind an approved repair.
- **Repair is previewable and transactional.** The preview names the proposed paths, semantic
  changes, files affected, and backup location, and writes nothing. The apply validates the
  reconstruction before any write, backs every existing target into a hash-verified set, and
  restores on any failure — leaving the original registry and manifest intact.
- **Verifiable backups.** Each entry records source, destination, byte count, SHA-256,
  timestamp, and operation, with a manifest that restores and verifies independently.
- **One complete status contract**, documented and tested: `ready`, `warning`,
  `repair-needed`, `repair-preview`, `repaired`, `adoptable`, `adopted`, `created`, `none`,
  `failed` — plus `--json` for the full structured result.
- **No global unversioned plugin pointer.** `~/.virtuoso/installs.json` is keyed by plugin
  version, and version-agnostic launchers (`virtuoso`, `virtuoso.ps1`) resolve the newest
  valid install. Two installed versions can no longer overwrite each other's discovery state.

### Governance registry redesign

- **One authority.** `Virtuoso/workspace-layout.json` holds the structured configuration;
  `Virtuoso.Governance.Readme.md` is a synchronized view with protected user sections.
  Divergence produces a diagnostic, never an overwrite.
- **A versioned schema** with a declared plugin-compatibility range.
- **Full role metadata**: path or external identifier, provider type, authority level,
  mutability, owning ceremony, allowed writers, validation method, presence, active/historical
  classification, and authored/generated origin.
- **Seven authority classifications**: live, terminal, mirror, report, evidence, archive,
  reference — plus `unknown` for conservative migration.
- **Authority is never inferred from a role name.** A role called `sprintCatalog` is
  authoritative only when the project says so.
- **External identifiers are valid registrations.** A board, project, database, or service id
  is validated by shape and never reported as a missing filesystem path.
- **Protected `x-` extension namespaces** survive plugin upgrades verbatim.
- **Registered paths are validated before use**: root escapes, unsafe absolute paths, archive
  paths claiming live authority, malformed external identifiers, and role/type mismatches are
  all rejected.
- **A registered-but-absent target is reported**, never repointed at a lookalike.
- **Conservative migration.** Unknown legacy roles stay unknown; the legacy local catalog
  migrates as a read-only compatibility mirror, not as the live register.

### Work-register provider architecture

- **A provider interface** with negotiated capabilities: list active, read sequence, read and
  write status, read prerequisites, read effort, store specification links, record
  completion, find the next eligible item.
- **Implementations** for local CSV, local Markdown, spreadsheet, read-only snapshot, and
  external registers (connector-backed task manager, issue tracker, database).
- **Three distinct roles**: the live work register, the append-only terminal ledger, and any
  optional compatibility export. The local CSV catalog is now optional.
- **Configurable field and status mappings.** Nothing requires the literal vocabulary
  *Queued*, *In Flight*, *Blocked*, *Completed*, *Stub*, or *Full Spec*.
- **Provenance on every derived metric**, and **"not computable"** with the missing inputs
  named rather than a fabricated figure.
- **Offline operation** through timestamped snapshots that are marked stale past a
  configurable window.
- **Optimistic concurrency**, **idempotent cross-system updates**, and **recovery records**
  that name exactly what remains after a partial failure.

### Ceremonies

- Roadmap Review works through the configured provider and touches a compatibility export
  only when it is registered, generated, and writable.
- Roadmap Status is **read-only by default**; corrections require an explicitly approved
  phase and a role this ceremony is registered to write.
- Next Pointer determines the next item through the provider — the absence of any particular
  file is no longer a hard stop — leads with descriptive names, and reports readiness as five
  separate findings: specification, prerequisite, repository, external-register, and
  execution-environment.
- Pointer Close-Out performs an ordered transactional crossing: verify evidence, create the
  artifact, append the terminal record, persist locally, close the item in the live register,
  verify every result — with a recovery record on any partial failure.
- The terminal ledger is **append-only** with configurable writers; corrections are new
  records referencing prior ones, and history is never reordered, rewritten, or deleted.
- The dispatch buffer, the phase/stage/lane hierarchy, and where specifications are stored
  are all project policy. Standing-rule identifiers and branch conventions come from policy;
  none are hardcoded. Issue escalation is provider-aware.
- **One shared, versioned readiness rubric** (`references/readiness-rubric.md`, v1.0), split
  into eight universal checks plus project-declared extensions. The two ceremonies that used
  to carry divergent copies now read the same file.

### Governance sweep

- Structural authority resolves through the registry; a directory readme is authoritative
  only when the project declares it so.
- Configurable scan boundaries (include/exclude, ignored directories, symlinks, file-size
  ceilings, binary policy) and protected path classes that can never enter a mutation plan.
- **Quarantine before deletion** by default, with irreversible actions moved to the end.
- Backup manifests that restore and verify; retention policy; backup and quarantine
  directories excluded from future sweeps.
- Source-and-derived artifact relationships, regeneration instead of hand-editing,
  document-type verification adapters, registered generation and validation commands,
  tested-before-documented command repair, immutable-hash verification, and exact repository
  scope in the completion report.

### Git and portability

- The universal "the planner never mutates git" rule is replaced by a configurable policy
  ladder: read-only, prepare-no-stage, explicit-path-stage, explicit-path-commit, push.
- Separation of duties is an optional project policy, tied to no product.
- The default branch and remote are **detected**; a repository with **no remote** is
  supported; branch cleanup is maintenance, not a dispatch prerequisite; a stale lock is
  reported, never deleted; network operations are explicit; and the plugin is worktree-aware.
- Product-, vendor-, and model-specific names are gone from shipped content. Actors are
  configurable roles; routing uses vendor-neutral task tiers; readiness never rests on a
  claim that one host or model is superior.
- A host-neutral launcher in both POSIX-shell and PowerShell forms; package resources resolve
  relative to the installed plugin; runtime dependencies are declared and checked; fixtures
  and comments carry no project's names, thresholds, or directory assumptions.

### Tooling

- The planning cockpit reads the configured authoritative provider instead of requiring a
  generated spreadsheet.
- The retired recalculation script is removed — bundled copy, tests, vendoring, and the
  visualizer's recommendation.
- Generated workbooks are presentation outputs; nothing reads one as operational truth.
- Close-out path resolution fails loudly on a malformed registry instead of falling back to a
  conventional directory, and is read-only unless `--prepare` is passed.

### Validation

216 tests and an expanded structural validator now cover byte-for-byte preservation, registry
round-tripping, authority precedence, external identifiers, read-only hooks, repair previews,
transactional failure, idempotency, cross-platform launchers, repository states, the provider
contract, documentation-to-code agreement, and migration fixtures for the older schema.

## v1.2.1 (2026-07-02)

### Added

- **Governance registry — `Virtuoso.Governance.Readme.md`.** A new project-root authority
  that maps every required governance role (roadmap, sprint catalog, lessons, close-outs,
  issues, reviews, outside audits) to its *actual* path in whatever layout the project uses,
  marking each present or absent. The preflight engine generates it idempotently on
  create/adopt/heal, and `Virtuoso/workspace-layout.json` is its machine-readable mirror.

### Changed

- **All six governance gate skills now read the registry first.** `/roadmap-status`,
  `/next-pointer`, `/roadmap-review`, `/pointer-closeout`, `/mid-dispatch-decision`, and
  `/3rd-party-audit` resolve every document through `Virtuoso.Governance.Readme.md`, defer to
  the paths it lists, and **never create a parallel or competing document for a role already
  registered.** On registry/disk divergence the rule is to repoint the registry, not fork a
  rival. A contract test enforces that every gate skill references the registry.

### Fixed

- **Established projects are no longer seeded over with an empty roadmap.** Preflight
  discovery previously recognized only `Project Documentation/` trees, so a project whose
  governance lives elsewhere (a root `ROADMAP.md`, a `docs/governance/` tree) was treated as
  bare and given a fresh empty template — which the skills then tried to reconcile against the
  real roadmap, improvising parallel plumbing. Discovery now finds the live roadmap across
  root, `docs/`, and `docs/governance/` layouts, adopts the project in place, and anchors
  every registry role to the real governance home instead of a phantom default path.

## v1.2.0 (2026-07-02)

### Changed

- **`sprint-catalog.csv` is now the source of truth for sprint/KPI data**, replacing
  `sprint-queue.xlsx`'s Dashboard + Catalog tabs across `/roadmap-status`,
  `/next-pointer`, `/roadmap-review`, and `/virtuoso-init`. All KPIs (totals, %
  complete, buffer health, phase progress) are computed catalog-direct from the CSV
  at read time — there is no cache to go stale, and no `recalc.py` step to run.
  Root cause: a companion xlsx's Dashboard tab is fed by Power Query, which only
  recomputes when a human opens the workbook in Excel; force-writing it headlessly
  via openpyxl (the old `recalc.py` path) fights that refresh and produces
  internally-contradictory cached values.
- `sprint-queue.xlsx` is now optional and, where a project keeps one, strictly a
  generated, human-facing report — written from the CSV via `build_sprint_queue.py`,
  never read back by any skill.
- `/virtuoso-init` seeds new workspaces with `sprint-catalog.csv` (header row only)
  instead of the `sprint-queue.xlsx` template.
- `pointer-closeout` documents the CSV as the authoritative catalog location, with
  `sprint-queue.xlsx` / `sprint-queue.md` named only as legacy/optional companions.

### Known gap

- `tools/roadmap_visualizer/workbook.py` (feeding the planning-cockpit generator)
  still reads `sprint-queue.xlsx` via openpyxl rather than `sprint-catalog.csv`;
  migrating it is tracked as follow-up work. Until then, treat the cockpit's
  sprint-level figures as secondary to the CSV-computed figures reported directly
  by `/roadmap-status` and `/next-pointer`.

## v1.1.7 (2026-06-30)

### Added

- **cwd-independent cockpit launcher.** `scripts/generate_cockpit.py` pins its own import
  root so the roadmap planning cockpit runs from any working directory (and for an installed
  plugin), fixing the previous `python -m tools.roadmap_visualizer.generate` command that
  only worked from `plugins/virtuoso/`. `/roadmap-review` now regenerates the cockpit as its
  final step (D.7) via the `~/.virtuoso/plugin-root` bridge; there is no standalone command.
- **`conftest.py`** pins the test import root so `tools.roadmap_visualizer` resolves
  regardless of the directory pytest is invoked from.

### Changed

- **CI runs the full test suite.** The `Tests` step now runs `pytest plugins/virtuoso/`
  instead of two hand-picked files, so the roadmap-visualizer suite (and every other
  previously-ungated test) actually gates merges. The green check is now honest.
- Removed the standalone "Roadmap planning cockpit" command/section from the README — the
  visualizer is invoked only from within `/roadmap-review`.

### Fixed

- `.gitignore` now excludes the `skills.zip` build artifact so it cannot be committed by
  accident.

## v1.1.6 (2026-06-30)

### Added

- **Adopt an established project in place.** The preflight gained `--mode adopt`: when a
  project already maintains its own documentation tree (`Project Documentation/` or
  `2. Project Documentation/` with a `1 governance` / `2 operational` subtree) but has no
  `Virtuoso/` marker, `adopt` lays down only a thin `Virtuoso/` control dir whose
  `workspace-layout.json` **points at the existing roadmap** (under any name, e.g.
  `GoG_Roadmap.md`). Nothing is moved or duplicated, and no parallel `Roadmap.md` is
  seeded. It prints a parseable `virtuoso-status: ready|adopted|none` line.
- **Roadmap discovery.** Both `adopt` and `create` now discover an existing roadmap and
  sprint-queue anywhere under the documentation root (preferring the live, non-archived
  copy with roadmap structural markers) and record those real paths in the manifest,
  instead of assuming `1 governance/Roadmap.md`.
- **Roadmap integrity guard.** `--check-roadmap PATH` sanity-checks a roadmap before a
  heavyweight rewrite and exits `0` ok / `2` warn (empty or unusually large) / `3` fail
  (null bytes, non-UTF-8, or missing). `/roadmap-review` runs it as a pre-rewrite gate and
  stops on a corrupt roadmap rather than rewriting it.

### Changed

- **Governance gate skills now adopt instead of bailing.** `roadmap-review`,
  `roadmap-status`, `next-pointer`, `pointer-closeout`, `mid-dispatch-decision`, and
  `3rd-party-audit` call `--mode adopt` and branch on the printed status, so an
  established project is brought under management in place rather than reporting "no
  workspace" and routing to `/virtuoso-init` (which would have scaffolded a parallel tree).
- `virtuoso-init` documents adoption and its `create` flow is now adoption-aware (points
  at an existing roadmap rather than seeding a new one).

### Fixed

- **No more parallel roadmap.** An established roadmap kept under a non-default name or in
  `2 operational/` is no longer shadowed by a freshly seeded `1 governance/Roadmap.md`.

## v1.1.5 (2026-06-30)

### Added

- **Roadmap visualizer** (`tools/roadmap_visualizer/`) — renders the roadmap +
  sprint-queue Dashboard to HTML, with manifest-aware workspace discovery and a
  staleness check that flags a drifted Excel Dashboard cache and routes it to
  `/roadmap-review`.
- **Workspace layout manifest.** `virtuoso-init` now offers a layout choice
  (plugin-only vs. canonical `Virtuoso/Project Documentation/`) and the preflight
  writes `Virtuoso/workspace-layout.json`. Skills resolve workspace paths from that
  manifest (`roadmap`, `sprintQueue`, `closeOuts`, `issues`, `outsideAudits`,
  `reference`, `scripts`) instead of hard-coded flat paths, falling back to the
  legacy layout for older projects.

### Changed

- **Preflight** gained `--mode detect|create` and `--layout plugin-only|canonical`,
  generating and respecting the workspace manifest (idempotent, non-destructive).
- Skills (`roadmap-review`, `roadmap-status`, `next-pointer`, `pointer-closeout`,
  `mid-dispatch-decision`, `3rd-party-audit`, `virtuoso`, `virtuoso-init`) now read
  the manifest as the source of truth for workspace paths.

### Fixed

- **Removed duplicate slash-menu entries.** The 10 `commands/*.md` wrappers each only
  re-invoked their matching skill, so every name appeared twice — once bare
  (`/roadmap-review`) and once namespaced (`/virtuoso:roadmap-review`). Skills are
  invoked directly via the `virtuoso:` namespace, so the wrappers were removed; the
  structural validator now treats `commands/` as optional.

## v1.1.4 (2026-06-30)

### Fixed

- **Relaxed the git posture in `next-pointer` (and clarified `git-handoff`).** The
  skills were conflating "Cowork doesn't *commit*" with "no git at all, even reads,"
  and quarantining the dispatch's git reconciliation into a read-only handoff packet.
  Now:
  - **Read-only git (`status`/`log`/`diff`/`show`) is always available** in every
    project — no project gates reads. Legacy mutating-handoff conventions (e.g.
    `git-handoff`) govern only *state-changing* commands; "no commits" never means
    "no git at all."
  - **The enrichment commit rides with the sprint.** The dispatch pointer's git
    reconciliation recipe lands the finalized spec as step 0 of the sprint (per the
    project's Git Workflow), instead of a separate pre-dispatch hand-off that could
    deadlock. Cowork still authors-but-doesn't-certify its own commit (separation of
    duties); the sprint's implementer (or the user) commits it.
  - `git-handoff` now states explicitly that even when the legacy packet is
    requested, read-only git stays available for verification.

## v1.1.3 (2026-06-29)

### Fixed

- **Eliminated duplicate skill registration.** The plugin now lives in a subdirectory
  (`plugins/virtuoso/`) with `marketplace.json` at the repo root pointing to it
  (`"source": "./plugins/virtuoso"`), matching the documented marketplace layout. Previously
  the plugin sat at the repo root (`"source": "."`), so the cloned marketplace directory was
  itself a plugin directory and Claude Code loaded every skill twice — once namespaced
  (`virtuoso:roadmap-review`) and once unprefixed (`roadmap-review`). Internal
  `${CLAUDE_PLUGIN_ROOT}` / vendored-script paths are unaffected (they resolve relative to the
  plugin directory, which moved as one unit). **Install commands are unchanged.**

### Upgrade note

- To clear the duplicate locally, fully reset the marketplace rather than a plain update:
  `/plugin marketplace remove virtuoso-marketplace`, then `/plugin marketplace add gorillabrown/virtuoso`
  and `/plugin install virtuoso@virtuoso-marketplace`. A plain `/plugin update` may leave the old
  root-plugin clone in place.

## v1.1.2 (2026-06-29)

Integration-correctness pass — **Phase 1 of the v1.2.0 integration design**
([docs/virtuoso/specs/2026-06-29-v1.2.0-integration-design.md](docs/virtuoso/specs/2026-06-29-v1.2.0-integration-design.md)).
Closes the lifecycle loop, reconciles conflicting load-bearing rules, and adds a structured
issue-handoff contract.

### Fixed

- **Git ownership reconciled; legacy `git-handoff` no longer mandated.** `pointer-closeout`
  now persists per the project's Git Workflow (Cowork never mutates git; the user or a
  dispatched executor commits; Cowork verifies read-only) instead of invoking the
  LEGACY/MANUAL-ONLY `git-handoff` skill, which disclaimed sprint-closeout use. (BC-1/BC-2)
- **Orchestrator naming unified to `Zeus`.** `zeus.md` no longer calls the orchestrator
  "CLI" (which contradicted the skill body and the README). It is rewritten as a lean,
  project-agnostic protocol — GoG-specific calibration bands, worktree scripts, absolute
  paths, and SRL/memo references removed; two clearly-marked illustrative blocks retained —
  with a Cowork/CLI ↔ Zeus vocabulary bridge. (BC-3/F17)

### Added

- **Closed the planning loop.** `pointer-closeout` runs a mandatory buffer-depletion check
  after elevating the conveyor belt — if fewer than 5 dispatch-ready specs remain (or the new
  head is a stub), it recommends `/roadmap-review`. The executor (`virtuoso`) is now
  bookended: its close-out names `/pointer-closeout`, and its spec source is `/next-pointer`.
  (BC-4/BC-5)
- **Structured issue-handoff contract (`virtuoso` → `mid-dispatch-decision`).** Every
  stop/hold/block/elevation is rendered in a fixed 7-field format (tl;dr, executive summary,
  evidence, possible causes, likely solutions, confidence 1–10, exported path) and saved as
  `Virtuoso/Issues/Issue.<id>.<date>.md`; `mid-dispatch-decision` now expects that path as
  its primary input. New `Virtuoso/Issues/` workspace directory.

### Notes

Phases 2–4 of the integration design (authoring-modifier wiring, the Ideas + `/reconcile`
skills, governance-sweep roadmap/queue hygiene, and shared-reference de-duplication) ship in
v1.2.0.

## v1.1.1 (2026-06-29)

### Fixed

- **Orchestrator renamed `codex-parent` → `Zeus`** in the `virtuoso` skill, matching the
  `zeus.md` orchestration protocol and the capitalized deity worker roster. The orchestrator
  (the parent agent that owns the plan, integration, decisions, and close-out) now shows as
  `Zeus` in task plans, the routing tree, narration, and the worker-utilization summary.

## v1.1.0 (2026-06-29)

Sprint-queue **v2** workbook support. The roadmap workbook was restructured; Virtuoso's
data engine, skills, and bundled template now match it.

### Changed

- **`sprint-queue.xlsx` v2 structure** — three sheets (`Dashboard`, `DATA.sprint-catalog`,
  `Variables`). The Catalog is a 20-column Excel table (`sprint_catalog`) with five
  formula-driven computed columns (Priority, Done?, PhaseRank, SizeRank, SortKey) that
  auto-rank the conveyor belt; the Dashboard carries a Status-Distribution doughnut chart and
  an auto-ranked "Next Up" queue.
- **`recalc.py` rewritten** — reads the Catalog by **header name** (column-order independent)
  and auto-detects the data sheet, so it is robust to the rename and the added `Notes` column.
  New Dashboard cell map (`B11–B18` pipeline incl. `Superseded`, `B21–B26` effort); LOE points
  span eight sizes (XS 0.5 … XL 20); status vocabulary adds `Superseded`/`Pivot` and matches
  `Completed*`. Validated against real data (reproduces every cached KPI); preserves the chart
  and tables on save.
- **Skills remapped to v2** — `roadmap-status`, `next-pointer`, and `roadmap-review` use the
  new Dashboard cells and the `DATA.sprint-catalog` layout. Buffer health, full-specs-queued,
  and phase progress (no longer Dashboard cells) are computed from the Catalog.
- **Bundled template refreshed** — `sprint-queue.template.xlsx` is the clean v2 workbook
  (chart, tables, and live formulas intact).

### Removed

- **`build_sprint_queue.py`** — the bundled `.xlsx` is the single source of truth for the
  template; the generator and its preflight/test/doc wiring are gone.

### Migration

- `/virtuoso-init` never overwrites an existing `sprint-queue.xlsx`. A project still on the
  old two-sheet workbook keeps it and will mismatch the v2 cell map — recreate it from the new
  template (or re-point your data) to adopt v2. New projects get v2 automatically.

## v1.0.0 (2026-06-29)

First public release. Virtuoso packages a complete Cowork-style governance & dispatch
system — roadmap planning, sprint execution discipline, close-outs, mid-run decisions,
external audits, and documentation hygiene — as a single installable Claude Code plugin,
backed by a self-healing per-project workspace.

### What's included

- **14 skills**, **10 commands**, and a **SessionStart hook**.
  - Execution & planning: `virtuoso`, `roadmap-review`, `roadmap-status`, `next-pointer`.
  - Close-out & decisions: `pointer-closeout`, `mid-dispatch-decision`.
  - Governance & audits: `governance-sweep`, `3rd-party-audit`.
  - Reasoning modifiers: `ultrathink`, `effort-levels`, `adversarial-review`.
  - Utilities: `delayed-start`, `git-handoff` (legacy/manual), `virtuoso-init`.
- **Self-healing `Virtuoso/` workspace** — `Roadmap.md`, `sprint-queue.xlsx`, lessons
  catalog, workflow-reference index, and review/close-out/audit folders, created and healed
  idempotently and never overwritten.
- **Bundled, dependency-light scripts** — `recalc.py` (pure-Python Dashboard KPI recalc,
  no Excel/LibreOffice required) and `virtuoso_preflight.py`.
- **Agent roster** — a dispatchable `agents/` roster (`Aristotle`, `Hercules`, `Hermes`,
  `Hippocrates`, `Plato`, `MarcusAurelius`, `Socrates`, `Pythagoras`, `Archimedes`, `Hesiod`)
  with the shared `AGENT_MEMORY_GUIDE.md`, plus the `zeus` orchestration protocol at
  `skills/virtuoso/references/zeus.md` (read by the virtuoso skill, not dispatched). The
  legacy single-dimension analysis agents were folded into `Plato` / `Hippocrates` /
  `MarcusAurelius` / `Aristotle`; superseded older agents were archived. All agent
  absolute paths were de-hardcoded to `<project-root>/…`.

### Robustness (incorporating learnings from obra/superpowers)

- **Skill bodies no longer depend on `${CLAUDE_PLUGIN_ROOT}`.** That variable resolves only
  inside hooks/MCP, never in skill or command markdown. The SessionStart hook now records
  the plugin's path to `~/.virtuoso/plugin-root`, and preflight vendors the bundled scripts
  into `Virtuoso/scripts/`, so every in-skill script call is workspace-relative and robust.
- **SessionStart hook scoped** to `startup|clear|compact` (was `*`), `async: false`.
- **Authoring fixes from the build:** the `3rd Party Audit SKILL.md` filename normalized;
  `delayed-start` frontmatter added; `pointer-closeout` absolute paths removed; dangling
  `WORKFLOW_REFERENCE.md §` citations repointed to the `effort-levels` / `3rd-party-audit`
  skills (with a generated index in the workspace).
- **Description hygiene:** `next-pointer` and `adversarial-review` descriptions trimmed under
  the 1024-char frontmatter limit, preserving all trigger phrases and manual-invocation
  gating.

### Tooling

- `scripts/validate.py` — structural validator (frontmatter, manifests, no absolute paths,
  no dangling refs, no `${CLAUDE_PLUGIN_ROOT}/` in skill bodies, command↔skill mapping).
- `scripts/bump_version.py` — version sync across manifests (`--check` / `--audit` / bump),
  driven by `.version-bump.json`.
- **GitHub Actions CI** runs the validator, version check, and the Python test suites
  (`recalc`, `virtuoso_preflight`) on every push and PR.

### Install

```
/plugin marketplace add gorillabrown/virtuoso
/plugin install virtuoso@virtuoso-marketplace
/virtuoso-init
```

### Known follow-ups (post-1.0)

- Split the largest skills' heavy reference detail into `references/` for token efficiency.
- Add behavioral/triggering evals (in the spirit of superpowers' eval harness).
- Optional Windows polyglot hook dispatcher for graceful no-op when Python/bash is absent.
- Reassess the Cowork/CLI vocabulary vs. true multi-harness support.
