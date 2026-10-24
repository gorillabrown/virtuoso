"""The cost guards: each holds a costly step once, says why and what it costs, and lets the
identical step through; none acts outside a Virtuoso project or gets in the way."""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import guards, hosts

GUARD = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_guard.py")
PREFLIGHT = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_preflight.py")


def _ago(minutes: float) -> str:
    moment = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _assistant(i, at, *, context=180_000, write_1h=0, tool=None):
    content = [dict({"type": "tool_use", "id": "t%d" % i}, **tool)] if tool else []
    return {"type": "assistant", "timestamp": at, "message": {
        "id": "m%d" % i, "model": "claude-opus-5-5", "content": content, "usage": {
            "input_tokens": 1, "output_tokens": 10, "cache_read_input_tokens": context - 1 - write_1h,
            "cache_creation": {"ephemeral_5m_input_tokens": 0,
                               "ephemeral_1h_input_tokens": write_1h}}}}


def _result(i, text, error=False):
    return {"type": "user", "toolUseResult": text, "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t%d" % i, "is_error": error, "content": text}]}}


def _transcript(path: Path, records) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def project(project):
    made = subprocess.run([sys.executable, PREFLIGHT, "--root", str(project), "--mode", "create",
                           "--authorize"], capture_output=True, text=True, encoding="utf-8")
    assert made.returncode == 0, made.stdout + made.stderr
    return project


def cold_transcript(tmp_path, idle=70, context=180_000, extra=(), closed=True):
    close = [{"type": "system", "subtype": "stop_hook_summary", "timestamp": _ago(idle)}]
    return _transcript(tmp_path / "t" / "s-1.jsonl", [
        {"type": "user", "message": {"content": "start"}},
        _assistant(1, _ago(idle), context=context, write_1h=1000)] + (close if closed else [])
        + list(extra))


def prompt_hook(project, transcript, prompt="carry on"):
    return {"hook_event_name": "UserPromptSubmit", "session_id": "s-1", "cwd": str(project),
            "transcript_path": transcript, "prompt": prompt}


def receipts(home) -> list[dict]:
    path = Path(home) / ".virtuoso" / "guard" / "receipts.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()] \
        if path.exists() else []


# --- where guards act (D7) ------------------------------------------------------------------

def test_outside_a_virtuoso_project_nothing_is_held_read_or_written(tmp_path, isolated_home):
    plain = tmp_path / "plain"
    plain.mkdir()
    transcript = cold_transcript(tmp_path)
    before = snapshot_tree(plain)
    for hook in (prompt_hook(plain, transcript),
                 {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(plain),
                  "session_id": "s-1", "transcript_path": transcript}):
        assert guards.handle(hook, "claude-code") is None
    assert snapshot_tree(plain) == before
    assert not (Path(isolated_home) / ".virtuoso" / "guard").exists()


def test_at_session_start_the_project_gets_zero_writes(project, tmp_path, isolated_home):
    before = snapshot_tree(project)
    guards.handle({"hook_event_name": "SessionStart", "source": "startup", "cwd": str(project),
                   "session_id": "s-1", "transcript_path": cold_transcript(tmp_path)},
                  "claude-code", "9.9.9")
    assert snapshot_tree(project) == before


def test_guards_switched_off_in_policy_do_nothing(project, tmp_path, isolated_home):
    manifest = project / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.setdefault("policy", {})["guards"] = {"enabled": False}
    manifest.write_text(json.dumps(data), encoding="utf-8")
    assert guards.handle(prompt_hook(project, cold_transcript(tmp_path)), "claude-code") is None


