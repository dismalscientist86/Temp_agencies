"""
Temp agency (NAICS 561320) demographic breakdowns, national.

For a single quarter, pull QWI employment for each demographic category from
every state and sum to a national total (small state x category cells are
suppressed, so totals rest on the states that report).

Endpoints (worker characteristics differ by QWI dataset):
    sa  -- sex x age            -> sex, agegrp breakdowns
    rh  -- race x ethnicity     -> race, ethnicity breakdowns

Education (E1-E5) is published only on the `se` dataset and only for the
25+ age restriction; for NAICS 561320 every state-level cell is suppressed,
so an education breakdown is not obtainable and is not attempted here.

Outputs (to output/), one set per demographic:
    temp_employment_by_{demo}_{YEAR}_Q{QUARTER}.csv
    temp_employment_by_{demo}_{YEAR}_Q{QUARTER}.png
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
from typing import Optional
import os

sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)

# Save outputs straight into the repo's output/ folder (this file lives in code/)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


class TempAgencyDemographics:
    """National QWI demographic breakdowns for temporary help services."""

    TEMP_NAICS = "561320"

    STATES = [
        '01', '02', '04', '05', '06', '08', '09', '10', '11', '12',
        '13', '15', '16', '17', '18', '19', '20', '21', '22', '23',
        '24', '25', '26', '27', '28', '29', '30', '31', '32', '33',
        '34', '35', '36', '37', '38', '39', '40', '41', '42', '44',
        '45', '46', '47', '48', '49', '50', '51', '53', '54', '55', '56'
    ]

    # demographic -> (QWI dataset, parameter name, ordered categories, labels)
    SPECS = {
        "sex": ("sa", "sex",
                ["1", "2"],
                {"1": "Male", "2": "Female"}),
        "agegrp": ("sa", "agegrp",
                   ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08"],
                   {"A01": "14-18", "A02": "19-21", "A03": "22-24", "A04": "25-34",
                    "A05": "35-44", "A06": "45-54", "A07": "55-64", "A08": "65+"}),
        "race": ("rh", "race",
                 ["A1", "A2", "A3", "A4", "A5", "A7"],
                 {"A1": "White", "A2": "Black", "A3": "Am. Indian / AK Native",
                  "A4": "Asian", "A5": "Hawaiian / Pac. Isl.", "A7": "Two or more"}),
        "ethnicity": ("rh", "ethnicity",
                      ["A1", "A2"],
                      {"A1": "Not Hispanic", "A2": "Hispanic"}),
    }

    PLOT_COLOR = {"sex": "steelblue", "agegrp": "coral",
                  "race": "mediumpurple", "ethnicity": "seagreen"}

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _base_params(self, dataset: str, state: str, year: int, quarter: int) -> dict:
        p = {
            "get": "Emp",
            "for": f"state:{state}",
            "industry": self.TEMP_NAICS,
            "ownercode": "A05",
            "sex": "0", "agegrp": "A00",
            "firmage": "0", "firmsize": "0",
            "year": str(year), "quarter": str(quarter),
            "key": self.api_key,
        }
        if dataset == "rh":
            p["race"] = "A0"
            p["ethnicity"] = "A0"
        else:  # sa / se also accept education
            p["education"] = "E0"
        return p

    def get_breakdown(self, demographic: str, year: int, quarter: int) -> Optional[pd.DataFrame]:
        dataset, param, codes, labels = self.SPECS[demographic]
        url = f"https://api.census.gov/data/timeseries/qwi/{dataset}"
        suppressed = {"", "N", "D", "S", None}

        print(f"\n{demographic}: {len(self.STATES)} states x {len(codes)} categories "
              f"= {len(self.STATES) * len(codes)} requests  (qwi/{dataset})")

        rows = []
        for code in codes:
            emp_total = 0
            states_with_data = 0
            for state in self.STATES:
                params = self._base_params(dataset, state, year, quarter)
                params[param] = code
                try:
                    r = requests.get(url, params=params, timeout=15)
                    if r.status_code == 200:
                        data = r.json()
                        if len(data) > 1:
                            v = data[1][0]
                            if v not in suppressed:
                                emp_total += int(v)
                                states_with_data += 1
                except Exception:
                    pass
                time.sleep(0.05)
            rows.append({"category": labels[code], "code": code,
                         "employment": emp_total, "states_with_data": states_with_data})
            print(f"  {labels[code]:24s} {emp_total:>11,}  ({states_with_data} states)")

        df = pd.DataFrame(rows)
        if df["employment"].sum() == 0:
            print(f"  [WARN] no unsuppressed data for {demographic}")
            return None
        df["percentage"] = (df["employment"] / df["employment"].sum() * 100).round(2)
        return df

    def plot(self, df: pd.DataFrame, demographic: str, year: int, quarter: int):
        titles = {"sex": "Sex", "agegrp": "Age group",
                  "race": "Race", "ethnicity": "Ethnicity"}
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(df["category"], df["percentage"],
               color=self.PLOT_COLOR.get(demographic, "steelblue"),
               edgecolor="black", linewidth=0.5)
        for i, (pct, n) in enumerate(zip(df["percentage"], df["states_with_data"])):
            ax.text(i, pct, f"{pct:.1f}%", ha="center", va="bottom", fontsize=9)
        ax.set_title(f"Temp help services (NAICS 561320) workers by "
                     f"{titles[demographic].lower()} - national ({year} Q{quarter})",
                     fontsize=13, fontweight="bold")
        ax.set_ylabel("Percentage of workforce")
        ax.set_xlabel(titles[demographic])
        ax.grid(axis="y", alpha=0.3)
        plt.xticks(rotation=30, ha="right")
        n_states = int(df["states_with_data"].min())
        ax.text(0.99, -0.18, f"Sum of {n_states}-{int(df['states_with_data'].max())} "
                             f"reporting states; suppressed cells excluded.",
                transform=ax.transAxes, ha="right", fontsize=8, color="gray")
        plt.tight_layout()
        fname = f"{OUTPUT_DIR}/temp_employment_by_{demographic}_{year}_Q{quarter}.png"
        plt.savefig(fname, dpi=300, bbox_inches="tight")
        print(f"  [OK] {fname}")
        plt.close()


def main():
    api_key = os.environ.get("CENSUS_API_KEY", "")
    YEAR, QUARTER = 2023, 1

    print("=" * 70)
    print(f"TEMP AGENCY DEMOGRAPHICS - NATIONAL ({YEAR} Q{QUARTER})")
    print("=" * 70)

    analyzer = TempAgencyDemographics(api_key)
    results = {}

    for demo in ["sex", "agegrp", "race", "ethnicity"]:
        print("\n" + "=" * 70)
        df = analyzer.get_breakdown(demo, YEAR, QUARTER)
        if df is None:
            continue
        csv = f"{OUTPUT_DIR}/temp_employment_by_{demo}_{YEAR}_Q{QUARTER}.csv"
        df.to_csv(csv, index=False)
        print(f"  [OK] {csv}")
        analyzer.plot(df, demo, YEAR, QUARTER)
        results[demo] = df

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for demo, df in results.items():
        print(f"\n{demo.upper()}")
        print(df[["category", "employment", "percentage", "states_with_data"]].to_string(index=False))

    print("\nNote: education (E1-E5) is suppressed for NAICS 561320 at the state "
          "level in QWI and cannot be tabulated.")
    print("=" * 70)


if __name__ == "__main__":
    main()
