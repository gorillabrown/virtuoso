# Project Specificity — Architecture

**Status:** implemented in v1.8.0 · **Date:** 2026-09-17 · **Follows:** `2026-09-16-project-overlays-design.md`

## Decisions (2026-09-17)

Four questions were open when this plan was written. All are now settled; the body below
reflects them.

| Question | Decision |
|---|---|
| How does the Stage 3 scaffold reach disk? | **Emitted, never written.** `overlays --scaffold` prints; the operator redirects. The read-only invariant stays unqualified. |
| Which references are overlayable? | **All but `references/registry-contract.md`**, on the bootstrap argument below. |
| How is a pairing body marked? | **A heading that *starts with* the declared id.** Not merely contains — see Stage 2. |
| How does this ship? | **One release, 1.8.0, all three stages.** Supersedes the two-release split this plan originally proposed. |

## Problem Statement

Virtuoso is a governance plugin for projects that differ from each other. Project
specificity should be the thing it is *good at*, not a capability bolted on beside the
generic machinery. Today it is three mechanisms that grew separately, and only two of them
are finished.

The gap is reproducible. Give a project a declared readiness extension:

```jsonc
"policy": { "rubric": { "version": "1.0", "extensions": ["db-migration"] } }
```

Now write down what `db-migration` actually requires. There is nowhere to put it.

- `references/readiness-rubric.md` is the natural home, and v1.7.0 overlays only mirror
  `skills/` and `agents/`. An overlay there is reported inert:
  `overlay references/readiness-rubric.md is not under skills or agents`.
- Putting the body in a skill overlay half-works. `next-pointer` would see it;
  `roadmap-review` also reads `policy.rubric.extensions` (`SKILL.md:195`, `:504`) and would
  not. Putting it in both is the whole-file fork problem, reintroduced one level up inside
  the overlay system.

So the plugin invites a project to declare a check and then gives it nowhere to say what the
check is. `policy.rubric.extensions` is a list of identifiers pointing at bodies that have no
declared location — a dangling reference by construction. The `x-` extension prefix has the
opposite problem: a project can store anything under it and nothing in the plugin ever reads
it, so it is a storage slot rather than a mechanism.

`policy.standingRules` is the counter-example that shows the right shape already exists in
the codebase: it carries **`ids`** *and* **`source`** — the identifiers and the role where
their bodies live. Nothing dangles.

## The architecture

Virtuoso has exactly three kinds of project specificity. Each answers a different question
and each needs its own home.

| Kind | Question it answers | Home | Machine-readable | State |
|---|---|---|---|---|
| **Location** | *Where* is this project's live register, ledger, issues? | registry roles | yes | solid |
| **Value** | *What* buffer size, branch template, status word, git policy? | `policy.*` | yes | solid |
| **Behavior** | *What does this project additionally require*, in prose? | overlays | no | new; covers `skills/` + `agents/` only |

### The pairing rule

> Every project-specific thing has two halves. A **declaration** — in a registry role or a
> `policy.*` key, typed and validated — says *that* it exists, so the machinery can count it,
> check it, and refuse to proceed without it. A **body** — an overlay at the shipped file's
> own mirror path — says *what it means*, in prose only an agent reads.
>
> A declaration with no body is a dangling reference: a gate nobody can satisfy because
> nobody can read it. A body with no declaration is invisible: prose no gate consults.
> Neither half alone is a project rule.

CI and the session-start audit enforce the pairing. It is the same shape as the
`overlay-orphan` finding that already ships.

### The corollary (and the honest limit)

An overlay is prose an agent reads. It is not enforced the way a policy value is.
`scripts/skill_rules.py` states this about the plugin's own rules: *"a promoted rule with no
dispatch-time machinery is applied inconsistently, by agent discretion."* A project overlay
carries exactly that weakness.

So the rule has a corollary, and it is a constraint on us as much as on projects:

> If a project constraint can be a policy value or a mechanical check, make it one.
> Overlays are for what can only be prose.

A "dispatch buffer of 3" is a value. "Migrations need a data-loss analysis" is prose. The
first must never be shipped as an overlay just because overlays are easier to write.

---

## Stage 1 — overlayable references

**Goal.** Close the dangling-body hole: anything the plugin ships as prose can be overlaid at
its own path.

### Changes

`tools/governance/overlays.py`

