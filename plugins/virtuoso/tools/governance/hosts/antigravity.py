"""Google Antigravity (``agy`` CLI, the Antigravity app and IDE): one folder per conversation
under ``<app data>/brain/<conversation id>/``, ``<app data>`` being ``~/.gemini/antigravity-cli``
(CLI), ``~/.gemini/antigravity`` (app) or ``~/.gemini/antigravity-ide`` (IDE). The transcript a
hook names is ``.system_generated/logs/transcript_full.jsonl``; each line is one step,
``{step_index, source, type, status, created_at, …}``.

Facts this module relies on were captured from agy 1.5.11 on 2026-11-18 (fixtures:
``scripts/fixtures/hosts/antigravity/``):

* hooks read camelCase JSON on stdin (``conversationId``, ``workspacePaths``, ``cwd``,
  ``transcriptPath``, ``hookEventName``, ``lastUserInput``; ``toolCall {id, name, args}`` on a
  tool hook) and run in the folder holding ``hooks.json`` — for a plugin, the plugin root —
  so the project comes from ``workspacePaths``, never from the working folder or an
  environment variable;
* the tools are ``run_command`` (``CommandLine``), ``read_file`` (``Path``, optional
  ``StartLine``/``EndLine``; one read returns at most 800 lines and 46,080 bytes, so a
  whole-file read never brings in more than that — below the big-read guard's default),
  ``write_file`` and ``edit_file`` (``Path``; ``Target``/``Replacement``),
  ``invoke_subagent`` (``Role``, ``Prompt``) and ``send_message``;
* a pre-tool hook's ``{"decision": "deny", "reason": …}`` stops the call, which the
  transcript records as a ``GENERIC`` step with ``status: ERROR``; a session-start hook's
  ``injectSteps`` system message reaches the model; a pre-invocation hook's ``errorMessage``
  with ``terminationBehavior: terminate`` holds a prompt (the prompt's ``USER_INPUT`` is still
  written, then an ``ERROR_MESSAGE``);
* usage is on each ``PLANNER_RESPONSE``: ``input_tokens`` excludes ``cache_read_tokens`` (their
  sums match the run's reported totals), no cache write is reported, and the provider decides
  how long a cache lives. Steps carry no call ids, so a call is ``<conversation>:<step>``, and a
  tool's result is the next ``GENERIC`` step after the response that called it, in order;
* a shell call's result says ``Command exited with code N.`` (the wrapper shell's code);
* a subagent is a conversation of its own, listed in its parent's
  ``.system_generated/subagents/<id>.json`` with its ``role`` (the spawn description) and
  ``spawnStepIndex``; hooks fire inside it under its own conversation id; it reports back with
  ``send_message``, which reaches the parent as a ``SYSTEM`` message and starts a new run of
  model calls there;
* nothing in a transcript or a hook's input tells a headless ``-p`` run from an interactive
  session, and no session-start event fires when a conversation is resumed.
"""
from __future__ import annotations

import glob
import json
import os
import re

from . import (DROPPED_AFTER, PROVIDER_DECIDED, Adapter, Call, TranscriptFacts, Usage,
               count_failure, is_read_only, read_jsonl)

SHELL_TOOLS = frozenset({"run_command"})
#: ``read_file`` was captured; ``view_file`` is the name the host's hook documentation uses.
READ_TOOLS = frozenset({"read_file", "view_file"})
#: ``edit_file`` and ``write_file`` were captured; the rest are the documented names.
EDIT_TOOLS = frozenset({"edit_file", "write_file", "write_to_file", "replace_file_content",
                        "multi_replace_file_content"})
SPAWN_TOOL = "invoke_subagent"
#: One read brings in at most this many lines, and at most this many bytes of them.
READ_LINES, READ_BYTES = 800, 46080
TRANSCRIPT = os.path.join(".system_generated", "logs", "transcript_full.jsonl")
APP_DATA_DIRS = ("antigravity-cli", "antigravity", "antigravity-ide")

_EXIT_RE = re.compile(r"Command exited with code (-?\d+)\.")
_REQUEST_RE = re.compile(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.S)
_SPAWNED_RE = re.compile(r'"conversationId"\s*:\s*"([0-9A-Fa-f-]{36})"')
_NO_HEADLESS = ("a hook cannot tell a headless -p run from an interactive session (neither the "
                "hook input nor the transcript says)")


