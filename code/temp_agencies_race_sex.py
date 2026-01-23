import requests
import pandas as pd
import matplotlib.pyplot as plt

def get_demographic_snapshot(api_key, state="06", year="2023", quarter="1"):
    url = "https://api.census.gov/data/timeseries/qwi/sa"
    base_params = {
        "for": f"state:{state}",
        "industry": "561320",
        "ownercode": "A05",
        "year": year,
        "quarter": quarter,
        "key": api_key
    }

    # 1. Fetch Sex Distribution (Keep Age at Total A00)
    sex_params = base_params.copy()
    sex_params.update({"get": "Emp,sex", "agegrp": "A00", "sex": "1,2"})
    
    # 2. Fetch Age Distribution (Keep Sex at Total 0)
    age_params = base_params.copy()
    age_params.update({"get": "Emp,agegrp", "sex": "0", "agegrp": "A01,A02,A03,A04,A05,A06,A07,A08"})

    # Helper to execute and clean
    def fetch_and_clean(p):
        r = requests.get(url, params=p)
        if r.status_code == 200:
            d = r.json()
            return pd.DataFrame(d[1:], columns=d[0])
        return None

    df_sex = fetch_and_clean(sex_params)
    df_age = fetch_and_clean(age_params)

    return df_sex, df_age

# --- Run and Plot ---
MY_KEY = "3192f7e1f6c2306861d2b03c9a6ae895ff43c788"
df_sex, df_age = get_demographic_snapshot(MY_KEY)

OUTPUT_DIR = "/m/Temp_agencies"

if df_sex is not None and df_age is not None:
    # Mapping Labels
    sex_map = {"1": "Male", "2": "Female"}
    age_map = {"A01": "14-18", "A02": "19-21", "A03": "22-24", "A04": "25-34",
               "A05": "35-44", "A06": "45-54", "A07": "55-64", "A08": "65-99"}

    df_sex['label'] = df_sex['sex'].map(sex_map)
    df_age['label'] = df_age['agegrp'].map(age_map)
    df_sex['Emp'] = pd.to_numeric(df_sex['Emp'])
    df_age['Emp'] = pd.to_numeric(df_age['Emp'])

    # Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Sex Chart
    ax1.pie(df_sex['Emp'], labels=df_sex['label'], autopct='%1.1f%%', colors=['#3498db', '#e74c3c'])
    ax1.set_title('Sex Distribution (NAICS 561320)')

    # Age Chart
    ax2.bar(df_age['label'], df_age['Emp'], color='#2ecc71')
    ax2.set_title('Age Distribution (NAICS 561320)')
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