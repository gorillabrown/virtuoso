"""Did it work? A change's runs after against its runs before: a verdict only on enough
work, the range when baselines disagree, trade-offs and confounders named."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from tools.governance import results

CHANGE = {"id": "CH-001", "action": "apply", "kind": "policy", "subject": "guards.retry",
          "effectiveFrom": "2026-10-20T00:00:00Z"}
TODAY = dt.date(2026, 11, 3)
LESSON = "SRL-%03d" % 1                  # a lesson id, built so no shipped line names one


def _log(directory: Path, name: str, day: str, rows: int, tokens: int, usd: float,
         usd_kind="measured", predicted=10, worked=10, added=0):
    events = [{"event": "open", "at": "%sT01:00:00Z" % day, "rows": [
        {"id": i + 1, "title": "r", "predicted": predicted, "basis": "estimated",
         "tier": "bounded"} for i in range(rows)]}]
    for i in range(rows):
        events += [{"event": "start", "row": i + 1, "at": "%sT01:00:00Z" % day},
                   {"event": "end", "row": i + 1, "at": "%sT01:%02d:00Z" % (day, worked),
                    "result": "done", "evidence": "x"}]
    for i in range(added):
        events += [{"event": "add", "at": "%sT01:00:00Z" % day, "rows": [
            {"id": rows + i + 1, "title": "late", "predicted": 5, "basis": "estimated"}]},
            {"event": "start", "row": rows + i + 1, "at": "%sT01:00:00Z" % day},
            {"event": "end", "row": rows + i + 1, "at": "%sT01:%02d:00Z" % (day, worked),
             "result": "done", "evidence": "x"}]
    events.append({"event": "cost", "source": "backfilled", "at": "2026-11-03T00:00:00Z",
                   "total": {"tokens": tokens, "usd": usd, "usdKind": usd_kind,
                             "kind": "measured"}})
    (directory / ("Timing.%s.jsonl" % name)).write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _days(start: str, count: int) -> list[str]:
    first = dt.date.fromisoformat(start)
    return [(first + dt.timedelta(days=n)).isoformat() for n in range(count)]


def _side(directory, prefix, days, per_row_tokens, rows=10, **extra):
    for n, day in enumerate(days):
        _log(directory, "%s-%d" % (prefix, n), day, rows, per_row_tokens * rows,
             per_row_tokens * rows / 1000, **extra)


def _judge(directory, change=CHANGE, ledger=None, unit="tokens", **kw):
    records = results.dispatch_facts(str(directory), prices={"models": {}})
    return results.judge(change, records, ledger or [change], unit=unit,
                         prices={"models": {}}, today=TODAY, **kw)


def test_no_verdict_before_enough_work_and_it_says_how_far_along(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 2), 500, rows=5)
    verdict = _judge(tmp_path)
    assert verdict["verdict"] == "not yet"
    assert verdict["needs"] == {"activeDays": 1, "closedLogs": 1, "measuredRows": 20}


def test_a_clear_drop_in_cost_per_row_reads_better(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    verdict = _judge(tmp_path)
    primary = verdict["primary"]
    assert verdict["verdict"] == "better" and primary["move"] == pytest.approx(-0.4)
    assert (primary["sides"]["before"]["value"], primary["sides"]["after"]["value"]) == (1000, 600)
    assert primary["kind"] == "measured" and primary["confidence"] in ("high", "likely")


def test_a_move_under_the_threshold_is_no_clear_effect(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 950)
    assert _judge(tmp_path)["verdict"] == "no clear effect"


def test_disagreeing_baselines_give_the_range_not_the_best_reading(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 11), 1000)
    _side(tmp_path, "C", _days("2026-10-17", 3), 500)          # the last 3 days were cheap
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    verdict = _judge(tmp_path)
    assert verdict["verdict"].startswith("range ")
    low, high = verdict["primary"]["range"]
    assert low < 0 < high


def test_a_figure_that_moved_the_wrong_way_is_a_trade_off(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000, worked=12)  # 20% over before
    _side(tmp_path, "A", _days("2026-10-21", 4), 600, worked=20)   # 100% over after
    verdict = _judge(tmp_path)
    assert verdict["others"]["rowError"]["before"] == pytest.approx(0.2)
    assert verdict["verdict"] == "better" and "rowError" in verdict["tradeOffs"]


def test_confounders_are_named(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-15", 5), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    other = {"id": "CH-002", "action": "apply", "kind": "lesson", "subject": LESSON,
             "effectiveFrom": "2026-10-22T00:00:00Z"}
    verdict = _judge(tmp_path, ledger=[CHANGE, other])
    text = " | ".join(verdict["confounders"])
    assert "another change in the window: CH-002" in text
    assert "a baseline covering 4 of its 14 days" in text


def test_a_working_week_baseline_is_not_called_short(tmp_path, isolated_home):
    weekdays = [d for d in _days("2026-10-06", 14)
                if dt.date.fromisoformat(d).weekday() < 5]               # ten days of work
    _side(tmp_path, "B", weekdays, 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    assert not any("baseline covering" in c for c in _judge(tmp_path)["confounders"])


def test_a_dollar_verdict_is_the_weaker_kind_of_its_sides(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000, usd_kind="estimated")
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    dollars = _judge(tmp_path, unit="dollars")
    tokens = _judge(tmp_path, unit="tokens")
    assert (dollars["primary"]["measure"], dollars["primary"]["kind"]) == ("usd", "estimated")
    assert (tokens["primary"]["measure"], tokens["primary"]["kind"]) == ("tokens", "measured")


def test_a_price_card_change_between_the_sides_never_reads_as_the_effect(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    prices = {"models": {"m": {"cards": [{"from": "2026-10-01"}, {"from": "2026-10-25"}]}}}
    records = results.dispatch_facts(str(tmp_path), prices=prices)
    verdict = results.judge(CHANGE, records, [CHANGE], unit="dollars", prices=prices,
                            today=TODAY)
    assert "the card changed between them for m" in verdict["measures"]["usd"]["missing"][0]
    assert verdict["primary"]["measure"] == "tokens" and verdict["verdict"] == "better"
    assert verdict["basis"].startswith("tokens per measured row; dollars not compared")
    assert "usd: not computable" in results.render([verdict], "dollars")


def test_both_units_give_both_verdicts_and_the_dollars_lead(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    verdict = _judge(tmp_path, unit="both")
    assert sorted(verdict["measures"]) == ["tokens", "usd"]
    assert verdict["primary"]["measure"] == "usd"
    assert verdict["measures"]["tokens"]["verdict"] == "better"


def test_the_split_is_by_instant_and_a_straddling_dispatch_is_left_out(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    _log(tmp_path, "SAME-DAY", "2026-10-20", 10, 10_000, 10.0)        # ends 01:10 that day
    late = dict(CHANGE, effectiveFrom="2026-10-20T15:00:00Z")          # recorded at 15:00
    verdict = _judge(tmp_path, change=late)
    assert verdict["progress"]["closedLogs"] == 4                     # not counted as after
    straddle = dict(CHANGE, effectiveFrom="2026-10-20T01:05:00Z")
    assert _judge(tmp_path, change=straddle)["straddling"] == ["SAME-DAY"]


def test_an_undone_change_stops_its_after_side_at_the_undo(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    _side(tmp_path, "U", _days("2026-10-26", 4), 2000)                 # after the undo
    undo = {"id": "CH-002", "action": "undo", "undoes": "CH-001", "kind": "policy",
            "subject": "guards.retry", "effectiveFrom": "2026-10-25T12:00:00Z"}
    verdict = _judge(tmp_path, ledger=[CHANGE, undo])
    assert verdict["progress"]["closedLogs"] == 4 and verdict["verdict"].startswith("better")
    assert "(undone 2026-10-25)" in verdict["verdict"]
    assert not any("CH-002" in c for c in verdict["confounders"])     # not its own confounder


def test_a_figure_one_side_never_observed_is_not_a_trade_off(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    verdict = _judge(tmp_path)
    assert verdict["others"]["coldReturns"]["before"] is None and "coldReturns" not in \
        verdict["tradeOffs"]


def test_a_small_spread_between_baselines_is_not_a_range(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 11), 1000)
    _side(tmp_path, "C", _days("2026-10-17", 3), 980)
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    assert _judge(tmp_path)["verdict"] == "better"


def test_the_configured_threshold_is_used_and_shown(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 850)
    assert _judge(tmp_path)["verdict"] == "better"
    wide = _judge(tmp_path, no_effect=0.2)
    assert wide["verdict"] == "no clear effect" and "under 20%" in results.render([wide], "tokens",
                                                                                   why=True)


def test_unknown_minimum_keys_are_refused_by_policy_and_ignored_by_the_judge(tmp_path,
                                                                            isolated_home):
    from tools.governance import policy
    assert any("results.minimum" in p for p in policy.load(
        {"results": {"minimum": {"foo": 1}}}).validate())
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000)
    _side(tmp_path, "A", _days("2026-10-21", 4), 600)
    assert _judge(tmp_path, minimum={"foo": 99})["verdict"] == "better"


def test_a_change_scoped_to_one_host_leaves_the_others_out():
    def record(n, day, host, tokens):
        end = dt.datetime.fromisoformat(day + "T02:00:00+00:00")
        return {"dispatch": "D-%d" % n, "start": end - dt.timedelta(hours=1), "end": end,
                "day": end.date(), "rows": 10, "rowError": 0.1, "addedShare": 0.0,
                "waited": 0.0, "tiers": [], "hosts": [host], "tokens": tokens, "usd": None,
                "tokensKind": "measured", "usdKind": None, "source": "bound",
                "coldReturns": None}
    records = [record(n, d, "a", 10_000) for n, d in enumerate(_days("2026-10-06", 14))]
    records += [record(100 + n, d, "a", 5_000) for n, d in enumerate(_days("2026-10-21", 4))]
    records += [record(200 + n, d, "b", 50_000) for n, d in enumerate(_days("2026-10-21", 4))]
    scoped = dict(CHANGE, scope={"hosts": ["a"], "agents": []})
    verdict = results.judge(scoped, records, [scoped], unit="tokens", prices={"models": {}},
                            today=TODAY)
    assert verdict["progress"]["closedLogs"] == 4 and verdict["verdict"] == "better"


def test_a_lesson_is_judged_by_its_own_measure(tmp_path, isolated_home):
    _side(tmp_path, "B", _days("2026-10-06", 14), 1000, added=2)
    _side(tmp_path, "A", _days("2026-10-21", 4), 1000)
    lesson = dict(CHANGE, kind="lesson", subject=LESSON)
    verdict = _judge(tmp_path, change=lesson)
    assert verdict["primary"]["measure"] == "addedShare" and verdict["verdict"] == "better"


@pytest.mark.parametrize("value, ok", [
    ({"activeDays": 3, "closedLogs": 3, "measuredRows": 30}, True),
    ({"activeDays": 0}, False),
    ({"activeDays": "3"}, False),
])
def test_the_minimum_sample_policy_is_checked(value, ok):
    from tools.governance import policy
    problems = policy.load({"results": {"minimum": value}}).validate()
    assert (not any("results.minimum" in p for p in problems)) is ok


def test_the_results_command_reads_the_ledger_and_the_logs(project):
    import os, subprocess, sys
    from conftest import PLUGIN_ROOT
    preflight = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_preflight.py")
    cli = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_registry.py")
    assert subprocess.run([sys.executable, preflight, "--root", str(project), "--mode",
                           "create", "--authorize"], capture_output=True).returncode == 0
    done = subprocess.run([sys.executable, cli, "--root", str(project), "--actor",
                           "project-profile", "policy-set", "cost.units", "--value-json",
                           '"tokens"', "--apply"], capture_output=True, text=True,
                          encoding="utf-8", env=dict(os.environ))
    assert done.returncode == 0, done.stderr
    shown = subprocess.run([sys.executable, cli, "--root", str(project), "results", "--json"],
                           capture_output=True, text=True, encoding="utf-8",
                           env=dict(os.environ))
    assert shown.returncode == 0, shown.stderr
    [verdict] = json.loads(shown.stdout)["results"]
    assert verdict["change"] == "CH-001" and verdict["verdict"] == "not yet"
    kpis = subprocess.run([sys.executable, cli, "--root", str(project), "kpis", "--json"],
                          capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
    assert json.loads(kpis.stdout)["applied"] == [
        {"change": "CH-001", "subject": "cost.units", "kind": "policy", "verdict": "not yet"}]
    text = subprocess.run([sys.executable, cli, "--root", str(project), "kpis"],
                          capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))
    assert "applied — changes in force" in text.stdout and "CH-001" in text.stdout
