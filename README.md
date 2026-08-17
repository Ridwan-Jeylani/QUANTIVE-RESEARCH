# QUANTIVE RESEARCH

Systematic crypto trading research. Two strategies that survived validation, published
as **daily return streams you can verify yourself** rather than as claims.

> ## ⭐ QUADRANT: 6.07% per month at a −9.95% maximum drawdown
>
> **MAR 7.35 · Sharpe 3.58 · 79% of months positive · 6.5 years · net of all costs**
>
> $473,414 withdrawn from a $100,000 base. Reproducible in one command from the
> published data — see **[quadrant/](quadrant/)**.

```bash
pip install pandas numpy
python verify.py
```

`verify.py` reads only the published CSVs and recomputes every headline figure —
Sharpe, Sortino, drawdown, MAR, year-by-year. It does not import any strategy code.
**If the tables below disagree with its output, trust the script.**

---

## The two strategies

| | [QUADRANT](quadrant/) | [VWAP-Z Trend Impulse](vwap-z-trend-impulse/) |
|---|---|---|
| Type | Cross-sectional multi-horizon trend | Single-asset intraday momentum |
| Universe | Top 8 perps by dollar volume (point-in-time) | BTC perp 1H (+ ETH transfer test) |
| Period | 2020-02 → 2026-07 (6.5y) | 2021-06 → 2026-06 (5.0y) |
| Total R | +1204.5 | +557.9 |
| Sharpe | 3.49 | 2.59 |
| Max DD | **−9.95%** (−30.6 R) | **−5.25%** (−21.0 R) |
| MAR | **7.35** | 5.32 |
| Positive years | 7 / 7 | 6 / 6 |
| **Return/month** | **6.07% mean** · 3.00% median | 2.29% mean · 2.29% median |
| Risk per trade | 0.4073% | 0.25% |

Results are stated in **R** — multiples of the risk taken per trade. R is
size-independent, so it can't be inflated by leverage or compounding. Percentage
returns depend entirely on position sizing; see each strategy's sizing section.

Percentages are stated at each strategy's documented risk setting, and **the two are
not the same sizing** — QUADRANT at **0.4073%** per trade with a drawdown throttle and
monthly profit sweep (its adopted live configuration), VWAP-Z at **0.25%** flat (its
Monte Carlo sizing, deliberately more conservative). Compare the two by **MAR and
Sharpe**, which are risk-normalised; comparing their monthly returns directly is
meaningless.

Every percentage in this repository is derived from the published daily series by
`make_charts.py`. Nothing is quoted from a run you can't reproduce.

---

## Why results and not code

The code stays private. That's a deliberate choice, not an evasion — and it costs you
nothing as a reviewer, because **verifying a track record does not require the source
that produced it.** A daily return series pinned to dates is checkable against public
market data: you can test it for lookahead-shaped anomalies, compare it to BTC
buy-and-hold, check whether the good years carry the bad ones, and confirm the risk
statistics are what I claim. None of that needs my entry logic.

What's published here is the layer that supports scrutiny:

- **Daily R series** for every strategy, in-sample and out-of-sample marked
- **Cost ladders** — results across the full range of realistic execution costs
- **Independent verification script** — you run it, not me
- **The caveats**, stated plainly, including the ones that weaken the case

Happy to go deeper under NDA, or to publish signals forward in real time — which is
strictly better evidence than any backtest and is the standard I'd want to be held to.

---

## How these were validated

Every result here cleared the same gauntlet. The failures are documented too; a
research process that never rejects anything isn't a research process.

**Costs are modelled before performance is believed.** Both strategies are reported
across a cost ladder rather than at a single optimistic assumption. A strategy is only
interesting if it survives the fees you'd actually pay, and the screen that matters is
stop-width versus round-trip cost — not headline PnL.

**Out-of-sample means genuinely unseen.** QUADRANT's primary OOS evidence is
*cross-sectional* (ranks 9–16 of the universe — assets the parameters were never fitted
to) and *pre-sample* (2018–19 spot, before the test window opens). VWAP-Z's is a
walk-forward with the exit target re-selected on training data only, plus an unchanged
transfer to ETH.

**Drawdown is quoted from the Monte Carlo, not the backtest.** The historical drawdown
is one draw from a distribution and is systematically optimistic. Sizing decisions here
use the 99th-percentile reshuffled drawdown.

**Compounding is separated from edge.** Compounded returns can be made arbitrarily large
by raising risk per trade. Total R is the edge; sizing is a separate decision.

---

## What isn't in this repository

Strategy source, entry/exit parameters, universe-selection rules, per-trade blotters,
and parameter sweeps. The sweeps are excluded deliberately — a search grid reveals both
the strategy family and how much fitting took place, which is arguably more disclosive
than the source itself.

---

*Contact for the full methodology, spec documents, or live signal access.*
