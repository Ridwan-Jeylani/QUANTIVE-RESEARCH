#!/usr/bin/env python3
"""Render the 1280x640 GitHub social preview card.

Reads the published daily series -- the curve and every stat on the card come
from the same data as the READMEs, so the preview can never drift from them.

    python make_social.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "social_preview.png"
BASE = 100_000.0

# Dark instance of the documented palette.
SURFACE = "#141413"
INK = "#ffffff"
INK_2 = "#c3c2b7"
MUTED = "#898781"
S1 = "#3987e5"      # categorical slot 1, dark step
RULE = "#2c2c2a"

W, H, DPI = 1280, 640, 160


def stats():
    df = pd.read_csv(ROOT / "quadrant/daily_returns.csv",
                     index_col=0, parse_dates=True).sort_index()
    pnl = df["pnl_usd"].astype(float)
    monthly = pnl.resample("ME").sum() / BASE * 100.0
    eq = BASE + pnl.cumsum()
    dd = float(((eq - eq.cummax()) / BASE * 100.0).min())
    years = (df.index.max() - df.index.min()).days / 365.25
    daily = pnl / BASE
    return {
        "curve": eq,
        "ret_mo": monthly.mean(),
        "dd": dd,
        "mar": (pnl.sum() / years / BASE * 100.0) / abs(dd),
        "sharpe": float(daily.mean() / daily.std(ddof=1) * np.sqrt(365)),
        "years": years,
    }


def main():
    s = stats()
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.patch.set_facecolor(SURFACE)

    # --- the curve, low and wide, as a ground rather than a focal point ---
    ax = fig.add_axes([0.0, 0.0, 1.0, 0.42])
    ax.set_facecolor(SURFACE)
    c = s["curve"]
    ax.fill_between(c.index, c.min(), c.to_numpy(), color=S1, alpha=0.16, linewidth=0)
    ax.plot(c.index, c.to_numpy(), color=S1, linewidth=2.4)
    ax.set_axis_off()
    ax.margins(x=0, y=0.06)

    # --- wordmark ---
    fig.text(0.055, 0.90, "QUANTIVE RESEARCH", fontsize=30, fontweight="bold",
             color=INK, ha="left", va="top", linespacing=1.0)
    fig.text(0.055, 0.775,
             "Systematic crypto trading research — verified track records",
             fontsize=12.5, color=INK_2, ha="left", va="top")

    fig.add_artist(plt.Line2D([0.055, 0.945], [0.735, 0.735],
                              color=RULE, linewidth=1.2))

    # --- the four numbers ---
    cells = [
        (f"{s['ret_mo']:.2f}%", "per month"),
        (f"{s['dd']:.2f}%", "max drawdown"),
        (f"{s['mar']:.2f}", "MAR"),
        (f"{s['sharpe']:.2f}", "Sharpe"),
    ]
    # Columns are sized for the widest value ("-9.95%") at this weight; keep
    # the size and the step in step if either changes.
    for i, (value, label) in enumerate(cells):
        x = 0.055 + i * 0.2250
        fig.text(x, 0.66, value, fontsize=27, fontweight="bold",
                 color=S1 if i == 0 else INK, ha="left", va="top")
        fig.text(x, 0.545, label.upper(), fontsize=10, color=MUTED,
                 ha="left", va="top")

    fig.text(0.055, 0.45,
             f"QUADRANT · {s['years']:.1f} years · net of all costs · "
             f"reproducible from the published data",
             fontsize=11.5, color=INK_2, ha="left", va="top")

    fig.savefig(OUT, facecolor=SURFACE, edgecolor="none")
    plt.close(fig)
    print(f"wrote {OUT.name}  ({W}x{H})")
    for value, label in cells:
        print(f"  {label:<14} {value}")


if __name__ == "__main__":
    main()
