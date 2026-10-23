"""The cost baseline backfilled from transcripts the host still keeps, automatically, inside
the next write of the closeOuts role."""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from tools.governance import backfill, costreport, hosts, timing

REGISTRY_CLI = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_registry.py")
PREFLIGHT = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_preflight.py")
LATER = dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc)      # long after the logs settled


def _log(directory: Path, dispatch: str, start: str, end: str, tokens=None,
         extra=()) -> Path:
    events = [{"event": "open", "at": start, "rows": [
        {"id": 1, "title": "work", "predicted": 5, "basis": "estimated"}]},
        {"event": "start", "row": 1, "at": start},
        dict({"event": "end", "row": 1, "at": end, "result": "done", "evidence": "x"},
             **({"tokens": tokens} if tokens else {}))] + list(extra)
    path = directory / ("Timing.%s.jsonl" % dispatch)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return path


def _call(i, at, output, command=None, cwd="", message_id=None):
    content = [{"type": "tool_use", "id": "t%d" % i, "name": "Bash",
                "input": {"command": command}}] if command else []
    return {"type": "assistant", "timestamp": at, "cwd": cwd, "message": {
        "id": message_id or "m%d" % i, "model": "claude-opus-5-5", "content": content,
        "usage": {"input_tokens": 10, "output_tokens": output, "cache_read_input_tokens": 0,
                  "cache_creation": {"ephemeral_5m_input_tokens": 0,
                                     "ephemeral_1h_input_tokens": 0}}}}


def _session(root: Path, session: str, records, subagent_records=None, folder="a-project"):
    where = root / "projects" / folder
    where.mkdir(parents=True, exist_ok=True)
    path = where / (session + ".jsonl")
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    if subagent_records:
        sub = where / session / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-a1.jsonl").write_text(
            "\n".join(json.dumps(r) for r in subagent_records) + "\n", encoding="utf-8")
        (sub / "agent-a1.meta.json").write_text(json.dumps({"description": "", "toolUseId": "t0"}),
                                                encoding="utf-8")
    return path


@pytest.fixture
def host(isolated_home):
    return Path(os.environ["CLAUDE_CONFIG_DIR"])


def worked(dispatch, verb="--start 1"):
    return "virtuoso_registry --root . --actor virtuoso timing --dispatch %s %s" % (dispatch, verb)


def run(directory, project, **kw):
    return backfill.run(str(directory), project=str(project), now=LATER, **kw)


def cost_events(path: Path) -> list[dict]:
    return [e for e in timing.load(str(path)) if e["event"] == "cost"]