def test_a_crash_inside_a_guard_lets_the_step_through(project, tmp_path, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("damaged")
    from tools.governance.hosts import claude_code
    monkeypatch.setattr(claude_code.ClaudeCode, "read_transcript", boom)
    assert guards.handle(prompt_hook(project, cold_transcript(tmp_path)), "claude-code") is None


# --- G1: a cold return ------------------------------------------------------------------------

def test_a_cold_return_is_held_once_then_goes_through(project, tmp_path, isolated_home):
    hook = prompt_hook(project, cold_transcript(tmp_path))
    held = guards.handle(hook, "claude-code")
    assert held["decision"] == "block"
    reason = held["reason"]
    assert reason.startswith("Idle 1h 10m, past its cache lifetime of 60 minutes.")
    assert "Send again to go ahead" in reason and "/clear" in reason
    assert guards.handle(hook, "claude-code") is None               # the identical step: through
    assert [r["event"] for r in receipts(isolated_home)] == ["hold", "sent"]


def test_mid_dispatch_the_hold_offers_the_compact_line_never_a_fresh_start(project, tmp_path,
                                                                           isolated_home):
    layout = json.loads((project / "Virtuoso" / "workspace-layout.json").read_text(
        encoding="utf-8"))
    close_outs = project.joinpath(*layout["roles"]["closeOuts"]["path"].split("/"))
    close_outs.mkdir(parents=True, exist_ok=True)
    (close_outs / "Timing.X-1.jsonl").write_text(json.dumps(
        {"event": "open", "at": "2026-10-22T00:00:00Z", "rows": [
            {"id": 1, "title": "w", "predicted": 5, "basis": "estimated"}]}) + "\n",
        encoding="utf-8")
    transcript = cold_transcript(tmp_path)
    hosts.record_binding("X-1", "s-1", transcript, "claude-code")
    reason = guards.handle(prompt_hook(project, transcript), "claude-code")["reason"]
    assert "/compact keep X-1, the time log, open decisions" in reason and "/clear" not in reason


@pytest.mark.parametrize("case", ["warm", "small", "injected", "headless"])
def test_a_cold_return_is_not_held_when_it_should_not_be(project, tmp_path, isolated_home, case):
    idle, context, prompt, extra = 70, 180_000, "carry on", ()
    if case == "warm":
        idle = 30
    elif case == "small":
        context = 20_000
    elif case == "injected":
        prompt = "<task-notification>\n<task-id>x</task-id>"
    else:                                       # its own close, so only headless can stop it
        extra = ({"type": "user", "promptSource": "sdk", "turnOrigin": "sdk",
                  "message": {"content": "go"}},
                 {"type": "system", "subtype": "stop_hook_summary", "timestamp": _ago(idle)})
    hook = prompt_hook(project, cold_transcript(tmp_path, idle, context, extra), prompt)
    assert guards.handle(hook, "claude-code") is None


def test_a_prompt_typed_before_the_turn_closed_is_not_held(project, tmp_path, isolated_home):
    hook = prompt_hook(project, cold_transcript(tmp_path, closed=False))
    assert guards.handle(hook, "claude-code") is None


def test_idle_time_runs_from_the_turn_close(project, tmp_path, isolated_home):
    def transcript(folder, closed_ago):
        return _transcript(tmp_path / folder / "s-1.jsonl", [
            {"type": "user", "message": {"content": "start"}},
            _assistant(1, _ago(70), write_1h=1000),
            {"type": "system", "subtype": "stop_hook_summary", "timestamp": _ago(closed_ago)}])
    assert guards.handle(prompt_hook(project, transcript("warm", 30)), "claude-code") is None
    held = guards.handle(prompt_hook(project, transcript("cold", 70)), "claude-code")
    assert held["decision"] == "block"


def test_the_handoff_note_reaches_the_next_session_once_within_thirty_minutes(project, tmp_path,
                                                                             isolated_home):
    guards.handle(prompt_hook(project, cold_transcript(tmp_path)), "claude-code")
    start = {"hook_event_name": "SessionStart", "source": "clear", "cwd": str(project),
             "session_id": "s-2", "transcript_path": ""}
    context = guards.handle(start, "claude-code")["hookSpecificOutput"]["additionalContext"]
    assert "previous conversation's own state" in context and "Asked last: start" in context
    again = guards.handle(start, "claude-code")
    assert again is None or "previous conversation" not in json.dumps(again)   # used once


# --- G5: a repeated failure ---------------------------------------------------------------------

def failing_transcript(tmp_path, times, command="python -m pytest x", changed=False):
    records = []
    for n in range(times):
        records += [_assistant(10 + n, _ago(1), tool={"name": "Bash", "input": {"command": command}}),
                    _result(10 + n, "Exit code 1\nboom", True)]
    if changed:
        records += [_assistant(99, _ago(1), tool={"name": "Edit", "input": {
            "file_path": "a.py", "old_string": "x", "new_string": "y"}}), _result(99, "ok")]
    return _transcript(tmp_path / "t" / "s-1.jsonl", records)


def tool_hook(project, transcript, command, tool="Bash", **extra):
    return dict({"hook_event_name": "PreToolUse", "session_id": "s-1", "cwd": str(project),
                 "transcript_path": transcript, "tool_name": tool,
                 "tool_input": {"command": command}}, **extra)


def test_a_third_identical_failing_command_is_denied_once(project, tmp_path, isolated_home):
    hook = tool_hook(project, failing_transcript(tmp_path, 2), "python -m pytest x")
    denied = guards.handle(hook, "claude-code")
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "failed 2 times in a row" in denied["hookSpecificOutput"]["permissionDecisionReason"]
    assert guards.handle(hook, "claude-code") is None               # one hold per streak


@pytest.mark.parametrize("times, command, changed", [
    (1, "python -m pytest x", False),                               # one failure: a re-run
    (2, "git status", False),                                       # read-only never counts
    (2, "python -m pytest x", True),                                # a fix since: a new streak
])
def test_a_retry_that_is_not_a_streak_goes_through(project, tmp_path, isolated_home, times,
                                                    command, changed):
    hook = tool_hook(project, failing_transcript(tmp_path, times, command, changed), command)
    assert guards.handle(hook, "claude-code") is None


@pytest.mark.parametrize("where, minutes_ago", [("other", 1), ("here", 45)])
def test_a_streak_in_another_folder_or_long_ago_goes_through(project, tmp_path, isolated_home,
                                                            where, minutes_ago):
    folder = str(project) if where == "here" else str(tmp_path / "elsewhere")
    records = []
    for n in range(2):
        use = _assistant(10 + n, _ago(minutes_ago), tool={"name": "Bash", "input": {
            "command": "make"}})
        result = dict(_result(10 + n, "Exit code 1\nboom", True), cwd=folder,
                      timestamp=_ago(minutes_ago))
        records += [use, result]
    hook = tool_hook(project, _transcript(tmp_path / "t" / "s-1.jsonl", records), "make")
    assert guards.handle(hook, "claude-code") is None


def test_the_retry_guard_holds_inside_a_subagent(project, tmp_path, isolated_home):
    top = _transcript(tmp_path / "t" / "s-1.jsonl", [_assistant(1, _ago(1))])
    sub = tmp_path / "t" / "s-1" / "subagents" / "agent-a1.jsonl"
    _transcript(sub, [r for n in range(2) for r in (
        _assistant(20 + n, _ago(1), tool={"name": "Bash", "input": {"command": "make"}}),
        _result(20 + n, "Exit code 2", True))])
    hook = tool_hook(project, top, "make", agent_id="a1", agent_type="general-purpose")
    assert guards.handle(hook, "claude-code")["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_a_host_without_the_capability_never_claims_a_hold(project, tmp_path, isolated_home):
    hook = tool_hook(project, failing_transcript(tmp_path, 3), "python -m pytest x")
    assert guards.handle(hook, "codex") is None                     # hold-tool not captured there


# --- G6: a big read ----------------------------------------------------------------------------

def test_a_big_whole_file_read_at_top_level_is_denied_once(project, tmp_path, isolated_home):
    big = tmp_path / "big.txt"
    big.write_text("x" * 70_000, encoding="utf-8")
    hook = {"hook_event_name": "PreToolUse", "session_id": "s-1", "cwd": str(project),
            "transcript_path": "", "tool_name": "Read", "tool_input": {"file_path": str(big)}}
    denied = guards.handle(hook, "claude-code")
    assert "read a range" in denied["hookSpecificOutput"]["permissionDecisionReason"]
    assert guards.handle(hook, "claude-code") is None
    ranged = dict(hook, tool_input={"file_path": str(big), "offset": 1, "limit": 50})
    assert guards.handle(ranged, "claude-code") is None
    inside = dict(hook, session_id="s-9", agent_id="a1")
    assert guards.handle(inside, "claude-code") is None             # subagents are exempt
    image = tmp_path / "big.png"
    image.write_bytes(b"x" * 70_000)
    pic = dict(hook, session_id="s-8", tool_input={"file_path": str(image)})
    assert guards.handle(pic, "claude-code") is None


# --- the binding, session start, the entry ----------------------------------------------------------

def test_working_a_row_binds_the_session_to_its_dispatch(project, tmp_path, isolated_home):
    hook = tool_hook(project, "/t/s-1.jsonl",
                     "virtuoso_registry --root . --actor virtuoso timing --dispatch X-2 --start 1")
    guards.handle(hook, "claude-code")
    assert hosts.read_binding("X-2")["session"] == "s-1"
    guards.handle(dict(hook, tool_input={"command": "virtuoso_registry --root . timing "
                                                    "--dispatch X-3 --status"}), "claude-code")
    assert hosts.read_binding("X-3") is None


def test_a_session_binds_even_with_guards_off(project, isolated_home):
    manifest = project / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.setdefault("policy", {})["guards"] = {"enabled": False}
    manifest.write_text(json.dumps(data), encoding="utf-8")
    guards.handle(tool_hook(project, "/t/s-1.jsonl", "virtuoso_registry --root . timing "
                            "--dispatch X-4 --start 1"), "claude-code")
    assert hosts.read_binding("X-4")["session"] == "s-1"


def test_two_hooks_racing_on_one_step_hold_it_once(isolated_home):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as pool:
        won = list(pool.map(lambda _: guards.mark("race|key"), range(16)))
    assert won.count(True) == 1 and guards.held_before("race|key")


def test_the_project_dir_counts_only_when_the_hook_runs_inside_it(project, tmp_path,
                                                                 isolated_home, monkeypatch):
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    hook = tool_hook(plain, "/t/s-1.jsonl", "virtuoso_registry --root . timing --dispatch "
                     "X-5 --start 1")
    guards.handle(hook, "claude-code")
    assert hosts.read_binding("X-5") is None          # outside the project: nothing
    guards.handle(dict(hook, cwd=str(project / "Virtuoso")), "claude-code")
    assert hosts.read_binding("X-5")["session"] == "s-1"


def test_a_missing_capability_is_said_once_per_version(project, isolated_home):
    start = {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(project),
             "session_id": "s-1", "transcript_path": ""}
    first = json.dumps(guards.handle(start, "codex", "1.16.0"))
    assert "hold-tool" in first and "turn-end-message" in first
    assert "hold-tool" not in json.dumps(guards.handle(start, "codex", "1.16.0"))
    assert "hold-tool" in json.dumps(guards.handle(start, "codex", "1.16.1"))
    assert guards.handle(start, "claude-code", "1.16.0") is None     # nothing missing there


def test_the_turn_end_message_was_captured_as_a_notice_for_the_person():
    lines = [json.loads(l) for l in (Path(PLUGIN_ROOT) / "scripts" / "fixtures" / "hosts" /
             "claude_code" / "hooks" / "stop_system_message.jsonl").read_text(
             encoding="utf-8").splitlines()]
    stream = next(l for l in lines if l["_from"] == "stream-json")
    assert (stream["type"], stream["subtype"]) == ("system", "informational")
    assert any((l.get("attachment") or {}).get("type") == "hook_system_message" for l in lines)
    from tools.governance.hosts import claude_code
    assert claude_code.ADAPTER.turn_end_message("x") == {"systemMessage": "x"}


def stop_hook(project, transcript, session="s-1"):
    return {"hook_event_name": "Stop", "session_id": session, "cwd": str(project),
            "transcript_path": transcript, "stop_hook_active": False}


def test_the_compact_nudge_comes_once_per_context_epoch(project, tmp_path, isolated_home):
    big = _transcript(tmp_path / "t" / "big.jsonl", [_assistant(1, _ago(1), context=170_000)])
    small = _transcript(tmp_path / "t" / "small.jsonl", [_assistant(2, _ago(1), context=30_000)])
    said = lambda t: json.dumps(guards.handle(stop_hook(project, t), "claude-code") or {})
    assert "/compact keep the task in hand" in said(big)                # past 0.75 of 200K
    assert "/compact" not in said(big)                                  # once per epoch
    said(small)                                                         # compacted
    assert "/compact" in said(big)                                      # a new epoch


def test_the_weekly_line_ends_the_first_turn_once_a_week(project, tmp_path, isolated_home):
    guards.receipt("retry", "hold", {"session_id": "old"}, str(project))
    t = _transcript(tmp_path / "t" / "s.jsonl", [_assistant(1, _ago(1), context=10_000)])
    first = guards.handle(stop_hook(project, t, "s-a"), "claude-code")
    assert "last 7 days against the 7 before" in first["systemMessage"]
    assert guards.handle(stop_hook(project, t, "s-a"), "claude-code") is None   # first turn only
    assert guards.handle(stop_hook(project, t, "s-b"), "claude-code") is None   # once a week
    start = {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(project),
             "session_id": "s-c", "transcript_path": t}
    assert "last 7 days" not in json.dumps(guards.handle(start, "claude-code") or {})


@pytest.mark.parametrize("source, interactive, shown", [
    ("startup", True, True), ("resume", True, False), ("clear", True, False),
    ("startup", False, False)])
def test_where_a_turn_cannot_end_with_a_message_the_weekly_line_rides_session_start(
        project, tmp_path, isolated_home, source, interactive, shown):
    guards.receipt("retry", "hold", {"session_id": "old"}, str(project))
    rollout = tmp_path / "r" / "rollout-x.jsonl"
    meta = {"type": "session_meta", "payload": {"id": "t", "source": "cli" if interactive
                                                else "exec"}}
    turn = {"type": "event_msg", "payload": {"type": "item_completed", "item": {
        "type": "UserMessage", "content": [{"type": "text", "text": "hi"}]}}}
    _transcript(rollout, [meta, turn])
    start = {"hook_event_name": "SessionStart", "source": source, "cwd": str(project),
             "session_id": "s-%s" % source, "transcript_path": str(rollout)}
    context = json.dumps(guards.handle(start, "codex") or {})
    assert ("Relay this one line to the person, verbatim" in context) is shown


def test_a_hold_then_sent_again_then_clear_injects_nothing(project, tmp_path, isolated_home):
    hook = prompt_hook(project, cold_transcript(tmp_path))
    assert guards.handle(hook, "claude-code")["decision"] == "block"       # held: note written
    assert guards.handle(hook, "claude-code") is None                      # sent again: ahead
    start = {"hook_event_name": "SessionStart", "source": "clear", "cwd": str(project),
             "session_id": "s-2", "transcript_path": ""}
    assert "previous conversation" not in json.dumps(guards.handle(start, "claude-code") or {})


def test_the_entry_script_prints_nothing_and_exits_zero_when_nothing_applies(tmp_path):
    for stdin in ("not json", json.dumps({"hook_event_name": "UserPromptSubmit",
                                          "cwd": str(tmp_path), "prompt": "x"})):
        done = subprocess.run([sys.executable, GUARD, "--host", "claude-code"], input=stdin,
                              capture_output=True, text=True, encoding="utf-8",
                              env=dict(os.environ))
        assert (done.returncode, done.stdout) == (0, "")


def test_the_entry_script_runs_from_any_folder(project, tmp_path):
    hook = prompt_hook(project, cold_transcript(tmp_path))
    done = subprocess.run([sys.executable, GUARD, "--host", "claude-code"],
                          input=json.dumps(hook), capture_output=True, text=True,
                          encoding="utf-8", cwd=str(tmp_path), env=dict(os.environ))
    assert done.returncode == 0 and json.loads(done.stdout)["decision"] == "block"


def test_a_large_transcript_is_read_within_budget(project, tmp_path, isolated_home):
    import time
    filler = json.dumps(_assistant(0, _ago(80), tool={"name": "Bash", "input": {
        "command": "echo " + "y" * 2000}}))
    path = tmp_path / "t" / "s-1.jsonl"
    path.parent.mkdir(parents=True)
    with open(path, "w", encoding="utf-8") as handle:
        for n in range(20_000):                                     # about 45 MB
            handle.write(filler.replace('"m0"', '"m%d"' % n) + "\n")
        handle.write(json.dumps(_assistant(99_999, _ago(70), write_1h=1000)) + "\n")
        handle.write(json.dumps({"type": "system", "subtype": "stop_hook_summary",
                                 "timestamp": _ago(70)}) + "\n")
    started = time.monotonic()
    held = guards.handle(prompt_hook(project, str(path)), "claude-code")
    assert held is not None and time.monotonic() - started < 3.0


def test_a_hook_file_running_anything_else_is_refused(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("validate_guard_hooks",
                                                  str(Path(PLUGIN_ROOT) / "scripts" / "validate.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "hooks.json").write_text(json.dumps({"hooks": {
        "SessionStart": [{"hooks": [{"command": "python x/scripts/virtuoso_preflight.py --mode check"}]}],
        "PreToolUse": [{"hooks": [{"command": "python x/scripts/something_else.py"}]}]}}),
        encoding="utf-8")
    module.ROOT = str(tmp_path)
    module.oks.clear(), module.fails.clear()
    module.check_session_hook()
    assert module.fails and "neither preflight" in module.fails[0]


# --- G3, starting load, the carriers and the receipts (D4) -------------------------------------

REGISTRY_CLI = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_registry.py")


def cli(root, *args):
    return subprocess.run([sys.executable, REGISTRY_CLI, "--root", str(root), "--actor",
                           "virtuoso"] + list(args), capture_output=True, text=True,
                          encoding="utf-8", env=dict(os.environ))


def test_a_bound_dispatch_records_its_starting_load_and_a_resume_after_the_cache(project,
                                                                                tmp_path):
    transcript = cold_transcript(tmp_path, idle=1)
    hosts.record_binding("X-5", "s-1", transcript, "claude-code")
    rows = tmp_path / "rows.json"
    rows.write_text(json.dumps([{"id": 1, "title": "w", "estimate": 5}]), encoding="utf-8")
    assert cli(project, "timing", "--dispatch", "X-5", "--open", "--rows-file", str(rows)
               ).returncode == 0
    layout = json.loads((project / "Virtuoso" / "workspace-layout.json").read_text(
        encoding="utf-8"))
    log = project.joinpath(*layout["roles"]["closeOuts"]["path"].split("/")) / "Timing.X-5.jsonl"
    events = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    assert events[0]["startingLoad"] == {"tokens": 180_000, "kind": "measured"}
    for step in (("--start", "1"), ("--wait", "1", "--reason", "owner")):
        assert cli(project, "timing", "--dispatch", "X-5", *step).returncode == 0
    # Back-date the wait so the resume falls past the cache's hour.
    lines = log.read_text(encoding="utf-8").splitlines()
    wait = json.loads(lines[-1])
    wait["at"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=90)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    log.write_text("\n".join(lines[:-1] + [json.dumps(wait)]) + "\n", encoding="utf-8")
    assert cli(project, "timing", "--dispatch", "X-5", "--resume", "1").returncode == 0
    resume = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    cold = resume["coldReturn"]
    assert (cold["tokens"], cold["kind"], cold["waiting"]) == (180_000, "inferred", "away")


def test_the_context_now_and_a_model_switch_reload_are_read_from_the_binding(project, tmp_path,
                                                                            isolated_home):
    transcript = cold_transcript(tmp_path, idle=1)
    hosts.record_binding("X-6", "s-1", transcript, "claude-code")
    shown = json.loads(cli(project, "guards", "--dispatch", "X-6", "--context", "--model",
                           "claude-opus-5-5", "--json").stdout)
    assert (shown["tokens"], shown["kind"]) == (180_000, "measured")
    assert shown["reload"]["computable"] and shown["reload"]["kind"] == "estimated"
    missing = json.loads(cli(project, "guards", "--dispatch", "X-0", "--context",
                             "--json").stdout)
    assert not missing["computable"] and "binding" in missing["missing"][0]


def test_an_unbound_session_finds_the_projects_one_open_log(project, tmp_path):
    rows = tmp_path / "rows.json"
    rows.write_text(json.dumps([{"id": 1, "title": "w", "estimate": 5}]), encoding="utf-8")
    assert cli(project, "timing", "--dispatch", "X-7", "--open", "--rows-file", str(rows)
               ).returncode == 0
    assert guards.open_dispatch(str(project), "s-unbound") == "X-7"
    assert cli(project, "timing", "--dispatch", "X-8", "--open", "--rows-file", str(rows)
               ).returncode == 0
    assert guards.open_dispatch(str(project), "s-unbound") == ""    # two open: no guess


def test_expired_handoff_notes_are_swept_and_dropped_secrets_masked(isolated_home):
    old = guards._path(os.path.join("handoffs", "old.json"))
    fresh = guards._path(os.path.join("handoffs", "fresh.json"))
    stale = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=45)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    from tools.governance import guardstate
    guardstate.write_json_atomic(old, {"at": stale, "note": "x"})
    guardstate.write_json_atomic(fresh, {"at": guards._stamp(guards.now()), "note": "x"})
    guards.sweep_handoffs()
    assert not os.path.exists(old) and os.path.exists(fresh)
    masked = guards.redact("curl -H 'token: abc123' --api-key=sk-1 run")
    assert "abc123" not in masked and "sk-1" not in masked and "[redacted]" in masked


