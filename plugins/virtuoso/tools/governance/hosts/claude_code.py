"""Claude Code: transcripts under ``~/.claude/projects/<folder>/<session>.jsonl``, each
subagent's beside it in ``<session>/subagents/`` (``agent-<agent_id>.jsonl``, workflow
subagents one folder deeper) with an ``agent-<agent_id>.meta.json`` naming its spawn
description; hooks read JSON on stdin.

Facts this module relies on were captured from Claude Code 2.1.309 on 2026-10-22
(fixtures: ``scripts/fixtures/hosts/claude_code/``):

* one API response is written as one record per content block, each repeating
  ``message.id`` and the usage; ``output_tokens`` can grow across those records, so a
  response is counted once, at its largest ``output_tokens``. A continued session copies
  earlier responses under its new session id with the usage zeroed: a record of the file's
  own session wins, so the copy never carries the earlier session's cost;
* cache writes are split by lifetime (``cache_creation.ephemeral_5m/1h_input_tokens``), and
  the lifetime depends on how the account is billed, so it is read from the writes;
* a failed shell call (Bash or PowerShell) is a ``tool_result`` with ``is_error`` and
  ``Exit code N``; a step the person declined carries ``toolDenialKind`` ``user-rejected``
  or ``cancelled``;
* a prompt Claude Code injected (a subagent's hand-back, a task notification, a slash
  command's expansion, a compaction summary) also reaches the prompt hook, and is not a
  typed prompt;
* a headless run marks its prompt ``promptSource`` / ``turnOrigin`` ``sdk``.
"""
from __future__ import annotations

import json
import os
import re

from . import (DROPPED_AFTER, FIXED, Adapter, Call, TranscriptFacts, Usage, count_failure,
               head_records, is_read_only, read_jsonl)

SHELL_TOOLS = frozenset({"Bash", "PowerShell"})
EDIT_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
SPAWN_TOOLS = frozenset({"Agent", "Task"})
DECLINED = frozenset({"user-rejected", "cancelled"})
SYNTHETIC_MODEL = "<synthetic>"
#: Prompt text Claude Code writes itself, never typed by the person.
_INJECTED_RE = re.compile(r"^\s*(?:<(?:agent-message|task-notification|command-name|"
                          r"command-message|local-command-stdout|local-command-caveat|"
                          r"system-reminder)\b|\[Request interrupted by user)")
_EXIT_RE = re.compile(r"^Exit code (\d+)")