- `MIRROR_ROOTS = ("skills", "agents", "references")`.
- New `NON_OVERLAYABLE = frozenset({"references/registry-contract.md"})`. That file defines
  the overlay mechanism itself; letting a project overlay it is a bootstrap problem — the
  contract that says what an overlay may do would become something an overlay may rewrite.
  The other four references (`WORKFLOW_REFERENCE.md`, `actors-and-interaction.md`,
  `git-policy.md`, `readiness-rubric.md`) are overlayable; `SAFETY_FLOOR` already covers
  git-safety and registry-resolution, so the existing narrowing does the work.
- `in_mirror_root()` becomes `is_overlayable(mirror)` — in a mirror root **and** not in
  `NON_OVERLAYABLE`.
- New finding `overlay-not-overlayable` (warning), distinct from `overlay-orphan`, so a
  project overlaying the registry contract is told *why* rather than told its file mirrors
  nothing. `_shipped_index` keeps indexing the file so this finding can fire instead of the
  generic one.

The clause, bumped to **v2**

The v1 clause tells a skill or agent to read *its own* overlay. A reference is not read by
itself — it is read by whichever skill follows a pointer to it — so nothing currently tells
that skill to check the reference's overlay too. v2 generalizes: read the overlay mirroring
**any shipped file you read, including a reference this file sends you to**.

Mechanical cost: 25 files, already scripted; `CLAUSE_MARKER` becomes
`<!-- virtuoso-overlay-clause v2 -->`; CI compares against the constant, so this is one
constant plus one regeneration pass.

### Done when

- `<overlays>/references/readiness-rubric.md` reports `applies`, not `inert`.
- `<overlays>/references/registry-contract.md` reports `overlay-not-overlayable` naming the
  bootstrap reason.
- Clause v2 verbatim in 15/15 skills and 10/10 agents; CI green.
- `references/registry-contract.md` and `README.md` document the three overlayable roots and
  the one exclusion.

---

## Stage 2 — pairing checks

**Goal.** A declared identifier with no body is reported, at session start, on the project
that has it.

### Changes

`tools/governance/overlays.py` — a declared pairing table, not scattered logic:

```python
@dataclass(frozen=True)
class Pairing:
    policy_key: str      # dotted key holding the declared ids
    mirror: str          # the overlay mirror path whose headings are the bodies
    label: str           # what one entry is, for the finding text

PAIRINGS = (
    Pairing("rubric.extensions", "references/readiness-rubric.md",
            "readiness-rubric extension check"),
)
```

`policy.py` imports nothing from the governance package (verified: `copy` and `dataclass`
only), so `overlays.py` can import it with no cycle.

**What counts as a body.** A markdown heading at depth 2–4 whose text **starts with** the
declared id: `(?m)^#{2,4}\s+<id>\b`. Anchoring to the start rather than matching anywhere in
the heading is deliberate — `## Why we dropped db-migration` must not count as a body for
`db-migration`. Documented in `references/readiness-rubric.md` beside the extension table, so
the convention ships where a project reads about extensions.

An anchor comment (`<!-- extension:<id> -->`, matching `skill_rules.py`'s promoted-rule
pattern) was considered and rejected: it is exact, but it is HTML syntax imposed on someone
whose only task is writing a rubric section, and lowering that friction is the point of the
stage.

