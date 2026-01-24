import requests
import pandas as pd
import matplotlib.pyplot as plt
import time

def get_qwi_piece_by_piece(api_key, state_code="06", start_year=2005, end_year=2024):
    url = "https://api.census.gov/data/timeseries/qwi/sa"
    all_rows = []

    print(f"Building timeline for NAICS 561320 (State {state_code})...")

    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5): # Loop through Q1, Q2, Q3, Q4
            print(f"  Fetching {year} Q{quarter}...", end="\r")
            
            params = {
                "get": "Emp,year,quarter",
                "for": f"state:{state_code}",
                "industry": "561311",
                "ownercode": "A05",
                "sex": "0",
                "agegrp": "A00",
                "education": "E0", # Mandatory
                "firmage": "0",    # Mandatory
                "firmsize": "0",   # Mandatory
                "year": str(year),
                "quarter": str(quarter), # Explicit quarter prevents 500 error
                "key": api_key
            }

            try:
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    all_rows.append(data[1][0:3]) # Grab just Emp, year, quarter
                elif response.status_code == 204:
                    pass # Data not yet published for this quarter
                else:
                    print(f"\n  {year} Q{quarter}: Failed ({response.status_code})")
            except Exception as e:
                print(f"\n  Error on {year} Q{quarter}: {e}")
            
            time.sleep(0.05) # Tiny pause

    if not all_rows:
        print("\nNo data retrieved. Verify the industry and state codes.")
        return None

    # Process and Graph
    df = pd.DataFrame(all_rows, columns=['Emp', 'year', 'quarter'])
    df['Emp'] = pd.to_numeric(df['Emp'])
    df['period'] = df['year'] + " Q" + df['quarter']
    df = df.sort_values(['year', 'quarter'])
    
    print("\nSuccess! Plotting data...")
    return df

# --- Run ---
API_KEY = ""
df_final = get_qwi_piece_by_piece(API_KEY)

OUTPUT_DIR = "M:/Temp_agencies"

if df_final is not None:
    plt.figure(figsize=(10, 5))
    plt.plot(df_final['period'], df_final['Emp'], marker='o', color='darkblue', linewidth=2)
    plt.title('NAICS 561311: Employment Over Time - California (Quarterly)')
    plt.xticks(rotation=45)
    plt.ylabel('Total Employees')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/temp_agencies_over_time.png", dpi=300, bbox_inches='tight')
    print(f"Saved plot to {OUTPUT_DIR}/temp_agencies_over_time.png")
    df_final.to_csv(f"{OUTPUT_DIR}/temp_agencies_over_time.csv", index=False)
    print(f"Saved data to {OUTPUT_DIR}/temp_agencies_over_time.csv")
    plt.close()