class ClaudeCode(Adapter):
    name = "claude-code"
    capabilities = frozenset({"read-transcript", "read-subagent-transcript", "hold-prompt",
                              "hold-tool", "hold-tool-in-subagent", "session-start-context",
                              "cache-lifetime", "edit-tracking", "turn-end-message"})
    missing: dict[str, str] = {}
    cache_lifetime = FIXED
    #: When a transcript shows no cache write: a subscription's main conversation keeps
    #: 60 minutes, a subagent 5 (inferred, never measured).
    cache_minutes = (60, 5)

    def read_transcript(self, path: str, tail_bytes: int | None = None) -> TranscriptFacts:
        facts = _facts(read_jsonl(path, tail_bytes), _session_of(path))
        if tail_bytes and not facts.headless:
            facts.headless = any(_is_headless(r) for r in head_records(path))
        return facts

    # --- hooks ------------------------------------------------------------------------------

    @staticmethod
    def is_subagent(hook: dict) -> bool:
        return bool(hook.get("agent_id"))

    @staticmethod
    def is_injected_prompt(prompt: str) -> bool:
        return bool(_INJECTED_RE.match(prompt or ""))

    @staticmethod
    def subagent_transcript(hook: dict) -> str:
        """The subagent's own transcript, for a hook fired inside it ("" at top level)."""
        agent, transcript = hook.get("agent_id"), hook.get("transcript_path") or ""
        if not agent or not transcript:
            return ""
        return os.path.join(os.path.dirname(transcript), hook.get("session_id") or
                            _session_of(transcript), "subagents", "agent-%s.jsonl" % agent)

    @staticmethod
    def hold_prompt(reason: str) -> dict:
        return {"decision": "block", "reason": reason}

    @staticmethod
    def deny_tool(reason: str) -> dict:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "permissionDecision": "deny",
                                       "permissionDecisionReason": reason}}

    @staticmethod
    def session_context(text: str) -> dict:
        return {"hookSpecificOutput": {"hookEventName": "SessionStart",
                                       "additionalContext": text}}

    @staticmethod
    def turn_end_message(text: str) -> dict:
        """Shown to the person when a turn ends (a Stop hook's ``systemMessage``: captured as
        a notice, never added to the model's context)."""
        return {"systemMessage": text}

    # --- subagents and their rows -----------------------------------------------------------

    @staticmethod
    def spawn_description(subagent_path: str) -> str:
        """The spawn description of a subagent transcript, from its ``.meta.json``; a nested
        subagent takes its depth-1 ancestor's, so a row's helpers count to the row. A
        subagent no spawn call started (a workflow's) has none: it is orchestration."""
        folder = os.path.dirname(subagent_path)
        meta = _meta(subagent_path)
        seen = set()
        while meta.get("parentAgentId") and meta["parentAgentId"] not in seen:
            seen.add(meta["parentAgentId"])
            parent = _meta(os.path.join(folder, "agent-%s.jsonl" % meta["parentAgentId"]))
            if not parent:
                break
            meta = parent
        return str(meta.get("description") or "") if meta.get("toolUseId") else ""

    @staticmethod
    def transcript_roots() -> list[str]:
        """Where this host keeps top-level transcripts: ``<config>/projects/<folder>/``,
        ``<config>`` being ``CLAUDE_CONFIG_DIR`` when set, else ``~/.claude``."""
        config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(
            os.path.expanduser("~"), ".claude")
        return [os.path.join(config, "projects")]

    @staticmethod
    def top_level_transcripts(root: str) -> list[str]:
        """The top-level session files under a root (subagents live one folder deeper)."""
        found = []
        try:
            folders = sorted(os.listdir(root))
        except OSError:
            return found
        for folder in folders:
            path = os.path.join(root, folder)
            try:
                names = os.listdir(path)
            except OSError:
                continue
            found += [os.path.join(path, n) for n in sorted(names) if n.endswith(".jsonl")]
        return found

    def subagents(self, transcript: str, facts: TranscriptFacts | None = None):
        """Each subagent of a session: ``(path, description, task_name)`` for the row rule."""
        return [(path, self.spawn_description(path), "")
                for path in self.subagent_transcripts(transcript)]

    @staticmethod
    def subagent_transcripts(transcript: str) -> list[str]:
        """Every subagent transcript of a top-level session, workflow ones included, in
        path order."""
        folder = os.path.join(os.path.dirname(transcript), _session_of(transcript), "subagents")
        found = []
        for path, _dirs, names in os.walk(folder):
            found += [os.path.join(path, n) for n in names
                      if n.startswith("agent-") and n.endswith(".jsonl")]
        return sorted(found)


ADAPTER = ClaudeCode()


# --- reading -----------------------------------------------------------------------------------

