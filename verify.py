#!/usr/bin/env python3
"""Independently recompute every headline statistic in this repository.

Reads only the published daily return series. Nothing here depends on the
strategy implementation -- if the numbers in the READMEs disagree with this
script's output, trust this script.

Usage:
    python verify.py                       # verify everything
    python verify.py quadrant/daily_returns.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

TRADING_DAYS = 365  # crypto trades every day


def max_drawdown_R(cum: np.ndarray) -> float:
    """Deepest peak-to-trough decline of the cumulative R curve."""
    peak = np.maximum.accumulate(cum)
    return float((cum - peak).min())


def sharpe(daily: np.ndarray) -> float:
    """Annualised Sharpe of a daily R series, zero risk-free rate."""
    sd = daily.std(ddof=1)
    if sd == 0 or not np.isfinite(sd):
        return float("nan")
    return float(daily.mean() / sd * np.sqrt(TRADING_DAYS))


def sortino(daily: np.ndarray) -> float:
    downside = daily[daily < 0]
    dd = downside.std(ddof=1) if len(downside) > 1 else 0.0
    if dd == 0 or not np.isfinite(dd):
        return float("nan")
    return float(daily.mean() / dd * np.sqrt(TRADING_DAYS))


def describe(df: pd.DataFrame, label: str) -> dict:
    r = df["R"].to_numpy(dtype=float)
    cum = np.cumsum(r)
    years = max((df.index.max() - df.index.min()).days / 365.25, 1e-9)
    mdd = max_drawdown_R(cum)

    stats = {
        "days": len(df),
        "from": str(df.index.min().date()),
        "to": str(df.index.max().date()),
        "total_R": r.sum(),
        "R_per_year": r.sum() / years,
        "sharpe": sharpe(r),
        "sortino": sortino(r),
        "max_dd_R": mdd,
        "mar": (r.sum() / years) / abs(mdd) if mdd else float("nan"),
        "best_day_R": r.max(),
        "worst_day_R": r.min(),
        "pct_days_positive": (r > 0).mean() * 100,
    }
    if "trades" in df.columns:
        stats["trades"] = int(df["trades"].sum())

    print(f"\n{'=' * 62}\n{label}\n{'=' * 62}")
    print(f"  period            {stats['from']} -> {stats['to']}  ({years:.2f}y, {stats['days']} days)")
    if "trades" in stats:
        print(f"  trades            {stats['trades']:,}")
    print(f"  total R           {stats['total_R']:+.1f}")
    print(f"  R per year        {stats['R_per_year']:+.1f}")
    print(f"  Sharpe            {stats['sharpe']:.2f}")
    print(f"  Sortino           {stats['sortino']:.2f}")
    print(f"  max drawdown      {stats['max_dd_R']:.1f} R")
    print(f"  MAR               {stats['mar']:.2f}")
    print(f"  best / worst day  {stats['best_day_R']:+.2f}R / {stats['worst_day_R']:+.2f}R")
    print(f"  days positive     {stats['pct_days_positive']:.1f}%")
    return stats


def by_year(df: pd.DataFrame) -> None:
    print("\n  year      R      Sharpe   maxDD_R")
    print("  " + "-" * 34)
    for year, g in df.groupby(df.index.year):
        r = g["R"].to_numpy(dtype=float)
        print(f"  {year}  {r.sum():+8.1f}   {sharpe(r):6.2f}   {max_drawdown_R(np.cumsum(r)):7.1f}")


def by_sample(df: pd.DataFrame) -> None:
    if "sample" not in df.columns:
        return
    print("\n  sample split")
    print("  " + "-" * 34)
    for name, g in df.groupby("sample", sort=False):
        r = g["R"].to_numpy(dtype=float)
        print(f"  {name:<8} {r.sum():+8.1f} R   Sharpe {sharpe(r):5.2f}   ({len(g)} days)")


BASE = 100_000.0


def account_stats(df: pd.DataFrame) -> None:
    """For series carrying realised USD P&L: monthly returns on a constant base.

    Nothing is modelled here -- monthly return is the monthly sum of the
    published pnl_usd column over the $100,000 base.
    """
    pnl = df["pnl_usd"].astype(float)
    monthly = pnl.resample("ME").sum() / BASE * 100.0
    years = max((df.index.max() - df.index.min()).days / 365.25, 1e-9)

    if "equity_usd" in df.columns:
        eq = df["equity_usd"].astype(float)
        dd_usd = float((eq - eq.cummax()).min())
    else:
        cum = pnl.cumsum().to_numpy()
        dd_usd = float((cum - np.maximum.accumulate(cum)).min())
    dd_pct = dd_usd / BASE * 100.0
    ann_pct = pnl.sum() / years / BASE * 100.0

    print(f"\n  $100,000 ACCOUNT (constant base, profit swept monthly)")
    print("  " + "-" * 46)
    print(f"  total profit          ${pnl.sum():>13,.0f}")
    print(f"  return / year         {ann_pct:>13.1f}%")
    print(f"  return / month mean   {monthly.mean():>13.2f}%")
    print(f"  return / month median {monthly.median():>13.2f}%")
    print(f"  best / worst month    {monthly.max():>8.2f}% / {monthly.min():.2f}%")
    print(f"  max drawdown          {dd_pct:>13.2f}%  (${dd_usd:,.0f})")
    print(f"  MAR                   {ann_pct / abs(dd_pct):>13.2f}")
    print(f"  months positive       {(monthly > 0).mean() * 100:>12.0f}%  "
          f"({(monthly > 0).sum()}/{len(monthly)})")


def verify(path: Path) -> None:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if "R" not in df.columns:
        raise SystemExit(f"{path}: expected a column named 'R'")
    df = df.sort_index()
    if "cum_R" not in df.columns:
        df["cum_R"] = df["R"].astype(float).cumsum()
    describe(df, str(path))
    if "pnl_usd" in df.columns:
        account_stats(df)
    by_sample(df)
    by_year(df)


def main() -> None:
    root = Path(__file__).resolve().parent
    targets = [Path(a) for a in sys.argv[1:]] or sorted(root.glob("*/daily_returns*.csv"))
    if not targets:
        raise SystemExit("no daily_returns*.csv found")
    for t in targets:
        verify(t if t.is_absolute() else root / t)
    print("\nAll series verified from published data alone.\n")


if __name__ == "__main__":
    main()
