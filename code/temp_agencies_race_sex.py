import requests
import pandas as pd
import matplotlib.pyplot as plt
import time
import os

def get_demographic_snapshot(api_key, state="06", year="2022", quarter="1"):
    url = "https://api.census.gov/data/timeseries/qwi/sa"
    base_params = {
        "for": f"state:{state}",
        "industry": "561320",
        "ownercode": "A05",
        "year": year,
        "quarter": quarter,
        "education": "E0",
        "firmage": "0",
        "firmsize": "0",
        "key": api_key
    }

    # Helper to fetch individual category
    def fetch_single(params):
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            d = r.json()
            if len(d) > 1:
                return d[1]
        return None

    # 1. Fetch Sex Distribution - individual calls
    sex_data = []
    for sex_val in ['1', '2']:
        params = base_params.copy()
        params.update({"get": "Emp", "agegrp": "A00", "sex": sex_val})
        result = fetch_single(params)
        if result:
            sex_data.append({'Emp': result[0], 'sex': sex_val})
        time.sleep(0.1)

    # 2. Fetch Age Distribution - individual calls
    age_codes = ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08']
    age_data = []
    for age_val in age_codes:
        params = base_params.copy()
        params.update({"get": "Emp", "sex": "0", "agegrp": age_val})
        result = fetch_single(params)
        if result:
            age_data.append({'Emp': result[0], 'agegrp': age_val})
        time.sleep(0.1)

    df_sex = pd.DataFrame(sex_data) if sex_data else None
    df_age = pd.DataFrame(age_data) if age_data else None

    return df_sex, df_age

# --- Run and Plot ---
MY_KEY = os.environ.get("CENSUS_API_KEY", "")
print("Fetching demographic data from Census QWI API...")
df_sex, df_age = get_demographic_snapshot(MY_KEY)

# Save outputs straight into the repo's output/ folder (this file lives in code/)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

if df_sex is not None and df_age is not None:
    # Mapping Labels
    sex_map = {"1": "Male", "2": "Female"}
    age_map = {"A01": "14-18", "A02": "19-21", "A03": "22-24", "A04": "25-34",
               "A05": "35-44", "A06": "45-54", "A07": "55-64", "A08": "65-99"}

    df_sex['label'] = df_sex['sex'].map(sex_map)
    df_age['label'] = df_age['agegrp'].map(age_map)
    df_sex['Emp'] = pd.to_numeric(df_sex['Emp'])
    df_age['Emp'] = pd.to_numeric(df_age['Emp'])

    print(f"Sex data: {len(df_sex)} records")
    print(f"Age data: {len(df_age)} records")

    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Sex Chart
    ax1.pie(df_sex['Emp'], labels=df_sex['label'], autopct='%1.1f%%', colors=['#3498db', '#e74c3c'])
    ax1.set_title('Sex Distribution - California (NAICS 561320)')

    # Age Chart
    ax2.bar(df_age['label'], df_age['Emp'], color='#2ecc71')
    ax2.set_title('Age Distribution - California (NAICS 561320)')
    ax2.set_ylabel('Number of Employees')
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/temp_agencies_race_sex.png", dpi=300, bbox_inches='tight')
    print(f"Saved plot to {OUTPUT_DIR}/temp_agencies_race_sex.png")
    df_sex.to_csv(f"{OUTPUT_DIR}/temp_agencies_sex.csv", index=False)
    df_age.to_csv(f"{OUTPUT_DIR}/temp_agencies_age.csv", index=False)
    print(f"Saved data to {OUTPUT_DIR}/")
    plt.close()
else:
    print("Failed to retrieve data")