def _session_of(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _meta(subagent_path: str) -> dict:
    try:
        with open(subagent_path[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _is_headless(record: dict) -> bool:
    return record.get("promptSource") == "sdk" or record.get("turnOrigin") == "sdk"


def _usage(raw: dict) -> Usage:
    split = raw.get("cache_creation")
    usage = Usage(input=raw.get("input_tokens") or 0, output=raw.get("output_tokens") or 0,
                  cache_read=raw.get("cache_read_input_tokens") or 0)
    if isinstance(split, dict):
        usage.cache_write_5m = split.get("ephemeral_5m_input_tokens") or 0
        usage.cache_write_1h = split.get("ephemeral_1h_input_tokens") or 0
    else:                                   # written, but for how long is not said
        usage.cache_write_no_lifetime = raw.get("cache_creation_input_tokens") or 0
    return usage


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(block.get("text", "") for block in content
                         if isinstance(block, dict) and block.get("type") == "text")
    return ""


def _result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content if isinstance(content, str) else ""


def _better(new: tuple[bool, Call], old: tuple[bool, Call]) -> bool:
    """Whether a later record of the same response replaces the one kept: a record of the
    file's own session beats a copy; then the larger output (it grows across blocks)."""
    return (new[0], new[1].usage.output) > (old[0], old[1].usage.output)


def _facts(records, session: str) -> TranscriptFacts:
    facts = TranscriptFacts(session_id=session)
    calls: dict[str, tuple[bool, Call]] = {}
    order: list[str] = []
    uses: dict[str, dict] = {}                  # tool_use id -> its block
    edits: list[tuple[str, str, str]] = []      # (file, old, new) of applied edits
    for record in records:
        kind, message = record.get("type"), record.get("message") or {}
        if _is_headless(record):
            facts.headless = True
        if kind == "system" and record.get("subtype") == "compact_boundary":
            facts.compacted_at = str(record.get("timestamp") or "")
        if kind == "assistant" and isinstance(message, dict):
            key = message.get("id") or record.get("requestId") or record.get("uuid")
            model = message.get("model") or ""
            if key and model != SYNTHETIC_MODEL and isinstance(message.get("usage"), dict):
                own = record.get("sessionId") in (None, session) or bool(record.get("agentId"))
                entry = (own, Call(id=key, time=record.get("timestamp") or "", model=model,
                                   usage=_usage(message["usage"])))
                if key not in calls:
                    order.append(key)
                    calls[key] = entry
                elif _better(entry, calls[key]):
                    calls[key] = entry
            for block in message.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and block.get("text"):
                    facts.last_reply = block["text"]
                elif block.get("type") == "tool_use":
                    uses[block.get("id")] = block
                    name, args = block.get("name"), block.get("input") or {}
                    if name in SPAWN_TOOLS:
                        facts.spawns[block.get("id")] = str(args.get("description") or "")
                    elif name in SHELL_TOOLS and args.get("command"):
                        facts.commands.append(str(args["command"]))
                        facts.command_times.append(str(record.get("timestamp") or ""))
                    elif name == "TodoWrite":
                        facts.todos = [str(t.get("content", "")) for t in args.get("todos") or []
                                       if isinstance(t, dict) and t.get("status") != "completed"]
        elif kind == "user" and isinstance(message, dict):
            content = message.get("content")
            text = _text(content)
            if (text and not record.get("isMeta") and not record.get("isCompactSummary")
                    and not ClaudeCode.is_injected_prompt(text)
                    and not record.get("toolUseResult")
                    and record.get("turnOrigin") != "task_notification"):
                facts.last_prompt = text
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    _result(facts, uses.get(block.get("tool_use_id")) or {}, block, record, edits)
    facts.calls = [calls[key][1] for key in order]
    facts.dropped += ["command failed %d times in a row: %s" % (count, command)
                      for command, count in facts.failing.items() if count >= DROPPED_AFTER]
    return facts


def _result(facts: TranscriptFacts, use: dict, block: dict, record: dict, edits: list) -> None:
    name, args = use.get("name"), use.get("input") or {}
    failed = bool(block.get("is_error"))
    if name in EDIT_TOOLS:
        target = str(args.get("file_path") or args.get("notebook_path") or "")
        if record.get("toolDenialKind") in DECLINED or (
                failed and _result_text(block).startswith("The user doesn't want to")):
            facts.dropped.append("edit declined: %s" % target)
        elif not failed:
            old, new = str(args.get("old_string") or ""), str(args.get("new_string") or "")
            if any(f == target and o == new and n == old for f, o, n in edits) and (old or new):
                facts.dropped.append("edit put back: %s" % target)
            edits.append((target, old, new))
            if target and target not in facts.edited:
                facts.edited.append(target)
            _changed(facts, use)
    elif name in SHELL_TOOLS:
        command = str(args.get("command") or "")
        if is_read_only(command):
            return
        if failed and _EXIT_RE.match(_result_text(block)):
            count_failure(facts, command, str(record.get("cwd") or ""),
                          str(record.get("timestamp") or ""))
        elif not failed:
            _changed(facts, use)


def _changed(facts: TranscriptFacts, use: dict) -> None:
    """A mutating step succeeded: every retry streak starts again after it."""
    facts.last_change = str(use.get("id") or "")
    facts.failing.clear()