class Antigravity(Adapter):
    name = "antigravity"
    capabilities = frozenset({"read-transcript", "read-subagent-transcript", "hold-tool",
                              "hold-tool-in-subagent", "session-start-context",
                              "cache-lifetime", "edit-tracking"})
    missing = {
        "hold-prompt": "a prompt can be held here, but " + _NO_HEADLESS + ", and a hold "
                       "fails a headless run, so a cold return is never held",
        "turn-end-message": "a Stop hook here can only keep the agent working; it has no "
                            "notice for the person alone, and " + _NO_HEADLESS + ", so the "
                            "weekly line and the compaction nudge are not given",
    }
    cache_lifetime = PROVIDER_DECIDED
    #: Whether a transcript can show that a session runs headless.
    tells_headless = False

    def read_transcript(self, path: str, tail_bytes: int | None = None) -> TranscriptFacts:
        compact = os.path.basename(path or "") == "transcript.jsonl"
        return _facts(read_jsonl(path, tail_bytes), _conversation_of(path), compact)

    # --- hooks ------------------------------------------------------------------------------

    def normalize(self, hook: dict) -> dict:
        """This host's hook input in the guards' vocabulary. A subagent's hook keeps the top
        conversation as its session, and its own transcript apart, as the guards expect.
        Input with no workspace and no working folder is nothing to act on (``{}``): this
        host runs hooks in the plugin's folder, which is never the project."""
        if "hook_event_name" in hook:
            return hook                                  # already in the guards' vocabulary
        workspaces = [w for w in hook.get("workspacePaths") or [] if isinstance(w, str) and w]
        project = workspaces[0] if workspaces else ""
        cwd = str(hook.get("cwd") or project)
        if not cwd:
            return {}
        event = str(hook.get("hookEventName") or "")
        conversation = str(hook.get("conversationId") or "")
        transcript = str(hook.get("transcriptPath") or "")
        out = {"hook_event_name": event, "session_id": conversation, "cwd": cwd,
               "project_dir": project, "transcript_path": transcript}
        parent = _parent_of(conversation, transcript)
        if parent:
            out.update(agent_id=conversation, session_id=parent,
                       agent_transcript_path=transcript,
                       transcript_path=os.path.join(_brain_of(transcript), parent, TRANSCRIPT))
        if event == "SessionStart":
            out["source"] = "startup"                    # it fires for new conversations only
        elif event == "PreInvocation":
            # Before every model call; a typed prompt is the first call of a run whose latest
            # step is that prompt (a subagent's report also starts a run, at a SYSTEM step).
            typed = (hook.get("invocationNum") == 0 and not parent
                     and _last_step_is_typed(transcript))
            out["hook_event_name"] = "UserPromptSubmit" if typed else "PreInvocation"
            out["prompt"] = str(hook.get("lastUserInput") or "")
        elif event in ("PreToolUse", "PostToolUse"):
            call = hook.get("toolCall") if isinstance(hook.get("toolCall"), dict) else {}
            name = str(call.get("name") or "")
            args = call.get("args") if isinstance(call.get("args"), dict) else {}
            if name in SHELL_TOOLS:
                out["tool_name"] = "Bash"                # the guards' name for a shell call
                out["tool_input"] = {"command": str(args.get("CommandLine") or "")}
            elif name in READ_TOOLS:
                out["tool_name"] = "Read"
                out["tool_input"] = {"file_path": _path_arg(args),
                                     "offset": args.get("StartLine"),
                                     "limit": args.get("EndLine")}
            else:
                out["tool_name"] = name
                out["tool_input"] = dict(args)
        elif event == "Stop":
            out["stop_hook_active"] = bool(hook.get("continuationActive"))
        return out

    @staticmethod
    def project_dir(hook: dict) -> str:
        return str(hook.get("project_dir") or "")

    @staticmethod
    def is_subagent(hook: dict) -> bool:
        return bool(hook.get("agent_id"))

    @staticmethod
    def is_injected_prompt(prompt: str) -> bool:
        return False                                     # normalize keeps only typed prompts

    @staticmethod
    def subagent_transcript(hook: dict) -> str:
        return str(hook.get("agent_transcript_path") or "") if hook.get("agent_id") else ""

    @staticmethod
    def read_bytes(path: str) -> int:
        """What a whole-file read brings into the conversation: its first ``READ_LINES``
        lines, cut at ``READ_BYTES``."""
        size = 0
        with open(path, "rb") as handle:
            for number, line in enumerate(handle):
                if number >= READ_LINES or size >= READ_BYTES:
                    break
                size += len(line)
        return min(size, READ_BYTES)

    @staticmethod
    def hold_prompt(reason: str) -> dict:
        return {"injectSteps": [{"errorMessage": {"userMessage": reason}}],
                "terminationBehavior": "terminate"}

    @staticmethod
    def deny_tool(reason: str) -> dict:
        return {"decision": "deny", "reason": reason}

    @staticmethod
    def session_context(text: str) -> dict:
        return {"injectSteps": [{"systemMessage": {"systemMessage": text}}]}

    # --- transcripts and subagents ----------------------------------------------------------

    @staticmethod
    def transcript_roots() -> list[str]:
        """``~/.gemini/<app>/brain`` for the CLI, the app and the IDE."""
        base = os.path.join(os.path.expanduser("~"), ".gemini")
        return [os.path.join(base, name, "brain") for name in APP_DATA_DIRS]

    @staticmethod
    def top_level_transcripts(root: str) -> list[str]:
        """Every conversation transcript under a brain folder that no other spawned."""
        try:
            names = sorted(os.listdir(root))
        except OSError:
            return []
        spawned = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(
            os.path.join(root, "*", ".system_generated", "subagents", "*.json"))}
        return [os.path.join(root, n, TRANSCRIPT) for n in names
                if n not in spawned and os.path.isfile(os.path.join(root, n, TRANSCRIPT))]

    def subagents(self, transcript: str, facts: TranscriptFacts | None = None):
        """Each subagent under a conversation: ``(path, description, task_name)`` for the row
        rule. A nested subagent takes its depth-1 ancestor's role, so a row's helpers count
        to the row."""
        brain = _brain_of(transcript)
        found, queue, seen = [], [(_conversation_of(transcript), None)], set()
        while queue:
            conversation, inherited = queue.pop(0)
            for child, role in _children(brain, conversation):
                if child in seen:
                    continue
                seen.add(child)
                description = inherited if inherited is not None else role
                found.append((os.path.join(brain, child, TRANSCRIPT), description, ""))
                queue.append((child, description))
        return sorted(found)

    def subagent_transcripts(self, transcript: str) -> list[str]:
        return [path for path, _d, _t in self.subagents(transcript)]


