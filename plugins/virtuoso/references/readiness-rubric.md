# Dispatch Readiness Rubric — v1.1

**One rubric, one version, one home.** Every ceremony that assesses readiness
reads *this* file. No skill restates the checks in its own words, and no skill
carries its own count of them. If you change a check, change it here and bump
`version` below; `policy.rubric.version` in a project's registry pins the
version that project expects. A ceremony always applies the current version; when a
project pins an earlier one, it names the checks added since before assessing, so no
project meets a new check by surprise. **v1.1** added U9, *Lessons applied*.

    version: 1.1
    universal-checks: 9
    extension-checks: project-defined (policy.rubric.extensions)

A specification is **dispatch-ready** when every universal check passes and every
project extension check the registry declares also passes. Readiness is a
property of the specification, not of who will implement it: nothing here
assumes the implementer is a weaker model, a particular product, or a particular
host (redesign item 75).

---

## Universal checks (U1–U9)

These apply to every project.

### U1 — Scope
- What is in scope is stated. What is explicitly out of scope is stated.
- The item's outcome is one sentence a reader could recognize as achieved or not.

### U2 — Edit sites
- Every location the work will touch is named concretely: file paths, symbols,
  endpoints, tables, or their equivalent in this project's domain.
- Any line numbers cited are verified current at the time of the check; if they
  have shifted, they are corrected in place.
- The thing named at each site actually exists and matches the specification's
  description of it.

### U3 — Tests
- Every test named is identified precisely enough to run: a full path and test
  name, or the project's equivalent addressing scheme.
- New tests state their target file, their name, and the assertion in concrete
  terms ("assert f(X) == Y"), not "verify it works".
- Modified tests quote both the current assertion and the intended one.

### U4 — Acceptance criteria
- Every criterion is mechanically verifiable: a command, an assertion, or a
  file-state check that returns true or false without judgement.
- No criterion depends on an opinion ("looks right", "is reasonable").
- The verification command for each criterion is written into the specification.

### U5 — Prerequisites
- Every prerequisite is terminal in the work register (completed, dissolved, or
  superseded with a recorded disposition), **or** the specification encodes the
  wait explicitly.
- Prerequisite identifiers resolve against the register; none are dangling.

### U6 — Failure handling
- For each known failure mode, "if X happens, do Y" is explicit.
- A rollback path is stated.
- A retry ceiling is stated.

### U7 — Source evidence
- Claims of fact cite where they come from: a close-out, an audit, a decision
  record, a measurement, a code reference — with a section anchor where one exists.
- No deferred decisions remain. Search for "TBD", "decide later", "confirm with",
  "to be determined": any hit must be resolved before the specification is saved.

### U8 — Repository plan
- The branch (or equivalent change unit) is named, and its base is named.
- The staging plan is explicit paths, per the project's git policy
  (see `git-policy.md` — the policy is registry configuration, not a fixed rule).
- The commit/push expectations match what that policy permits.

### U9 — Lessons applied
- The specification carries a **Lessons applied** section. It names, by identifier,
  each live lesson in the registered `lessons` role that bears on this item and the
  concrete change each one made to *this* specification — or it states that no live
  lesson applies.
- Every identifier it cites resolves to a recorded lesson. A lesson since promoted is
  cited as the standing rule it became; a retired lesson is not cited.
- Live lessons the section leaves uncited were considered and judged not to apply.
  The check lists them, so that judgement is made rather than skipped.
- Verify it mechanically — exit 0 passes, exit 1 names what is missing; `--item`
  locates a specification stored inline in the roadmap:

      "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --check <spec> --item <ITEM-ID>

This is where a project's own history reaches its next piece of work. A lesson the
close-out recorded and no specification applied was learned once and paid for twice.

---

## Project extension checks

A project declares its own domain checks in
`policy.rubric.extensions` in `Virtuoso/workspace-layout.json`. They are checked
alongside the universal set and reported separately, so a reader can always tell
which failures are universal and which are this project's.

Extensions exist because domains differ. Examples a project might declare:

| Extension id | Typical check |
|---|---|
| `calibration` | measurement cadence, escalation threshold, pre-authorized halt conditions |
| `db-migration` | forward and backward migration, data-loss analysis, run order |
| `deployment` | environment, rollout order, health gate, rollback command |
| `regulated-review` | who signs off, what record the sign-off leaves |
| `visual-inspection` | what is rendered, at what size, and what "correct" looks like |
| `accessibility` | which criteria, checked with what tool |

Declaring none is normal and correct for many projects.

### Where an extension is defined

Declaring the id is half of it. The id tells every ceremony that a check exists and must
pass; it does not say what passing means. The other half is prose, and it lives in the
project's overlay of *this file*:

    <overlays>/references/readiness-rubric.md

A section counts as an extension's definition when its heading **starts with** the declared
id, at depth 2 to 4:

```markdown
## db-migration — forward and backward migration

- both migrations are written and named in the specification
- the data-loss analysis states which columns can and cannot be reconstructed
- run order relative to the deploy is stated
```

The heading must start with the id, so `## Why we dropped db-migration` does not count —
a heading that discusses a check is not a definition of it. A longer id does not stand in
for a shorter one either: `## db-migration-rollback` does not define `db-migration`.

Case does not matter, so `## Deployment — environment and rollback` defines `deployment`:
the id is an identifier and the heading is prose you write. The id and the `#` marks must
be on the same line, and a heading inside a fenced code block is an example of a heading
rather than one — the block just above is exactly that, and copying it verbatim into your
overlay defines nothing.

A section with a heading and no prose under it is reported too. The placeholder is not
the only way to leave a check undefined; deleting it is the other.

A declared id with no definition is reported at session start as `pairing-body-missing`, and
an id declared with no `overlays` role registered at all as `pairing-mirror-unregistered`. A
section left as the scaffold's placeholder is reported as `pairing-body-stub` — a heading
shaped like a definition is not one, so generating the skeleton does not clear the warning
that produced it. All three are warnings or information, never errors: an undefined check is
the project's to write, and no repair the plugin could run would write it.

To generate the skeleton (it writes nothing; redirect it yourself):

    <launcher> virtuoso_registry --root . overlays --scaffold --for references/readiness-rubric.md

---

## Reporting

Report readiness as separate findings, never as one blended verdict
(redesign item 39):

1. **Specification readiness** — U1–U4, U6, U7, U9 plus declared extensions.
2. **Prerequisite readiness** — U5, resolved against the live work register.
3. **Repository readiness** — U8 plus the repository's actual current state.
4. **External-register readiness** — whether the register can be read, whether
   the snapshot is fresh, and whether the mutations the ceremony will need are
   supported by the configured provider.
5. **Execution-environment readiness** — tooling, dependencies, and access the
   work needs.

A ceremony reports each of the five independently. "Not ready" is never a single
undifferentiated verdict.
