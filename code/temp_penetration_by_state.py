"""
Temporary help services penetration by state.

Penetration = temp help employment (NAICS 561320) as a share of total private
employment (NAICS 00) in a state. QWI `Emp` counts are pulled per state for a
year in one call and averaged across the four quarters.

Produces a tile-grid ("statebins") choropleth and a ranked bar chart for the
latest year, plus a CSV that also carries an earlier year for comparison.

Outputs (to output/):
    temp_penetration_by_state.csv     state, both years, penetration, rank, change
    temp_penetration_map.png          tile-grid map, latest year
    temp_penetration_ranking.png      ranked horizontal bar, latest year
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import cm, colors
import seaborn as sns
import time
import sys
import os

sns.set_style("white")

# Save outputs straight into the repo's output/ folder (this file lives in code/)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

COMPARE_YEAR = 2010
LATEST_YEAR = 2023
# A few states stop reporting to QWI at different points (Michigan after 2021;
# Alaska after 2016) -- fall back year by year until a state has data.
LATEST_FALLBACK = list(range(LATEST_YEAR, COMPARE_YEAR - 1, -1))

# FIPS -> (USPS abbreviation, full name)
STATES = {
    '01': ('AL', 'Alabama'), '02': ('AK', 'Alaska'), '04': ('AZ', 'Arizona'),
    '05': ('AR', 'Arkansas'), '06': ('CA', 'California'), '08': ('CO', 'Colorado'),
    '09': ('CT', 'Connecticut'), '10': ('DE', 'Delaware'), '11': ('DC', 'D.C.'),
    '12': ('FL', 'Florida'), '13': ('GA', 'Georgia'), '15': ('HI', 'Hawaii'),
    '16': ('ID', 'Idaho'), '17': ('IL', 'Illinois'), '18': ('IN', 'Indiana'),
    '19': ('IA', 'Iowa'), '20': ('KS', 'Kansas'), '21': ('KY', 'Kentucky'),
    '22': ('LA', 'Louisiana'), '23': ('ME', 'Maine'), '24': ('MD', 'Maryland'),
    '25': ('MA', 'Massachusetts'), '26': ('MI', 'Michigan'), '27': ('MN', 'Minnesota'),
    '28': ('MS', 'Mississippi'), '29': ('MO', 'Missouri'), '30': ('MT', 'Montana'),
    '31': ('NE', 'Nebraska'), '32': ('NV', 'Nevada'), '33': ('NH', 'New Hampshire'),
    '34': ('NJ', 'New Jersey'), '35': ('NM', 'New Mexico'), '36': ('NY', 'New York'),
    '37': ('NC', 'North Carolina'), '38': ('ND', 'North Dakota'), '39': ('OH', 'Ohio'),
    '40': ('OK', 'Oklahoma'), '41': ('OR', 'Oregon'), '42': ('PA', 'Pennsylvania'),
    '44': ('RI', 'Rhode Island'), '45': ('SC', 'South Carolina'), '46': ('SD', 'South Dakota'),
    '47': ('TN', 'Tennessee'), '48': ('TX', 'Texas'), '49': ('UT', 'Utah'),
    '50': ('VT', 'Vermont'), '51': ('VA', 'Virginia'), '53': ('WA', 'Washington'),
    '54': ('WV', 'West Virginia'), '55': ('WI', 'Wisconsin'), '56': ('WY', 'Wyoming'),
}

# Tile-grid layout: abbreviation -> (row, col), row 0 at top
GRID = {
    'AK': (0, 0),                                                                 'ME': (0, 10),
    'VT': (1, 9), 'NH': (1, 10),
    'WA': (2, 0), 'ID': (2, 1), 'MT': (2, 2), 'ND': (2, 3), 'MN': (2, 4),
    'IL': (2, 5), 'WI': (2, 6), 'MI': (2, 7),               'NY': (2, 9), 'RI': (2, 10),
    'OR': (3, 0), 'NV': (3, 1), 'WY': (3, 2), 'SD': (3, 3), 'IA': (3, 4),
    'IN': (3, 5), 'OH': (3, 6), 'PA': (3, 7), 'NJ': (3, 8), 'CT': (3, 9), 'MA': (3, 10),
    'CA': (4, 0), 'UT': (4, 1), 'CO': (4, 2), 'NE': (4, 3), 'MO': (4, 4),
    'KY': (4, 5), 'WV': (4, 6), 'VA': (4, 7), 'MD': (4, 8), 'DE': (4, 9),
    'AZ': (5, 1), 'NM': (5, 2), 'KS': (5, 3), 'AR': (5, 4), 'TN': (5, 5),
    'NC': (5, 6), 'SC': (5, 7), 'DC': (5, 8),
                  'OK': (6, 3), 'LA': (6, 4), 'MS': (6, 5), 'AL': (6, 6), 'GA': (6, 7),
    'HI': (7, 0),               'TX': (7, 3),                             'FL': (7, 8),
}


class PenetrationAnalyzer:
    BASE_URL = "https://api.census.gov/data/timeseries/qwi/sa"

    def __init__(self, api_key):
        self.api_key = api_key
        self._test_api_connection()

    def _test_api_connection(self):
        print("\n" + "=" * 70)
        print("TESTING API CONNECTION")
        print("=" * 70)
        params = self._params("06", "561320", 2023)
        r = requests.get(self.BASE_URL, params=params, timeout=15)
        print(f"Response status: {r.status_code}")
        if r.status_code != 200:
            print(f"[FAILED] {r.text[:400]}")
            sys.exit(1)
        print(f"[OK] {len(r.json()) - 1} rows for test query")
        print("=" * 70 + "\n")

    def _params(self, state, naics, year):
        return {
            "get": "Emp",
            "for": f"state:{state}",
            "industry": naics,
            "ownercode": "A05",
            "sex": "0", "agegrp": "A00", "education": "E0",
            "firmage": "0", "firmsize": "0",
            "time": f"from {year} to {year}",
            "key": self.api_key,
        }

    def _avg_emp(self, state, naics, year):
        """Mean Emp over the four quarters of `year`; None if suppressed/missing."""
        try:
            r = requests.get(self.BASE_URL, params=self._params(state, naics, year), timeout=30)
            if r.status_code != 200:
                return None
            data = r.json()
            idx = {h: j for j, h in enumerate(data[0])}
            vals = []
            for row in data[1:]:
                v = row[idx["Emp"]]
                if v not in {"", "N", "D", "S", None}:
                    vals.append(int(v))
            return sum(vals) / len(vals) if vals else None
        except Exception:
            return None

    def build(self):
        records = []
        for i, (fips, (abbr, name)) in enumerate(STATES.items(), 1):
            print(f"  {i:2}/{len(STATES)}  {abbr}", end="\r")
            rec = {"fips": fips, "abbr": abbr, "state": name}

            # latest: try the fallback years in order until one has data
            rec["year_used"] = None
            for year in LATEST_FALLBACK:
                temp = self._avg_emp(fips, "561320", year)
                total = self._avg_emp(fips, "00", year)
                time.sleep(0.05)
                if temp and total:
                    rec["year_used"] = year
                    rec["temp_emp_latest"] = temp
                    rec["total_emp_latest"] = total
                    rec["penetration_latest"] = 100 * temp / total
                    break
            else:
                rec["temp_emp_latest"] = rec["total_emp_latest"] = rec["penetration_latest"] = None

            temp = self._avg_emp(fips, "561320", COMPARE_YEAR)
            total = self._avg_emp(fips, "00", COMPARE_YEAR)
            time.sleep(0.05)
            rec["penetration_compare"] = (100 * temp / total) if temp and total else None
            records.append(rec)
        print(" " * 30, end="\r")

        df = pd.DataFrame(records)
        df["change_pp"] = df["penetration_latest"] - df["penetration_compare"]
        df = df.sort_values("penetration_latest", ascending=False).reset_index(drop=True)
        df["rank"] = df.index + 1
        return df

    # ------------------------------------------------------------------ plots
    @staticmethod
    def plot_map(df, output_file=f"{OUTPUT_DIR}/temp_penetration_map.png"):
        vals = df.set_index("abbr")["penetration_latest"]
        yr_used = df.set_index("abbr")["year_used"]
        vmin, vmax = vals.min(), vals.max()
        norm = colors.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.get_cmap("Blues")

        n_rows = max(r for r, _ in GRID.values()) + 1
        fig, ax = plt.subplots(figsize=(13, 8.5))

        for abbr, (row, col) in GRID.items():
            v = vals.get(abbr)
            has = pd.notna(v)
            y = n_rows - row
            face = cmap(norm(v)) if has else "lightgray"
            ax.add_patch(mpatches.Rectangle((col, y), 0.92, 0.92, facecolor=face,
                                            edgecolor="white", linewidth=1.5))
            text_color = "white" if (has and norm(v) > 0.6) else "black"
            ax.text(col + 0.46, y + 0.58, abbr, ha="center", va="center",
                    fontsize=10, fontweight="bold", color=text_color)
            yu = yr_used.get(abbr)
            note = (f"{v:.1f}" + (f" ('{str(int(yu))[2:]})" if pd.notna(yu) and yu != LATEST_YEAR else "")
                    if has else "n/a")
            ax.text(col + 0.46, y + 0.28, note, ha="center", va="center",
                    fontsize=8, color=text_color if has else "gray")

        ax.set_xlim(-0.3, 11.3)
        ax.set_ylim(-0.3, n_rows + 1.3)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(
            f"Temporary help services as a share of total private employment, "
            f"by state ({LATEST_YEAR})",
            fontsize=14, fontweight="bold", pad=16)

        sm = cm.ScalarMappable(norm=norm, cmap=cmap)
        cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
        cbar.set_label("Temp share of private employment (%)")

        med = vals.median()
        ax.text(0, -0.1,
                f"Range {vmin:.1f}%-{vmax:.1f}%, median {med:.1f}%. Grey = no QWI "
                f"data in {COMPARE_YEAR}-{LATEST_YEAR}. A year tag (e.g. '16) marks "
                f"a state whose latest available year is not {LATEST_YEAR} "
                f"(MI left QWI after 2021; AK after 2016).",
                fontsize=9, color="dimgray")

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"[OK] Saved {output_file}")
        plt.close()

    @staticmethod
    def plot_ranking(df, output_file=f"{OUTPUT_DIR}/temp_penetration_ranking.png"):
        d = df.dropna(subset=["penetration_latest"]).sort_values("penetration_latest").copy()
        stale = d["year_used"] != LATEST_YEAR
        labels = [f"{s} *" if st else s for s, st in zip(d["state"], stale)]

        fig, ax = plt.subplots(figsize=(9, 12))
        national = d["temp_emp_latest"].sum() / d["total_emp_latest"].sum() * 100
        bar_colors = ["darkblue" if v >= national else "#8fb3d9"
                      for v in d["penetration_latest"]]
        ax.barh(labels, d["penetration_latest"], color=bar_colors)
        ax.axvline(national, color="darkred", linestyle="--", linewidth=1.5)
        ax.text(national, len(d) - 0.2, f"  U.S. {national:.1f}%", color="darkred",
                fontsize=9, va="top")
        ax.set_xlabel("Temp help employment as % of total private employment")
        ax.set_title(f"Temp penetration by state, {LATEST_YEAR}", fontsize=14, fontweight="bold")
        ax.margins(y=0.01)
        ax.grid(True, axis="x", alpha=0.3)
        if stale.any():
            tagged = ", ".join(f"{s} ({int(y)})" for s, y, st in
                               zip(d["state"], d["year_used"], stale) if st)
            ax.text(0, -0.045, f"* latest available year, not {LATEST_YEAR}: {tagged}",
                    transform=ax.transAxes, fontsize=8, color="gray")
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"[OK] Saved {output_file}")
        plt.close()


def main():
    api_key = os.environ.get("CENSUS_API_KEY", "")

    print("=" * 70)
    print("TEMP HELP SERVICES PENETRATION BY STATE")
    print("=" * 70)

    analyzer = PenetrationAnalyzer(api_key)
    df = analyzer.build()

    csv_cols = ["rank", "abbr", "state", "year_used",
                "temp_emp_latest", "total_emp_latest", "penetration_latest",
                "penetration_compare", "change_pp"]
    out_csv = f"{OUTPUT_DIR}/temp_penetration_by_state.csv"
    df[csv_cols].to_csv(out_csv, index=False)
    print(f"\n[OK] Saved {out_csv}")

    analyzer.plot_map(df)
    analyzer.plot_ranking(df)

    top = df.head(5)
    bot = df.dropna(subset=["penetration_latest"]).tail(5)
    print("\n" + "=" * 70)
    print(f"HIGHEST PENETRATION ({LATEST_YEAR})")
    print("=" * 70)
    for _, r in top.iterrows():
        print(f"  {r['state']:18} {r['penetration_latest']:.1f}%  "
              f"({r['change_pp']:+.1f} pp since {COMPARE_YEAR})")
    print(f"\nLOWEST PENETRATION ({LATEST_YEAR})")
    for _, r in bot.iterrows():
        print(f"  {r['state']:18} {r['penetration_latest']:.1f}%")

    nat = df["temp_emp_latest"].sum() / df["total_emp_latest"].sum() * 100
    print(f"\nU.S. overall: {nat:.1f}%")
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