def test_a_closed_log_gains_its_dispatch_level_cost_marked_backfilled(tmp_path, host):
    logs, proj = tmp_path / "logs", tmp_path / "proj"
    logs.mkdir(), proj.mkdir()
    _log(logs, "X-5", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    _session(host, "s-1", [_call(1, "2026-10-10T09:00:00.000Z", 999, cwd=str(proj)),
                           _call(2, "2026-10-10T10:01:00.000Z", 100, worked("X-5"), str(proj)),
                           _call(3, "2026-10-10T10:30:00.000Z", 50, cwd=str(proj))],
             subagent_records=[_call(9, "2026-10-10T10:10:00.000Z", 300)])
    [done] = run(logs, proj)
    assert (done["dispatch"], done["computable"], done["tokens"]) == ("X-5", True, 480)
    [event] = cost_events(logs / "Timing.X-5.jsonl")
    assert event["source"] == "backfilled" and event["sessions"] == ["s-1.jsonl"]
    assert event["window"] == ["2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z"]
    assert event["orchestration"]["usage"]["output"] == 150 and event["total"]["usage"][
        "output"] == 450
    assert event["total"]["kind"] == "measured" and event["total"]["usdKind"] == "estimated"
    assert event["attribution"] == "session-window" and not event["perRow"]["computable"]
    assert costreport.dispatch_cost(str(logs), "X-5")["total"]["tokens"] == 480


def test_a_log_whose_transcript_is_gone_is_marked_once_and_measured_again_only_if_it_moved(
        tmp_path, host):
    path = _log(tmp_path, "X-6", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    assert [d["computable"] for d in run(tmp_path, tmp_path)] == [False]
    assert run(tmp_path, tmp_path) == []                             # not retried
    [event] = cost_events(path)
    assert event["computable"] is False and "works a row of X-6" in event["missing"][0]
    assert not timing.check_log(timing.load(str(path)))              # the log still checks clean
    with open(path, "a", encoding="utf-8") as handle:                # work resumed later on
        for e in ({"event": "add", "at": "2026-10-12T10:00:00Z", "rows": [
                {"id": 2, "title": "more", "predicted": 5, "basis": "estimated"}]},
                  {"event": "start", "row": 2, "at": "2026-10-12T10:00:00Z"},
                  {"event": "end", "row": 2, "at": "2026-10-12T11:00:00Z", "result": "done",
                   "evidence": "x"}):
            handle.write(json.dumps(e) + "\n")
    assert [d["dispatch"] for d in run(tmp_path, tmp_path)] == ["X-6"]
    assert costreport.recorded(timing.load(str(path)))["window"][1] == "2026-10-12T11:00:00Z"


def test_only_a_session_that_worked_a_row_inside_the_work_is_the_dispatchs(tmp_path, host):
    _log(tmp_path, "X-7", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    p = str(tmp_path)
    _session(host, "reader", [_call(1, "2026-10-10T10:05:00.000Z", 1,
                                    "virtuoso_registry --root . timing --dispatch X-7 --status", p)])
    _session(host, "ruler", [_call(2, "2026-10-10T10:05:00.000Z", 1,
                                   worked("X-7", "--confirm 1"), p)])
    _session(host, "talker", [_call(3, "2026-10-10T10:05:00.000Z", 1,
                                    'git commit -m "timing --dispatch X-7 --start 1"', p)])
    _session(host, "late", [_call(4, "2026-10-10T18:00:00.000Z", 1, worked("X-7"), p)])
    [done] = run(tmp_path, tmp_path)
    assert done["computable"] is False


def test_a_later_ruling_never_stretches_the_window(tmp_path, host):
    p = str(tmp_path)
    _log(tmp_path, "X-8", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z",
         extra=[{"event": "confirm", "row": 1, "at": "2026-10-10T13:00:00Z"}])
    _session(host, "s", [_call(1, "2026-10-10T10:01:00.000Z", 10, worked("X-8"), p),
                         _call(2, "2026-10-10T12:30:00.000Z", 9000, cwd=p)])   # after the work
    run(tmp_path, tmp_path)
    [event] = cost_events(tmp_path / "Timing.X-8.jsonl")
    assert event["window"][1] == "2026-10-10T11:00:00Z"
    assert event["total"]["usage"]["output"] == 10


def test_unsettled_bound_and_current_logs_are_left_alone(tmp_path, host):
    _log(tmp_path, "X-9", "2026-10-19T22:00:00Z", "2026-10-19T23:00:00Z")      # an hour ago
    _log(tmp_path, "X-10", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    _log(tmp_path, "X-11", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    _log(tmp_path, "X-12", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z", tokens=1234)
    hosts.record_binding("X-10", "s", "/t/s.jsonl", "claude-code")
    names = [d for d, _e in backfill.candidates(str(tmp_path), current="X-11",
                                                now=dt.datetime(2026, 10, 19, 23, 30,
                                                                tzinfo=dt.timezone.utc))]
    assert names == []


def test_overlapping_dispatches_in_one_session_are_marked(tmp_path, host):
    p = str(tmp_path)
    _log(tmp_path, "X-13", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    _log(tmp_path, "X-14", "2026-10-10T10:30:00Z", "2026-10-10T11:30:00Z")
    _session(host, "s", [_call(1, "2026-10-10T10:01:00.000Z", 10, worked("X-13"), p),
                         _call(2, "2026-10-10T10:31:00.000Z", 20, worked("X-14"), p)])
    run(tmp_path, tmp_path)
    assert cost_events(tmp_path / "Timing.X-13.jsonl")[0]["overlaps"] == ["X-14"]
    assert cost_events(tmp_path / "Timing.X-14.jsonl")[0]["overlaps"] == ["X-13"]


def test_a_response_copied_into_another_file_is_counted_once(tmp_path, host):
    p = str(tmp_path)
    _log(tmp_path, "X-15", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    _session(host, "s-a", [_call(1, "2026-10-10T10:01:00.000Z", 10, worked("X-15"), p),
                           _call(2, "2026-10-10T10:20:00.000Z", 70, cwd=p, message_id="shared")])
    _session(host, "s-b", [_call(3, "2026-10-10T10:02:00.000Z", 10, worked("X-15", "--end 1"), p),
                           _call(4, "2026-10-10T10:20:00.000Z", 70, cwd=p, message_id="shared")])
    run(tmp_path, tmp_path)
    [event] = cost_events(tmp_path / "Timing.X-15.jsonl")
    assert event["total"]["calls"] == 3 and event["total"]["usage"]["output"] == 90


def test_damaged_older_and_other_projects_transcripts_are_skipped(tmp_path, host):
    proj, other = tmp_path / "proj", tmp_path / "elsewhere"
    proj.mkdir(), other.mkdir()
    _log(tmp_path, "X-16", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    good = _session(host, "s-2", [_call(1, "2026-10-10T10:05:00.000Z", 70, worked("X-16"),
                                        str(proj))])
    (good.parent / "truncated.jsonl").write_bytes(
        b'{"type": "assistant", "cwd": "x", "message": {"id": "m9", "content": [{"type": '
        b'"tool_use", "name": "Bash", "input": {"command": "' + worked("X-16").encode())
    (good.parent / "binary.jsonl").write_bytes(b"\xff\xfe timing X-16 \x00\x00")
    _session(host, "s-other", [_call(5, "2026-10-10T10:05:00.000Z", 9999, worked("X-16"),
                                     str(other))], folder="b-project")
    old = _session(host, "s-old", [_call(6, "2026-10-10T10:05:00.000Z", 9999, worked("X-16"),
                                         str(proj))], folder="c-project")
    os.utime(old, (1_700_000_000, 1_700_000_000))                    # written long before
    run(tmp_path, proj)
    [event] = cost_events(tmp_path / "Timing.X-16.jsonl")
    assert event["sessions"] == ["s-2.jsonl"] and event["total"]["usage"]["output"] == 70


def test_a_run_out_of_time_records_only_what_it_found(tmp_path, host, monkeypatch):
    p = str(tmp_path)
    _log(tmp_path, "X-19", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    _log(tmp_path, "X-20", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    _session(host, "a", [_call(1, "2026-10-10T10:05:00.000Z", 1, worked("X-19"), p)])
    real = backfill._sessions

    def cut_short(wanted, roots, project, reader, deadline):
        found, _done = real(wanted, roots, project, reader, deadline)
        return found, False                            # as if time ran out after "a"
    monkeypatch.setattr(backfill, "_sessions", cut_short)
    done = {d["dispatch"]: d for d in run(tmp_path, tmp_path)}
    assert done["X-19"]["computable"] is True and done["X-20"].get("deferred")
    assert cost_events(tmp_path / "Timing.X-20.jsonl") == []        # never marked unseen


def test_a_run_out_of_time_writes_nothing_and_leaves_the_rest_for_later(tmp_path, host):
    _log(tmp_path, "X-17", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    _session(host, "s", [_call(1, "2026-10-10T10:05:00.000Z", 1, worked("X-17"), str(tmp_path))])
    assert run(tmp_path, tmp_path, budget=0) == [{"dispatch": "X-17", "computable": None,
                                                  "deferred": True}]
    assert cost_events(tmp_path / "Timing.X-17.jsonl") == []


def test_a_log_that_cannot_be_written_is_named_and_not_retried_at_once(tmp_path, host,
                                                                       monkeypatch):
    path = _log(tmp_path, "X-18", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    # A refused write, forced directly: a read-only bit does not stop root (WSL, containers).
    from tools.governance import timing

    def refused(*_a, **_k):
        raise PermissionError("the time log is read-only")
    monkeypatch.setattr(timing, "append", refused)
    [done] = run(tmp_path, tmp_path)
    assert done["computable"] is None and "read-only" in done["error"]
    assert run(tmp_path, tmp_path) == []                             # skipped for a while
    monkeypatch.undo()
    assert cost_events(path) == []


def test_a_test_may_never_read_this_machines_transcripts(tmp_path):
    with pytest.raises(RuntimeError, match="outside VIRTUOSO_HOME"):
        backfill._guarded_roots({"claude-code": [str(Path.home() / ".claude" / "projects")]})


def test_the_next_write_of_the_close_outs_role_backfills_with_nothing_run_by_hand(project, host):
    made = subprocess.run([sys.executable, PREFLIGHT, "--root", str(project), "--mode", "create",
                           "--authorize"], capture_output=True, text=True, encoding="utf-8")
    assert made.returncode == 0, made.stdout + made.stderr
    layout = json.loads((project / "Virtuoso" / "workspace-layout.json").read_text(
        encoding="utf-8"))
    close_outs = project.joinpath(*layout["roles"]["closeOuts"]["path"].split("/"))
    close_outs.mkdir(parents=True, exist_ok=True)
    _log(close_outs, "X-5", "2026-10-10T10:00:00Z", "2026-10-10T11:00:00Z")
    _session(host, "s-1", [_call(2, "2026-10-10T10:05:00.000Z", 100, worked("X-5"),
                                 str(project))])
    rows = project / "rows.json"
    rows.write_text(json.dumps([{"id": 1, "title": "a", "estimate": 5}]), encoding="utf-8")
    done = subprocess.run([sys.executable, REGISTRY_CLI, "--root", str(project), "--actor",
                           "virtuoso", "timing", "--dispatch", "NEW-1", "--open",
                           "--rows-file", str(rows)], capture_output=True, text=True,
                          encoding="utf-8", env=dict(os.environ))
    assert done.returncode == 0, done.stderr
    assert "cost backfilled for 1 closed time log(s)" in done.stderr
    assert [e["source"] for e in cost_events(close_outs / "Timing.X-5.jsonl")] == ["backfilled"]
    status = subprocess.run([sys.executable, REGISTRY_CLI, "--root", str(project), "timing",
                             "--dispatch", "NEW-1", "--status"], capture_output=True, text=True,
                            encoding="utf-8", env=dict(os.environ))
    assert status.returncode == 0                                    # reading never backfills
    assert len(cost_events(close_outs / "Timing.X-5.jsonl")) == 1
