"""What work cost, in tokens and dollars, from a dated price catalogue.

A call is priced at the rate card in force on the day it was made
(``references/model-prices.json``, merged under the user's ``~/.virtuoso/prices.json``). A
model with no card has a dollar figure of *not computable*, naming the model — never an
approximation. Token counts are what the host reported: ``measured``. A dollar figure is
``measured`` when the call's day has a card, and ``estimated`` when the call predates the
model's first card (the rate on that day was not recorded).

Dollars are always "at API prices": on a subscription plan they measure the work, not the
bill. Savings come in three tiers that are never added together (:data:`TIERS`).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from . import install
from .providers.kpi import CONFIDENCE, ESTIMATED, KINDS, MEASURED

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOGUE = os.path.join(PLUGIN_ROOT, "references", "model-prices.json")
PER = 1_000_000

#: FIX: clear waste, removing it leaves the work unchanged. TRY: a likely saving that
#: changes what the agent does. TEST: a trade-off sized from the project's own runs.
TIERS = ("FIX", "TRY", "TEST")
_TIER_PREFIX = {"FIX": "", "TRY": "+", "TEST": "up to "}


def normal_model(model: str) -> str:
    """A model id as the catalogue keys it: without a ``[…]`` marker or a date suffix."""
    text = re.sub(r"\[[^\]]*\]$", "", (model or "").strip())
    return re.sub(r"-\d{8}$", "", text)


def _read(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def catalogue() -> dict:
    """The shipped price catalogue with the user's override merged over it: a model the
    user gives replaces the shipped entry; a provider the user gives replaces its policy."""
    shipped = _read(CATALOGUE)
    user = _read(os.path.join(install.state_dir(), "prices.json"))
    merged = dict(shipped)
    for key in ("models", "providers", "sources"):
        mine = shipped.get(key) if isinstance(shipped.get(key), dict) else {}
        theirs = user.get(key) if isinstance(user.get(key), dict) else {}  # a bad file adds none
        merged[key] = dict(mine, **theirs)
    return merged


@dataclass
class Price:
    """A dollar figure, or why there is none."""
    usd: float | None
    kind: str = MEASURED
    basis: str = ""
    missing: list[str] = field(default_factory=list)

    @property
    def computable(self) -> bool:
        return self.usd is not None


def _card(entry: dict, day: str) -> tuple[dict | None, bool]:
    """The card in force on ``day`` (YYYY-MM-DD) and whether it really was in force then
    (``False``: the day predates the first card)."""
    cards = sorted((c for c in entry.get("cards") or [] if isinstance(c, dict)),
                   key=lambda c: str(c.get("from") or ""))
    if not cards:
        return None, False
    current = [c for c in cards if str(c.get("from") or "") <= day]
    return (current[-1], True) if current else (cards[0], False)


def price(usage, model: str, day: str, prices: dict | None = None) -> Price:
    """What one call cost at API prices. ``usage`` is a :class:`hosts.Usage`."""
    prices = prices if prices is not None else catalogue()
    key = normal_model(model)
    entry = (prices.get("models") or {}).get(key)
    if not isinstance(entry, dict):
        return Price(None, missing=["a price card for model %s" % (key or "(none recorded)")])
    card, in_force = _card(entry, day or "")
    if card is None:
        return Price(None, missing=["a price card for model %s" % key])
    limit = card.get("contextLimit")
    if isinstance(limit, (int, float)) and usage.context > limit:
        return Price(None, missing=["a price for model %s above %d prompt tokens (the card "
                                    "covers prompts up to it)" % (key, limit)])
    long = card.get("longPrompt")
    if isinstance(long, dict) and usage.context > (long.get("over") or 0):
        card = dict(card, **long)
    policy = ((prices.get("providers") or {}).get(entry.get("provider")) or {})
    write_as_input = policy.get("cacheWrite") == "input"
    writes = (("cacheWrite5m", usage.cache_write_5m), ("cacheWrite1h", usage.cache_write_1h))
    if write_as_input:
        counted = [("input", usage.input + usage.cache_write_5m + usage.cache_write_1h
                    + usage.cache_write_no_lifetime)]
    elif usage.cache_write_no_lifetime:
        return Price(None, missing=["the cache lifetime of %d written tokens (model %s)"
                                    % (usage.cache_write_no_lifetime, key)])
    else:
        counted = [("input", usage.input)] + list(writes)
    counted += [("output", usage.output),
                ("cacheRead" if "cacheRead" in card else "input", usage.cache_read)]
    usd = 0.0
    for name, count in counted:
        if not count:
            continue
        try:
            rate = float(card[name])
        except (KeyError, TypeError, ValueError):
            return Price(None, missing=["the %s rate for model %s" % (name, key)])
        usd += count * rate
    usd /= PER
    source = ((prices.get("sources") or {}).get(entry.get("provider")) or {})
    review_by = str(card.get("reviewBy") or "")
    if not in_force:
        return Price(usd, ESTIMATED, "rate as published %s; the rate on %s was not recorded"
                     % (card.get("from"), day or "an unknown day"))
    if review_by and day and day > review_by:
        return Price(usd, ESTIMATED, "%s card from %s, published as holding to %s; the rate "
                     "on %s was not recorded" % (key, card.get("from"), review_by, day))
    return Price(usd, MEASURED, "%s card from %s (%s)" % (key, card.get("from"),
                                                           source.get("url", "")))


def price_calls(calls, prices: dict | None = None) -> tuple[float | None, str, list[str]]:
    """The dollar total of a list of :class:`hosts.Call`, its kind (``estimated`` if any
    call was), and what is missing for the calls that could not be priced (then ``None``)."""
    prices = prices if prices is not None else catalogue()
    total, kind, missing = 0.0, MEASURED, []
    for call in calls:
        if getattr(call, "unpriceable", ""):
            if call.unpriceable not in missing:
                missing.append(call.unpriceable)
            continue
        found = price(call.usage, call.model, (call.time or "")[:10], prices)
        if not found.computable:
            missing += [m for m in found.missing if m not in missing]
            continue
        total += found.usd
        if found.kind == ESTIMATED or getattr(call, "assumption", ""):
            kind = ESTIMATED
    return (None if missing else total), kind, missing


# --- units --------------------------------------------------------------------------------

UNITS = ("both", "tokens", "dollars")


def units(raw_policy: dict | None = None) -> str:
    """``both`` | ``tokens`` | ``dollars``: the project's own ``cost.units`` (``raw_policy``
    is the workspace layout's ``policy`` block as written, before defaults) when it sets
    one, else the user's default in ``~/.virtuoso/config.json``, else ``both``."""
    project = (raw_policy or {}).get("cost") if isinstance(raw_policy, dict) else None
    if isinstance(project, dict) and project.get("units") in UNITS:
        return project["units"]
    user = _read(os.path.join(install.state_dir(), "config.json")).get("cost")
    value = user.get("units") if isinstance(user, dict) else None
    return value if value in UNITS else "both"


