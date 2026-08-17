#!/usr/bin/env python3
"""Render the charts and markdown tables for this repository.

Reads only the published daily return series -- same inputs as verify.py, no
strategy logic. Regenerate everything with:

    python make_charts.py
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

ROOT = Path(__file__).resolve().parent

# Palette: documented default instance, used unchanged.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
S1 = "#2a78d6"   # categorical slot 1 - blue
S2 = "#eb6834"   # categorical slot 2 - orange
NEG = "#d03b3b"  # status critical - drawdown

# Diverging ramp for the heatmap: red <- neutral gray -> blue.
DIVERGING = LinearSegmentedColormap.from_list(
    "quant_div",
    ["#8c1f1f", "#d03b3b", "#e89a9a", "#f0efec", "#9ec5f4", "#2a78d6", "#0d366b"],
)

STRATEGIES = {
    "quadrant": {
        "csv": "quadrant/daily_returns.csv",
        "name": "QUADRANT",
        "risk": 0.004073,
        "risk_label": "0.4073% risk/trade, smooth drawdown throttle, profit swept "
                      "monthly — the adopted configuration",
    },
    "vwap-z-trend-impulse": {
        "csv": "vwap-z-trend-impulse/daily_returns.csv",
        "name": "VWAP-Z Trend Impulse",
        "risk": 0.0025,
        "risk_label": "0.25% risk/trade — Monte Carlo sizing (99th-pct DD 12%)",
    },
}

BASE = 100_000.0


def style_axes(ax, ylabel: str = "") -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8, alpha=1.0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK_2, fontsize=10)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def new_fig(title: str, subtitle: str, size=(11, 5.0)):
    fig, ax = plt.subplots(figsize=size, dpi=160)
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.055, 0.955, title, ha="left", va="top", fontsize=15,
             fontweight="bold", color=INK)
    wrapped = "\n".join(textwrap.wrap(subtitle, width=104))
    fig.text(0.055, 0.885, wrapped, ha="left", va="top", fontsize=9.5,
             color=MUTED, linespacing=1.45)
    return fig, ax


def save(fig, path: Path, top: float = 0.78) -> None:
    """Right margin leaves room for the end-of-series direct labels."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(top=top, bottom=0.10, left=0.115, right=0.865)
    fig.savefig(path, facecolor=SURFACE, edgecolor="none")
    plt.close(fig)
    print(f"  wrote {path.relative_to(ROOT)}")


def load(cfg: dict) -> pd.DataFrame:
    """Prefer realised USD P&L when the series carries it.

    A series with pnl_usd already has the account model baked in (position
    throttle, monthly sweep), so its dollar figures must be read off that column
    rather than re-derived from R -- re-deriving would silently drop the throttle.
    """
    df = pd.read_csv(ROOT / cfg["csv"], index_col=0, parse_dates=True).sort_index()
    r = df["R"].astype(float)
    risk = cfg["risk"]
    if "cum_R" not in df.columns:
        df["cum_R"] = r.cumsum()

    if "pnl_usd" in df.columns:
        pnl = df["pnl_usd"].astype(float)
        df["flat"] = BASE + pnl.cumsum()
        # Indicative only: the same daily return stream left to compound.
        df["comp"] = BASE * (1.0 + pnl / BASE).cumprod()
        df["daily_pct"] = pnl / BASE * 100.0
    else:
        df["flat"] = BASE + r.cumsum() * risk * BASE
        df["comp"] = BASE * (1.0 + r * risk).cumprod()
        df["daily_pct"] = r * risk * 100.0

    # Constant capital means profits are withdrawn, so the risked base never
    # grows: drawdown is the decline in cumulative profit measured against the
    # base, NOT a percentage of a rising equity curve (which would flatter
    # later drawdowns).
    cum = df["flat"].to_numpy(dtype=float)
    df["dd_pct"] = (cum - np.maximum.accumulate(cum)) / BASE * 100.0
    return df


