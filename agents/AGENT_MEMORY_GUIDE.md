# Shared Agent Memory Guide

All GoG agents use a persistent, file-based memory system at:
`<project-root>/.claude/agent-memory/{agent-name}/`

## Memory Types

| Type | Purpose | Save When |
|------|---------|-----------|
| `user` | User's role, preferences, expertise | Learn about user's background or working style |
| `feedback` | Corrections to your approach | User says "don't...", "instead do...", "stop..." |
| `project` | Ongoing work, bugs, decisions not in code/git | Learn who/what/why/when about work in progress |
| `reference` | Pointers to external resources | Learn about tools, docs, or systems outside the repo |

## How to Save

**Step 1** — Write memory to its own file with frontmatter:
```markdown
---
name: {{memory name}}
description: {{one-line description}}
type: {{user|feedback|project|reference}}
---
{{memory content}}
```

**Step 2** — Add pointer to `MEMORY.md` index (keep under 200 lines).

## Rules
- Don't duplicate what's in code, git history, or CLAUDE.md
- **Don't duplicate what belongs in the ICM Knowledge System.** When a finding is about measured or inferred interaction behavior, store it in the ICM system (Interaction Registry, Calibration Strategy Guide, or Validation Log), not in agent memory. Memory should only retain workflow-specific pointers, stable user preferences, or external references.
- Don't save ephemeral task state — use tasks/plans for that
- Convert relative dates to absolute dates
- Update/remove outdated memories
- Check for existing memory before creating duplicates

## ICM Knowledge System Reference
- **Governing spec**: `2. Project Documentation/1 governance/ICM_Knowledge_System_Specification.md` (v2.3)
- **Interaction Registry**: `.GOGFight_Engine/Calibration/interaction_registry.toml`
- **Calibration Strategy Guide**: `.GOGFight_Engine/Calibration/calibration_strategy_guide.toml`
- **Validation Log**: `.GOGFight_Engine/Calibration/validation_log.json`
- **Custodian**: MarcusAurelius (executes triage gate, maintains all 3 artifacts)

## Bash Execution Rule
**Never run multi-line Python as inline bash strings.** This triggers security prompts about `#`-prefixed lines hiding arguments. Instead:
1. Write a temp `.py` file (e.g., `/tmp/agent_query.py`)
2. Run it: `python /tmp/agent_query.py`
3. Clean up if needed

This applies to ALL agents running SQLite queries, data analysis, calibration scripts, or any Python longer than a single expression.

## Findings Output
All agents write findings to: `2. Project Documentation/2 operational/AGENT_FINDINGS.md`
Use the template in that file. Status flow: NEW → TRIAGED → Phase X.Y | DEFERRED | WONTFIX
