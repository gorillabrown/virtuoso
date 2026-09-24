---
name: storyboard
description: |
  MANUAL INVOCATION ONLY. The ad hoc way in: the first half of Storyboard, then
  Write-Plan, then Virtuoso, for work the user wants handled now that is not on the
  roadmap. Its one job is alignment. It sizes the work out loud, investigates the code,
  roadmap, register, and holding bay, then asks one bounded question at a time about
  outcome, placement, touchpoints, externalities, upstream, and downstream impact. It
  writes back what the user said apart from what it assumed, walks concrete frames of
  the finished work, and proposes approaches and a skeleton. Only when the user approves
  does it record an Aligned verdict. It holds the result in the registered holding bay,
  never the roadmap or the register, and continues into /write-plan. Epic-scale ideas
  are aligned here and held for roadmap review. Triggered by "/storyboard", "storyboard
  this", "I want to do X now", or "let's get aligned on X before we plan it".
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

# Storyboard

The first half of the ad hoc path: **Storyboard → Write-Plan → Virtuoso**
(`references/execution-paths.md`). Work that arrives between roadmap reviews comes in
here. The roadmap paths, `/next-pointer` and `/epic`, open only on items a review has
already placed.

This skill has one job: **make sure the agent and the user want the same thing before a
plan exists.** An agent that misunderstands the work will build the wrong thing, and do
it well. Every step below exists to bring a misunderstanding to the surface while it is
still one sentence long. What this skill produces is an **alignment record** the user
has approved, held in the registered holding bay. It writes no specification (that is
`/write-plan`). It does no roadmapping (that is `/roadmap-review`).

**Announce at start:** "Using storyboard to get us aligned before anything is planned."

## Preflight — read-only registry check (run first)

Resolve the plugin through its launcher, then run the **read-only** check. It performs
discovery and validation with zero project writes.

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check

Read the `virtuoso-status:` line and branch:

- `ready` — continue.
- `warning` — surface the findings and continue.
- `repair-needed` — **STOP.** Run `--mode repair` to produce the preview, show it, and
  apply it only with `--apply` after the user approves.
- `adoptable` — offer `--mode adopt`, which registers what exists in place.
- `none` — no registry. Alignment can still happen in this conversation, but nothing can
  be held, and the next review can reconcile nothing. Say so, and offer `/virtuoso-init`.
- `failed` — report the error verbatim and stop.

Then resolve the holding bay, the one place this skill writes:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . holding --open

Exit 3 naming `holdingBay` means the project has not registered the role. The role is
opt-in. Show the user the entry the message prints, and let them choose the directory
and add it. Never fall back to a conventional path. Alignment can proceed while they do,
but Step 10 cannot run until the role exists.

## When to use

- The user wants something done now that is not on the roadmap: a feature, a fix, a
  change, an investigation that will ship something.
- The user says "I want to do X" and X is not yet clear enough to plan.
- A held storyboard needs to change: `/storyboard <entry>` reopens it.
- `/write-plan` sent you here because no approved storyboard exists, or because
  something that was agreed is now in question.

## Route instead

| Signal | Route |
|---|---|
| The work is already an item on the master roadmap | That item: `/next-pointer` if it is the head, otherwise `/roadmap-review` |
| The work is already a held entry | Reopen that entry (`/storyboard <entry>`) or plan it (`/write-plan <entry>`); never a second entry for the same work |
| A question whose answer is information, not shipped work | Answer it directly |
| A change the project's policy lets you make without an item | Make it directly |
| A running dispatch has reached a decision | `/mid-dispatch-decision` |
| The whole roadmap needs recalibrating | `/roadmap-review` |

## Alignment principles

1. **Alignment is the deliverable.** A storyboard that ends with the agent and the user
   picturing different outcomes has failed, however complete it looks.
2. **Investigate before you ask.** Read the code, the roadmap, the register, the holding
   bay, the lessons, and the standing rules first. Ask the user only what investigation
   cannot settle: intent, priority, trade-offs, and permission.
3. **One question per message.** Follow `references/actors-and-interaction.md`: 2–4
   concrete options, one recommended, and an escape hatch. Ask an open question only
   about purpose, where no fair set of options exists.
4. **Their words, then yours.** Record what the user said close to verbatim, apart from
   what you inferred. A paraphrase can quietly change the meaning.
5. **Every assumption resolves.** Before the verdict, each assumption is confirmed,
   corrected, or accepted with a guard. None stays silent.
6. **Show, don't only tell.** Frames are concrete scenes of the finished work. They
   expose a misunderstanding faster than any list of requirements, because an example is
   hard to misread.
7. **Disagree once, then record the decision.** If you think the user's choice is risky,
   say so once, give the reason, and give your recommendation. Then follow their decision
   and record it as theirs.
8. **Approval is specific.** An approval covers what the user saw. "Sounds right" about
   the understanding does not approve the skeleton.
9. **Sizing is a one-way ratchet.** Announce the size before your first question. If you
   uncover hidden complexity, stop, say so, and move to the heavier size. Nothing gets
   lighter mid-storyboard.