def tokens_text(count: int) -> str:
    if count >= 1_000_000:
        return "%.1fM tokens" % (count / 1_000_000)
    if count >= 1000:
        return "%dK tokens" % round(count / 1000)
    return "%d tokens" % count


def amount(tokens: int, usd: float | None, unit: str = "both") -> str:
    """A cost as the units choose: ``$1.30 (162K tokens)``, ``162K tokens`` or ``$1.30``.
    A dollar figure that is not computable says so."""
    if usd is None:
        dollars = "$ not computable"
    elif 0 < usd < 0.005:
        dollars = "<$0.01"
    else:
        dollars = "$%.2f" % usd
    if unit == "tokens":
        return tokens_text(tokens)
    if unit == "dollars":
        return dollars
    return "%s (%s)" % (dollars, tokens_text(tokens))


# --- findings that carry a cost -------------------------------------------------------------

@dataclass
class Finding:
    """A finding that carries a cost or a saving, in the one format every reporter uses."""
    tier: str
    title: str
    confidence: str
    happened: str
    matters: str
    todo: str
    now: str
    after: str
    rows: int = 0
    share: str = ""
    kind: str = MEASURED

    def __post_init__(self):
        if self.tier not in TIERS:
            raise ValueError("tier %r is not one of %s" % (self.tier, ", ".join(TIERS)))
        if self.confidence not in CONFIDENCE:
            raise ValueError("confidence %r is a level, one of %s, never a percentage"
                             % (self.confidence, ", ".join(CONFIDENCE)))
        if self.kind not in KINDS:
            raise ValueError("kind %r is not one of %s" % (self.kind, ", ".join(KINDS)))

    def figure(self, text: str) -> str:
        return _TIER_PREFIX[self.tier] + text

    def render(self) -> str:
        scope = ", ".join(p for p in ("%d rows" % self.rows if self.rows else "",
                                       "%s of the dispatch" % self.share if self.share else "")
                          if p)
        return "\n".join([
            "%-5s %s · %s" % (self.tier, self.title, self.confidence),
            "        What happened   %s" % self.happened,
            "        Why it matters  %s" % self.matters,
            "        What to do      %s" % self.todo,
            "        now %s  ->  after %s%s   %s" % (self.now, self.figure(self.after),
                                                    "   (%s)" % scope if scope else "",
                                                    self.kind)])

    def register_lines(self) -> list[str]:
        """The lines a Findings-register entry adds beside its usual fields."""
        return ["**Tier:** %s" % self.tier, "**Confidence:** %s" % self.confidence,
                "**Kind:** %s" % self.kind,
                "**Figure:** now %s -> after %s" % (self.now, self.figure(self.after))]


def total_within_tier(findings: list[Finding], tier: str, values: dict[str, float]) -> float:
    """A saving total, only ever within one tier: ``values`` maps a finding title to its
    saving; findings of another tier are refused rather than added in."""
    other = [f.title for f in findings if f.tier != tier]
    if other:
        raise ValueError("savings of different tiers are never added: %s" % ", ".join(other))
    return sum(values[f.title] for f in findings)