ADAPTER = Antigravity()


# --- reading -----------------------------------------------------------------------------------

def _conversation_of(path: str) -> str:
    """The conversation id of a transcript: the folder above ``.system_generated``."""
    return os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(path or ""))))


def _brain_of(path: str) -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(path or ""))))


def _children(brain: str, conversation: str) -> list[tuple[str, str]]:
    """``(conversation id, role)`` of each subagent a conversation spawned."""
    folder = os.path.join(brain, conversation, ".system_generated", "subagents")
    found = []
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        child = str(data.get("conversationId") or os.path.splitext(os.path.basename(path))[0])
        descriptor = data.get("subagentDescriptor") if isinstance(
            data.get("subagentDescriptor"), dict) else {}
        found.append((child, str(descriptor.get("role") or "")))
    return found


def _parent_of(conversation: str, transcript: str) -> str:
    """The conversation that spawned this one, or ``""`` at top level."""
    if not conversation or not transcript:
        return ""
    found = glob.glob(os.path.join(glob.escape(_brain_of(transcript)), "*", ".system_generated",
                                   "subagents", glob.escape(conversation) + ".json"))
    return os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(found[0])))) \
        if found else ""


def _last_step_is_typed(transcript: str) -> bool:
    """Whether the latest step is a prompt the person typed (hook-injected system steps
    after it, written by a session-start hook, do not count)."""
    last = None
    for record in read_jsonl(transcript, 65536):
        if record.get("source") != "SYSTEM_SDK":
            last = record
    return bool(last) and last.get("type") == "USER_INPUT"


def _path_arg(args: dict) -> str:
    for key in ("Path", "AbsolutePath", "File", "TargetFile"):
        if isinstance(args.get(key), str) and args[key]:
            return args[key]
    return ""


