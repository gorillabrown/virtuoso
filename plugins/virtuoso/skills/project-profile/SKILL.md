---
name: project-profile
description: >
  Establish or revisit what makes THIS project different from every other one Virtuoso
  governs — its phases and lanes, its status vocabulary, its extra readiness checks, its
  standing rules, its git policy, its actor names, and what its agents must know that the
  plugin cannot. Reports the project's current specificity surface, interviews from a fixed
  catalogue, previews every change, and writes only the machine-readable half. Use when the
  user says "set up this project", "configure Virtuoso for us", "what's configured here?",
  "add a readiness check", "our status words are different", "teach the agents our rules",
  "why isn't my overlay being applied", or after preflight reports declared identifiers with
  no definition. NOT for registering or creating a workspace (virtuoso-init), and not for
  planning work (roadmap-review).
---

<!-- virtuoso-shared-contract v2 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — `Virtuoso/workspace-layout.json` is the authority; `Virtuoso.Governance.Readme.md` is its synchronized human view. Resolve every document, work item, and permission through the registry. Never hardcode a path, never fall back to a conventional one, and never infer authority from a role's name. Full contract: the plugin's `references/registry-contract.md`.
- **Read-only preflight** — session start and any "where am I" check runs `--mode check`, which performs **zero project writes**. Adoption, creation, and repair are separate operations, each explicitly invoked.
- **Providers** — work items come from the configured work-register provider (local file, spreadsheet, connector-backed task manager, issue tracker, database, or read-only snapshot). Negotiate capabilities before planning work; never open a register file directly. The live work register, the append-only terminal ledger, and any compatibility export are three different roles.
- **Provenance** — every derived figure cites its provider, source, and snapshot time. A figure whose inputs are missing is reported as *not computable* with the missing inputs named, never approximated.
- **Git** — behaviour is `policy.git`, not a fixed rule of this plugin. See `references/git-policy.md`. Under every policy: inspect first, stage exact paths, preserve unrelated work, no destructive flags, no force-push without explicit authorization.
- **Readiness** — one shared, versioned rubric: `references/readiness-rubric.md` (its universal checks, at the version it declares, plus the project's declared extensions). No skill restates it in its own words.
- **Actors** — roles from `policy.actors`: planner, implementation agent, reviewer, repository operator. Never a product, vendor, or model name. See `references/actors-and-interaction.md`.
- **Issue contract** — any stop, hold, block, or elevation becomes an issue document, routed per `policy.issues.targets` (local file, external tracker, or both).
- **Effort levels** — low / medium / high / max. A property of the task's difficulty, never a ranking of whoever performs it.

<!-- virtuoso-overlay-clause v2 -->
**Project overlay.** If the registry declares an `overlays` role, read the overlay mirroring
every shipped file you read beneath it — this file at its own path (`skills/<skill>/SKILL.md`,
`agents/<Agent>.md`) and any `references/<file>.md` this one sends you to — and apply each on
top of the file it mirrors. Resolve them with the registry helper's `overlays` subcommand;
never fork or edit a shipped file to carry a project's rules. An overlay is additive and
wins on conflict, with one exception: it may not loosen a shared-contract safety rule
(registry resolution, read-only preflight, write permission, git safety, provenance, the
issue contract), and `references/registry-contract.md` may not be overlaid at all. No
`overlays` role, an absent overlays directory, and no matching overlay file all mean the
same thing — proceed on the shipped file alone.

# Project Profile

Virtuoso governs projects that differ from each other. A project says how it differs in two
halves, and this ceremony establishes both.

| Half | What it is | Where it lives |
|------|------------|----------------|
| **Declaration** | typed, validated, machine-readable | a registry role or a `policy.*` key |
| **Body** | prose only an agent reads | an overlay at the shipped file's own path |

A declaration with no body is an identifier no ceremony can apply. A body with no declaration
is prose no gate consults. Neither half alone is a project rule.

**The corollary governs every answer below:** if a constraint can be a policy value or a
mechanical check, make it one. An overlay is applied at the agent's discretion; a policy value
is enforced. "Dispatch buffer of 3" is a value. "Migrations need a data-loss analysis" is prose.

**Announce at start:** "Using the project-profile skill to establish this project's
specificity."

---

## Phase 1 — report what is already specific (read-only)

Run the read-only check and the overlay audit. Neither writes anything.

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check --json
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . overlays

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check --json
    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_registry --root . overlays

Read the `virtuoso-status:` line and branch:

- `none` or `adoptable` — this project is not registered yet. Stop and route to
  `virtuoso-init`; there is no profile to establish until there is a registry.
- `repair-needed` — stop and route to `--mode repair`. Never profile an invalid registry.
- `ready` or `warning` — continue.

Then report, in plain language, three things:

1. **Registered roles** whose target differs from the defaults — where this project keeps its
   register, ledger, issues, and overlays.
2. **Policy values** this project sets, and what each one changes.
3. **Overlays in force**, from the `overlays:` line, plus every finding. A
   `pairing-body-missing` here is a check the project declared and never defined; a
   `pairing-mirror-unregistered` is a set of checks with nowhere to live at all.

Report what is *absent* as explicitly as what is present. A project with no declared lanes has
no lanes — say so, rather than leaving the reader to infer it from silence.

---

## Phase 2 — interview from the catalogue

Ask only these. Each question maps to exactly one declaration, and a question that maps to no
declaration does not belong here — it produces prose nothing can act on.

| Ask | It declares |
|-----|-------------|
| What phases or stages does work move through? Which lanes run in parallel? | `policy.roadmap.hierarchy`, `policy.roadmap.lanes` |
| What status words does your register actually use for queued, in-flight, blocked, done? | `policy.workRegister.statusMappings` |
| Beyond the universal rubric, what must be true before work is dispatch-ready here? | `policy.rubric.extensions` **and their bodies** |
| What rules does every item inherit, and where are they written? | `policy.standingRules.ids`, `policy.standingRules.source` |
| How much may a ceremony touch the repository? | `policy.git.policy` |
| What do you call the people and agents in this workflow? | `policy.actors` |
| Where should a stop, hold, or block be recorded? | `policy.issues.targets` |
| Is there a date the work must be done by? Who set it, which finish line does it date, and which items count toward it? | `policy.roadmap.deadlines` **and its finish-line heading** |
| What must every agent know here that the plugin cannot? Which shipped file does each rule belong on top of? | no declaration — these are **bodies**, recorded in Phase 3 and emitted in Phase 5 |

The last row is the exception that proves the rule, and it is marked as one: it collects
bodies rather than declarations. Every other row names exactly one `policy.*` key, and a
question that named none would produce prose nothing consults.

Batch the questions; do not interrogate one at a time. Carry forward what Phase 1 already
found and ask only about what is missing or looks wrong — re-asking a settled question is how
a profile gets overwritten with a worse answer.

Where an answer is a *value*, record the value. Where it is genuinely prose, record which
shipped file it belongs on top of: a rule about dispatching belongs on `next-pointer`, a rule
about running tests belongs on the test-running agent, a readiness check belongs on the
rubric.

---

## Phase 3 — preview, and stop

Present both halves as one plan, and change nothing yet.

```
POLICY (written on approval)
  policy.roadmap.hierarchy       [] -> ["phase", "stage"]
  policy.rubric.extensions       [] -> ["db-migration"]
  policy.roadmap.deadlines.v1    (unset) -> {"date": "2027-01-01", "owner": "<who ruled>",
                                             "finishLine": "Finish Line — Target"}

OVERLAYS (emitted for you to save; never written by this ceremony)
  <overlays>/references/readiness-rubric.md   defines: db-migration
  <overlays>/agents/<Agent>.md                the sharded-suite rule
```

State for every policy line what behaviour changes, and for every overlay which shipped file
it is read on top of. An operator approving a plan must be able to predict what the next
session does differently.

Stop here for explicit approval. Approval covers this plan, not future ones.

---

## Phase 4 — write the policy half

Only after approval, and only the machine-readable half. Policy lives in the manifest, so
it is written through the registry helper's explicit writer — never by hand-editing the
file. Preview first; `--apply` is what writes:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor project-profile \
        policy-set rubric.extensions --value-json '["db-migration"]'
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor project-profile \
        policy-set rubric.extensions --value-json '["db-migration"]' --apply

One key per invocation, so each approved line in the Phase 3 preview is one write you can
point at. The value is JSON, so a list stays a list. The write validates the resulting
policy before touching anything, backs the manifest up, and rolls back if the registry
would not reload cleanly.

A deadline is one entry, keyed by an id you choose, so declaring it never restates another:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor project-profile \
        policy-set roadmap.deadlines.v1 \
        --value-json '{"date": "2027-01-01", "owner": "<who ruled>", "finishLine": "Finish Line — Target"}'

Its body is the roadmap heading `finishLine` names — the section that says what done means.
If the roadmap has no such heading, the deadline is reported at session start until it does.

The helper refuses a key the plugin does not document, because a key no ceremony reads is
configuration that looks live and is inert. If an answer has nowhere documented to go, it
is a body, not a declaration — take it to Phase 5.

Re-run `--mode check` afterwards and confirm the status is `ready` or `warning`. A profile
that leaves a registry in `repair-needed` has made the project worse.

---

## Phase 5 — emit the overlay half

**This ceremony never writes a project's overlays.** They are registered read-only precisely
so that no ceremony edits what a project authored. Emit the skeletons and let the operator
save them:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . overlays --scaffold

That lists every overlay the project is currently missing. For one file, the output is exactly
that file's content, so the operator's own redirect is the whole write:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . overlays --scaffold --for references/readiness-rubric.md

Say plainly that the skeletons are stubs: a heading with `(state what must be true...)` under
it defines nothing, and the pairing check will keep reporting the identifier until real prose
replaces it. Offer to draft that prose from the interview answers — drafting it is this
ceremony's job; saving it is the operator's.

Finish by re-running the audit and reading the result back:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . overlays

End on that line. It is the same line the next session starts with, so the operator sees
exactly what they will see tomorrow.

---

## What this ceremony never does

- **Never writes an overlay.** Emit it; the operator saves it. There is no flag for this.
- **Never writes policy without an approved preview.** Phase 3 is not optional.
- **Never invents a declaration the user did not give.** An id nobody asked for is a gate
  nobody can pass.
- **Never registers or creates a workspace.** That is `virtuoso-init`, and Phase 1 routes there.
- **Never profiles an invalid registry.** `repair-needed` routes to repair first.
- **Never asks a question outside the catalogue.** A question with no declaration behind it
  produces prose nothing consults.

## Locating the plugin

Skill bodies cannot expand plugin-root variables. Both launchers resolve the newest valid
installed version, or `VIRTUOSO_PLUGIN_ROOT` when it is set. If neither resolves, report that
the plugin could not be located — do not guess a path.
