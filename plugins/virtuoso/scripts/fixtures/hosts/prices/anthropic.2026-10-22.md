# Anthropic API rates — dated copy

- Source: https://platform.claude.com/docs/en/about-claude/pricing (redirected from
  docs.claude.com/en/docs/about-claude/pricing)
- Fetched: 2026-10-22. The page carries no last-updated date.
- Scope: the *Model pricing* table only (USD per million tokens, standard global routing).
  Modifiers not copied: batch discount, US-only inference (1.1x), fast mode, server-tool fees.

| Model | Base input | 5m cache write | 1h cache write | Cache hit / refresh | Output |
|---|---|---|---|---|---|
| Claude Fable 5.1 | 10 | 12.50 | 20 | 0.25 | 50 |
| Claude Mythos 5.1 | 10 | 12.50 | 20 | 0.25 | 50 |
| Claude Fable 5 | 10 | 12.50 | 20 | 1 | 50 |
| Claude Mythos 5 | 10 | 12.50 | 20 | 1 | 50 |
| Claude Opus 5.5 | 4 | 5 | 8 | 0.20 | 20 |
| Claude Opus 5 | 5 | 6.25 | 10 | 0.50 | 25 |
| Claude Opus 4.8 | 5 | 6.25 | 10 | 0.50 | 25 |
| Claude Opus 4.7 | 5 | 6.25 | 10 | 0.50 | 25 |
| Claude Opus 4.6 | 5 | 6.25 | 10 | 0.50 | 25 |
| Claude Opus 4.5 | 5 | 6.25 | 10 | 0.50 | 25 |
| Claude Opus 4.1 | 15 | 18.75 | 30 | 1.50 | 75 |
| Claude Opus 4 | 15 | 18.75 | 30 | 1.50 | 75 |
| Claude Sonnet 5.5 | 2 | 2.50 | 4 | 0.10 | 10 |
| Claude Sonnet 5 | 2 | 2.50 | 4 | 0.20 | 10 |
| Claude Sonnet 4.6 | 3 | 3.75 | 6 | 0.30 | 15 |
| Claude Sonnet 4.5 | 3 | 3.75 | 6 | 0.30 | 15 |
| Claude Sonnet 4 | 3 | 3.75 | 6 | 0.30 | 15 |
| Claude Haiku 5.5 (prompt ≤ 100,000 tokens) | 0.10 | 0.125 | 0.20 | 0.01 | 0.50 |
| Claude Haiku 5.5 (prompt > 100,000 tokens) | 0.50 | 0.625 | 1 | 0.05 | 2.50 |
| Claude Haiku 4.5 | 1 | 1.25 | 2 | 0.10 | 5 |
| Claude Haiku 3.5 | 0.80 | 1 | 1.60 | 0.08 | 4 |

Rules stated on the page that a price card must carry:

- Cache writes: 5-minute = 1.25x base input; 1-hour = 2x base input. Cache hit = 0.1x base
  input, except 0.025x (Fable 5.1, Mythos 5.1) and 0.05x (Opus 5.5, Sonnet 5.5).
- Sonnet 5's $2 / $10 is the standard price (the scheduled 2026-09-01 increase did not occur).
- Claude 4.6 and later (except Haiku 5.5) bill the full 1M context at standard rates. Haiku 5.5
  bills a request whose prompt (input + cache reads + cache writes) exceeds 100,000 tokens at
  the higher row, per request.
