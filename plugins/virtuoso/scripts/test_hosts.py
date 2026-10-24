"""Host adapters: the host-neutral half — the dispatch binding, the row rule, token usage —
and each adapter's reading of transcripts captured from the real host."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from tools.governance import hosts

FIXTURES = Path(PLUGIN_ROOT) / "scripts" / "fixtures" / "hosts"


# --- the binding signal and the row rule --------------------------------------------------

@pytest.mark.parametrize("command, dispatch", [
    ('"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor virtuoso timing '
     '--dispatch X-1 --open --from-spec spec.md', "X-1"),
    ("virtuoso_registry --root . --actor virtuoso timing --dispatch=HB-9 --start 2", "HB-9"),
    ("python scripts/virtuoso_registry.py --root . timing --sprint EPIC-A --end 3", "EPIC-A"),
    ("virtuoso_registry timing --dispatch 'X-2-S1' --resume 2", "X-2-S1"),
    ("T='\"$HOME/.virtuoso/bin/virtuoso\" virtuoso_registry --root . --actor virtuoso timing "
     "--dispatch X-3'; eval \"$T --start 4 --model m\"", "X-3"),        # the call in a variable
    ("virtuoso_registry --root . timing --end 2 --dispatch X-4", "X-4"),  # the verb first
    ("& \"$HOME/.virtuoso/bin/virtuoso.ps1\" virtuoso_registry --root . --actor virtuoso "
     "timing --confirm 2 --sprint EPIC-B", "EPIC-B"),
    ("virtuoso_registry --root . timing --dispatch \"X-5\" --evidence \"a; b\" --start 1",
     "X-5"),
    ("virtuoso_registry --root . timing --dispatch X-6. --start 1", "X-6"),  # a trailing dot
    ('cd /c/p && V="$HOME/.virtuoso/bin/virtuoso"; timeout 60 "$V" virtuoso_registry --root . '
     "--actor virtuoso timing --sprint X-7 --start 1 --model m", "X-7"),
    ('$v="$HOME/.virtuoso/bin/virtuoso.ps1"; & $v virtuoso_registry --root . timing --confirm 2 '
     "--sprint X-8 --actor a", "X-8"),
    ('V="$HOME/.virtuoso/bin/virtuoso"; sh "$V" virtuoso_registry --root . timing --end 1 '
     "--dispatch X-9", "X-9"),
    ("echo virtuoso_registry --root . timing --dispatch X-1 --start 1", ""),   # echoed, not run
    ("cat <<'EOF'\nvirtuoso_registry is run as: timing --dispatch X-1 --end 3\nEOF", ""),
    ("virtuoso_registry --root . timing --dispatch X-1 --status; git commit --start", ""),
    ("echo 'virtuoso_registry --root . timing --dispatch X-1 --start 1'", ""),
    ("virtuoso_registry --root . timing --dispatch X-1 --status", ""),   # reading binds nothing
    ("virtuoso_registry --root . timing --dispatch X-1 --summary --json", ""),
    ('git commit -m "timing --dispatch X-1 --open"', ""),                # quoted, not run
    ("grep -rn 'timing --dispatch X-1 --start' .", ""),
    ("echo --dispatch X-1 --open", ""),
    ("git log --oneline", ""),
])
def test_working_a_row_names_its_dispatch(command, dispatch):
    assert hosts.binding_dispatch(command) == dispatch


@pytest.mark.parametrize("description, task_name, row", [
    ("row 4 — host must-verify", "", 4),
    ("Row 12: run the suite", "", 12),
    ("review the branch", "", None),
    ("narrow 3 files", "", None),                     # "row" inside another word
    ("", "row_5_probe", 5),                           # a host that keeps only a task name
    ("", "row_5", 5),
    ("", "arrow_5", None),
    ("", "probe_row_5", None),                        # a task name must start with it
    ("row 5 — probe", "row_5_probe", 5),              # both, agreeing
    ("row 5 — probe", "row_6_probe", None),           # both, disagreeing: never guessed
])
def test_a_spawn_names_its_row(description, task_name, row):
    assert hosts.spawn_row(description, task_name) == row


def test_a_binding_is_kept_in_the_users_folder_and_moves_with_the_run(isolated_home):
    assert hosts.read_binding("X-9") is None
    hosts.record_binding("X-9", "s-1", "/t/s-1.jsonl", "host-a")
    hosts.record_binding("X-9", "s-2", "/t/s-2.jsonl", "host-a")
    binding = hosts.read_binding("X-9")
    assert (binding["session"], binding["transcript"]) == ("s-2", "/t/s-2.jsonl")
    assert [s["session"] for s in binding["sessions"]] == ["s-1", "s-2"]
    path = Path(isolated_home) / ".virtuoso" / "guard" / "bindings" / "X-9.json"
    assert path.is_file()
    assert not list(path.parent.glob("*.tmp"))       # written atomically


def test_guard_state_is_never_written_outside_the_users_guard_folder(isolated_home, tmp_path):
    from tools.governance import guardstate
    with pytest.raises(ValueError, match="only under"):
        guardstate.write_json_atomic(str(tmp_path / "project" / "x.json"), {})
    with pytest.raises(ValueError):
        guardstate.write_json_atomic(guardstate.guard_dir() + "-sibling/x.json", {})
    assert not (tmp_path / "project").exists()


def test_an_unreadable_binding_reads_as_none(isolated_home):
    path = Path(isolated_home) / ".virtuoso" / "guard" / "bindings" / "X-9.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    assert hosts.read_binding("X-9") is None


@pytest.mark.parametrize("command, read_only", [
    ("ls /nowhere", True),
    ("git status --porcelain", True),
    ("git --no-optional-locks log --oneline", True),
    ("cd sub && grep -n x file", True),
    ("Get-Content a.txt", True),
    ("git -C ../other status", True),
    ("git -c core.pager=cat log -1", True),
    ("git branch --list", True),
    ("git worktree list --porcelain", True),
    ('cd "C:/Program Files/x" && dir', True),
    ("ls; rm -rf x", False),                          # every part must read only
    ("grep -l x * | xargs rm", False),
    ("cat a | python x.py", False),
    ("echo hi > f.txt", False),                       # a redirect writes
    ("git status 2>&1", True),                        # joining streams writes no file
    ("ls x 2>/dev/null", True),
    ("ls x 2>&1 > out.txt", False),
    ("find . -name '*.tmp' -delete", False),
    ("git branch -D old", False),
    ("git worktree add ../x", False),
    ("git commit -m x", False),
    ("python -m pytest tests", False),
    ("PYTHONPATH=. python run.py", False),
])
def test_read_only_commands_are_told_apart(command, read_only):
    assert hosts.is_read_only(command) is read_only


def test_usage_adds_by_kind_and_knows_its_context():
    one = hosts.Usage(input=10, output=5, cache_read=100, cache_write_5m=20, cache_write_1h=30)
    two = hosts.Usage(input=1, output=1)
    assert (one + two).as_tuple() == (11, 6, 100, 20, 30, 0)
    assert one.context == 160 and one.total == 165


def test_only_the_adapter_directories_may_name_a_host(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "virtuoso_validate_hosts", str(Path(PLUGIN_ROOT) / "scripts" / "validate.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    line = "Reads the OpenAI rollout.\n"                 # validate-ok: the term under test
    for rel in ("tools/governance/hosts/x.py", "scripts/fixtures/hosts/x/README.md",
                "tools/governance/hostsish.py", "scripts/fixtures/other.md"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(line, encoding="utf-8")
    module.ROOT = str(tmp_path)
    module.oks.clear()
    module.fails.clear()
    module.check_text_scans([])
    flagged = " ".join(f for f in module.fails if "host terms" in f)
    assert "tools/governance/hostsish.py" in flagged and "scripts/fixtures/other.md" in flagged
    assert "hosts/x.py" not in flagged and "fixtures/hosts/x/README.md" not in flagged


# --- Claude Code, from transcripts captured 2026-10-22 -------------------------------------

CC = FIXTURES / "claude_code"
RUN1 = CC / "transcripts" / "capture" / "11111111-1111-4111-8111-111111111111.jsonl"
RUN2 = CC / "transcripts" / "capture" / "22222222-2222-4222-8222-222222222222.jsonl"
RUN2_SUB = (RUN2.parent / RUN2.stem / "subagents" / "agent-a2222222222222222.jsonl")
SPECIMEN_SUB = (CC / "transcripts" / "specimen" / "55555555-5555-4555-8555-555555555555"
                / "subagents" / "agent-a5555555555555555.jsonl")


def cc_adapter():
    from tools.governance.hosts import claude_code
    return claude_code.ADAPTER


def test_the_claude_code_adapter_is_found_by_name():
    assert hosts.adapter("claude-code") is cc_adapter()
    assert hosts.adapter("no-such-host") is None
    assert cc_adapter().has("hold-tool-in-subagent") and cc_adapter().has("turn-end-message")
    assert cc_adapter().missing == {}
    assert cc_adapter().turn_end_message("x") == {"systemMessage": "x"}


def test_each_response_is_counted_once_at_its_largest_output():
    facts = cc_adapter().read_transcript(str(SPECIMEN_SUB))
    first = facts.calls[0]
    assert (first.id, first.usage.output) == ("msg_FX000000000000000012", 224)  # not 20, not 244
    assert len({call.id for call in facts.calls}) == len(facts.calls)
    assert facts.usage.as_tuple()[:2] == (12, 2288)


def test_a_top_level_transcript_reads_its_calls_spawns_and_lifetime():
    facts = cc_adapter().read_transcript(str(RUN2))
    assert [c.usage.as_tuple() for c in facts.calls] == [
        (2, 79, 30240, 0, 26368, 0), (2, 178, 56608, 0, 742, 0), (2, 90, 57350, 0, 883, 0)]
    assert {c.model for c in facts.calls} == {"claude-opus-5-5"}
    assert list(facts.spawns.values()) == ["row 7 - capture probe"]
    assert facts.headless is True                      # a `-p` run
    assert cc_adapter().lifetime(facts) == (60, hosts.MEASURED)
    sub = cc_adapter().read_transcript(str(RUN2_SUB))
    assert cc_adapter().lifetime(sub, subagent=True) == (5, hosts.MEASURED)


@pytest.mark.parametrize("writes, subagent, expected", [
    ([(0, 500)], False, (60, "measured")),
    ([(0, 500), (300, 0)], False, (5, "measured")),     # the most recent write decides
    ([(200, 200)], False, (60, "measured")),            # a tie goes to the longer
    ([(10, 0), (0, 0)], True, (5, "measured")),         # a call writing nothing tells nothing
    ([(0, 0)], False, (60, "inferred")),                # no write in view: the usual lifetime
    ([], True, (5, "inferred")),
])
def test_the_cache_lifetime_is_read_per_call(writes, subagent, expected):
    facts = hosts.TranscriptFacts(calls=[
        hosts.Call(id=str(i), time="", model="m",
                   usage=hosts.Usage(cache_write_5m=five, cache_write_1h=hour))
        for i, (five, hour) in enumerate(writes)])
    assert cc_adapter().lifetime(facts, subagent=subagent) == expected
    assert cx_adapter().lifetime(facts) == (None, "inferred")   # the provider decides


def test_a_continued_session_never_carries_the_earlier_sessions_cost(tmp_path):
    source = CC / "records" / "copied_session_zero_usage.jsonl"
    for session, output in (("f000009a-0000-4000-8000-00000000009a", 0),
                            ("f0000095-0000-4000-8000-000000000095", 6098)):
        path = tmp_path / (session + ".jsonl")
        path.write_bytes(source.read_bytes())
        [call] = cc_adapter().read_transcript(str(path)).calls
        assert call.usage.output == output


def test_a_cache_write_without_its_lifetime_is_kept_apart(tmp_path):
    record = {"type": "assistant", "message": {"id": "m1", "model": "m", "content": [],
              "usage": {"input_tokens": 1, "output_tokens": 1,
                        "cache_creation_input_tokens": 900}}}
    facts = cc_adapter().read_transcript(_write(tmp_path, [record]))
    assert facts.calls[0].usage.as_tuple() == (1, 1, 0, 0, 0, 900)
    assert cc_adapter().lifetime(facts) == (60, hosts.INFERRED)


def test_headless_is_seen_from_the_files_head_on_a_tail_read(tmp_path):
    first = {"type": "user", "promptSource": "sdk", "turnOrigin": "sdk",
             "message": {"content": "go"}}
    filler = [_use(i, "Bash", command="echo %d" % i) for i in range(1, 40)]
    path = _write(tmp_path, [first] + filler)
    assert cc_adapter().read_transcript(path, tail_bytes=300).headless is True
    blocked = CC / "transcripts" / "capture" / "33333333-3333-4333-8333-333333333333.jsonl"
    facts = cc_adapter().read_transcript(str(blocked))   # a held prompt writes no user record
    assert facts.calls == [] and facts.last_prompt == ""


def test_claude_code_reads_the_turn_close_past_trailing_bookkeeping():
    capture = CC / "transcripts" / "capture"
    path = capture / "11111111-1111-4111-8111-111111111111.jsonl"
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
    close = lines[18]                                   # line 19, before the bookkeeping
    assert (close["type"], close["subtype"]) == ("system", "stop_hook_summary")
    assert [r["type"] for r in lines[19:]] == ["last-prompt", "cost-state"]
    assert cc_adapter().read_transcript(str(path)).turn_closed_at == close["timestamp"]
    blocked = capture / "33333333-3333-4333-8333-333333333333.jsonl"
    assert cc_adapter().read_transcript(str(blocked)).turn_closed_at == ""


def test_claude_code_a_later_record_reopens_the_turn(tmp_path):
    def closing(at):
        return {"type": "assistant", "timestamp": at, "message": {
            "id": "m1", "model": "m", "stop_reason": "end_turn", "usage": {
                "input_tokens": 1, "output_tokens": 1}, "content": [
                {"type": "text", "text": "done"}]}}
    at = "2026-10-22T10:00:00.000Z"
    prompt = {"type": "user", "timestamp": "2026-10-22T10:05:00.000Z",
              "message": {"content": "next"}}
    reopened = cc_adapter().read_transcript(_write(tmp_path, [closing(at), prompt]))
    assert reopened.turn_closed_at == ""
    bookkeeping = [{"type": "last-prompt", "lastPrompt": "next"},
                   {"type": "cost-state", "totalCostUSD": 0}]
    kept = cc_adapter().read_transcript(_write(tmp_path, [closing(at)] + bookkeeping))
    assert kept.turn_closed_at == at
    for later, expected in (
            ({"type": "system", "subtype": "turn_duration", "durationMs": 1}, at),
            ({"type": "attachment", "attachment": {"type": "file"}}, at),
            ({"type": "system", "subtype": "compact_boundary", "timestamp": at}, ""),
            ({"type": "assistant", "timestamp": at, "message": {
                "id": "m2", "model": "m", "stop_reason": "tool_use", "content": []}}, "")):
        facts = cc_adapter().read_transcript(_write(tmp_path, [closing(at), later]))
        assert facts.turn_closed_at == expected, later


def test_workflow_and_nested_subagents_are_found_and_attributed(tmp_path):
    metas = [json.loads(l) for l in (CC / "records" / "meta_variants.jsonl")
             .read_text(encoding="utf-8").splitlines()]
    top = tmp_path / "s-1.jsonl"
    top.write_text("", encoding="utf-8")
    folder = tmp_path / "s-1" / "subagents"
    layout = {"agent-a000000000000f001": folder, "agent-a000000000000f002": folder,
              "agent-a000000000000f004": folder, "agent-a000000000000f003": folder,
              "agent-a000000000000f099": folder / "workflows" / "wf_1"}
    names = ["agent-a000000000000f003", "agent-a000000000000f002", "agent-a000000000000f004",
             "agent-a000000000000f099"]
    for name, meta in zip(names, metas):
        layout[name].mkdir(parents=True, exist_ok=True)
        (layout[name] / (name + ".jsonl")).write_text("", encoding="utf-8")
        (layout[name] / (name + ".meta.json")).write_text(json.dumps(meta), encoding="utf-8")
    found = [Path(p).name for p in cc_adapter().subagent_transcripts(str(top))]
    assert "agent-a000000000000f099.jsonl" in found and len(found) == 4
    nested = folder / "agent-a000000000000f004.jsonl"          # spawnDepth 2, parent f003
    assert cc_adapter().spawn_description(str(nested)) == "review the change"
    workflow = layout["agent-a000000000000f099"] / "agent-a000000000000f099.jsonl"
    assert cc_adapter().spawn_description(str(workflow)) == ""  # no spawn call: orchestration


def test_the_captured_declines_drop_only_declined_edits(tmp_path):
    source = (CC / "records" / "denials_and_declines.jsonl").read_text(encoding="utf-8")
    path = tmp_path / "s.jsonl"
    path.write_text(source, encoding="utf-8")
    facts = cc_adapter().read_transcript(str(path))
    assert [d for d in facts.dropped if d.startswith("edit declined")] == [
        "edit declined: <input:file_path>"]                       # the cancelled Edit
    assert not any("command failed" in d for d in facts.dropped)  # holds are not failures


@pytest.mark.parametrize("prompt, injected", [
    ("<agent-message from=\"a1\">\n[Subagent hand-back] done", True),
    ("<task-notification>\n<task-id>x</task-id>", True),
    ("<command-message>review</command-message>", True),
    ("[Request interrupted by user]", True),
    ("please run the tests", False),
    ("  <b>bold</b> text", False),
])
def test_text_the_host_wrote_is_not_a_typed_prompt(prompt, injected):
    assert cc_adapter().is_injected_prompt(prompt) is injected


def test_a_compaction_summary_and_a_powershell_failure_read_as_captured(tmp_path):
    records = [{"type": "user", "message": {"content": "fix the bug"}},
               {"type": "user", "isCompactSummary": True, "message": {"content": "Summary: …"}},
               _use(1, "PowerShell", command="python -m pytest"),
               _result(1, "Exit code 1\nInvoke-Expression: Missing closing ')'", True),
               _use(2, "PowerShell", command="python -m pytest"),
               _result(2, "Exit code 1\nInvoke-Expression: Missing closing ')'", True)]
    facts = cc_adapter().read_transcript(_write(tmp_path, records))
    assert facts.last_prompt == "fix the bug"
    assert facts.failing == {"python -m pytest": 2}


def test_a_subagent_is_found_from_its_hook_and_named_by_its_spawn():
    lines = (CC / "hooks" / "stdin_run2.jsonl").read_text(encoding="utf-8").splitlines()
    inside = [json.loads(l) for l in lines if '"agent_id"' in l]
    hook = next(h for h in inside if h["hook_event_name"] == "PreToolUse")
    derived = cc_adapter().subagent_transcript(hook)
    assert derived.replace("\\", "/").endswith(
        "22222222-2222-4222-8222-222222222222/subagents/agent-a2222222222222222.jsonl")
    assert cc_adapter().is_subagent(hook)
    assert cc_adapter().spawn_description(str(RUN2_SUB)) == "row 7 - capture probe"
    assert hosts.spawn_row(cc_adapter().spawn_description(str(RUN2_SUB))) == 7
    assert [Path(p).name for p in cc_adapter().subagent_transcripts(str(RUN2))] == [
        "agent-a2222222222222222.jsonl"]


def test_injected_prompts_are_not_typed_prompts():
    lines = (CC / "hooks" / "stdin_run2.jsonl").read_text(encoding="utf-8").splitlines()
    prompts = [json.loads(l)["prompt"] for l in lines if '"UserPromptSubmit"' in l]
    assert [cc_adapter().is_injected_prompt(p) for p in prompts] == [False, True]
    assert cc_adapter().is_injected_prompt("<task-notification>\n<task-id>x</task-id>")


def test_hook_outputs_have_the_captured_shape():
    a = cc_adapter()
    assert a.hold_prompt("why") == {"decision": "block", "reason": "why"}
    assert a.deny_tool("why")["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert a.session_context("note")["hookSpecificOutput"]["additionalContext"] == "note"


def _use(i, name, **args):
    return {"type": "assistant", "message": {"id": "m%d" % i, "model": "m", "usage": {
        "input_tokens": 1, "output_tokens": 1}, "content": [
        {"type": "tool_use", "id": "t%d" % i, "name": name, "input": args}]}}


def _result(i, text, error=False, **record):
    return dict({"type": "user", "toolUseResult": text, "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t%d" % i, "is_error": error,
         "content": text}]}}, **record)


def _write(tmp_path, records, extra=b""):
    path = tmp_path / "s.jsonl"
    path.write_bytes(b"\n".join(json.dumps(r).encode("utf-8") for r in records) + b"\n" + extra)
    return str(path)


def test_a_command_failing_twice_with_nothing_changed_is_a_streak_and_dropped(tmp_path):
    records = [_use(1, "Bash", command="pytest -x"), _result(1, "Exit code 1\nboom", True),
               _use(2, "Bash", command="ls"), _result(2, "Exit code 2", True),      # read-only
               _use(3, "Bash", command="pytest -x"), _result(3, "Exit code 1\nboom", True)]
    facts = cc_adapter().read_transcript(_write(tmp_path, records))
    assert facts.failing == {"pytest -x": 2}
    assert facts.dropped == ["command failed 2 times in a row: pytest -x"]


def test_a_successful_change_resets_every_streak(tmp_path):
    records = [_use(1, "Bash", command="pytest -x"), _result(1, "Exit code 1", True),
               _use(2, "Edit", file_path="a.py", old_string="x", new_string="y"),
               _result(2, "ok"),
               _use(3, "Bash", command="pytest -x"), _result(3, "Exit code 1", True)]
    facts = cc_adapter().read_transcript(_write(tmp_path, records))
    assert facts.failing == {"pytest -x": 1} and facts.last_change == "t2"
    assert facts.edited == ["a.py"] and facts.dropped == []


def test_declined_and_put_back_edits_are_dropped(tmp_path):
    records = [_use(1, "Edit", file_path="a.py", old_string="x", new_string="y"),
               _result(1, "The user doesn't want to proceed with this tool use.", True,
                       toolDenialKind="user-rejected"),
               _use(2, "Edit", file_path="b.py", old_string="1", new_string="2"),
               _result(2, "ok"),
               _use(3, "Edit", file_path="b.py", old_string="2", new_string="1"),
               _result(3, "ok")]
    facts = cc_adapter().read_transcript(_write(tmp_path, records))
    assert facts.dropped == ["edit declined: a.py", "edit put back: b.py"]


def test_damaged_lines_are_skipped_and_a_tail_read_starts_on_a_whole_line(tmp_path):
    records = [_use(i, "Bash", command="echo %d" % i) for i in range(1, 6)]
    path = _write(tmp_path, records, extra=b'{"type": "assistant", "mess\n\xff\xfe broken\n')
    facts = cc_adapter().read_transcript(path)
    assert len(facts.calls) == 5
    tail = cc_adapter().read_transcript(path, tail_bytes=420)
    assert 0 < len(tail.calls) < 5 and tail.commands[-1] == "echo 5"
    whole = cc_adapter().read_transcript(path, tail_bytes=10_000_000)  # a tail past the file
    assert len(whole.calls) == 5
    assert cc_adapter().read_transcript(str(tmp_path / "missing.jsonl")).calls == []


# --- the "codex" adapter, from rollouts captured 2026-10-22 ---------------------------------

CX = FIXTURES / "codex" / "sessions" / "2026" / "10" / "22"
CX_RUN2 = CX / "rollout-2026-10-22T20-18-05-22222222-2222-7222-8222-222222222222.jsonl"
CX_PARENT = CX / "rollout-2026-10-22T20-22-35-33333333-3333-7333-8333-333333333333.jsonl"
CX_SUB = CX / "rollout-2026-10-22T20-22-43-44444444-4444-7444-8444-444444444444.jsonl"


def cx_adapter():
    from tools.governance.hosts import codex
    return codex.ADAPTER


def test_a_codex_tail_read_still_knows_a_headless_run(tmp_path):
    path = tmp_path / "rollout.jsonl"
    filler = [{"type": "event_msg", "payload": {"type": "note", "text": "x" * 500}}] * 200
    path.write_text("\n".join(json.dumps(r) for r in [
        {"type": "session_meta", "payload": {"id": "c-1", "source": "exec",
                                             "cli_version": "0.1"}}] + filler) + "\n",
        encoding="utf-8")
    facts = cx_adapter().read_transcript(str(path), 4096)
    assert facts.headless and facts.host_version == "0.1"


def test_the_codex_adapter_claims_only_what_was_captured():
    a = cx_adapter()
    assert hosts.adapter("codex") is a
    assert sorted(a.capabilities) == ["cache-lifetime", "hold-prompt", "read-subagent-transcript",
                                      "read-transcript", "session-start-context"]
    assert sorted(a.missing) == ["edit-tracking", "hold-tool", "hold-tool-in-subagent",
                                 "turn-end-message"]
    assert a.cache_lifetime == hosts.PROVIDER_DECIDED
    assert set(a.capabilities) | set(a.missing) == set(hosts.CAPABILITIES)
    cc = cc_adapter()
    assert set(cc.capabilities) | set(cc.missing) == set(hosts.CAPABILITIES)


def test_the_isolated_capture_shows_a_held_prompt_and_session_context():
    hooks = [json.loads(l) for l in (FIXTURES / "codex" / "hooks" / "stdin_isolated_home.jsonl")
             .read_text(encoding="utf-8").splitlines()]
    assert [h["hook_event_name"] for h in hooks] == ["SessionStart", "UserPromptSubmit",
                                                     "SessionEnd"]
    rollout = (FIXTURES / "codex" / "hooks" / "rollout_isolated_home.jsonl").read_text(
        encoding="utf-8")
    assert "V51-CX-CTX-4410" in rollout                  # the session-start context arrived
    assert '"UserMessage"' not in rollout                # the held prompt never reached it
    assert cx_adapter().hold_prompt("why") == {"decision": "block", "reason": "why"}


def test_codex_usage_separates_cached_input_and_keeps_unreported_writes_apart():
    facts = cx_adapter().read_transcript(str(CX_RUN2))
    first = facts.calls[0]
    assert (first.id, first.model) == ("resp_FX016", "gpt-6.1-sol")
    assert first.usage.as_tuple() == (30126 - 13440, 63, 13440, 0, 0, 0)
    assert first.usage.context == 30126                 # input already counted the cache
    assert facts.headless is True                       # an exec run


def test_a_failed_codex_command_counts_and_a_read_only_one_does_not_reset_it():
    facts = cx_adapter().read_transcript(str(CX_RUN2))
    failed, echoed = facts.commands
    assert failed.startswith("python -c") and echoed.startswith("echo")
    assert facts.failing == {failed: 1} and facts.last_change == ""


def test_a_codex_subagent_is_found_by_its_spawn_and_named_by_its_task():
    parent = cx_adapter().read_transcript(str(CX_PARENT))
    assert list(parent.spawns.values()) == ["row_5_probe"]
    assert hosts.spawn_row(task_name="row_5_probe") == 5
    assert list(parent.spawn_threads.values()) == ["44444444-4444-7444-8444-444444444444"]
    assert [Path(p).name for p in cx_adapter().subagent_transcripts(str(CX_PARENT))] == [
        CX_SUB.name]


def test_a_codex_subagent_skips_the_parents_replayed_history():
    sub = cx_adapter().read_transcript(str(CX_SUB))
    assert sub.session_id == "44444444-4444-7444-8444-444444444444"
    assert [c.id for c in sub.calls] == ["resp_FX033", "resp_FX036", "resp_FX038"]
    assert sub.last_prompt == ""                        # its prompt is the parent's, replayed


@pytest.mark.parametrize("path", [
    CX / "rollout-2026-10-22T20-13-15-11111111-1111-7111-8111-111111111111.jsonl",
    CX_RUN2, CX_PARENT, CX_SUB])
def test_codex_reads_task_complete_as_the_turn_close(path, tmp_path):
    last = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    assert last["payload"]["type"] == "task_complete"
    closed = dt.datetime.fromtimestamp(last["payload"]["completed_at"], dt.timezone.utc)
    assert cx_adapter().read_transcript(str(path)).turn_closed_at == closed.strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    meta = {"type": "session_meta", "payload": {"id": "c-1",
                                                "subagent_history_start_ordinal": 2}}
    complete = {"type": "event_msg", "timestamp": "2026-10-22T10:00:00Z",
                "payload": {"type": "task_complete", "completed_at": 1792718012}}
    started = {"type": "event_msg", "payload": {"type": "task_started"}}
    rollout = tmp_path / "rollout.jsonl"
    rollout.write_text("\n".join(json.dumps(r) for r in [meta, complete, started]) + "\n",
                       encoding="utf-8")
    assert cx_adapter().read_transcript(str(rollout)).turn_closed_at == ""
    unreadable = dict(complete, payload=dict(complete["payload"], completed_at=1e20))
    rollout.write_text("\n".join(json.dumps(r) for r in [meta, unreadable]) + "\n",
                       encoding="utf-8")
    assert cx_adapter().read_transcript(str(rollout)).turn_closed_at == complete["timestamp"]
    for ordinal, expected in ((1, ""), (2, "2026-10-23T01:13:32Z")):   # replayed, then own
        rollout.write_text("\n".join(json.dumps(r) for r in [
            meta, dict(complete, ordinal=ordinal)]) + "\n", encoding="utf-8")
        assert cx_adapter().read_transcript(str(rollout)).turn_closed_at == expected