def _arg(args: dict, key: str, compact: bool):
    """One tool argument. The compact transcript writes each value JSON-encoded."""
    value = args.get(key)
    if compact and isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _facts(records, conversation: str, compact: bool = False) -> TranscriptFacts:
    facts = TranscriptFacts(session_id=conversation)
    pending: list[tuple[str, dict, str, str]] = []  # (tool, args, call id, stamp), in order
    edits: list[tuple[str, str, str]] = []          # (file, target, replacement) applied
    for record in records:
        kind, source = record.get("type"), record.get("source")
        stamp = str(record.get("created_at") or "")
        step = record.get("step_index")
        if kind == "USER_INPUT":
            pending.clear()                         # calls never answered are gone
            match = _REQUEST_RE.search(_text(record.get("content")))
            facts.last_prompt = match.group(1) if match else _text(record.get("content"))
        elif kind == "PLANNER_RESPONSE":
            calls = [c for c in record.get("tool_calls") or [] if isinstance(c, dict)]
            facts.turn_closed_at = "" if calls else stamp
            if _text(record.get("content")):
                facts.last_reply = record["content"]
            if record.get("model") and any(isinstance(record.get(k), int) for k in (
                    "input_tokens", "output_tokens", "cache_read_tokens")):
                facts.calls.append(Call(
                    id="%s:%s" % (conversation, step), time=stamp, model=str(record["model"]),
                    usage=Usage(input=record.get("input_tokens") or 0,
                                output=record.get("output_tokens") or 0,
                                cache_read=record.get("cache_read_tokens") or 0)))
            for n, call in enumerate(calls):
                name = str(call.get("name") or "")
                args = call.get("args") if isinstance(call.get("args"), dict) else {}
                call_id = "%s:%s:%d" % (conversation, step, n)
                if name in SHELL_TOOLS:
                    command = _arg(args, "CommandLine", compact)
                    if isinstance(command, str) and command:
                        facts.commands.append(command)
                        facts.command_times.append(stamp)
                elif name == SPAWN_TOOL:
                    facts.spawns[call_id] = str(_arg(args, "Role", compact) or "")
                pending.append((name, args, call_id, stamp))
        elif kind == "GENERIC" and source == "MODEL":
            facts.turn_closed_at = ""
            if pending:
                _result(facts, pending.pop(0), record, edits, compact)
        elif kind == "SYSTEM_MESSAGE" and source == "SYSTEM":
            facts.turn_closed_at = ""               # another agent's message starts work
    facts.dropped += ["command failed %d times in a row: %s" % (count, command)
                      for command, count in facts.failing.items() if count >= DROPPED_AFTER]
    return facts


def _result(facts: TranscriptFacts, use: tuple, record: dict, edits: list,
            compact: bool) -> None:
    name, args, call_id, stamp = use
    done = record.get("status") == "DONE" and not record.get("error")
    content = _text(record.get("content"))
    if name in SHELL_TOOLS:
        command = _arg(args, "CommandLine", compact)
        if not isinstance(command, str) or not command or not done or is_read_only(command):
            return                                  # held or failed to start: never ran
        code = _EXIT_RE.search(content)
        if code and int(code.group(1)) != 0:
            count_failure(facts, command, "", str(record.get("created_at") or stamp))
        elif code:
            _changed(facts, call_id)
    elif name in EDIT_TOOLS:
        if _arg(args, "ArtifactMetadata", compact):
            return                                  # the host's own artifact, not the project
        target = _arg(args, "Path", compact) or _arg(args, "TargetFile", compact) or ""
        if not done or not isinstance(target, str):
            return
        old = _text(_arg(args, "Target", compact))
        new = _text(_arg(args, "Replacement", compact))
        if (old or new) and any(f == target and o == new and n == old for f, o, n in edits):
            facts.dropped.append("edit put back: %s" % target)
        edits.append((target, old, new))
        if target and target not in facts.edited:
            facts.edited.append(target)
        _changed(facts, call_id)
    elif name == SPAWN_TOOL and done:
        spawned = _SPAWNED_RE.search(content)
        if spawned:
            facts.spawn_threads[call_id] = spawned.group(1)


def _changed(facts: TranscriptFacts, call_id: str) -> None:
    """A mutating step succeeded: every retry streak starts again after it."""
    facts.last_change = call_id
    facts.failing.clear()
