"""
Worker turnover and job stability in temporary help services.

Compares temp agencies (NAICS 561320) with Administrative & Support Services
(NAICS 56) and the total private sector (NAICS 00) on how transient employment
is: the full-quarter ("stable") employment share, quarterly churn, and the
share of hires that last a full quarter.

QWI counts (Emp, EmpEnd, EmpS, HirA, HirN, Sep, HirAs, SepS) are pulled per
state for the whole 2005-2023 span in a single call, summed to a national
total, and turned into rates at the national level.

Rate definitions (per quarter):
    stable_share      = EmpS / Emp
    accession_rate    = HirA / mean(Emp, EmpEnd)
    separation_rate   = Sep  / mean(Emp, EmpEnd)
    churn_rate        = (HirA + Sep) / (Emp + EmpEnd)
    stable_hire_share = HirAs / HirA

Outputs (to M:/Temp_agencies):
    temp_agency_turnover.csv          quarterly, long format
    temp_agency_turnover_annual.csv   annual means by industry
    turnover_trends.png              3-panel time series, 2005-2023
    turnover_comparison.png          latest-year bar comparison
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
import sys
import os

sns.set_style("whitegrid")

OUTPUT_DIR = "M:/Temp_agencies"


class TurnoverAnalyzer:
    """National QWI turnover / job-stability comparison across three industries."""

    BASE_URL = "https://api.census.gov/data/timeseries/qwi/sa"

    INDUSTRIES = {
        "561320": "Temp Help Services",
        "56": "Admin & Support (56)",
        "00": "Total Private",
    }

    # Consistent colours/markers with temp_agency_wages.py so the deck reads as one set
    STYLE = {
        "561320": dict(color="darkblue", marker="o"),
        "56": dict(color="darkgreen", marker="s"),
        "00": dict(color="darkred", marker="^"),
    }

    COUNT_VARS = ["Emp", "EmpEnd", "EmpS", "HirA", "HirN", "Sep", "HirAs", "SepS"]

    # 50 states + DC
    STATES = [
        '01', '02', '04', '05', '06', '08', '09', '10', '11', '12',
        '13', '15', '16', '17', '18', '19', '20', '21', '22', '23',
        '24', '25', '26', '27', '28', '29', '30', '31', '32', '33',
        '34', '35', '36', '37', '38', '39', '40', '41', '42', '44',
        '45', '46', '47', '48', '49', '50', '51', '53', '54', '55', '56'
    ]

    def __init__(self, api_key, start_year=2005, end_year=2023):
        self.api_key = api_key
        self.start_year = start_year
        self.end_year = end_year
        self._test_api_connection()

    def _test_api_connection(self):
        print("\n" + "=" * 70)
        print("TESTING API CONNECTION")
        print("=" * 70)
        params = {
            "get": ",".join(self.COUNT_VARS),
            "for": "state:06",
            "industry": "561320",
            "ownercode": "A05",
            "sex": "0", "agegrp": "A00", "education": "E0",
            "firmage": "0", "firmsize": "0",
            "time": "from 2022 to 2022",
            "key": self.api_key,
        }
        try:
            r = requests.get(self.BASE_URL, params=params, timeout=15)
            print(f"Response status: {r.status_code}")
            if r.status_code != 200:
                print(f"[FAILED] {r.text[:400]}")
                sys.exit(1)
            print(f"[OK] Sample rows: {len(r.json()) - 1}")
        except Exception as e:
            print(f"[FAILED] {e}")
            sys.exit(1)
        print("=" * 70 + "\n")

    def fetch_industry(self, naics):
        """One request per state for the whole time span; return a tidy DataFrame."""
        label = self.INDUSTRIES[naics]
        print(f"Fetching turnover counts for {label} (NAICS {naics})...")
        rows = []
        suppressed = {"", "N", "D", "S", None}

        for i, state in enumerate(self.STATES, 1):
            print(f"  state {i}/{len(self.STATES)} ({state})", end="\r")
            params = {
                "get": ",".join(self.COUNT_VARS),
                "for": f"state:{state}",
                "industry": naics,
                "ownercode": "A05",
                "sex": "0", "agegrp": "A00", "education": "E0",
                "firmage": "0", "firmsize": "0",
                "time": f"from {self.start_year} to {self.end_year}",
                "key": self.api_key,
            }
            try:
                r = requests.get(self.BASE_URL, params=params, timeout=60)
                if r.status_code != 200:
                    continue
                data = r.json()
                header = data[0]
                idx = {h: j for j, h in enumerate(header)}
                for row in data[1:]:
                    rec = {}
                    ok = True
                    for v in self.COUNT_VARS:
                        val = row[idx[v]]
                        if val in suppressed:
                            ok = False
                            break
                        rec[v] = int(val)
                    if not ok:
                        continue
                    tval = row[idx["time"]]          # e.g. "2015-Q3"
                    yr, qtr = tval.split("-Q")
                    rec["year"] = int(yr)
                    rec["quarter"] = int(qtr)
                    rec["state"] = state
                    rows.append(rec)
            except Exception:
                pass
            time.sleep(0.05)

        print(f"  [OK] {len(rows):,} state-quarter rows retrieved" + " " * 20)
        return pd.DataFrame(rows)

    @staticmethod
    def aggregate_national(df, naics, label):
        """Sum counts across states by quarter, then derive rates."""
        g = df.groupby(["year", "quarter"], as_index=False)[TurnoverAnalyzer.COUNT_VARS].sum()
        avg_emp = (g["Emp"] + g["EmpEnd"]) / 2

        g["industry"] = naics
        g["industry_label"] = label
        g["stable_share"] = g["EmpS"] / g["Emp"]
        g["accession_rate"] = g["HirA"] / avg_emp
        g["separation_rate"] = g["Sep"] / avg_emp
        g["churn_rate"] = (g["HirA"] + g["Sep"]) / (g["Emp"] + g["EmpEnd"])
        g["stable_hire_share"] = g["HirAs"] / g["HirA"]
        g["period"] = g["year"].astype(str) + " Q" + g["quarter"].astype(str)
        return g.sort_values(["year", "quarter"]).reset_index(drop=True)

    def build(self):
        frames = []
        for naics, label in self.INDUSTRIES.items():
            print("=" * 70)
            raw = self.fetch_industry(naics)
            if raw.empty:
                print(f"[FAILED] no data for {label}")
                sys.exit(1)
            frames.append(self.aggregate_national(raw, naics, label))
        combined = pd.concat(frames, ignore_index=True)
        return combined

    # ------------------------------------------------------------------ plots
    @staticmethod
    def _shade_recessions(ax, periods):
        for start, end in [("2007 Q4", "2009 Q2"), ("2020 Q1", "2020 Q2")]:
            if start not in periods and end not in periods:
                continue
            x0 = periods.index(start) if start in periods else 0
            x1 = periods.index(end) if end in periods else len(periods) - 1
            ax.axvspan(x0, x1, color="gray", alpha=0.15, linewidth=0, zorder=0)

    def plot_trends(self, df, output_file=f"{OUTPUT_DIR}/turnover_trends.png"):
        panels = [
            ("stable_share", False,
             "Full-quarter ('stable') employment\nas share of beginning-of-quarter employment"),
            ("churn_rate", False,
             "Quarterly churn rate\n(hires + separations) / average employment"),
            ("stable_hire_share", True,
             "Share of hires that reach full-quarter status (HirAs / HirA)\n"
             "4-quarter moving average"),
        ]
        periods = sorted(df["period"].unique(),
                         key=lambda p: (int(p[:4]), int(p.split("Q")[1])))
        x = range(len(periods))

        fig, axes = plt.subplots(3, 1, figsize=(14, 13), sharex=True)
        for ax, (col, smooth, title) in zip(axes, panels):
            for naics, label in self.INDUSTRIES.items():
                s = df[df["industry"] == naics].set_index("period").reindex(periods)[col]
                if smooth:
                    s = s.rolling(4, min_periods=4).mean()
                ax.plot(x, s.values, linewidth=2, markersize=3,
                        label=label, **self.STYLE[naics])
                last = s.dropna()
                if len(last):
                    ax.annotate(f" {label}", xy=(len(periods) - 1, last.iloc[-1]),
                                xytext=(4, 0), textcoords="offset points",
                                fontsize=8, va="center", color=self.STYLE[naics]["color"])
            self._shade_recessions(ax, periods)
            ax.set_title(title, fontsize=12, fontweight="bold")
            ax.grid(True, alpha=0.3)
            ax.set_xlim(-1, len(periods) + 8)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))

        tick_positions = list(range(0, len(periods), 4))
        axes[-1].set_xticks(tick_positions)
        axes[-1].set_xticklabels([periods[i] for i in tick_positions], rotation=45, ha="right")
        axes[-1].set_xlabel("Quarter", fontsize=12)

        fig.suptitle("Job stability and turnover: temp help vs. sector vs. all private (national)",
                     fontsize=14, fontweight="bold")
        plt.tight_layout(rect=(0, 0, 1, 0.98))
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"[OK] Saved {output_file}")
        plt.close()

    def plot_comparison(self, df, output_file=f"{OUTPUT_DIR}/turnover_comparison.png"):
        year = int(df["year"].max())
        latest = df[df["year"] == year]
        metrics = [
            ("accession_rate", "Accession rate / qtr"),
            ("separation_rate", "Separation rate / qtr"),
            ("churn_rate", "Churn rate / qtr"),
        ]
        means = {naics: latest[latest["industry"] == naics][[m for m, _ in metrics]].mean()
                 for naics in self.INDUSTRIES}

        fig, ax = plt.subplots(figsize=(11, 4.6))
        n = len(self.INDUSTRIES)
        bar_h = 0.8 / n
        ypos = range(len(metrics))
        for k, (naics, label) in enumerate(self.INDUSTRIES.items()):
            vals = [means[naics][m] for m, _ in metrics]
            offs = [y + (k - (n - 1) / 2) * bar_h for y in ypos]
            bars = ax.barh(offs, vals, height=bar_h, color=self.STYLE[naics]["color"],
                           label=label)
            for b, v in zip(bars, vals):
                ax.text(b.get_width() + 0.005, b.get_y() + b.get_height() / 2,
                        f"{v:.0%}", va="center", fontsize=8)
        ax.set_yticks(list(ypos))
        ax.set_yticklabels([lbl for _, lbl in metrics])
        ax.invert_yaxis()
        ax.set_xlabel(f"Quarterly rate, {year} average")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.set_title(f"Hires, separations and churn per quarter, {year}",
                     fontsize=13, fontweight="bold")
        ax.legend(loc="lower right", fontsize=9)
        ax.grid(True, axis="x", alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"[OK] Saved {output_file}")
        plt.close()


def main():
    api_key = os.environ.get("CENSUS_API_KEY", "")

    print("=" * 70)
    print("TEMP AGENCY TURNOVER / JOB-STABILITY ANALYSIS")
    print("=" * 70)

    analyzer = TurnoverAnalyzer(api_key, start_year=2005, end_year=2023)
    df = analyzer.build()

    quarterly_cols = [
        "period", "year", "quarter", "industry", "industry_label",
        *TurnoverAnalyzer.COUNT_VARS,
        "stable_share", "accession_rate", "separation_rate",
        "churn_rate", "stable_hire_share",
    ]
    q_csv = f"{OUTPUT_DIR}/temp_agency_turnover.csv"
    df[quarterly_cols].to_csv(q_csv, index=False)
    print(f"\n[OK] Saved quarterly data to {q_csv}")

    annual = (df.groupby(["year", "industry", "industry_label"], as_index=False)
                [["stable_share", "accession_rate", "separation_rate",
                  "churn_rate", "stable_hire_share"]].mean())
    a_csv = f"{OUTPUT_DIR}/temp_agency_turnover_annual.csv"
    annual.to_csv(a_csv, index=False)
    print(f"[OK] Saved annual data to {a_csv}")

    analyzer.plot_trends(df)
    analyzer.plot_comparison(df)

    print("\n" + "=" * 70)
    print("KEY NUMBERS (latest year)")
    print("=" * 70)
    year = int(df["year"].max())
    for naics, label in TurnoverAnalyzer.INDUSTRIES.items():
        s = df[(df["industry"] == naics) & (df["year"] == year)]
        print(f"  {label:22} stable share {s['stable_share'].mean():.0%} | "
              f"churn {s['churn_rate'].mean():.0%}/qtr | "
              f"stable-hire share {s['stable_hire_share'].mean():.0%}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