def test_a_cold_return_after_a_compaction_is_not_held(project, tmp_path, isolated_home):
    transcript = cold_transcript(tmp_path, extra=[      # closed again, so only the compaction
        {"type": "system", "subtype": "compact_boundary", "timestamp": _ago(65)},
        {"type": "system", "subtype": "stop_hook_summary", "timestamp": _ago(60)}])
    assert guards.handle(prompt_hook(project, transcript), "claude-code") is None


def test_an_unbound_dispatch_adds_nothing_to_its_events(project, tmp_path):
    rows = tmp_path / "rows.json"
    rows.write_text(json.dumps([{"id": 1, "title": "w", "estimate": 5}]), encoding="utf-8")
    assert cli(project, "timing", "--dispatch", "X-6", "--open", "--rows-file", str(rows)
               ).returncode == 0
    layout = json.loads((project / "Virtuoso" / "workspace-layout.json").read_text(
        encoding="utf-8"))
    log = project.joinpath(*layout["roles"]["closeOuts"]["path"].split("/")) / "Timing.X-6.jsonl"
    assert "startingLoad" not in json.loads(log.read_text(encoding="utf-8").splitlines()[0])


def test_a_failure_held_by_the_guard_reaches_every_carrier(project, tmp_path, isolated_home):
    transcript = failing_transcript(tmp_path, 2, "make build")
    hosts.record_binding("X-7", "s-1", transcript, "claude-code")
    denied = guards.handle(tool_hook(project, transcript, "make build"), "claude-code")
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    tried = cli(project, "guards", "--dispatch", "X-7", "--tried", "--json")
    assert json.loads(tried.stdout)["dropped"] == ["command failed 2 times in a row: make build"]
    skills = Path(PLUGIN_ROOT) / "skills"
    issue = (skills / "virtuoso" / "SKILL.md").read_text(encoding="utf-8")
    state = (skills / "epic" / "assets" / "state.template.md").read_text(encoding="utf-8")
    handoff = (skills / "git-handoff" / "SKILL.md").read_text(encoding="utf-8")
    field3 = issue[issue.index("3. **Evidence of issue:**"):issue.index("4. **Possible cause")]
    assert "Tried and failed" in field3 and "guards --dispatch <DISPATCH-ID> --tried" in field3
    assert state.index("## Blockers") < state.index("## Tried and failed") < state.index(
        "## Decision log")
    assert "--tried" in handoff and "Do not retry" in handoff


