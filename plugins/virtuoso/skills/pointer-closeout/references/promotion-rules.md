# Promotion Rules

Use this reference when deciding whether a retrospective lesson stays an observation or
becomes a standing workflow rule.

## Default Rule

- First occurrence: record as **Observation**
- Second occurrence of the same pattern: **Promote**

## Promotion Workflow

1. List the live lessons — the registered role, never a filename:
   `virtuoso_registry --root . lessons --open`.
2. Search them for the same pattern or recommendation theme.
3. If it already exists:
   - append a status record under the earlier identifier, citing this second
     occurrence; never edit the earlier entry:
     `virtuoso_registry --root . lessons --record-status <ID> --status "Promoted -> <destination>" --actor pointer-closeout --item <ITEM-ID> --apply`
   - write the promoted rule into the destination document
   `lessons --candidates` computes the same second occurrences across every close-out;
   `roadmap-review` works through it at each review, and `governance-sweep` merges
   what recurred with `lessons --hygiene`.
4. If it does not exist:
   - append a new `<prefix>-NNN` entry
   - set its status to `Observation`

## Good Promotion Targets

- workflow reference
- dispatch template
- agent reference / routing docs
- lessons learned for workflow patterns

Do not promote one-off anecdotes.
