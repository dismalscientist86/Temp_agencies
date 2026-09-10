# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Analysis of temporary employment agencies and staffing services over time using Quarterly Workforce Indicators (QWI) data from the U.S. Census Bureau. Examines national and state-level employment trends, demographic composition, industry comparisons, and temp agency share within the broader Administrative and Support Services sector.

## Structure

```
Temp_agencies/
├── code/           # Python analysis scripts (7 files)
├── output/         # Generated visualizations (PNG) and data exports (CSV)
├── .env            # Census API key (git-ignored)
├── .gitignore
├── CLAUDE.md
└── README.md
```

## Code Files

**National analyses:**
- `temp_agencies_over_time_national.py`: National temp agency employment timeline (all 50 states + DC aggregated). Class-based (`QWITempAgencyAnalyzer`). NAICS 561320. Recession shading on the plot. Also has sex/age/education breakdown code, but education is unavailable (see Known Issues) — use `temp_agencies_demographics.py` for demographics.
- `temp_agency_share_NAICS56.py`: Temp agency (561320) employment as share of NAICS 56 (Administrative and Support Services). Class-based (`SectorShareAnalyzer`). Dual-panel plots showing absolute levels and share percentage.
- `temp_agency_wages.py`: Compares average earnings (EarnS, EarnHirAS) in temp agencies (561320) against NAICS 56 and total private sector. Class-based (`WageAnalyzer`). Employment-weighted national aggregation. 3-panel wage trends plot and wage gap visualization. Outputs quarterly and annual CSVs.
- `temp_agency_turnover.py`: Job stability and churn vs. NAICS 56 and total private, 2005-2023. Class-based (`TurnoverAnalyzer`). Pulls QWI counts (Emp, EmpEnd, EmpS, HirA, HirN, Sep, HirAs, SepS), sums to national, derives rates: stable_share (EmpS/Emp), accession/separation/churn rates, stable_hire_share (HirAs/HirA). 3-panel trends + comparison bar. Uses `time=from YYYY to YYYY` batching (one call per state).
- `temp_penetration_by_state.py`: Temp help (561320) as a share of total private (00) employment by state. Class-based (`PenetrationAnalyzer`). Tile-grid (`GRID`) choropleth in pure matplotlib (no geo deps) + ranked bar. Compares LATEST_YEAR (2023) with COMPARE_YEAR (2010). One call per state per industry per year.
- `temp_agencies_demographics.py`: National demographic breakdowns for one quarter (default 2023 Q1). Class-based (`TempAgencyDemographics`). Sex and age come from the `qwi/sa` dataset; race and ethnicity from `qwi/rh` (they are not on `sa`). Sums per-category employment across states. Education is not attempted — it lives only on `qwi/se` for the 25+ restriction and is fully suppressed for NAICS 561320.

**State-level analyses (California):**
- `temp_agencies_over_time.py`: Basic quarterly timeline of temp help services (NAICS 561320) for a single state (default CA), 2005-2024. Plots with one x-axis label per year.
- `employment_services_over_time.py`: Compares 4 NAICS codes within employment services (561311, 561320, 561312, 561330) for California.

**Demographic snapshots:**
- `temp_agencies_race_sex.py`: Sex and age distribution snapshot (despite filename, does not analyze race). Single state (CA), single quarter (default 2022 Q1).

## Data Source

**Census QWI API:** `https://api.census.gov/data/timeseries/qwi/sa`

**Key NAICS codes used:**
- 561320: Temporary Help Services (primary focus, used by national scripts)
- 561311: Employment Placement Agencies (comparison only, in `employment_services_over_time.py`)
- 561312: Executive Search Services (comparison only)
- 561330: Professional Employer Organizations (comparison only)
- 00: Total private sector (used by `temp_agency_wages.py` for wage comparison baseline)

**Required API parameters:** `ownercode=A05, sex=0, agegrp=A00, education=E0, firmage=0, firmsize=0` (totals). Demographic breakdowns override the relevant parameter with category-specific codes.

## Setup and Configuration

**Python:** Anaconda at `C:\Users\Sandler\anaconda3\python.exe` (Python 3.11.7, conda 24.5.0). Not on PATH — invoke with full path or activate the conda environment first.

**Census API key:** All scripts read from the `CENSUS_API_KEY` environment variable via `os.environ.get("CENSUS_API_KEY", "")`. The key is stored in `.env` at the repo root (git-ignored). To obtain a key: https://api.census.gov/data/key_signup.html. To load the `.env` before running, either `set` the variable in your shell or use a tool like `python-dotenv`.

**Output path:** Scripts save to `M:/Temp_agencies` (hardcoded). The `output/` directory in the repo contains previously generated results.

**Dependencies:** requests, pandas, matplotlib, seaborn

## Running Scripts

Scripts are standalone. Run from the `code/` directory:
```bash
cd code
python temp_agencies_over_time_national.py   # National timeline (~10K API calls, slow)
python temp_agency_share_NAICS56.py          # Sector share (~5.7K API calls)
python temp_agency_wages.py                  # Wage comparison (~8.6K API calls)
python temp_agency_turnover.py               # Turnover / job stability (~150 API calls, fast)
python temp_penetration_by_state.py          # State penetration map (~200 API calls, fast)
python temp_agencies_demographics.py         # Sex/age/race/ethnicity (~900 API calls)
python employment_services_over_time.py      # CA industry comparison
python temp_agencies_over_time.py            # CA single-industry timeline
python temp_agencies_race_sex.py             # CA demographic snapshot
```

The older national scripts issue one request per state/year/quarter and are rate-limited, so they take tens of minutes. `temp_agency_turnover.py` and `temp_penetration_by_state.py` pull a whole year range per state in one call (`time=from YYYY to YYYY`) and finish in a couple of minutes — the preferred pattern for new scripts.

## Known Issues

- No education breakdown: QWI education is only on the `se` dataset for the 25+ restriction and is fully suppressed for NAICS 561320 at state level
- `temp_agencies_race_sex.py` filename is misleading — it only analyzes sex and age, not race
- QWI revises published cells between pulls, so re-running a script can shift values slightly versus the committed CSVs
