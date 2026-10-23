"""Codex CLI: one rollout per thread under ``$CODEX_HOME/sessions/YYYY/MM/DD/
rollout-<local time>-<thread id>.jsonl``, subagents included; each line is
``{timestamp, ordinal, type, payload}``.

Facts this module relies on were captured from Codex CLI 0.163.0 on 2026-10-22 (fixtures:
``scripts/fixtures/hosts/codex/``):

* usage is one ``token_usage_record`` per model response (``response_id``); its
  ``input_tokens`` *includes* ``cached_input_tokens``; cache writes carry no lifetime, and
  the provider decides how long a cache lives;
* a shell command is an ``item_completed`` ``CommandExecution`` with ``status`` and
  ``exit_code`` (the wrapper shell's) and stdout and stderr merged;
* a subagent is a ``spawn_agent`` call whose task text is stored encrypted: only its
  ``task_name`` is readable, so the row rule reads the task name (``row_5_…``); its own
  rollout replays the parent's history below ``subagent_history_start_ordinal``;
* hooks: with an isolated home, a ``SessionStart`` hook's context reached the thread and a
  ``UserPromptSubmit`` hook blocked the prompt, in the same output shapes as the other
  host. A tool hook fires only once a model call is made, which the capture could not, so
  holding a tool is a missing capability.
"""
from __future__ import annotations

import json
import os

from . import (DROPPED_AFTER, PROVIDER_DECIDED, Adapter, Call, TranscriptFacts, Usage,
               count_failure, head_records, is_read_only, read_jsonl)

SPAWN_CALL = "spawn_agent"
_UNCAPTURED_TOOL_HOOK = "a pre-tool hook needs a model call to fire, and none was captured"


class Codex(Adapter):
    name = "codex"
    capabilities = frozenset({"read-transcript", "read-subagent-transcript", "hold-prompt",
                              "session-start-context", "cache-lifetime"})
    missing = {
        "hold-tool": _UNCAPTURED_TOOL_HOOK,
        "hold-tool-in-subagent": _UNCAPTURED_TOOL_HOOK,
        "turn-end-message": "a message shown only to the person when a turn ends was not "
                            "captured on this host",
        "edit-tracking": "file edits (patches) were not captured, so a retry streak may "
                         "survive a fix: failures here are reported, never held",
    }
    cache_lifetime = PROVIDER_DECIDED

    def read_transcript(self, path: str, tail_bytes: int | None = None) -> TranscriptFacts:
        facts = _facts(read_jsonl(path, tail_bytes))
        if tail_bytes and not facts.headless and not facts.host_version:
            # the tail missed session_meta, which says whether the run is headless
            head = _facts(r for r in head_records(path) if r.get("type") == "session_meta")
            facts.headless, facts.host_version = head.headless, head.host_version
        return facts

    @staticmethod
    def is_injected_prompt(prompt: str) -> bool:
        return False

    @staticmethod
    def hold_prompt(reason: str) -> dict:
        return {"decision": "block", "reason": reason}

    @staticmethod
    def session_context(text: str) -> dict:
        return {"hookSpecificOutput": {"hookEventName": "SessionStart",
                                       "additionalContext": text}}

    @staticmethod
    def transcript_roots() -> list[str]:
        """``$CODEX_HOME/sessions``, ``CODEX_HOME`` defaulting to ``~/.codex``."""
        home = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
        return [os.path.join(home, "sessions")]

    @staticmethod
    def top_level_transcripts(root: str) -> list[str]:
        """Every rollout under a sessions root whose thread was not spawned by another."""
        found = []
        for folder, _dirs, names in os.walk(root):
            for name in sorted(names):
                if name.startswith("rollout-") and name.endswith(".jsonl"):
                    path = os.path.join(folder, name)
                    head = next(iter(read_jsonl(path)), {})
                    meta = head.get("payload") if isinstance(head, dict) else None
                    if not (isinstance(meta, dict) and meta.get("parent_thread_id")):
                        found.append(path)
        return sorted(found)

    def subagents(self, transcript: str, facts: TranscriptFacts | None = None):
        """Each subagent under a thread: ``(path, description, task_name)`` for the row rule.
        Only the task name is readable here; a grandchild takes its own spawn's name."""
        paths = self.subagent_transcripts(transcript, facts)
        names: dict[str, str] = {}
        for found in [facts or self.read_transcript(transcript)] + [
                self.read_transcript(p) for p in paths]:
            for call, thread in found.spawn_threads.items():
                names.setdefault(thread, found.spawns.get(call, ""))
        return [(path, "", names.get(_thread_of(path), "")) for path in paths]

    @staticmethod
    def subagent_transcripts(transcript: str, facts: TranscriptFacts | None = None) -> list[str]:
        """The rollouts of every subagent under a thread (its spawns, theirs, and so on),
        found by thread id in the same sessions tree; a subagent may start on a later day."""
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(transcript))))
        files = {}
        for folder, _dirs, names in os.walk(root):
            for name in names:
                if name.startswith("rollout-") and name.endswith(".jsonl"):
                    files[_thread_of(name)] = os.path.join(folder, name)
        found, queue = [], [facts or ADAPTER.read_transcript(transcript)]
        while queue:
            for thread in queue.pop().spawn_threads.values():
                path = files.get(thread)
                if path and path not in found:
                    found.append(path)
                    queue.append(ADAPTER.read_transcript(path))
        return sorted(found)


