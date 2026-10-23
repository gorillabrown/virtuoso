# Codex host fixtures

Captured 2026-10-22 on the owner's Windows machine (windows-aarch64), Codex CLI 0.163.0 (npm
`@openai/codex`, `originator: codex_exec`), model `gpt-6.1-sol`, ChatGPT sign-in. One specimen
excerpt comes from a Codex Desktop session (`cli_version: 0.163.0-alpha.10.2`). The files are
for VIR-051 *Must verify* items 1 and 2. They are test input for `tools/governance/hosts/codex.py`.

**No hook stdin was captured.** Project-level hooks (`<cwd>\.codex\hooks.json`) load only when
the project is trusted. Trust is stored in the user-level `~/.codex/config.toml`
(`[projects."<path>"] trust_level`), and a `-c projects…trust_level` override on the command line
did not load the project layer. The user config was not edited, so the probe hook never ran.
For the same reason no PreToolUse deny or UserPromptSubmit block was captured.

## Scrubbing

- Prompt text is `<prompt-text>`, assistant text is `<response-text>`, developer and
  instruction text is `<developer-text>` / `<base-instructions>`, the environment block is
  `<environment-context>`, hook-injected developer context is `<hook-additional-context>`, and
  reasoning is `<thinking>`. Encrypted blobs (`gAAAA…`: spawn messages, `encrypted_content`) are
  `<encrypted>`. Inter-agent messages keep their harness header (`Message Type:`, `Task name:`,
  `Sender:`, `Payload:`), and the payload text is `<inter-agent-payload>`.
- In `world_state` and `additional_tools`, every string longer than 64 characters is
  `<redacted>`, and `approved_command_prefixes` is `[["<redacted>"]]`.
- Probe commands and their outputs are kept as they ran. Run 1 tried
  `python -c "…sys.stderr.write('v51err'); sys.exit(3)"`, `echo v51ok` and `echo v51deny`.
  Run 2 ran `python -c "…print('v51out'); sys.stderr.write('v51err'); sys.exit(3)"` and
  `echo v51ok`. In run 3 the subagent ran `…sys.stderr.write('v51suberr'); sys.exit(4)` and
  `echo v51subok`.
- Placeholders: `<home>` is the user profile, `<cwd>` the scratch capture folder,
  `<projects>\<other-project>` another project folder, and `<user>` the username.
  `creator_user_id`, `creator_account_id` and `rate_limits.plan_type` are `<user-id>`,
  `<account-id>` and `<plan>`. In the specimen, the git URL and commit are `<repository-url>`
  and `<commit>`.
- Ids are renamed the same way in every file here, so cross-file links still resolve. Thread
  ids are `11111111-…` (run 1), `22222222-…` (run 2), `33333333-…` (run 3 parent) and
  `44444444-…` (run 3 subagent). In the specimen they are `55555555-…` (desktop parent) and
  `66666666-…` (desktop subagent). Every other uuid becomes `f0000NNN-0000-7000-8000-…`. Hex
  ids with a prefix (`call_`, `resp_`, `msg_`, `ctc_`, `fc_`) become `<kind>_FX<counter>`. Ids
  with a uuid suffix keep their prefix, and the uuid is mapped as above.
- Kept as captured: every key, the record order, `ordinal`, timestamps, usage numbers, model
  ids, exit codes, `status`, `agent_path`, `agent_nickname`, `task_name` and rate-limit
  numbers.

## Layout

`sessions/` stands in for `$CODEX_HOME/sessions/`.