10. **No roadmapping.** Never write the roadmap, the live register, a specification
    store, or a sequence. The holding bay is the only place this skill writes. Placement
    is recorded as a recommendation for the review to decide.
11. **Descriptive names first.** Lead every reference to an item with its title; the
    identifier comes second.

---

## Step 1 — Intake

Restate the request in one sentence, in the user's own terms. If the request does not
say what problem the work solves or who it is for, ask that first. Everything else
depends on the answer.

## Step 2 — Size it, out loud

Classify the work and **say the classification**, so the user can override it:

| Size | Signal | What happens |
|---|---|---|
| **Single item** | One outcome, one change unit, fits one dispatch | Storyboard, then `/write-plan` |
| **Item set** | Separable outcomes, or one outcome that needs more than one dispatch | Storyboard the set, then `/write-plan`, with explicit prerequisites between the items |
| **Epic-scale** | Outcome-stated, multi-phase, spans sessions, walk-away | Storyboard it here, because alignment cannot wait. It is then held. The next `/roadmap-review` places it as `Path: epic`, and `/epic` charters it. `/write-plan` never plans it. |
| **Not an item** | An answer rather than shipped work, or a change policy allows without an item | Route per the table above |

> "This looks like a single item: one change to the export path, one dispatch. I'll
> storyboard it as one unless you see more to it."

If the request covers several independent subsystems, say so **before** you refine any
detail, and agree how to split it first.

## Step 3 — Investigate

Before your first substantive question, read:

- the code, configuration, and documents the work will plausibly touch
- the live register, through the provider (`virtuoso_registry --actor storyboard items
  --all --json`): anything that already covers, overlaps, blocks, or depends on this work
- the roadmap's active section and its non-blocking follow-up queue
- the holding bay's open entries (`holding --open`), because the same idea may already
  be held
- the live lessons (`lessons --open`) and the standing rules at
  `policy.standingRules.source`
- the declared deadlines, through the `pace` block of `kpis --json`
- in-flight branches and worktrees, using read-only git
  (`GIT_OPTIONAL_LOCKS=0 git --no-optional-locks …`)

**If the work already exists, stop and say where.** A roadmap item belongs to the
roadmap, and a held entry is reopened rather than duplicated. The user may still tell
you it is genuinely different work. If so, record why in the alignment record.

## Step 4 — Ask through six lenses

Ask one question per message, and only where investigation left a real gap. Put the
highest-leverage lens first. Skip a lens that investigation already answered, and say
that you skipped it.

| Lens | What you need to know |
|---|---|
| **Outcome** | What does done look like, observably? What must never happen? What is out of scope? |
| **Placement** | Where would this sit on the roadmap: which group, lane, or finish line? Does it count toward a declared deadline? Is it more urgent than the current head? The answer is a recommendation the review reads. You never act on it. |
| **Touchpoints** | Which modules, interfaces, data, documents, and tests does it change directly? |
| **Externalities** | Which services, credentials, data owners, users, teams, or repositories outside the codebase does it reach? |
| **Upstream** | What must be true first? Which items, decisions, or dependencies does it wait on, directly or indirectly? |
| **Downstream** | Which items, specifications, consumers, reports, or documents change because this lands? Which dispatch-ready specifications cite a location this will move? |

## Step 5 — Write back the understanding (checkpoint 1)

Show the draft alignment record, in the shape the held-plan template uses
([assets/held-plan.template.md](assets/held-plan.template.md)):

- **Outcome**, **Why now**, **Done looks like**, **Must never happen**, **Out of scope**
- **You said** — their words
- **Assumed** — each assumption with its resolution column still open
- **Decisions** — made so far, and by whom
- **Impact map** — upstream, downstream, sideways, external, and deadline rows, each one
  citing what you read

Then ask: *"Is this what you mean?"* Fold in every correction and show the record again
until the user confirms it. Resolve each assumption here, in the order of what breaks if
it is wrong.

## Step 6 — Walk the frames (checkpoint 2)

Describe 3–6 **frames**: concrete scenes of the world once the work is done, each in the
form *given [situation], when [action], then [observable result]*. Include:

- the main success scene
- at least one scene where something goes wrong: bad input, a failure, a timeout, a
  missing permission
- one scene showing what does **not** change, which carries the *must never happen* row

Ask the user to confirm or correct each frame. A correction usually means a lens missed
something, so update the record too. For work that is not software, a frame is an
observable state: what a reader of the document sees, or what the next person to run the
process can do.

Frames are not decoration. `/write-plan` turns each confirmed frame into a *Done when*
row or a *Review focus* line.

## Step 7 — Choose the approach (checkpoint 3)

When more than one reasonable approach exists, present 2–3 of them with their
trade-offs. Lead with the one you recommend, and say why. Cut any feature the outcome
does not need. When only one approach makes sense, say so in one line and do not invent
alternatives. Record the user's choice under **Decisions**.

## Step 8 — Draft the skeleton (checkpoint 4)

At item altitude, with no implementation detail and no code, draft each item:

- **What**, **Why**, **Out of scope**
- **Done when (draft)** — taken from the confirmed frames
- **Edit sites (expected)** — from investigation, named concretely
- **Prerequisites** — by descriptive name
- **Effort** — low / medium / high / max
- **Interfaces** — for an item set only: what each item consumes and produces

