import requests
import pandas as pd
import matplotlib.pyplot as plt
import time
import os

def get_qwi_data_for_naics(api_key, naics_code, state_code="06", start_year=2005, end_year=2024):
    url = "https://api.census.gov/data/timeseries/qwi/sa"
    all_rows = []

    print(f"Fetching data for NAICS {naics_code} (State {state_code})...")

    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5):
            params = {
                "get": "Emp,year,quarter",
                "for": f"state:{state_code}",
                "industry": naics_code,
                "ownercode": "A05",
                "sex": "0",
                "agegrp": "A00",
                "education": "E0", # Mandatory
                "firmage": "0",    # Mandatory
                "firmsize": "0",   # Mandatory
                "year": str(year),
                "quarter": str(quarter),
                "key": api_key
            }

            try:
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    all_rows.append(data[1][0:3])  # Emp, year, quarter
                elif response.status_code == 204:
                    pass
                else:
                    print(f"\n  {year} Q{quarter}: Failed ({response.status_code})")
            except Exception as e:
                print(f"\n  Error on {year} Q{quarter}: {e}")

            time.sleep(0.05)

    if not all_rows:
        print(f"\nNo data retrieved for NAICS {naics_code}.")
        return None

    df = pd.DataFrame(all_rows, columns=['Emp', 'year', 'quarter'])
    df['Emp'] = pd.to_numeric(df['Emp'])
    df['year'] = df['year'].astype(str)
    df['quarter'] = df['quarter'].astype(str)
    df['period'] = df['year'] + " Q" + df['quarter']
    df = df.sort_values(['year', 'quarter']).reset_index(drop=True)
    return df

# --- Run ---
API_KEY = os.environ.get("CENSUS_API_KEY", "")
naics_codes = {"561311": "Employment Placement Agencies", "561320": "Temporary Help Services", "561312": "Executive Search Services", "561330" : "Professional Employer Organizations" }

# Pull data for both NAICS codes
dfs = {}
for code, label in naics_codes.items():
    dfs[code] = get_qwi_data_for_naics(API_KEY, code)

# Merge on period
df_merged = dfs["561311"][["period", "Emp"]].rename(columns={"Emp": "561311"})
df_merged = df_merged.merge(dfs["561320"][["period", "Emp"]].rename(columns={"Emp": "561320"}), on="period")
df_merged = df_merged.merge(dfs["561312"][["period", "Emp"]].rename(columns={"Emp": "561312"}), on="period")
df_merged = df_merged.merge(dfs["561330"][["period", "Emp"]].rename(columns={"Emp": "561330"}), on="period")

# Save outputs straight into the repo's output/ folder (this file lives in code/)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

# Plot with cleaned-up x-axis
plt.figure(figsize=(12, 6))
plt.plot(df_merged['period'], df_merged['561311'], marker='o', label='Employment Services (561311)')
plt.plot(df_merged['period'], df_merged['561320'], marker='s', label='Temporary Help Services (561320)')
plt.plot(df_merged['period'], df_merged['561312'], marker='o', label='Executive Search Services (561312)')
plt.plot(df_merged['period'], df_merged['561330'], marker='s', label='Professional Employer Organization (561330)')

plt.title('Employment Over Time by NAICS Code - California (Quarterly)')
plt.ylabel('Total Employees')
plt.xlabel('Period')
plt.grid(True, alpha=0.3)
plt.legend()

# Clean up x-axis: label every 4th quarter
xticks_positions = range(0, len(df_merged), 4)  # every 4th quarter
xticks_labels = [df_merged['period'].iloc[i] for i in xticks_positions]
plt.xticks(ticks=xticks_positions, labels=xticks_labels, rotation=45)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/employment_services_over_time.png", dpi=300, bbox_inches='tight')
print(f"Saved plot to {OUTPUT_DIR}/employment_services_over_time.png")
df_merged.to_csv(f"{OUTPUT_DIR}/employment_services_over_time.csv", index=False)
print(f"Saved data to {OUTPUT_DIR}/employment_services_over_time.csv")
plt.close()