ADAPTER = Codex()


def _thread_of(path: str) -> str:
    """The thread id a rollout's file name ends with (a 36-character id)."""
    return os.path.basename(path)[:-len(".jsonl")][-36:]


def _text(content) -> str:
    if isinstance(content, list):
        return "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return content if isinstance(content, str) else ""


def _command(argv) -> str:
    """The command a ``CommandExecution`` ran: the script after a shell's ``-Command`` /
    ``-c`` flag, else the argv joined."""
    if isinstance(argv, str):
        return argv
    if not isinstance(argv, list):
        return ""
    for flag in ("-Command", "-c", "/c"):
        if flag in argv[:-1]:
            return str(argv[argv.index(flag) + 1])
    return " ".join(str(part) for part in argv)


def _facts(records) -> TranscriptFacts:
    facts = TranscriptFacts()
    calls: dict[str, Call] = {}
    model, start = "", 0
    for record in records:
        payload, kind = record.get("payload") or {}, record.get("type")
        if not isinstance(payload, dict):
            continue
        if kind == "session_meta" and not facts.session_id:
            facts.session_id = str(payload.get("id") or "")
            start = payload.get("subagent_history_start_ordinal") or 0
            facts.headless = payload.get("source") == "exec"
            facts.host_version = str(payload.get("cli_version") or "")
            continue
        if isinstance(record.get("ordinal"), int) and record["ordinal"] < start:
            continue                            # the parent's history, replayed
        if kind == "turn_context":
            model = str(payload.get("model") or model)
        elif kind == "token_usage_record" and payload.get("response_id"):
            raw = payload.get("usage") or {}
            cached = raw.get("cached_input_tokens") or 0
            written = raw.get("cache_write_input_tokens") or 0
            fresh = (raw.get("input_tokens") or 0) - cached - written
            version = facts.host_version or "this version"
            call = Call(                            # input_tokens counts cached and written too
                id=payload["response_id"], time=record.get("timestamp") or "", model=model,
                usage=Usage(input=max(0, fresh), output=raw.get("output_tokens") or 0,
                            cache_read=cached, cache_write_no_lifetime=written))
            if fresh < 0:
                call.unpriceable = ("input_tokens is below cached_input_tokens + "
                                    "cache_write_input_tokens (Codex %s)" % version)
            elif written:
                call.assumption = ("cache writes assumed inside input_tokens; not observed "
                                   "nonzero on Codex %s" % version)
            calls[payload["response_id"]] = call
        elif kind == "response_item" and payload.get("type") == "function_call":
            if payload.get("name") == SPAWN_CALL:
                try:
                    args = json.loads(payload.get("arguments") or "{}")
                except ValueError:
                    args = {}
                facts.spawns[str(payload.get("call_id"))] = str(args.get("task_name") or "")
        elif kind == "event_msg" and payload.get("type") == "item_completed":
            _item(facts, payload.get("item") or {}, str(record.get("timestamp") or ""))
    facts.calls = list(calls.values())
    facts.dropped += ["command failed %d times in a row: %s" % (count, command)
                      for command, count in facts.failing.items() if count >= DROPPED_AFTER]
    return facts


def _item(facts: TranscriptFacts, item: dict, at: str = "") -> None:
    kind = item.get("type")
    if kind == "UserMessage":
        facts.last_prompt = _text(item.get("content")) or facts.last_prompt
    elif kind == "AgentMessage":
        facts.last_reply = _text(item.get("content")) or facts.last_reply
    elif kind == "SubAgentActivity" and item.get("kind") == "started":
        facts.spawn_threads[str(item.get("id"))] = str(item.get("agent_thread_id") or "")
    elif kind == "CommandExecution":
        command = _command(item.get("command"))
        facts.commands.append(command)
        facts.command_times.append(at)
        if is_read_only(command):
            return
        if item.get("status") == "failed" or (item.get("exit_code") or 0) != 0:
            count_failure(facts, command, str(item.get("cwd") or ""), at)
        elif item.get("status") == "completed":
            facts.last_change = str(item.get("id") or "")
            facts.failing.clear()
