# Project Specificity — Architecture

**Status:** approved, unimplemented · **Date:** 2026-09-17 · **Follows:** `2026-09-16-project-overlays-design.md`

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

**What counts as a body.** A markdown heading at depth 2–4 whose text contains the declared
id: `(?m)^#{2,4}\s+.*\b<id>\b`. Documented in `references/readiness-rubric.md` beside the
extension table, so the convention ships where a project reads about extensions.

**New findings** (severity discipline unchanged — never `error`, because an overlay problem is
the project's to fix and `repair` has nothing to propose for a file the plugin does not own):

| finding | severity | meaning |
|---|---|---|
| `pairing-body-missing` | warning | `policy.<key>` declares `<id>`; the overlay has no section for it |
| `pairing-body-orphan` | info | the overlay has a section for `<id>`, which no policy key declares |
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
  `pairing-body-missing` in the session-start overlay line and in `overlays`.
- Adding the heading clears it with no other change.
- An undeclared body reports `pairing-body-orphan` and nothing else.
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

*Rejected:* a narrow create-if-absent exception under `--authorize`, matching `create`'s
never-overwrite behaviour. It is defensible, and it costs the plain sentence "the plugin never
writes a project's overlays" — which is worth more than the keystrokes. Open to being
overruled; recorded here so the trade is visible.

### Done when

- `project-profile` reports an unconfigured project's full specificity surface without
  writing anything.
- An interview run produces a preview; nothing is written without approval.
- Approval writes only policy, transactionally, with a backup.
- `overlays --scaffold` emits a skeleton carrying one section per declared id, and
  `writes: 0` holds for every invocation.
- 16 skills; the clause check covers the new one with no edit to the validator.

---

## Sequencing, versions, edit sites

Stage 2 needs Stage 1's overlayable rubric. Stage 3 scaffolds from Stage 2's pairing table.
Strictly ordered.

| Release | Contents | Why grouped |
|---|---|---|
| **1.8.0** | Stages 1 + 2 | Both are small, and Stage 1 alone would ship an overlayable rubric with nothing checking that it is used |
| **1.9.0** | Stage 3 | A larger design; must not hold up 1 + 2 |

**Edit sites for Stage 3's sixteenth skill** (found by inspection now, so the count is not
discovered mid-release):

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
| The pairing convention (a heading containing the id) is too loose or too strict | Documented beside the extension table; `pairing-body-orphan` catches the strict direction, `pairing-body-missing` the loose one |
| Stage 3's interview grows unbounded | The catalogue is fixed and each entry names the one declaration it writes; a question with no declaration does not belong in it |