def chart_equity(df: pd.DataFrame, cfg: dict, out: Path) -> None:
    """Both sizing conventions, one $ axis, log scale for the magnitude gap."""
    fig, ax = new_fig(
        f"{cfg['name']} — equity curve",
        f"$100,000 base at {cfg['risk_label']}. Log scale: the two conventions "
        f"differ by orders of magnitude, not by edge.",
    )
    ax.plot(df.index, df["flat"], color=S1, linewidth=2.0, label="Constant capital (profits withdrawn)")
    ax.plot(df.index, df["comp"], color=S2, linewidth=2.0, label="Compounded (profits reinvested)")
    ax.set_yscale("log")
    style_axes(ax, "Account equity (USD, log)")
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")

    for col, color in (("comp", S2), ("flat", S1)):
        ax.annotate(f"${df[col].iloc[-1]:,.0f}",
                    xy=(df.index[-1], df[col].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points",
                    color=color, fontsize=10, fontweight="bold", va="center")

    leg = ax.legend(loc="upper left", frameon=False, fontsize=9.5)
    for t in leg.get_texts():
        t.set_color(INK_2)
    save(fig, out)


def chart_pnl(df: pd.DataFrame, cfg: dict, out: Path) -> None:
    """Cumulative R -- the size-independent edge."""
    fig, ax = new_fig(
        f"{cfg['name']} — cumulative P&L in R",
        "R = multiples of risk per trade. Size-independent: cannot be inflated "
        "by leverage or compounding.",
    )
    ax.fill_between(df.index, 0, df["cum_R"], color=S1, alpha=0.13, linewidth=0)
    ax.plot(df.index, df["cum_R"], color=S1, linewidth=2.0)
    ax.axhline(0, color=AXIS, linewidth=1.0)
    style_axes(ax, "Cumulative R")
    ax.annotate(f"{df['cum_R'].iloc[-1]:+,.1f}R",
                xy=(df.index[-1], df["cum_R"].iloc[-1]),
                xytext=(6, 0), textcoords="offset points",
                color=S1, fontsize=11, fontweight="bold", va="center")
    save(fig, out)


def chart_drawdown(df: pd.DataFrame, cfg: dict, out: Path) -> None:
    fig, ax = new_fig(
        f"{cfg['name']} — drawdown",
        f"Peak-to-trough decline on constant capital at {cfg['risk_label']}.",
        size=(11, 4.0),
    )
    ax.fill_between(df.index, 0, df["dd_pct"], color=NEG, alpha=0.20, linewidth=0)
    ax.plot(df.index, df["dd_pct"], color=NEG, linewidth=1.6)
    ax.axhline(0, color=AXIS, linewidth=1.0)
    style_axes(ax, "Drawdown (%)")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")

    worst = df["dd_pct"].idxmin()
    ax.annotate(f"worst {df['dd_pct'].min():.2f}%",
                xy=(worst, df["dd_pct"].min()),
                xytext=(8, 10), textcoords="offset points",
                color=NEG, fontsize=10, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=NEG, linewidth=1.0))
    save(fig, out, top=0.72)