Then add a **placement recommendation** for the review, with its reason, and the
**impact actions**: the downstream items whose specifications this work will make stale.
You flag them here, and the review acts on them. Neither this skill nor `/write-plan`
edits another item.

## Step 9 — The alignment verdict (the gate)

The verdict is **Aligned** only when all of these hold:

- the understanding is confirmed
- every assumption is confirmed, corrected, or accepted with a guard
- every frame is confirmed
- the approach is chosen
- the skeleton is approved
- no question is open

Show the check before asking:

```
Alignment check — [Title]
✓ Understanding confirmed          ✓ [N] frames confirmed
✓ [N] assumptions resolved         ✓ Approach: [name] (chosen by you)
✓ Skeleton approved ([N] item(s))  ✓ No open questions
```

Then ask one bounded question: **(a)** Approve the storyboard *(recommended when every
line above is ✓)*, **(b)** Revise [a named part], or **(c)** Stop.

On approval, write the verdict with the user's own words:
`Aligned — YYYY-MM-DD. The user approved: "…"`. Anything short of approval leaves the
verdict at `Not aligned —`, followed by the open items by name, and returns to the
earliest step that affects them.

## Step 10 — Hold it

1. Copy [assets/held-plan.template.md](assets/held-plan.template.md) into the holding
   bay as `<yyyy-mm-dd>-<slug>.md`. Fill in the header, and fill in the `## Storyboard`
   section: alignment record, frames, approach, skeleton, and verdict. Leave `## Plan`
   empty.
2. Check it. The only finding you should see is `held-unrecorded`:

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . holding --check <entry>

3. Record it. Preview the command first, then run it with `--apply`:

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor storyboard holding --record <entry> --state storyboarded --note "<one line: aligned; N items>" --apply

   The record is refused unless the verdict reads *Aligned*. That refusal is the gate
   working, not an obstacle to route around.
4. Persist the file as `policy.git` permits, using the same five-level table next-pointer's
   Phase 3.5 applies: report it, leave it, stage it, commit it, or push it. Stage the exact
   path only.

Reopening a held entry (`/storyboard <entry>`) edits that same file and records
`storyboarded` again. If the entry was already `planned`, its plan no longer stands:
say so, because `/write-plan` must rewrite the plan before the entry can be planned
again.

## Step 11 — Continue

- **Single item or item set:** ask whether to continue into `/write-plan` now.
  **(a)** Continue now *(recommended: the context is warm, and the alignment is
  fresh)*. **(b)** Hold the storyboard. The entry stays in the holding bay:
  `/write-plan <entry>` resumes it any time, and otherwise the next `/roadmap-review`
  absorbs it as a stub, with this alignment record as its source. **(c)** Withdraw it,
  giving a reason (`--state withdrawn --note "<reason>"`).
- **Epic-scale:** it is held. Tell the user the route: the next `/roadmap-review` places
  it on the master roadmap as `Path: epic`, and `/epic` charters it from there with this
  alignment record as its source. If they want to start soon, offer to run
  `/roadmap-review` now.

---

## Output — the summary

```
# Storyboard — [Title]

**[One-sentence outcome.]** *(held as [entry] · [size])*

| | |
|---|---|
| Aligned | YYYY-MM-DD — "[the user's words]" |
| Frames | [N] confirmed |
| Assumptions | [N] resolved — [n] confirmed · [n] corrected · [n] accepted with a guard |
| Approach | [the chosen approach] |
| Skeleton | [N] item(s) |
| Impact | [n] upstream · [n] downstream · [n] sideways · [n] external |
| Placement (recommended) | [for the review to decide] |
| Next | /write-plan now · held for review · epic-scale → review → /epic |
```

## Red flags

| Thought | Reality |
|---|---|
| "I already understand what they want" | Then the write-back takes thirty seconds. Show it. |
| "They said yes to the summary, so the skeleton is approved" | Approvals are specific. The skeleton has its own checkpoint. |
| "This assumption is obviously right" | Then confirming it is cheap. An unconfirmed assumption is how a plan goes wrong without anyone noticing. |
| "I'll ask all my questions at once to save time" | A wall of questions gets half-answered. Ask one at a time, highest leverage first. |
| "Frames are overkill for this" | One success frame and one failure frame take a minute, and they catch what a list of requirements hides. |
| "I'll put it on the roadmap so it isn't lost" | The holding bay is where it isn't lost. The roadmap is `/roadmap-review`'s to write. |
| "It's epic-scale, so I'll start the charter" | `/epic` starts from the master roadmap, after a review has placed the work. |
| "They disagreed with my recommendation, so I'll quietly build mine" | Say it once, then build theirs and record it as their decision. |

## Integration

- `references/execution-paths.md` — the three paths and the one destination they share.
- `/write-plan` — the continuation. It always starts from the storyboard this skill holds.
- `/roadmap-review` — absorbs or withdraws every open held entry at the next review.
- `adversarial-review` — an optional red-team of the skeleton before approval.