def test_receipts_count_only_holds_that_stuck_and_copy_once(project, tmp_path, isolated_home):
    transcript = failing_transcript(tmp_path, 2, "make build")
    hosts.record_binding("X-8", "s-1", transcript, "claude-code")
    hook = tool_hook(project, transcript, "make build")
    guards.handle(hook, "claude-code")                               # held
    guards.handle(hook, "claude-code")                               # sent again: not kept
    shown = json.loads(cli(project, "guards", "--dispatch", "X-8", "--json").stdout)
    assert (shown["holds"], shown["kept"]) == (1, 0)
    refused = cli(project, "guards", "--dispatch", "X-8", "--copy", "--apply")
    assert refused.returncode != 0 and '"guardLog": {"path": "<file>.jsonl"' in refused.stderr
    manifest = project / "Virtuoso" / "workspace-layout.json"
    layout = json.loads(manifest.read_text(encoding="utf-8"))
    layout["roles"]["guardLog"] = {"path": "guard-log.jsonl", "provider": "jsonl",
                                   "authority": "evidence", "mutability": "append-only",
                                   "owner": "dispatch-closeout",
                                   "allowedWriters": ["dispatch-closeout"]}
    manifest.write_text(json.dumps(layout, indent=2), encoding="utf-8")
    (project / "guard-log.jsonl").write_text("", encoding="utf-8")
    copy = lambda: subprocess.run([sys.executable, REGISTRY_CLI, "--root", str(project),
                                   "--actor", "dispatch-closeout", "guards", "--dispatch", "X-8",
                                   "--copy", "--apply", "--json"], capture_output=True,
                                  text=True, encoding="utf-8", env=dict(os.environ))
    first = copy()
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["copied"] == 2 and json.loads(copy().stdout)["copied"] == 0
