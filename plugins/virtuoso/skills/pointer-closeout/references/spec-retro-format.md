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

## Running Lessons Document

Retrospective lessons are appended to:

- `SpecRetro.Lessons_Learned.md`

Use sequential IDs:

- `<prefix>-001`
- `<prefix>-002`

The prefix is project configuration — `SRL` is only the default. Resolve the next
identifier with `virtuoso_registry closeout --lesson-prefix <prefix>`, which reads the
registered lessons document and never creates it.
- ...

Check the existing document before appending new entries.