**New findings** (severity discipline unchanged — never `error`, because an overlay problem is
the project's to fix and `repair` has nothing to propose for a file the plugin does not own):

| finding | severity | meaning |
|---|---|---|
| `pairing-body-missing` | warning | `policy.<key>` declares `<id>`; the overlay has no section for it |
| ~~`pairing-body-orphan`~~ | — | **Not implemented.** Dropped during Stage 3; see the implementation notes |
| `pairing-body-stub` | warning | the section exists but is empty, or still the scaffold's placeholder |
| `pairing-mirror-unregistered` | info | ids are declared but no `overlays` role exists to hold their bodies |

**Plugin-side half.** `validate.py` asserts every `Pairing.mirror` names a file the plugin
actually ships and that is overlayable — so the table can never point at a path that does not
exist or one `NON_OVERLAYABLE` excludes.

### Deliberately out of scope

`policy.standingRules` pairs `ids` with `source`, a **role**, not an overlay. Checking those
bodies means parsing a project's own roadmap document, which preflight does not otherwise do.
The `Pairing` shape leaves room for a role-sourced variant later; this stage does not add one.

### Done when

- A project declaring `rubric.extensions: ["db-migration"]` with no body sees
  `pairing-body-missing` named in the session-start overlay line and in `overlays`, in
  every registration state — including with no `overlays` role and with the directory
  absent.
- Adding the heading clears it with no other change.
- `validate.py` fails if `PAIRINGS` names a path the plugin does not ship.

---

## Stage 3 — `project-profile`, the front door

**Goal.** Make specificity something a project is *walked through*, not something it
hand-edits JSON to acquire. This is the stage that makes specificity a hallmark rather than a
capability.

### Why a new skill rather than a phase of `virtuoso-init`

Different lifecycles. `virtuoso-init` is a one-time crossing: register a project or
initialize a workspace. A profile is revisited — a project adds a rubric extension in month
six, changes its git policy after an incident, gains a lane. A recurring ceremony inside a
one-time one gets invoked wrongly or not at all.

It will also be the first genuine test of the "a sixteenth skill cannot ship without the
clause" property, since CI enumerates the skills folder rather than a list.

### Shape

Read-only until an explicit approval, like every other ceremony that touches a registry.

1. **Report what is already specific.** Registered roles, non-default policy values, overlays
   in force, and every pairing finding. A project that has drifted sees it here.
2. **Interview from a fixed catalogue**, not open-ended. Each question maps to exactly one
   declaration:

   | Question | Declaration it writes |
   |---|---|
   | What phases/stages does work move through? | `policy.roadmap.hierarchy`, `.lanes` |
   | What status words does your register actually use? | `policy.workRegister.statusMappings` |
   | What extra readiness checks does your domain need? | `policy.rubric.extensions` **+ bodies** |
   | What rules does every item inherit? | `policy.standingRules.ids` + `.source` |
   | How much may a ceremony touch the repository? | `policy.git.policy` |
   | Who are the actors here? | `policy.actors` |
   | What must every agent know that the plugin cannot? | overlay bodies on `agents/` |

3. **Preview a plan** — policy keys to write, overlay bodies to author — and stop.
4. **On approval, write the policy half only**, through the existing preview/apply/backup
   path (`repair`'s discipline, items 7 and 8). Manifest writes are already transactional;
   this reuses that, it does not invent a second write path.
5. **Emit the overlay half as content, never as a write.**
6. **Print what is now in force**, so the ceremony ends on the same line the next session
   starts with.

### The write asymmetry, and why it stays

The `overlays` role is registered `read-only` with no `allowedWriters`, and v1.7.0's central
claim is that no ceremony can write it because the guard that already refuses read-only roles
refuses these too. A ceremony that scaffolds overlay files would break that claim for a
copy-paste's worth of convenience.

So the scaffold is emitted, not written: **`virtuoso_registry.py overlays --scaffold [--for
PATH]`** prints the skeleton to stdout, and the operator's own shell redirects it. The verb
stays read-only, the invariant stays unqualified, and the ceremony still produces a file the
operator only has to fill in.

*Rejected (settled 2026-09-17):* a narrow create-if-absent exception under `--authorize`,
matching `create`'s never-overwrite behaviour. It is defensible, and it costs the plain
sentence "the plugin never writes a project's overlays" — which is worth more than the
keystrokes. Recorded so the trade stays visible if the friction later proves real.

### Done when

- `project-profile` reports an unconfigured project's full specificity surface without
  writing anything.
- An interview run produces a preview; nothing is written without approval.
- Approval writes only policy, transactionally, with a backup — through
  `virtuoso_registry.py policy-set <key> --value-json <json> --apply`, which validates the
  resulting policy, backs the manifest up, and rolls back if the registry would not reload.
- `overlays --scaffold` emits a skeleton carrying one section per declared id, and
  `writes: 0` holds for every invocation.
- 16 skills; the clause check covers the new one with no edit to the validator.

---

## Sequencing, versions, edit sites

Stage 2 needs Stage 1's overlayable rubric. Stage 3 scaffolds from Stage 2's pairing table.
Strictly ordered in implementation, shipped together.

**One release: 1.8.0, all three stages.** The build order is still 1 → 2 → 3, each gated on
the full suite and `validate.py` before the next begins, so a stage that turns out harder than
planned is visible as a stalled gate rather than as a half-finished release. Commits stay
per-stage for reviewability; the version bump happens once, at the end.

**Edit sites for the sixteenth skill** — listed now, so the count is not discovered
mid-release:

- `.claude-plugin/marketplace.json` — description says "15 skills"
- `README.md` — the skills table
- `scripts/test_overlays.py:771` — `assert len(found) == 15`. This is a redundant hardcode of
  mine: the line above it already asserts `found == SKILL_NAMES`, which is the real property.
  It should become a comparison against the folder count, not the literal.

## Risks

| Risk | Mitigation |
|---|---|
| Overlayable references become a way to quietly restate a shared contract | `SAFETY_FLOOR` already forbids loosening one; `registry-contract.md` is excluded outright; `check_single_rubric` still guards the plugin's own tree |
| Projects push enforceable constraints into prose because prose is easier | The corollary is stated in the contract reference, and Stage 3's interview routes each answer to a *declaration* first |
| Clause v2 regeneration silently drops a file | CI compares all 25 bodies against the single constant; a missed file fails the build |
| The pairing convention is too loose or too strict | Documented beside the extension table; a body must be a single-line depth 2–4 heading outside a code fence, matched case-insensitively, with prose under it. The reverse direction is deliberately unchecked — see the implementation notes |
| Stage 3's interview grows unbounded | The catalogue is fixed and each entry names the one declaration it writes; a question with no declaration does not belong in it |


---

## Implementation notes (v1.8.0)

Two things changed from this plan, both found by running it rather than reading it.

**`pairing-body-orphan` was dropped.** The plan proposed reporting a body for an id no longer
declared. There is no reliable signal: nothing distinguishes a project's ordinary section
heading from a stale body, and a single-word id like `deployment` or `accessibility` — both
from the rubric's own example table — cannot be told apart from a heading that happens to
start with that word. Telling someone their own prose is dead when it is not is worse than
staying quiet about a heading nobody reads. Only the unambiguous direction is checked.

**`pairing-body-stub` was added, and was not in the plan.** The first end-to-end run of Stage
3 exposed it: saving the scaffold cleared the warning that produced the scaffold. The stub
heading reads as a definition to any "does a section exist" check, so a project could reach
green with nothing written. The scaffold's placeholder is now a sentinel, and a section still
carrying it is reported until real prose replaces it. A gate its own remedy satisfies is not a
gate.

Everything else shipped as planned, including the property this was partly a test of: adding
`project-profile` as the sixteenth skill required **no edit to `validate.py`**, because the
clause check enumerates the skills folder rather than a list. The three edit sites the plan
listed in advance (marketplace description, README table, the `len(found) == 15` hardcode in
`test_overlays.py`) were the only ones, and the hardcode is now a comparison against the
folder contents.

### Found by reviewing the release rather than the plan (2026-09-17)

Five things the completion report claimed were not true when measured on Windows, which
is the platform this plugin is maintained from. All five are fixed in the release that
actually shipped.

The suite was green on Linux only. A fixture wrote two overlay paths differing only in
case, which are one file on NTFS and on a default macOS volume, so five tests asserted
against content the fixture had not produced. `windows-latest` had been red since v1.6.0
on an unrelated cross-drive path, so it had stopped working as a gate and absorbed these
without anyone reading it. A red gate is not a gate.

The documented redirect produced an unreadable overlay. `--scaffold --for X > X` is the
whole write, and on Windows it wrote a legacy code page under pwsh and UTF-16 under
PowerShell 5.1. Both made `read_text` return `None`, and the audit then reported
`pairing-body-missing` about a file carrying exactly the right heading. Scaffolds are now
emitted as UTF-8 bytes, a BOM is honoured on read, and genuinely undecodable bytes are
reported as `overlay-unreadable` rather than laundered into a misleading finding.

The status line was silent in two of three states. The finding suffix was computed after
the early returns, so the two states a project is in the moment it declares its first
extension reported a clean line. It now applies everywhere and names the undefined ids.

Body detection passed what is not a body: a heading split across a newline, a heading
inside a fenced code block — including the one this plugin's own rubric shows as an
example — a section with nothing under it, and, in the other direction, rejected
`## Deployment` for `deployment`. The empty-section case mattered most: deleting the
placeholder is the obvious way to clear the stub warning, so the gate still had a second
route its own remedy could satisfy.

`project-profile` Phase 4 had no mechanism. It is now `policy-set`, built on `apply_plan`
so a policy write inherits the same transaction repair has.

A version bump is not a release. 1.8.0 was bumped inside feature commits on a branch while
`origin/main` sat at v1.6.0 and the installed plugin on the maintainer's machine was
v1.6.0. `release.py` exists because two releases once shipped on red CI; it was bypassed.
That release step remains outstanding and is the last thing between this work and a
plugin anyone actually runs.
