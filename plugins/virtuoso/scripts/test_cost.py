"""Figures with their kind and basis; prices from a dated catalogue; units; savings tiers and
the one finding format."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from tools.governance import cost, hosts
from tools.governance.providers import kpi


# --- figures carry their kind ------------------------------------------------------------

def test_a_figure_carries_its_kind_and_its_calculation():
    metric = kpi.Metric("row-error", 0.2, basis="median of 12 rows",
                        assumptions=["a parallel row overlaps"], confidence="high")
    data = metric.as_dict()
    assert (data["kind"], data["basis"], data["confidence"]) == ("measured", "median of 12 rows",
                                                                 "high")
    assert "unit" not in data
    assert metric.line().split()[-2:] == ["measured,", "high"]
    why = metric.line(why=True)
    assert "How this was calculated: median of 12 rows" in why
    assert "Assumption: a parallel row overlaps" in why
    gap = kpi.Metric("x", computable=False, missing_inputs=["a log"]).as_dict()
    assert gap["note"] == "not computable" and "kind" not in gap


@pytest.mark.parametrize("kind, records, changes_tokens, level", [
    ("measured", 12, False, "high"),
    ("measured", 12, True, "likely"),
    ("measured", 3, False, "likely"),
    ("measured", 2, False, "possible"),
    ("inferred", 10, False, "likely"),
    ("inferred", 9, False, "possible"),
    ("estimated", 50, False, "possible"),
])
def test_confidence_is_a_level_set_by_kind_and_sample(kind, records, changes_tokens, level):
    assert kpi.confidence_for(kind, records, changes_tokens) == level


# --- the price catalogue ------------------------------------------------------------------

CATALOGUE = json.loads((Path(PLUGIN_ROOT) / "references" / "model-prices.json")
                       .read_text(encoding="utf-8"))


def test_the_catalogue_cites_its_pages_and_pins_one_published_rate():
    fetched = {s["fetched"] for s in CATALOGUE["sources"].values()}
    first_cards = {sorted(c["from"] for c in m["cards"])[0] for m in CATALOGUE["models"].values()}
    assert first_cards <= fetched                     # no card older than the page it came from
    card = CATALOGUE["models"]["claude-opus-5-5"]["cards"][0]
    # The one pinned boundary: the dated copy in fixtures/hosts/prices/ holds the same row.
    assert (card["input"], card["cacheWrite5m"], card["cacheWrite1h"], card["cacheRead"],
            card["output"]) == (4, 5, 8, 0.2, 20)
    page = (Path(PLUGIN_ROOT) / "scripts" / "fixtures" / "hosts" / "prices"
            / "anthropic.2026-10-22.md").read_text(encoding="utf-8")
    assert "| Claude Opus 5.5 | 4 | 5 | 8 | 0.20 | 20 |" in page  # validate-ok: the page row


@pytest.mark.parametrize("model, key", [
    ("claude-opus-5-5", "claude-opus-5-5"),
    ("claude-opus-5-5[1m]", "claude-opus-5-5"),
    ("claude-haiku-4-5-20251001", "claude-haiku-4-5"),
    ("gpt-6.1-sol", "gpt-6.1-sol"),
])
def test_model_ids_are_read_as_the_catalogue_keys_them(model, key):
    assert cost.normal_model(model) == key and key in CATALOGUE["models"]


def test_a_call_is_priced_by_kind_of_token():
    usage = hosts.Usage(input=1_000_000, output=100_000, cache_read=2_000_000,
                        cache_write_5m=100_000, cache_write_1h=50_000)
    found = cost.price(usage, "claude-opus-5-5", "2026-10-23", CATALOGUE)
    # 4 + 0.1*20 + 2*0.2 + 0.1*5 + 0.05*8
    assert found.usd == pytest.approx(4 + 2 + 0.4 + 0.5 + 0.4)
    assert found.kind == "measured" and "card from 2026-10-22" in found.basis


def test_a_call_before_the_first_card_is_estimated_never_measured():
    found = cost.price(hosts.Usage(output=1_000_000), "claude-opus-5-5", "2026-10-12", CATALOGUE)
    assert found.usd == pytest.approx(20) and found.kind == "estimated"
    assert "the rate on 2026-10-12 was not recorded" in found.basis


def test_a_model_with_no_card_is_not_computable_and_named():
    found = cost.price(hosts.Usage(input=10), "made-up-model-9", "2026-10-23", CATALOGUE)
    assert not found.computable and found.missing == ["a price card for model made-up-model-9"]


def test_cached_input_on_the_rollout_host_is_not_charged_twice():
    # A rollout record: input_tokens 30126 of which 13440 cached, 63 output (gpt-6.1-sol).
    from tools.governance.hosts import codex
    record = {"type": "token_usage_record", "payload": {"response_id": "r1", "usage": {
        "input_tokens": 30126, "cached_input_tokens": 13440, "cache_write_input_tokens": 0,
        "output_tokens": 63}}}
    [call] = codex._facts([{"type": "turn_context", "payload": {"model": "gpt-6.1-sol"}},
                           record]).calls
    found = cost.price(call.usage, call.model, "2026-10-23", CATALOGUE)
    assert found.usd == pytest.approx((16686 * 2 + 13440 * 0.1 + 63 * 10) / 1_000_000)


def test_a_long_prompt_is_priced_at_its_higher_card():
    short = cost.price(hosts.Usage(input=100_000), "claude-haiku-5-5", "2026-10-23", CATALOGUE)
    long = cost.price(hosts.Usage(input=100_001), "claude-haiku-5-5", "2026-10-23", CATALOGUE)
    assert short.usd == pytest.approx(0.01) and long.usd == pytest.approx(100_001 * 0.5 / 1e6)


def test_the_users_price_file_replaces_a_model(isolated_home):
    path = Path(isolated_home) / ".virtuoso" / "prices.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"models": {"claude-opus-5-5": {"provider": "anthropic",
                    "cards": [{"from": "2026-01-01", "input": 1, "output": 1}]}}}),
                    encoding="utf-8")
    merged = cost.catalogue()
    assert merged["models"]["claude-opus-5-5"]["cards"][0]["input"] == 1
    assert "claude-sonnet-5-5" in merged["models"]                # the rest is kept


def test_a_list_of_calls_is_estimated_if_any_call_is_and_gaps_are_named():
    calls = [hosts.Call("a", "2026-10-23T01:00:00Z", "claude-opus-5-5", hosts.Usage(output=1000)),
             hosts.Call("b", "2026-10-10T01:00:00Z", "claude-opus-5-5", hosts.Usage(output=1000))]
    total, kind, missing = cost.price_calls(calls, CATALOGUE)
    assert total == pytest.approx(0.04) and kind == "estimated" and missing == []
    total, _kind, missing = cost.price_calls(
        calls + [hosts.Call("c", "", "nobody-1", hosts.Usage(input=1))], CATALOGUE)
    assert total is None and missing == ["a price card for model nobody-1"]


# --- units --------------------------------------------------------------------------------

def test_units_come_from_the_project_then_the_user_then_both(isolated_home):
    assert cost.units(None) == "both"
    config = Path(isolated_home) / ".virtuoso" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"cost": {"units": "tokens"}}), encoding="utf-8")
    assert cost.units({}) == "tokens"
    assert cost.units({"cost": {"units": "dollars"}}) == "dollars"
    assert cost.units({"cost": {"units": "pounds"}}) == "tokens"     # not a unit: ignored


@pytest.mark.parametrize("tokens, usd, unit, text", [
    (162_000, 1.3, "both", "$1.30 (162K tokens)"),
    (162_000, 1.3, "tokens", "162K tokens"),
    (162_000, 1.3, "dollars", "$1.30"),
    (2_400_000, None, "both", "$ not computable (2.4M tokens)"),
    (999, 0.004, "both", "<$0.01 (999 tokens)"),
    (0, 0.0, "dollars", "$0.00"),
])
def test_an_amount_is_shown_in_the_chosen_units(tokens, usd, unit, text):
    assert cost.amount(tokens, usd, unit) == text


def test_the_cost_units_policy_value_is_checked():
    from tools.governance import policy
    assert policy.load({}).get("cost.units") == "both"
    assert any("cost.units" in p for p in policy.load({"cost": {"units": "pounds"}}).validate())


# --- the cost command ---------------------------------------------------------------------

CC_RUN2 = (Path(PLUGIN_ROOT) / "scripts" / "fixtures" / "hosts" / "claude_code" / "transcripts"
           / "capture" / "22222222-2222-4222-8222-222222222222.jsonl")


def _log(directory: Path, dispatch: str, start: str, end: str, rows=((7, "capture probe"),)):
    events = [{"event": "open", "at": start, "rows": [
        {"id": n, "title": t, "predicted": 5, "basis": "estimated"} for n, t in rows]}]
    for n, _title in rows:
        events += [{"event": "start", "row": n, "at": start},
                   {"event": "end", "row": n, "at": end, "result": "done", "evidence": "x"}]
    (directory / ("Timing.%s.jsonl" % dispatch)).write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_a_bound_dispatch_prices_its_rows_and_its_orchestration_apart(tmp_path, isolated_home):
    from tools.governance import costreport
    _log(tmp_path, "X-1", "2026-10-23T01:18:00Z", "2026-10-23T01:20:00Z")
    hosts.record_binding("X-1", "22222222-2222-4222-8222-222222222222", str(CC_RUN2),
                         "claude-code")
    report = costreport.dispatch_cost(str(tmp_path), "X-1", CATALOGUE)
    row = report["rows"][0]["cost"]
    assert (report["source"], report["host"]) == ("bound", ["claude-code"])
    # The row-7 subagent's three calls (fixture usage), apart from the top-level session's.
    assert row["calls"] == 3 and row["usage"]["output"] == 255
    assert report["orchestration"]["calls"] == 3 and report["orchestration"]["usage"][
        "output"] == 347
    assert report["total"]["tokens"] == row["tokens"] + report["orchestration"]["tokens"]
    assert report["total"]["usdKind"] == "measured" and report["total"]["usd"] > 0
    text = costreport.render_dispatch(report, "both")
    assert "orchestration" in text and "measured" in text and "guard catches: not computable" \
        in text
    assert "How this was calculated" in costreport.render_dispatch(report, "tokens", why=True)


def test_calls_outside_the_time_log_are_not_the_dispatchs(tmp_path, isolated_home):
    from tools.governance import costreport
    _log(tmp_path, "X-2", "2026-10-23T02:00:00Z", "2026-10-23T03:00:00Z")
    hosts.record_binding("X-2", "22222222-2222-4222-8222-222222222222", str(CC_RUN2),
                         "claude-code")
    report = costreport.dispatch_cost(str(tmp_path), "X-2", CATALOGUE)
    assert report["total"]["calls"] == 0 and report["total"]["tokens"] == 0


def test_an_unbound_dispatch_names_the_missing_binding_and_never_guesses(tmp_path, isolated_home):
    from tools.governance import costreport
    _log(tmp_path, "X-3", "2026-10-23T01:18:00Z", "2026-10-23T01:20:00Z")
    report = costreport.dispatch_cost(str(tmp_path), "X-3", CATALOGUE)
    assert report["missing"] and "a dispatch binding for X-3" in report["missing"][0]
    assert "total" not in report
    listed = costreport.recent(str(tmp_path), 10, CATALOGUE)
    assert listed["dispatches"][0]["tokens"] is None and listed["topShare"] is None


def test_a_backfilled_log_reports_its_dispatch_level_cost(tmp_path, isolated_home):
    from tools.governance import costreport
    _log(tmp_path, "X-4", "2026-10-10T01:00:00Z", "2026-10-10T02:00:00Z")
    with open(tmp_path / "Timing.X-4.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"event": "cost", "source": "backfilled",
                                 "at": "2026-10-23T00:00:00Z",
                                 "orchestration": {"tokens": 100, "usd": 0.5,
                                                   "usdKind": "estimated"},
                                 "total": {"tokens": 400, "usd": 2.0,
                                           "usdKind": "estimated"}}) + "\n")
    report = costreport.dispatch_cost(str(tmp_path), "X-4", CATALOGUE)
    assert report["source"] == "backfilled" and report["total"]["tokens"] == 400
    assert not report["perRow"]["computable"]
    listed = costreport.recent(str(tmp_path), 10, CATALOGUE)
    assert listed["dispatches"][0]["tokens"] == 400 and listed["topShare"] == 1.0


def test_a_cold_return_and_a_model_change_are_found_between_calls():
    from tools.governance import costreport
    from tools.governance.hosts import claude_code
    calls = [hosts.Call("a", "2026-10-23T01:00:00.000Z", "claude-opus-5-5",
                        hosts.Usage(cache_write_1h=50_000)),
             hosts.Call("b", "2026-10-23T02:10:00.000Z", "claude-opus-5-5",
                        hosts.Usage(cache_write_1h=180_000)),
             hosts.Call("c", "2026-10-23T03:20:00.000Z", "claude-opus-5-5",   # idle, but warm:
                        hosts.Usage(cache_read=900_000, cache_write_1h=100)),  # it read more
             hosts.Call("d", "2026-10-23T03:21:00.000Z", "claude-sonnet-5-5[1m]",
                        hosts.Usage(cache_write_1h=170_000)),
             hosts.Call("e", "2026-10-23T03:22:00.000Z", "claude-sonnet-5-5",  # same model
                        hosts.Usage(cache_read=170_000))]
    facts = hosts.TranscriptFacts(calls=calls)
    [cold] = costreport.cold_returns(calls, claude_code.ADAPTER, facts, CATALOGUE)
    assert (cold["idleMinutes"], cold["tokens"], cold["kind"]) == (70, 180_000, "measured")
    assert cold["usd"] == pytest.approx(180_000 * (8 - 0.2) / 1e6)      # write over read
    [reload] = costreport.model_reloads(calls, CATALOGUE)
    assert (reload["from"], reload["to"], reload["tokens"]) == ("claude-opus-5-5",
                                                                "claude-sonnet-5-5", 170_000)
    assert reload["usd"] == pytest.approx(170_000 * (4 - 0.1) / 1e6) and reload["kind"] == \
        "measured"


def test_a_transcript_no_longer_on_disk_is_named_never_read_as_zero(tmp_path, isolated_home):
    from tools.governance import costreport
    _log(tmp_path, "X-11", "2026-10-23T01:18:00Z", "2026-10-23T01:20:00Z")
    hosts.record_binding("X-11", "gone", str(tmp_path / "gone.jsonl"), "claude-code")
    report = costreport.dispatch_cost(str(tmp_path), "X-11", CATALOGUE)
    assert "total" not in report and "no longer on disk" in report["missing"][0]
    assert "no longer on disk" in costreport.render_dispatch(report, "both")


def test_a_missing_price_is_named_in_the_text(tmp_path, isolated_home):
    from tools.governance import costreport
    _log(tmp_path, "X-12", "2026-10-23T01:18:00Z", "2026-10-23T01:20:00Z")
    hosts.record_binding("X-12", "22222222-2222-4222-8222-222222222222", str(CC_RUN2),
                         "claude-code")
    report = costreport.dispatch_cost(str(tmp_path), "X-12", {"models": {}})
    text = costreport.render_dispatch(report, "both")
    assert "$ not computable" in text and "missing: a price card for model claude-opus-5-5" \
        in text


def test_a_rate_the_card_lacks_is_never_priced_at_zero():
    card = {"models": {"m-1": {"provider": "p", "cards": [{"from": "2026-01-01", "input": 1}]},
                       "m-2": {"provider": "p", "cards": [{"from": "2026-01-01", "input": "x",
                                                           "output": 1}]}}}
    found = cost.price(hosts.Usage(input=10, output=10), "m-1", "2026-10-23", card)
    assert not found.computable and found.missing == ["the output rate for model m-1"]
    assert cost.price(hosts.Usage(input=10), "m-1", "2026-10-23", card).computable
    bad = cost.price(hosts.Usage(input=10), "m-2", "2026-10-23", card)
    assert not bad.computable and bad.missing == ["the input rate for model m-2"]


def test_a_prompt_above_the_cards_limit_is_not_computable():
    found = cost.price(hosts.Usage(input=300_000), "gpt-5.4", "2026-10-23", CATALOGUE)
    assert not found.computable and "above 272000 prompt tokens" in found.missing[0]
    assert cost.price(hosts.Usage(input=272_000), "gpt-5.4", "2026-10-23", CATALOGUE).computable


def test_a_promotional_card_past_its_review_date_is_estimated():
    usage = hosts.Usage(input=1000)
    assert cost.price(usage, "gpt-5.6-sol", "2026-11-21", CATALOGUE).kind == "measured"
    late = cost.price(usage, "gpt-5.6-sol", "2026-11-22", CATALOGUE)
    assert late.kind == "estimated" and "holding to 2026-11-21" in late.basis


def test_a_call_is_priced_at_the_card_in_force_on_its_day():
    two = {"models": {"m": {"provider": "p", "cards": [
        {"from": "2026-11-01", "input": 2, "output": 0}, {"from": "2026-10-01", "input": 1,
                                                          "output": 0}]}}}
    day = lambda d: cost.price(hosts.Usage(input=1_000_000), "m", d, two)
    assert (day("2026-10-31").usd, day("2026-11-01").usd, day("2026-12-01").usd) == (1, 2, 2)
    assert day("2026-09-30").kind == "estimated" and day("2026-10-01").kind == "measured"


def test_an_earlier_card_from_the_user_makes_october_calls_measured(isolated_home):
    path = Path(isolated_home) / ".virtuoso" / "prices.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"models": {"claude-opus-5-5": {"provider": "anthropic",
                    "cards": [{"from": "2026-10-01", "input": 4, "output": 20, "cacheRead": 0.2,
                               "cacheWrite5m": 5, "cacheWrite1h": 8}]}}}), encoding="utf-8")
    found = cost.price(hosts.Usage(output=1_000_000), "claude-opus-5-5", "2026-10-12")
    assert found.kind == "measured" and found.usd == pytest.approx(20)


def test_a_malformed_price_file_adds_nothing_and_breaks_nothing(isolated_home):
    path = Path(isolated_home) / ".virtuoso" / "prices.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"models": ["not", "a", "map"], "sources": 7}), encoding="utf-8")
    assert "claude-opus-5-5" in cost.catalogue()["models"]
    path.write_text("{broken", encoding="utf-8")
    assert "claude-opus-5-5" in cost.catalogue()["models"]


def test_a_cache_write_on_the_rollout_host_is_billed_as_input_and_estimated():
    from tools.governance.hosts import codex
    meta = {"type": "session_meta", "payload": {"id": "t", "cli_version": "0.163.0"}}
    context = {"type": "turn_context", "payload": {"model": "gpt-6.1-sol"}}
    def call(usage):
        return codex._facts([meta, context, {"type": "token_usage_record", "payload": {
            "response_id": "r1", "usage": usage}}]).calls[0]
    written = call({"input_tokens": 10_000, "cached_input_tokens": 2_000,
                    "cache_write_input_tokens": 3_000, "output_tokens": 0})
    assert written.usage.as_tuple() == (5_000, 0, 2_000, 0, 0, 3_000)
    usd, kind, missing = cost.price_calls([written], CATALOGUE)
    assert usd == pytest.approx((8_000 * 2 + 2_000 * 0.1) / 1e6)      # (input − cached) × input
    assert kind == "estimated" and "not observed nonzero on" in written.assumption
    assert written.assumption.endswith(" 0.163.0")
    broken = call({"input_tokens": 1_000, "cached_input_tokens": 900,
                   "cache_write_input_tokens": 300, "output_tokens": 5})
    usd, _kind, missing = cost.price_calls([broken], CATALOGUE)
    assert usd is None and "input_tokens is below" in missing[0] and "0.163.0" in missing[0]
    assert broken.usage.output == 5                                     # tokens still reported


def test_a_cost_event_never_stretches_the_window(tmp_path):
    from tools.governance import costreport
    events = [{"event": "open", "at": "2026-10-10T00:30:00Z"},
              {"event": "start", "at": "2026-10-10T01:00:00Z"},
              {"event": "end", "at": "2026-10-10T02:00:00Z"},
              {"event": "confirm", "at": "2026-10-10T03:00:00Z"},     # a ruling, made later
              {"event": "park", "at": "2026-10-10T03:10:00Z"},
              {"event": "cost", "at": "2026-12-01T00:00:00Z"}]
    assert costreport.window(events) == ("2026-10-10T01:00:00Z", "2026-10-10T02:00:00Z")


def test_a_session_moved_to_another_host_is_read_by_its_own_adapter(tmp_path, isolated_home):
    from tools.governance import costreport
    cx = (Path(PLUGIN_ROOT) / "scripts" / "fixtures" / "hosts" / "codex" / "sessions" / "2026"
          / "10" / "22" / "rollout-2026-10-22T20-18-05-22222222-2222-7222-8222-222222222222.jsonl")
    _log(tmp_path, "X-13", "2026-10-22T00:00:00Z", "2026-10-23T23:00:00Z")
    hosts.record_binding("X-13", "22222222-2222-4222-8222-222222222222", str(CC_RUN2),
                         "claude-code")
    hosts.record_binding("X-13", "22222222-2222-7222-8222-222222222222", str(cx), "codex")
    report = costreport.dispatch_cost(str(tmp_path), "X-13", CATALOGUE)
    assert report["host"] == ["claude-code", "codex"]
    assert report["total"]["calls"] == 3 + 3 + 3                # both sessions, each host's
    assert report["total"]["usage"]["output"] == 347 + 255 + (63 + 24 + 24)


def test_an_open_log_counts_on_and_says_so(tmp_path, isolated_home):
    from tools.governance import costreport
    (tmp_path / "Timing.X-14.jsonl").write_text(json.dumps(
        {"event": "open", "at": "2026-10-23T01:18:00Z", "rows": [
            {"id": 7, "title": "probe", "predicted": 5, "basis": "estimated"}]}) + "\n",
        encoding="utf-8")
    hosts.record_binding("X-14", "22222222-2222-4222-8222-222222222222", str(CC_RUN2),
                         "claude-code")
    report = costreport.dispatch_cost(str(tmp_path), "X-14", CATALOGUE)
    assert report["window"] == "open" and report["total"]["kind"] == "estimated"
    assert "still open" in costreport.render_dispatch(report, "both")


def test_recent_ranks_by_the_shown_unit_and_refuses_a_bad_count(tmp_path, isolated_home):
    from tools.governance import costreport
    for n, (tokens, usd) in enumerate(((100, 9.0), (900, 1.0)), 1):
        _log(tmp_path, "Y-%d" % n, "2026-10-1%dT01:00:00Z" % n, "2026-10-1%dT02:00:00Z" % n)
        with open(tmp_path / ("Timing.Y-%d.jsonl" % n), "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": "cost", "source": "backfilled", "at": "x",
                                     "total": {"tokens": tokens, "usd": usd,
                                               "usdKind": "measured"}}) + "\n")
    assert [e["dispatch"] for e in costreport.recent(str(tmp_path), unit="dollars")[
        "dispatches"]] == ["Y-1", "Y-2"]
    by_tokens = costreport.recent(str(tmp_path), unit="tokens")
    assert [e["dispatch"] for e in by_tokens["dispatches"]] == ["Y-2", "Y-1"]
    assert by_tokens["rankedBy"] == "tokens"
    with pytest.raises(ValueError):
        costreport.recent(str(tmp_path), 0)


def test_a_row_no_subagent_named_points_at_orchestration(tmp_path, isolated_home):
    from tools.governance import costreport
    _log(tmp_path, "X-15", "2026-10-23T01:18:00Z", "2026-10-23T01:20:00Z",
         rows=((7, "probe"), (8, "inline")))
    hosts.record_binding("X-15", "22222222-2222-4222-8222-222222222222", str(CC_RUN2),
                         "claude-code")
    report = costreport.dispatch_cost(str(tmp_path), "X-15", CATALOGUE)
    inline = next(r for r in report["rows"] if r["id"] == 8)
    assert inline["cost"] is None and "in orchestration" in inline["costNote"]
    assert next(r for r in report["rows"] if r["id"] == 7)["taskKind"] == ""


def test_a_spawn_naming_two_rows_is_flagged_ambiguous():
    assert hosts.spawn_row_detail("row 5 — x", "row_6_x") == (None, True)
    assert hosts.spawn_row_detail("review", "probe") == (None, False)
    assert hosts.spawn_row_detail("row 5 — x", "row_5_x") == (5, False)


def test_a_finding_takes_only_levels_and_kinds():
    with pytest.raises(ValueError, match="never a percentage"):
        cost.Finding("FIX", "t", "85%", "", "", "", "", "")
    with pytest.raises(ValueError):
        cost.Finding("FIX", "t", "high", "", "", "", "", "", kind="guessed")


def test_the_cost_command_takes_why_and_refuses_a_bad_count(workspace_root):
    import subprocess, sys
    script = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_registry.py")
    why = subprocess.run([sys.executable, script, "--root", str(workspace_root), "cost",
                          "--why"], capture_output=True, text=True, encoding="utf-8")
    assert why.returncode == 0 and "How this was calculated" in why.stdout
    bad = subprocess.run([sys.executable, script, "--root", str(workspace_root), "cost",
                          "--last", "0"], capture_output=True, text=True, encoding="utf-8")
    assert bad.returncode == 2 and "1 or more" in bad.stderr


def test_the_cost_command_runs_read_only(workspace_root):
    import subprocess, sys
    before = sorted(p.relative_to(workspace_root) for p in workspace_root.rglob("*"))
    done = subprocess.run([sys.executable, str(Path(PLUGIN_ROOT) / "scripts" /
                           "virtuoso_registry.py"), "--root", str(workspace_root), "cost",
                           "--json"], capture_output=True, text=True, encoding="utf-8")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["units"] == "both"
    assert sorted(p.relative_to(workspace_root) for p in workspace_root.rglob("*")) == before


@pytest.fixture
def workspace_root(project):
    import subprocess, sys
    made = subprocess.run([sys.executable, str(Path(PLUGIN_ROOT) / "scripts" /
                           "virtuoso_preflight.py"), "--root", str(project), "--mode", "create",
                           "--authorize"], capture_output=True, text=True, encoding="utf-8")
    assert made.returncode == 0, made.stdout + made.stderr
    return project


# --- tiers and the finding format ---------------------------------------------------------

def test_a_finding_has_the_one_format_and_its_tier_marks_the_figure():
    finding = cost.Finding("TRY", "Cold return mid-dispatch", "likely",
                           "Idle 2h 10m, then 180K tokens re-read", "Paid once more",
                           "Paste the /compact line", "$1.10", "$0.20", rows=3, share="12%")
    text = finding.render().splitlines()
    assert text[0] == "TRY   Cold return mid-dispatch · likely"
    assert text[1].strip().startswith("What happened") and text[3].strip().startswith(
        "What to do")
    assert "now $1.10  ->  after +$0.20   (3 rows, 12% of the dispatch)   measured" in text[4]
    assert finding.register_lines()[0] == "**Tier:** TRY"
    assert cost.Finding("TEST", "t", "possible", "", "", "", "a", "b").figure("$1") == "up to $1"
    with pytest.raises(ValueError):
        cost.Finding("MAYBE", "t", "possible", "", "", "", "a", "b")


def test_savings_of_different_tiers_are_never_added():
    fix = cost.Finding("FIX", "a", "high", "", "", "", "", "")
    fix2 = cost.Finding("FIX", "b", "high", "", "", "", "", "")
    test = cost.Finding("TEST", "c", "possible", "", "", "", "", "")
    assert cost.total_within_tier([fix, fix2], "FIX", {"a": 1.0, "b": 2.0}) == 3.0
    with pytest.raises(ValueError, match="never added"):
        cost.total_within_tier([fix, test], "FIX", {"a": 1.0, "c": 2.0})
