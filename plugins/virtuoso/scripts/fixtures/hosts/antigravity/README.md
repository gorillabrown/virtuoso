# Antigravity host fixtures

Captured 2026-11-18 on the owner's Windows 11 machine, Antigravity CLI `agy` 1.5.11, model
`gemini-4-argon-medium`. Every run was headless: `agy -p "<prompt>" --output-format json`, run in a
scratch folder with `--settings` that trusted the folder and allowed its commands. The files are
test input for `tools/governance/hosts/antigravity.py`, and the guard and preflight tests use
them too.

## The probe hook

The capture runs used workspace hooks (`<cwd>\.agents\hooks.json`) that ran `cap.py` for every
event. It appended each hook's stdin to a file, along with its working folder, a few environment
variables and, for PreInvocation, SessionStart and Stop, the last two transcript records at the
moment the hook ran. It answered three probes:

- **SessionStart** printed `{"injectSteps":[{"systemMessage":{"systemMessage":"AGY-CTX-TOKEN-7731: …"}}]}`.
  The model repeated the token (run 1), so this context reaches it.
- **PreToolUse** on a call whose arguments held `AGYDENY` printed
  `{"decision":"deny","reason":"AGY probe deny: …"}`. The call was refused, and the transcript
  recorded the step as `status: ERROR` (run 1, step 9).
- **PreInvocation** at `invocationNum` 0 with `AGYBLOCK` in `lastUserInput` printed an
  `errorMessage` with `terminationBehavior: "terminate"`. The prompt was held. In `-p` mode the
  run then ended with `status: ERROR` and exit code 3 (run 4).

A hook that prints plain text instead of JSON fails with a protojson unmarshal error, which is
why the preflight answers in JSON.

## What the capture showed about the host

- Hook stdin is camelCase. It carries `conversationId`, `cwd`, `workspacePaths`,
  `transcriptPath`, `artifactDirectoryPath`, `modelName` and `lastUserInput`. PreInvocation adds
  `invocationNum` and `initialNumSteps`. Tool events add `toolCall {name, args}`. Stop adds
  `continuationActive`.
- `transcriptPath` names `.system_generated/logs/transcript_full.jsonl`. The compact
  `transcript.jsonl` beside it holds the same records with tool arguments JSON-encoded as strings.
- Hooks ran through `cmd /c` with the working folder set to the folder that holds the hooks
  file (`_hookCwd`). `PLUGIN_ROOT` was not set for these workspace hooks (`_pluginRootEnv`).
- There is no headless marker in the hook input or the transcript.
- Records carry no call ids. A tool result pairs with its call by order.
- `input_tokens` excludes `cache_read_tokens`; their sums match the CLI's `usage` totals. No
  cache writes are reported.
- A shell result reads `Command exited with code N.` with the wrapper's code, so
  `sys.exit(4)` shows as 1. PostToolUse carries no error for a failing command.
- A whole-file read stops at 800 lines and at 46,080 bytes, whichever comes first.
- A subagent is its own conversation with its own transcript, listed in the parent's
  `.system_generated/subagents/<id>.json` with `subagentDescriptor.role`. Its hooks, SessionStart
  included, fire under its own `conversationId`, and its message back wakes the parent with `invocationNum` 0 again.
- A resumed conversation (`--conversation <id>`) fires no SessionStart. A held prompt still
  writes its `USER_INPUT`, followed by a `SYSTEM_SDK` `ERROR_MESSAGE`.

## Scrubbing

- Prompts are the innocuous test prompts as they were typed. Thinking is `<thinking>`, and the
  content of file reads is `<tool-output trimmed>`. Shell output, harness messages, the probe
  token and the probe reasons are kept.
- Paths are placeholders:

  | Placeholder | What it stands for |
  |---|---|
  | `<home>` | the user profile |
  | `<cwd>` | the scratch capture folder (the workspace) |
  | `<capture>` | the folder that held the probe hook |
  | `<plugin>` | the installed plugin folder |

  Each is replaced in its plain, JSON-escaped and forward-slash forms.
- The username is `<user>`.
- Ids are renamed the same way in every file here, so cross-file links still resolve.
  Conversation ids are `11111111-…` (run 1), `22222222-…` (runs 2 to 4, one conversation
  resumed twice), `33333333-…` (the run-2 subagent) and `44444444-…` (run 5). Tool-call ids
  become `call_FX<counter>`.
- `_hookCwd`, `_pluginRootEnv` and `_transcriptTailAtHook` in the stdin files were added by the
  probe hook. Everything else is the host's.
- Kept as captured: every key, the record order, step indexes, timestamps, statuses, usage
  numbers, the model id and the subagent role.

## Layout

`brain/` stands in for `~/.gemini/antigravity-cli/brain/`. To resolve hook paths against these
files, replace `<home>\.gemini\antigravity-cli\brain` with `brain`.

| File | Source | What it shows |
|---|---|---|
| `brain/11111111-…/.system_generated/logs/transcript_full.jsonl` | run 1 | two failing `run_command` calls (`python -c "import sys; sys.exit(3)"`), `echo agyok`, `echo AGYDENY` denied by the hook (`status: ERROR`), a `read_file`, a `write_file`, and a closing answer that repeats the SessionStart token |
| `brain/22222222-…/.system_generated/logs/transcript_full.jsonl` | runs 2 to 4 | run 2: a whole-file `read_file` of a 3000-line file (`Showing lines 1-800 of 3000`) and an `invoke_subagent` in the same step, the subagent's message waking the parent (`SYSTEM` `SYSTEM_MESSAGE`); run 3: a resumed second turn; run 4: the held `AGYBLOCK` prompt (`USER_INPUT`, then `ERROR_MESSAGE`) |
| `brain/22222222-…/.system_generated/logs/transcript.jsonl` | runs 2 to 4 | the compact form of the same conversation |
| `brain/22222222-…/.system_generated/subagents/33333333-….json` | run 2 | the subagent listing: `conversationId`, `subagentDescriptor.role: "row 7 - capture probe"`, `spawnStepIndex` |
| `brain/33333333-…/.system_generated/logs/transcript_full.jsonl` | run 2, subagent | `echo agysub` and a failing `sys.exit(4)` in one step, then `send_message` to the parent |
| `brain/44444444-…/.system_generated/logs/transcript_full.jsonl` | run 5 | an `edit_file` and a ranged `read_file` (`StartLine` 10, `EndLine` 20) |
| `hooks/stdin_run1.jsonl` … `stdin_run5.jsonl` | the stdin of every hook, in firing order | SessionStart, PreInvocation and PostInvocation around every model call, PreToolUse and PostToolUse per call, Stop; in run 2, the subagent's hooks under its own `conversationId`; runs 3 and 4 have no SessionStart |
| `hooks/headless_output_run1.txt` … `headless_output_run5.txt` | the `--output-format json` result of each run | `conversation_id`, `status`, `response`, `num_turns` and `usage`; run 4 is `status: ERROR` with the probe's block message |
| `hooks/live_read_capped.txt` | a later live run, 2026-11-18, same version | the head of a whole-file read of a 1000-line file with 121-byte lines: `Partial read (lines 1-800 of 1000). Showing bytes 0-46080 …, truncated at the 46080-byte limit` |
