"""
Occupational mix of temporary help services (NAICS 561320).

What jobs are temp-agency workers actually placed in, and what do those jobs
pay? Source: BLS Occupational Employment and Wage Statistics (OEWS),
national industry-specific estimates, May 2025.

OEWS is NOT available through the BLS public time-series API (industry x
occupation series return no data), and www.bls.gov blocks scripted file
downloads. The estimates here were captured from the OEWS query system
(https://data.bls.gov/oes/#/industry/561320/2025) and saved verbatim to
output/oews_561320_may2025.csv; refresh that file from the same page when a
newer May-year is published.

Blank employment / wage cells are BLS non-disclosure (footnotes 8 / 4).

Outputs (to output/):
    oews_561320_major_groups.csv   major SOC groups: employment, share, wages
    oews_occupation_mix.png        occupational mix bar chart
    oews_occupation_pay.png        employment share vs. annual mean wage
    oews_top_occupations.png       largest detailed occupations
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

sns.set_style("whitegrid")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_CSV = os.path.join(REPO, "output", "oews_561320_may2025.csv")
OUTPUT_DIR = os.path.join(REPO, "output")
PERIOD = "May 2025"


def load():
    df = pd.read_csv(SRC_CSV)
    for c in ("employment", "annual_mean_wage", "annual_median_wage"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def major_groups(df):
    total = df.loc[df["soc"] == "00-0000", "employment"].iloc[0]
    mg = df[(df["level"] == "major") & (df["soc"] != "00-0000")].copy()
    mg["share"] = mg["employment"] / total * 100
    mg["group"] = mg["occupation"].str.replace(" Occupations", "", regex=False)
    return total, mg.sort_values("share", ascending=False)


def plot_mix(total, mg, output_file=f"{OUTPUT_DIR}/oews_occupation_mix.png"):
    top = mg.head(13).copy()
    other = mg.iloc[13:]["employment"].sum()
    if other > 0:
        top = pd.concat([top, pd.DataFrame([{
            "group": "All other groups", "employment": other,
            "share": other / total * 100, "annual_mean_wage": None}])], ignore_index=True)

    fig, ax = plt.subplots(figsize=(11, 7))
    order = top.iloc[::-1]
    colors = ["#8c1515" if g in ("Transportation and Material Moving", "Production")
              else "#33608c" for g in order["group"]]
    ax.barh(order["group"], order["share"], color=colors)
    for y, (s, e) in enumerate(zip(order["share"], order["employment"])):
        ax.text(s + 0.3, y, f"{s:.1f}%  ({e/1000:,.0f}k)", va="center", fontsize=8)

    ax.set_xlabel("Share of temp-help employment (%)")
    ax.set_title(f"What temp-agency workers do: occupational mix of NAICS 561320\n"
                 f"OEWS {PERIOD}, {total/1e6:.2f} million jobs", fontsize=13, fontweight="bold")
    ax.margins(x=0.18)
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"[OK] {output_file}")
    plt.close()


def plot_pay(total, mg, all_mean, output_file=f"{OUTPUT_DIR}/oews_occupation_pay.png"):
    d = mg.dropna(subset=["annual_mean_wage"]).copy()
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.scatter(d["share"], d["annual_mean_wage"], s=60, color="#33608c", zorder=3)
    for _, r in d.iterrows():
        if r["share"] > 3 or r["annual_mean_wage"] > 120000:
            ax.annotate(r["group"], (r["share"], r["annual_mean_wage"]),
                        xytext=(6, 0), textcoords="offset points", fontsize=8, va="center")
    ax.axhline(all_mean, color="darkred", linestyle="--", linewidth=1.2)
    ax.text(ax.get_xlim()[1], all_mean, f"  all-occupation mean ${all_mean:,.0f}",
            color="darkred", fontsize=8, va="bottom", ha="right")
    ax.set_xlabel("Share of temp-help employment (%)")
    ax.set_ylabel("Annual mean wage ($)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
    ax.set_title(f"Temp help concentrates in its lowest-paid occupations\n"
                 f"major SOC groups, OEWS {PERIOD}", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"[OK] {output_file}")
    plt.close()


def plot_top_occupations(df, total, output_file=f"{OUTPUT_DIR}/oews_top_occupations.png"):
    det = df[df["level"] == "detail"].dropna(subset=["employment"]).copy()
    det = det.sort_values("employment", ascending=False).head(14)
    det["short"] = det["occupation"].str.replace(r",.*", "", regex=True).str.slice(0, 42)
    det["share"] = det["employment"] / total * 100

    fig, ax = plt.subplots(figsize=(11, 7))
    order = det.iloc[::-1]
    ax.barh(order["short"], order["employment"] / 1000, color="#33608c")
    for y, (e, w) in enumerate(zip(order["employment"], order["annual_mean_wage"])):
        lbl = f"{e/1000:,.0f}k" + (f"  ·  ${w/1000:,.0f}k/yr" if pd.notna(w) else "")
        ax.text(e / 1000 + 3, y, lbl, va="center", fontsize=8)
    ax.set_xlabel("Employment (thousands)")
    ax.set_title(f"Largest detailed occupations in temp help (NAICS 561320)\n"
                 f"OEWS {PERIOD}", fontsize=13, fontweight="bold")
    ax.margins(x=0.16)
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"[OK] {output_file}")
    plt.close()


def main():
    df = load()
    total, mg = major_groups(df)
    all_mean = df.loc[df["soc"] == "00-0000", "annual_mean_wage"].iloc[0]

    out_csv = f"{OUTPUT_DIR}/oews_561320_major_groups.csv"
    mg[["soc", "group", "employment", "share", "annual_mean_wage", "annual_median_wage"]] \
        .to_csv(out_csv, index=False)
    print(f"[OK] {out_csv}")

    plot_mix(total, mg, )
    plot_pay(total, mg, all_mean)
    plot_top_occupations(df, total)

    print("\n" + "=" * 70)
    print(f"OEWS {PERIOD} - NAICS 561320, {total:,.0f} jobs, "
          f"all-occ mean ${all_mean:,.0f}/yr")
    print("=" * 70)
    blue = mg[mg["soc"].isin(["53-0000", "51-0000", "47-0000", "49-0000",
                              "37-0000", "45-0000"])]["share"].sum()
    print(f"Blue-collar groups (53/51/47/49/37/45): {blue:.0f}% of employment")
    for _, r in mg.head(8).iterrows():
        print(f"  {r['group']:38} {r['share']:5.1f}%   ${r['annual_mean_wage']:>8,.0f}/yr"
              if pd.notna(r["annual_mean_wage"])
              else f"  {r['group']:38} {r['share']:5.1f}%")


if __name__ == "__main__":
    main()
