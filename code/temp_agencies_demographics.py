"""
Temp Agency Demographic Analysis - CORRECTED VERSION

Key fix: Remove race/ethnicity parameters that were causing issues
"""

import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
from typing import Optional
import sys

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

class TempAgencyDemographicsCorrected:
    """Demographic analysis using exact parameters that worked for timeline"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.census.gov/data/timeseries/qwi/sa"
        self.temp_naics = "561320"
        
        self.states = [
            '01', '02', '04', '05', '06', '08', '09', '10', '11', '12',
            '13', '15', '16', '17', '18', '19', '20', '21', '22', '23',
            '24', '25', '26', '27', '28', '29', '30', '31', '32', '33',
            '34', '35', '36', '37', '38', '39', '40', '41', '42', '44',
            '45', '46', '47', '48', '49', '50', '51', '53', '54', '55', '56'
        ]
    
    def get_demographic_breakdown(
        self,
        demographic_var: str,
        year: int,
        quarter: int
    ) -> Optional[pd.DataFrame]:
        """
        Get demographic breakdown WITHOUT race/ethnicity parameters
        """
        
        # Categories we can query
        categories = {
            'sex': ['1', '2'],
            'agegrp': ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08'],
            'education': ['E1', 'E2', 'E3', 'E4', 'E5']
        }
        
        labels = {
            'sex': {
                '1': 'Male',
                '2': 'Female'
            },
            'agegrp': {
                'A01': '14-18',
                'A02': '19-21', 
                'A03': '22-24',
                'A04': '25-34',
                'A05': '35-44',
                'A06': '45-54',
                'A07': '55-64',
                'A08': '65+'
            },
            'education': {
                'E1': 'Less than HS',
                'E2': 'High School',
                'E3': 'Some College',
                'E4': "Bachelor's",
                'E5': 'Advanced Degree'
            }
        }
        
        if demographic_var not in categories:
            print(f"Invalid demographic variable. Choose from: {list(categories.keys())}")
            return None
        
        print(f"\nFetching {demographic_var} breakdown for {year} Q{quarter}...")
        print(f"Querying {len(self.states)} states × {len(categories[demographic_var])} categories = {len(self.states) * len(categories[demographic_var])} requests")
        print()
        
        all_data = []
        request_count = 0
        total_requests = len(self.states) * len(categories[demographic_var])
        
        for category_code in categories[demographic_var]:
            category_label = labels[demographic_var].get(category_code, category_code)
            category_employment = []
            states_with_data = []
            
            for state in self.states:
                request_count += 1
                
                if request_count % 20 == 0:
                    print(f"  Progress: {request_count}/{total_requests}...", end="\r")
                
                # Build parameters - EXACT format from working timeline query
                params = {
                    "get": "Emp",
                    "for": f"state:{state}",
                    "industry": self.temp_naics,
                    "ownercode": "A05",
                    "firmage": "0",
                    "firmsize": "0",
                    "year": str(year),
                    "quarter": str(quarter),
                    "key": self.api_key
                }
                
                # Set the demographic filter we're analyzing
                if demographic_var == 'sex':
                    params['sex'] = category_code
                    params['agegrp'] = 'A00'
                    params['education'] = 'E0'
                elif demographic_var == 'agegrp':
                    params['sex'] = '0'
                    params['agegrp'] = category_code
                    params['education'] = 'E0'
                elif demographic_var == 'education':
                    params['sex'] = '0'
                    params['agegrp'] = 'A00'
                    params['education'] = category_code
                
                # CRITICAL: Do NOT include race or ethnicity parameters
                
                try:
                    response = requests.get(self.base_url, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if len(data) > 1:
                            emp = data[1][0]
                            if emp and emp not in ['', 'N', 'D', 'S']:
                                category_employment.append(int(emp))
                                states_with_data.append(state)
                    
                except Exception as e:
                    pass  # Skip errors silently
                
                time.sleep(0.1)
            
            total_emp = sum(category_employment)
            
            all_data.append({
                'category': category_label,
                'code': category_code,
                'employment': total_emp,
                'states_with_data': len(states_with_data)
            })
            
            print(f"  {category_label:30s}: {total_emp:>10,} (from {len(states_with_data)} states)")
        
        print()
        
        if not all_data or sum(d['employment'] for d in all_data) == 0:
            print(f"  [WARN] No data available for {demographic_var}")
            return None
        
        df = pd.DataFrame(all_data)
        total_employment = df['employment'].sum()
        df['percentage'] = (df['employment'] / total_employment * 100).round(2)
        
        print(f"Total employment: {total_employment:,}")
        print(f"Average states with data per category: {df['states_with_data'].mean():.1f}")
        
        return df
    
    def create_visualization(self, df: pd.DataFrame, demographic_var: str, 
                            year: int, quarter: int):
        """Create bar chart"""
        if df is None or len(df) == 0:
            return
        
        var_names = {
            'sex': 'Gender',
            'agegrp': 'Age Group',
            'education': 'Education Level'
        }
        
        colors = {
            'sex': 'steelblue',
            'agegrp': 'coral',
            'education': 'seagreen'
        }
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(df['category'], df['percentage'], 
               color=colors.get(demographic_var, 'steelblue'), 
               edgecolor='black', linewidth=0.5)
        
        ax.set_title(f'Temp Agency Workers by {var_names[demographic_var]} - National ({year} Q{quarter})', 
                     fontsize=14, fontweight='bold')
        ax.set_xlabel(var_names[demographic_var], fontsize=12)
        ax.set_ylabel('Percentage of Workforce', fontsize=12)
        ax.grid(axis='y', alpha=0.3)
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        filename = f'M:/Temp_agencies/temp_employment_by_{demographic_var}_{year}_Q{quarter}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"[OK] Saved plot: {filename}")
        plt.close()


def main():
    """Main analysis for demographic breakdowns"""
    
    API_KEY = ""
    
    # Use the same year range that worked for timeline: 2015-2023
    # Start with most recent and work backwards
    YEAR = 2023
    QUARTER = 1  # Start with Q1, can try other quarters if needed
    
    print("="*70)
    print("TEMP AGENCY DEMOGRAPHIC ANALYSIS - CORRECTED VERSION")
    print("="*70)
    print(f"\nAnalyzing: {YEAR} Q{QUARTER}")
    print(f"(Based on parameters that worked for national timeline)")
    print()
    
    analyzer = TempAgencyDemographicsCorrected(API_KEY)
    
    # Try all three demographic variables
    demographic_vars = ['sex', 'agegrp', 'education']
    results = {}
    
    for demo_var in demographic_vars:
        print("\n" + "="*70)
        print(f"ANALYZING: {demo_var.upper()}")
        print("="*70)
        
        df = analyzer.get_demographic_breakdown(demo_var, YEAR, QUARTER)
        
        if df is not None:
            csv_filename = f'M:/Temp_agencies/temp_employment_by_{demo_var}_{YEAR}_Q{QUARTER}.csv'
            df.to_csv(csv_filename, index=False)
            print(f"[OK] Saved: {csv_filename}")
            
            analyzer.create_visualization(df, demo_var, YEAR, QUARTER)
            
            results[demo_var] = df
        else:
            print(f"[FAILED] No data for {demo_var}")
        
        print()
    
    print("="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    
    if results:
        print("\n[OK] Successfully generated files:")
        for demo_var in results.keys():
            print(f"\n{demo_var.upper()}:")
            print(f"  - temp_employment_by_{demo_var}_{YEAR}_Q{QUARTER}.csv")
            print(f"  - temp_employment_by_{demo_var}_{YEAR}_Q{QUARTER}.png")
        
        print("\n" + "="*70)
        print("SUMMARY STATISTICS")
        print("="*70)
        
        for demo_var, df in results.items():
            print(f"\n{demo_var.upper()}:")
            print(df.to_string(index=False))
    else:
        print("\n[FAILED] No data was retrieved")
        print("\nTry running diagnostic_corrected.py first to verify")
        print("which year/quarter has available data")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()