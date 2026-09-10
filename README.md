# Temp Agencies

Analysis of temporary employment agencies and staffing services over time using
**Quarterly Workforce Indicators (QWI)** data from the U.S. Census Bureau. The
project examines national and state-level employment trends, demographic
composition, wages, industry comparisons, and the temp-agency share of the
broader Administrative and Support Services sector.

Primary industry of interest: **NAICS 561320 – Temporary Help Services**.

## Repository layout

```
Temp_agencies/
├── code/       # Python analysis scripts
├── output/     # Generated visualizations (PNG) and data exports (CSV)
├── .env        # Census API key (git-ignored)
├── CLAUDE.md   # Detailed notes for AI-assisted development
└── README.md
```

## Data source

Census QWI API: `https://api.census.gov/data/timeseries/qwi/sa`

| NAICS | Description | Use |
|-------|-------------|-----|
| 561320 | Temporary Help Services | Primary focus (all temp-agency scripts) |
| 561311 | Employment Placement Agencies | Comparison only (`employment_services_over_time.py`) |
| 561312 | Executive Search Services | Comparison only |
| 561330 | Professional Employer Organizations | Comparison only |
| 56 | Administrative and Support Services | Sector-share / wage baseline |
| 00 | Total private sector | Wage comparison baseline |

Required "totals" API parameters: `ownercode=A05, sex=0, agegrp=A00,
education=E0, firmage=0, firmsize=0`. Demographic breakdowns override the
relevant parameter with category-specific codes.

QWI coverage for this industry effectively begins in **2015**; earlier years
return no data even when requested.

## Scripts

**National**

| Script | What it does |
|--------|--------------|
| `temp_agencies_over_time_national.py` | National temp-agency employment timeline (50 states + DC), with sex / age / education breakdowns |
| `temp_agency_share_NAICS56.py` | Temp agency (561320) employment as a share of NAICS 56 |
| `temp_agency_wages.py` | Average earnings (EarnS, EarnHirAS) in temp agencies vs. NAICS 56 and total private; employment-weighted national aggregation |
| `temp_agency_turnover.py` | Job stability and churn (EmpS/Emp, accession/separation/churn rates, stable-hire share) vs. NAICS 56 and total private, 2005--2023 |
| `temp_penetration_by_state.py` | Temp help (561320) as a share of total private employment, by state; tile-grid map + ranked bar, 2023 vs. 2010 |
| `temp_agencies_demographics.py` | National demographic breakdowns (sex, age group, education) |

**California / state-level**

| Script | What it does |
|--------|--------------|
| `temp_agencies_over_time.py` | Quarterly timeline of temp help services (561320) for a single state (default CA), 2005--2024 |
| `employment_services_over_time.py` | Compares four employment-services NAICS codes (561311, 561320, 561312, 561330) for CA |
| `temp_agencies_race_sex.py` | Sex and age distribution snapshot for a single state/quarter (default CA, 2022 Q1) |

## Setup

**Python:** Anaconda (`C:\Users\Sandler\anaconda3\python.exe`, Python 3.11).
Not on PATH — invoke with the full path or activate the conda environment.

**Dependencies:** `requests`, `pandas`, `matplotlib`, `seaborn`

**Census API key:** all scripts read `CENSUS_API_KEY` from the environment
(`os.environ.get("CENSUS_API_KEY", "")`). Store it in `.env` at the repo root
(git-ignored) and load it before running, e.g.:

```bash
export $(grep -v '^#' .env | xargs)   # bash
```

Get a key at https://api.census.gov/data/key_signup.html.

**Output path:** scripts write to the hardcoded location `M:/Temp_agencies`.
Copy results into this repo's `output/` folder to version them.

## Running

Run from the `code/` directory:

```bash
cd code
python temp_agencies_over_time_national.py   # National timeline (~10K API calls, slow)
python temp_agency_share_NAICS56.py          # Sector share (~5.7K API calls)
python temp_agency_wages.py                  # Wage comparison (~8.6K API calls)
python temp_agency_turnover.py               # Turnover / job stability (~150 API calls)
python temp_penetration_by_state.py          # State penetration map (~200 API calls)
python temp_agencies_demographics.py         # Demographics (~400 API calls)
python employment_services_over_time.py      # CA industry comparison
python temp_agencies_over_time.py            # CA single-industry timeline
python temp_agencies_race_sex.py             # CA demographic snapshot
```

The older national scripts issue one request per state × year × quarter and are
rate-limited (~0.08s/request), so a full run takes tens of minutes.
`temp_agency_turnover.py` and `temp_penetration_by_state.py` instead pull a whole
year range per state in one call (`time=from YYYY to YYYY`), so they finish in a
couple of minutes.

## Outputs

Generated into `output/`:

- `national_timeline.png`, `national_temp_employment.csv` — national employment trend
- `sector_share_plot.png`, `temp_agency_sector_share*.csv` — 561320 share of NAICS 56
- `wage_trends.png`, `wage_gap.png`, `temp_agency_wages*.csv` — wage comparison
- `turnover_trends.png`, `turnover_comparison.png`, `temp_agency_turnover*.csv` — job stability / churn
- `temp_penetration_map.png`, `temp_penetration_ranking.png`, `temp_penetration_by_state.csv` — state penetration
- `temp_employment_by_*` — demographic breakdown plots and tables
- `employment_services_over_time.*`, `temp_agencies_over_time.*` — California analyses

## Known issues

- Education-breakdown data returns all zeros — a QWI data-availability limitation.
- `temp_agencies_race_sex.py` analyzes only sex and age despite its filename.
- QWI cells are revised between pulls, so re-running a script can shift values
  slightly versus the committed CSVs.
