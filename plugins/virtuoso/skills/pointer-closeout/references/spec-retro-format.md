# Spec Retrospective Format

Use this reference for the workflow-facing retrospective.

## Verdict Style

Lead with clear verdicts, not empty tables:

- "Effort calibration: slightly under-scoped."
- "Dispatch precision: high."
- "Discovery yield: worth the sprint."

Use tables only as scaffolding for the reasoning.

## Review Categories

Evaluate:

- effort calibration
- sizing accuracy
- agent routing
- dispatch precision
- discovery yield
- workflow recommendations

## Suggested Structure

1. One-paragraph overall verdict
2. 2-5 focused sections with evidence
3. 2-5 workflow recommendations

## Recommendation Rules

Each recommendation must say:

- what should change
- why
- where it applies

Avoid vague advice like "be more specific."

## The lessons document

Lessons are appended to the registered `lessons` role. Resolve it through the
registry, never by filename, and read it before appending:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --open

Identifiers are `<prefix>-NNN`. The prefix is `policy.lessons.idPrefix` (`SRL` by
default) and the next free identifier is `nextLessonId` in
`virtuoso_registry closeout --item <ID> --date <date>`, which reads the registered
document and never creates it.

One entry per lesson, in this shape — these fields are what `lessons` reads back:

    ### <prefix>-NNN — Short title (ITEM-ID, YYYY-MM-DD)
    **Verdict:** what was learned, in a sentence or two
    **Evidence:** what happened, with numbers or scope
    **Recommendation:** the concrete change a future specification should make
    **Applies to:** when it bears on future work
    **Status:** Observation

`Applies to` is the field a future author matches against a new item. Write *when*
it bears — "any item that adds a gate", "continuations on a red base" — not a category.

**Status records, never edits.** The role is append-only. To promote, retire, or
supersede a lesson, append a new entry under the same identifier whose field is its
status; the latest status recorded is the current one, and the history shows why:

    ### <prefix>-NNN — status (ITEM-ID, YYYY-MM-DD)
    **Status:** Promoted -> standing rule <rule id> (second occurrence in ITEM-ID)

A lesson is **live** until a status beginning `Promoted`, `Retired`, or `Superseded`
is appended. The live lessons are what readiness check U9 holds every specification
to.
