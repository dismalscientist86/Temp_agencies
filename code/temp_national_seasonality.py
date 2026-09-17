"""
Seasonality in national temp-agency employment.

QWI publishes no seasonally-adjusted series (see qwi_seasonal.py for why).
Every other chart in this project now plots the seasonally-adjusted level
computed there; this script is the one chart that shows the *raw* series
and the seasonal pattern being removed from it, using the same
decomposition (statsmodels seasonal_decompose, multiplicative, period=4)
applied to the national temp-employment series.

Reads output/national_temp_employment.csv (produced by
temp_agencies_over_time_national.py) -- no API calls.

Outputs (to output/):
    national_seasonality.png
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from qwi_seasonal import seasonally_adjust

sns.set_style("whitegrid")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(REPO, "output")


def main():
    src = f"{OUTPUT_DIR}/national_temp_employment.csv"
    df = pd.read_csv(src).sort_values(["year", "quarter"]).reset_index(drop=True)
    df = seasonally_adjust(df, "Emp")
    periods = list(df["period"])
    x = range(len(df))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10),
                                   gridspec_kw={"height_ratios": [2.2, 1]})

    # Panel 1: raw vs seasonally adjusted, over time
    ax1.plot(x, df["Emp"] / 1000, marker="o", markersize=3, linewidth=1.5,
             color="#8fb3d9", label="Raw (unadjusted)")
    ax1.plot(x, df["Emp_sa"] / 1000, linewidth=2.5, color="darkblue",
             label="Seasonally adjusted")

    recessions = [("2007 Q4", "2009 Q2"), ("2020 Q1", "2020 Q2")]
    for start, end in recessions:
        if start not in periods and end not in periods:
            continue
        x0 = periods.index(start) if start in periods else 0
        x1 = periods.index(end) if end in periods else len(periods) - 1
        ax1.axvspan(x0, x1, color="gray", alpha=0.15, linewidth=0, zorder=0)

    ax1.set_title("National temp-agency employment: raw vs. seasonally adjusted",
                  fontsize=14, fontweight="bold")
    ax1.set_ylabel("Employment (thousands)")
    ax1.legend(loc="lower right", fontsize=10)
    ax1.grid(True, alpha=0.3)
    tick_positions = list(range(0, len(df), 4))
    ax1.set_xticks(tick_positions)
    ax1.set_xticklabels([periods[i] for i in tick_positions], rotation=45, ha="right")

    # Panel 2: the seasonal factor itself, by quarter of year
    factor_by_q = (df.assign(dev_pct=(df["Emp_seasonal"] - 1) * 100)
                     .groupby("quarter")["dev_pct"].mean())
    colors = ["#33608c" if v >= 0 else "#c0504d" for v in factor_by_q]
    bars = ax2.bar([f"Q{q}" for q in factor_by_q.index], factor_by_q.values, color=colors)
    for b, v in zip(bars, factor_by_q.values):
        ax2.text(b.get_x() + b.get_width() / 2, v + (0.15 if v >= 0 else -0.15),
                 f"{v:+.1f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=10)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_title("Average seasonal deviation by quarter, 2005-2023",
                  fontsize=12, fontweight="bold")
    ax2.set_ylabel("Deviation from\nseasonally-adjusted level (%)")
    ax2.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    out = f"{OUTPUT_DIR}/national_seasonality.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"[OK] Saved {out}")
    plt.close()

    print("\nSeasonal factors (avg. deviation from SA level, by quarter):")
    for q, v in factor_by_q.items():
        print(f"  Q{q}: {v:+.1f}%")


if __name__ == "__main__":
    main()