| File | Source | What it shows |
|---|---|---|
| `sessions/2026/10/22/rollout-2026-10-22T20-13-15-11111111-1111-7111-8111-111111111111.jsonl` | run 1: `codex exec --json --skip-git-repo-check --ignore-user-config --dangerously-bypass-hook-trust -s workspace-write` in `<cwd>` | `--ignore-user-config` left `sandbox_policy: read-only`, `approval_policy: never`. Each shell call is a `custom_tool_call` (`name: exec`) whose `custom_tool_call_output` reads `Script failed … Script error: exec_command failed: CreateProcess { … Rejected(…) rejected: blocked by policy }`. There is no `CommandExecution` item. No plugin SessionStart hook ran (no `hooks.additional_context` message). |
| `sessions/2026/10/22/rollout-2026-10-22T20-18-05-22222222-2222-7222-8222-222222222222.jsonl` | run 2: `codex exec --json --skip-git-repo-check -s workspace-write` in `<cwd>` | a failing command: `item_completed` → `CommandExecution` with `status: failed`, `exit_code: 1` (python exited 3; `pwsh -Command` reports 1), and stdout and stderr merged in `aggregated_output` (`v51errv51out`). A succeeding one (`status: completed`, `exit_code: 0`). `token_usage_record` per response (`usage` / `turn_token_usage` / `thread_token_usage`) and `event_msg` `token_count` (`total_token_usage` / `last_token_usage`). The user-level plugin SessionStart hooks' output becomes developer messages with `content_item_kinds: ["hooks.additional_context"]`. |
| `sessions/2026/10/22/rollout-2026-10-22T20-22-35-33333333-3333-7333-8333-333333333333.jsonl` | run 3 parent (same flags as run 2) | `function_call` `spawn_agent` (`namespace: collaboration`): `task_name: row_5_probe` is plain text and `message` is `<encrypted>`. `SubAgentActivity` `kind: started` (id = the spawn `call_id`, `agent_thread_id`, `agent_path: /root/row_5_probe`). `wait_agent`, `CollabAgentToolCall`, `SubAgentActivity` `kind: completed`, and the subagent's `agent_message` (`author: /root/row_5_probe`, `recipient: /root`). The parent's usage records do not include the subagent's tokens. |
| `sessions/2026/10/22/rollout-2026-10-22T20-22-43-44444444-4444-7444-8444-444444444444.jsonl` | run 3 subagent | its own rollout file. `session_meta` `id` is the subagent thread, `session_id` is the root, and `parent_thread_id`, `forked_from_id`, `source.subagent.thread_spawn {parent_thread_id, depth, agent_path, agent_nickname, agent_role}`, `thread_source: subagent` and `subagent_history_start_ordinal: 11` are set. A second `session_meta` (the parent's) and the parent's history are replayed in ordinals 1–10, marked `inherited_user_message: true`. Its own failing and succeeding `CommandExecution` items, and `token_usage_record` with `thread_id` = the subagent and `session_id` = the root. |
| `exec_json/exec_json_run1.jsonl`, `exec_json_run2.jsonl`, `exec_json_run3.jsonl` | the stdout of `codex exec --json` for runs 1–3 | the headless event stream: `thread.started`, `turn.started`, `item.started` / `item.completed` (`command_execution` with `exit_code` and `status`, `agent_message`, `collab_tool_call`, `error`), and `turn.completed.usage` (the parent thread only) |
| `hooks/hook_schemas.0.163.0.json` | the JSON Schemas (draft-07) embedded in the installed 0.163.0 binary (`@openai/codex-win32-arm64/vendor/aarch64-pc-windows-msvc/bin/codex.exe`), pulled out as strings and not changed | the input and output schemas for every command-hook event (`<event>.command.input` / `.command.output`): `session-start`, `session-end` (input only), `user-prompt-submit`, `pre-tool-use`, `permission-request`, `post-tool-use`, `pre-compact`, `post-compact`, `stop`, `subagent-start`, `subagent-stop`, `interrupt`. This is documented, not captured: no hook ran in these sessions. |
| `specimen/desktop_spawn_excerpt.jsonl` | Codex Desktop session, 2026-10-21: 4 parent records and 2 subagent records | a `spawn_agent` with `agent_type`, `model`, `reasoning_effort`, `fork_turns: none`; `SubAgentActivity` started and completed; the subagent's `session_meta` (`agent_role: Plato`, no `forked_from_id`) and its first `token_usage_record` |
