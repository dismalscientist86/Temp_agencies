# Project Overview

Analysis of temporary employment agencies over time using Quarterly Workforce Indicators (QWI) data with 6-digit NAICS codes.

## Structure

- `code/` - Python analysis scripts
- `output/` - Generated visualizations (PNG) and data exports (CSV)

## Code Files

- `temp_agencies_over_time.py` - Basic temporal analysis of temp agencies
- `temp_agencies_over_time_national.py` - National-level temporal analysis
- `employment_services_over_time.py` - Broader employment services trends
- `temp_agencies_demographics.py` - Demographic breakdowns (age, education)
- `temp_agencies_race_sex.py` - Race and sex analysis
- `temp_agency_share_NAICS56.py` - Temp agency share within NAICS 56 sector

## Data Source

QWI (Quarterly Workforce Indicators) from the U.S. Census Bureau, filtered to NAICS 561320 (Temporary Help Services).

## Running Scripts

Scripts are standalone Python files. Run from the `code/` directory:
```bash
python <script_name>.py
```

Output files are saved to the `output/` directory.
