# Claude Code host fixtures

Captured 2026-10-22 on the owner's Windows machine, Claude Code 2.1.309 (headless captures) and
2.1.304 (desktop specimen records), for VIR-051 *Must verify* items 3 and 4. They are test input
for `tools/governance/hosts/claude_code.py`.

## Scrubbing

- Prompt text is `<prompt-text>`, assistant text is `<response-text>`, thinking is `<thinking>`, and
  signatures are `<signature>`. Output from non-probe tools is `<tool-output>`. The one exception
  is a leading `Exit code N` line, which is kept.
- Harness-written messages are kept as they appeared. These are denials, interruptions, the hook
  block text and the async-launch notice.
- Commands and outputs from the probe runs are kept as they ran (`echo v51-top`, `echo V51DENY`,
  `ls /v51-does-not-exist`). The probe hook's own reasons and context token (`V51 ...`,
  `V51-CTX-TOKEN-7731`) are kept too.
- Paths are placeholders:

  | Placeholder | What it stands for |
  |---|---|
  | `<home>` | the user profile |
  | `<cwd>` | the scratch capture folder |
  | `<repo>` | the private dev clone |
  | `<projects>\<other-project>` | other project folders |
  | `<project-folder>` | the transcript folder for the capture runs |
  | `<project-folder-specimen>` | the transcript folder for the desktop specimen |

- The username and email are `<user>` and `<email>`.
- Ids are renamed the same way in every file here, so cross-file links still resolve. Session
  ids are `11111111-…` (run 1), `22222222-…` (run 2), `33333333-…` (run 3) and `55555555-…`
  (specimen). Agent ids are `a2222222222222222` (the run-2 subagent) and `a5555555555555555`
  (the specimen subagent). Every other uuid becomes `f0000NNN-0000-4000-8000-…`, and
  `toolu_`/`msg_`/`req_` ids become `<kind>_FX<counter>`.
- Kept as captured: every key, the record order, usage numbers, model ids, timestamps and spawn
  descriptions.
- Transcript record types are trimmed as follows:
  - Dropped: `api-request`, `api-request-blob`, `api-request-shape`, `atis-latch`,
    `file-history-*`, `bridge-session`, `agent-name` and `custom-title`.
  - Attachments: only `hook_success` and `hook_additional_context` are kept, and other hooks'
    output is replaced with placeholders.

## Layout

`transcripts/<set>/` stands in for `~/.claude/projects/<project-folder>/`. To resolve hook paths
against these files, replace `<home>\.claude\projects\<project-folder>` with
`transcripts/capture`.

| File | Source | What it shows |
|---|---|---|
| `transcripts/capture/11111111-1111-4111-8111-111111111111.jsonl` | headless run 1: `claude -p` in a scratch folder | a failing shell call (`is_error: true`, `Exit code 2`); a PreToolUse deny of the `Agent` call at top level; SessionStart `additionalContext` reaching the model; 1h-only cache writes |
| `transcripts/capture/22222222-2222-4222-8222-222222222222.jsonl` | headless run 2 | a foreground `Agent` spawn whose description is `row 7 - capture probe`; the synchronous `toolUseResult` (`status: completed`, `agentId`, `handback`, `usage`, `totalTokens`); `promptSource`/`turnOrigin: "sdk"`; the closing `cost-state` record |
| `transcripts/capture/22222222-2222-4222-8222-222222222222/subagents/agent-a2222222222222222.jsonl` | headless run 2, subagent | `agentId` on every record; a PreToolUse deny inside the subagent (`toolDenialKind: permission-rule`, `permissionDecision.source: hook`); `SubagentHandback`; 5m-only cache writes |
| `transcripts/capture/22222222-2222-4222-8222-222222222222/subagents/agent-a2222222222222222.meta.json` | headless run 2 | `description`, `toolUseId`, `spawnDepth`, `requestShape` |
| `transcripts/capture/33333333-3333-4333-8333-333333333333.jsonl` | headless run 3 | a prompt blocked by UserPromptSubmit: no user record is written, only a `system`/`informational` record with `promptSubmitEnding.ending.kind: blocked_by_hook` |
| `transcripts/specimen/55555555-5555-4555-8555-555555555555.jsonl` | desktop session record excerpt | a background (async) spawn: the `Agent` tool_use (two blocks of one `message.id`); `toolUseResult` with `isAsync: true`, `status: async_launched`, `agentId`, `outputFile`; the `<task-notification>` queue-operation and user record carrying `<usage>` |
| `transcripts/specimen/55555555-5555-4555-8555-555555555555/subagents/agent-a5555555555555555.jsonl` | desktop subagent, first 21 user/assistant records | `output_tokens` growing across blocks of one `message.id` (20 then 224; 59, 59 then 237); 5m-only writes; `attributionAgent` |
| `transcripts/specimen/55555555-5555-4555-8555-555555555555/subagents/agent-a5555555555555555.meta.json` | desktop subagent | async meta (`requestShape: background`, `finished`) |
| `hooks/stdin_run1.jsonl` | stdin of each hook in run 1, in firing order | SessionStart, UserPromptSubmit, PreToolUse/PostToolUse, Stop, SessionEnd; no PostToolUse for the failing call |
| `hooks/stdin_run2.jsonl` | stdin of each hook in run 2 | SubagentStart and the PreToolUse/PostToolUse calls inside the subagent, which carry `agent_id` and `agent_type`; SubagentStop with `agent_transcript_path`; a second UserPromptSubmit for the subagent hand-back (`<agent-message from=…>`); Stop; SessionEnd |
| `hooks/stdin_run3.jsonl` | stdin of each hook in run 3 | SessionStart, the blocked UserPromptSubmit, SessionEnd (no Stop) |
| `hooks/headless_output_run1.jsonl` | `claude -p --output-format json` result, run 1 | `permission_denials` lists the hook-denied call; `usage.cache_creation` |
| `hooks/headless_output_run3.jsonl` | `claude -p --output-format json`, run 3 | the `system`/`informational` block message, and a result with `num_turns: 0` and zero usage |
| `records/denials_and_declines.jsonl` | desktop sessions in other projects, plus this machine's row-4 subagent | tool_use and tool_result pairs: `user-rejected` (PowerShell, in a subagent), `cancelled` (Edit), `permission-rule` with a hook exit 2 (Bash), `automode-blocked`, `interrupted` |
| `records/meta_variants.jsonl` | four `.meta.json` files | async spawn; fork (`isFork`, `model: inherit`); nested (`parentAgentId`, `spawnDepth: 2`); workflow subagent (`workflowPhase`, no `toolUseId`; the transcript lives under `subagents/workflows/wf_*/`) |
| `records/copied_session_zero_usage.jsonl` | a desktop session continued from another | the same `message.id` recorded twice: once with real usage under the original `sessionId`, then again under the new `sessionId` with top-level usage zeroed (`iterations` still non-zero) |

The probe hook was `cap.py`. On stdin it appended the JSON to a file. For SessionStart it printed
`hookSpecificOutput.additionalContext`. For PreToolUse on a shell command containing `V51DENY` it
printed `permissionDecision: "deny"`. For UserPromptSubmit containing `V51BLOCK` it printed
`{"decision":"block","reason":…}`.