def monthly_table(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    m = df["daily_pct"].resample("ME").sum()
    t = pd.DataFrame({"year": m.index.year, "month": m.index.month, "ret": m.values})
    return t.pivot(index="year", columns="month", values="ret")


def chart_heatmap(df: pd.DataFrame, cfg: dict, out: Path) -> None:
    piv = monthly_table(df, cfg)
    piv = piv.reindex(columns=range(1, 13))
    vals = piv.to_numpy(dtype=float)
    lim = float(np.nanmax(np.abs(vals)))
    norm = TwoSlopeNorm(vmin=-lim, vcenter=0.0, vmax=lim)

    fig, ax = plt.subplots(figsize=(11, 0.52 * len(piv) + 2.4), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.055, 0.955, f"{cfg['name']} — monthly returns",
             ha="left", va="top", fontsize=15, fontweight="bold", color=INK)
    sub = (f"Constant capital at {cfg['risk_label']}. Blue = gain, red = loss, "
           f"gray = flat. Values are percent.")
    fig.text(0.055, 0.885, "\n".join(textwrap.wrap(sub, width=104)),
             ha="left", va="top", fontsize=9.5, color=MUTED, linespacing=1.45)

    ax.set_facecolor(SURFACE)
    masked = np.ma.masked_invalid(vals)
    ax.imshow(masked, cmap=DIVERGING, norm=norm, aspect="auto")

    ax.set_xticks(range(12))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_yticks(range(len(piv)))
    ax.set_yticklabels(piv.index)
    ax.tick_params(colors=INK_2, labelsize=9.5, length=0)
    for s in ax.spines.values():
        s.set_visible(False)

    # 2px surface gap between cells
    ax.set_xticks(np.arange(-0.5, 12, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(piv), 1), minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="minor", length=0)

    # Every cell is labelled -- identity never rests on color alone.
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            v = vals[i, j]
            if np.isnan(v):
                continue
            shade = "#ffffff" if abs(v) > lim * 0.55 else INK
            ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                    fontsize=8.5, color=shade)

    fig.subplots_adjust(top=0.76, bottom=0.06, left=0.075, right=0.965)
    fig.savefig(out, facecolor=SURFACE, edgecolor="none")
    plt.close(fig)
    print(f"  wrote {out.relative_to(ROOT)}")


def write_tables(df: pd.DataFrame, cfg: dict, out: Path) -> None:
    """Markdown monthly/yearly tables, for readers who want the numbers."""
    piv = monthly_table(df, cfg).reindex(columns=range(1, 13))
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    lines = [f"# {cfg['name']} — monthly returns (%)", "",
             f"Constant capital, $100,000 base, {cfg['risk_label']}.",
             "Generated by `make_charts.py` from `daily_returns.csv`.", "",
             "| Year | " + " | ".join(months) + " | Year |",
             "|---" * 14 + "|"]
    for year, row in piv.iterrows():
        cells = ["" if pd.isna(v) else f"{v:+.2f}" for v in row]
        lines.append(f"| **{year}** | " + " | ".join(cells) +
                     f" | **{np.nansum(row.to_numpy(dtype=float)):+.2f}** |")

    lines += ["", "## By year", "",
              "| Year | Total R | Return | Sharpe | Max DD |",
              "|---|---:|---:|---:|---:|"]
    for year, g in df.groupby(df.index.year):
        r = g["R"].to_numpy(dtype=float)
        pct = g["daily_pct"].to_numpy(dtype=float)
        sd = pct.std(ddof=1)
        sh = pct.mean() / sd * np.sqrt(365) if sd else float("nan")
        cum = np.cumsum(pct)
        dd = float((cum - np.maximum.accumulate(cum)).min())
        lines.append(f"| {year} | {r.sum():+.1f} | {pct.sum():+.2f}% "
                     f"| {sh:.2f} | {dd:.2f}% |")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {out.relative_to(ROOT)}")


def main() -> None:
    for folder, cfg in STRATEGIES.items():
        print(f"{cfg['name']}:")
        df = load(cfg)
        charts = ROOT / folder / "charts"
        chart_equity(df, cfg, charts / "01_equity.png")
        chart_pnl(df, cfg, charts / "02_cumulative_r.png")
        chart_drawdown(df, cfg, charts / "03_drawdown.png")
        chart_heatmap(df, cfg, charts / "04_monthly_heatmap.png")
        write_tables(df, cfg, ROOT / folder / "MONTHLY.md")
        print(f"  final: flat ${df['flat'].iloc[-1]:,.0f} | "
              f"compounded ${df['comp'].iloc[-1]:,.0f} | "
              f"worst DD {df['dd_pct'].min():.2f}%")


if __name__ == "__main__":
    main()
