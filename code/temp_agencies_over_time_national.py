import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
from typing import Optional, List, Dict
import sys

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)

class QWITempAgencyAnalyzer:
    """Analyzer for temp agency employment using Census QWI data"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.census.gov/data/timeseries/qwi/sa"
        
        # NAICS codes for temp agencies
        # 561320: Temporary Help Services (the main temp agency code)
        # 561311: Employment Placement Agencies (staffing/placement)
        # 561312: Executive Search Services
        self.temp_naics = "561320"  # Focus on temp help services
        
        # Test API connectivity
        self._test_api_connection()
        
    def _test_api_connection(self):
        """Test if API is accessible and credentials work"""
        print("\n" + "="*70)
        print("TESTING API CONNECTION")
        print("="*70)
        
        test_params = {
            "get": "Emp",
            "for": "state:06",  # California
            "industry": self.temp_naics,
            "ownercode": "A05",
            "sex": "0",
            "agegrp": "A00",
            "education": "E0",
            "firmage": "0",
            "firmsize": "0",
            "year": "2023",
            "quarter": "1",
            "key": self.api_key
        }
        
        try:
            print(f"Testing connection to: {self.base_url}")
            print(f"Using API key: {self.api_key[:10]}...")
            response = requests.get(self.base_url, params=test_params, timeout=10)
            
            print(f"\nResponse Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ API connection successful!")
                print(f"Sample data received: {data}")
            elif response.status_code == 400:
                print(f"✗ Bad Request (400)")
                print(f"Response: {response.text[:500]}")
                print("\nPossible issues:")
                print("  1. Invalid parameter combination")
                print("  2. Invalid API key")
                print("  3. Requested data doesn't exist")
                sys.exit(1)
            elif response.status_code == 204:
                print(f"✓ API connected but no data for test query")
            else:
                print(f"✗ Unexpected status: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                sys.exit(1)
                
        except requests.exceptions.ConnectionError as e:
            print(f"✗ Connection Error: Cannot reach Census API")
            print(f"Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error: {e}")
            sys.exit(1)
        
        print("="*70 + "\n")
    
    def get_national_employment_timeline(
        self, 
        start_year: int = 2005, 
        end_year: int = 2024
    ) -> Optional[pd.DataFrame]:
        """
        Get national employment timeline for temp agencies.
        Uses state-level data and aggregates to avoid geography issues.
        """
        
        # State FIPS codes for all 50 states + DC
        states = [
            '01', '02', '04', '05', '06', '08', '09', '10', '11', '12',
            '13', '15', '16', '17', '18', '19', '20', '21', '22', '23',
            '24', '25', '26', '27', '28', '29', '30', '31', '32', '33',
            '34', '35', '36', '37', '38', '39', '40', '41', '42', '44',
            '45', '46', '47', '48', '49', '50', '51', '53', '54', '55', '56'
        ]
        
        all_data = []
        total_requests = len(states) * (end_year - start_year + 1) * 4
        request_count = 0
        error_count = 0
        no_data_count = 0
        
        print(f"Fetching national data for NAICS {self.temp_naics}...")
        print(f"Total requests to make: {total_requests}")
        print(f"Year range: {start_year}-{end_year}")
        print()
        
        for state in states:
            for year in range(start_year, end_year + 1):
                for quarter in range(1, 5):
                    request_count += 1
                    
                    if request_count % 50 == 0:
                        success_rate = len(all_data) / request_count * 100 if request_count > 0 else 0
                        print(f"  Progress: {request_count}/{total_requests} | "
                              f"Success: {len(all_data)} | "
                              f"Errors: {error_count} | "
                              f"No Data: {no_data_count} | "
                              f"Rate: {success_rate:.1f}%", end="\r")
                    
                    params = {
                        "get": "Emp",
                        "for": f"state:{state}",
                        "industry": self.temp_naics,
                        "ownercode": "A05",  # All private firms
                        "sex": "0",          # All sexes
                        "agegrp": "A00",     # All age groups
                        "education": "E0",   # All education levels
                        "firmage": "0",      # All firm ages
                        "firmsize": "0",     # All firm sizes
                        "year": str(year),
                        "quarter": str(quarter),
                        "key": self.api_key
                    }
                    
                    try:
                        response = requests.get(self.base_url, params=params, timeout=10)
                        
                        if response.status_code == 200:
                            data = response.json()
                            if len(data) > 1:  # Has data beyond header
                                row = data[1]
                                emp_value = row[0]
                                
                                # Handle various response formats
                                if emp_value and emp_value not in ['', 'N', 'D', 'S']:
                                    all_data.append({
                                        'Emp': int(emp_value),
                                        'state': row[1],
                                        'year': year,
                                        'quarter': quarter
                                    })
                                else:
                                    no_data_count += 1
                            else:
                                no_data_count += 1
                                
                        elif response.status_code == 204:
                            no_data_count += 1  # No data for this period
                            
                        elif response.status_code == 400:
                            error_count += 1
                            if error_count <= 5:  # Only print first 5 errors
                                print(f"\n  [400 Error] State {state}, {year} Q{quarter}")
                                print(f"  Response: {response.text[:200]}")
                        else:
                            error_count += 1
                            if error_count <= 5:
                                print(f"\n  [Status {response.status_code}] State {state}, {year} Q{quarter}")
                                
                    except requests.exceptions.Timeout:
                        error_count += 1
                        if error_count <= 5:
                            print(f"\n  [Timeout] State {state}, {year} Q{quarter}")
                            
                    except requests.exceptions.ConnectionError:
                        error_count += 1
                        if error_count <= 5:
                            print(f"\n  [Connection Error] State {state}, {year} Q{quarter}")
                            
                    except Exception as e:
                        error_count += 1
                        if error_count <= 5:
                            print(f"\n  [Error] State {state}, {year} Q{quarter}: {type(e).__name__}")
                    
                    # Rate limiting - be nice to the API
                    time.sleep(0.1)  # Increased to 100ms between requests
        
        # Final statistics
        print(f"\n\n{'='*70}")
        print("FETCH STATISTICS")
        print(f"{'='*70}")
        print(f"Total requests made:     {request_count:,}")
        print(f"Successful data points:  {len(all_data):,}")
        print(f"No data responses:       {no_data_count:,}")
        print(f"Errors encountered:      {error_count:,}")
        print(f"Success rate:            {len(all_data)/request_count*100:.1f}%")
        print(f"{'='*70}\n")
        
        if not all_data:
            print("⚠ WARNING: No data retrieved!")
            print("\nPossible reasons:")
            print("  1. API key may be invalid or expired")
            print("  2. The NAICS code might not have data for this time period")
            print("  3. Parameter combination might be invalid")
            print("  4. API structure may have changed")
            print("\nTroubleshooting steps:")
            print("  1. Verify your API key at: https://api.census.gov/data/key_signup.html")
            print("  2. Check Census QWI documentation: https://www.census.gov/data/developers/data-sets/qwi.html")
            print("  3. Try a simpler query with fewer parameters")
            return None
        
        # Aggregate to national level
        df = pd.DataFrame(all_data)
        
        # Show sample of raw data
        print("Sample of retrieved data:")
        print(df.head(10))
        print()
        
        # Aggregate by year-quarter
        national_df = df.groupby(['year', 'quarter'])['Emp'].sum().reset_index()
        national_df['period'] = national_df['year'].astype(str) + " Q" + national_df['quarter'].astype(str)
        national_df = national_df.sort_values(['year', 'quarter'])
        
        print(f"Aggregated to {len(national_df)} national quarterly observations")
        
        return national_df
    
    def get_demographic_breakdown(
        self,
        demographic_var: str,
        year: int = 2023,
        quarter: int = 4,
        state_code: str = "00"  # 00 = national
    ) -> Optional[pd.DataFrame]:
        """
        Get breakdown by demographic characteristic.
        
        demographic_var options:
        - 'sex': Gender breakdown (1=Male, 2=Female)
        - 'agegrp': Age groups (A01-A08)
        - 'education': Education levels (E1-E5)
        - 'race': Race/ethnicity (A0-A8)
        """
        
        # Define the categories to loop through
        categories = {
            'sex': ['1', '2'],  # Male, Female
            'agegrp': ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08'],
            'education': ['E1', 'E2', 'E3', 'E4', 'E5'],
            'race': ['A0', 'A1', 'A2', 'A3', 'A5', 'A6', 'A7', 'A8']
        }
        
        # Labels for categories
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
                'E4': 'Bachelor\'s',
                'E5': 'Advanced Degree'
            },
            'race': {
                'A0': 'White Alone',
                'A1': 'Black Alone',
                'A2': 'American Indian/Alaska Native',
                'A3': 'Asian Alone',
                'A5': 'Native Hawaiian/Pacific Islander',
                'A6': 'Two or More Races',
                'A7': 'Hispanic/Latino',
                'A8': 'Non-Hispanic/Latino'
            }
        }
        
        if demographic_var not in categories:
            print(f"Invalid demographic variable. Choose from: {list(categories.keys())}")
            return None
        
        all_data = []
        
        print(f"\nFetching {demographic_var} breakdown for {year} Q{quarter}...")
        
        # If using national level, need to aggregate states
        states_to_fetch = ['00'] if state_code == '00' else [state_code]
        
        # For national, we need to aggregate across all states
        if state_code == '00':
            states_to_fetch = [
                '01', '02', '04', '05', '06', '08', '09', '10', '11', '12',
                '13', '15', '16', '17', '18', '19', '20', '21', '22', '23',
                '24', '25', '26', '27', '28', '29', '30', '31', '32', '33',
                '34', '35', '36', '37', '38', '39', '40', '41', '42', '44',
                '45', '46', '47', '48', '49', '50', '51', '53', '54', '55', '56'
            ]
        
        for category_code in categories[demographic_var]:
            category_data = []
            
            for state in states_to_fetch:
                # Build base parameters
                params = {
                    "get": "Emp",
                    "for": f"state:{state}",
                    "industry": self.temp_naics,
                    "ownercode": "A05",
                    "year": str(year),
                    "quarter": str(quarter),
                    "key": self.api_key
                }
                
                # Set demographic parameters - default others to "all"
                params['sex'] = category_code if demographic_var == 'sex' else '0'
                params['agegrp'] = category_code if demographic_var == 'agegrp' else 'A00'
                params['education'] = category_code if demographic_var == 'education' else 'E0'
                params['firmage'] = '0'
                params['firmsize'] = '0'
                
                # Race/ethnicity handled differently
                if demographic_var == 'race':
                    if category_code in ['A7', 'A8']:  # Hispanic/Latino categories
                        params['race'] = 'A0'
                        params['ethnicity'] = category_code
                    else:
                        params['race'] = category_code
                        params['ethnicity'] = '0'
                else:
                    params['race'] = 'A0'
                    params['ethnicity'] = '0'
                
                try:
                    response = requests.get(self.base_url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if len(data) > 1:
                            emp = data[1][0]
                            if emp and emp not in ['', 'N', 'D', 'S']:
                                category_data.append(int(emp))
                    elif response.status_code == 204:
                        pass  # No data
                    elif response.status_code == 400:
                        pass  # Skip bad requests silently in demographic queries
                        
                except Exception as e:
                    pass  # Skip errors silently
                
                time.sleep(0.1)
            
            # Sum across states for national estimate
            total_emp = sum(category_data)
            
            all_data.append({
                'category': labels[demographic_var].get(category_code, category_code),
                'code': category_code,
                'employment': total_emp
            })
            
            print(f"  {labels[demographic_var].get(category_code, category_code)}: {total_emp:,}")
        
        if not all_data or sum(d['employment'] for d in all_data) == 0:
            print(f"  ⚠ No data available for {demographic_var} breakdown")
            return None
            
        df = pd.DataFrame(all_data)
        df['percentage'] = df['employment'] / df['employment'].sum() * 100
        
        return df


def main():
    """Main analysis pipeline"""
    
    # Your API key
    API_KEY = "3192f7e1f6c2306861d2b03c9a6ae895ff43c788"
    
    print("="*70)
    print("CENSUS QWI TEMP AGENCY ANALYSIS")
    print("="*70)
    
    analyzer = QWITempAgencyAnalyzer(API_KEY)
    
    # Step 1: Get national employment timeline
    print("\n" + "="*70)
    print("STEP 1: NATIONAL EMPLOYMENT TIMELINE")
    print("="*70)
    
    national_timeline = analyzer.get_national_employment_timeline(
        start_year=2005,  # Starting from 2015 for more recent data
        end_year=2023     # 2023 to ensure data availability
    )
    
    if national_timeline is not None and len(national_timeline) > 0:
        # Save timeline data
        output_file = '/m/Temp_agencies/national_temp_employment.csv'
        national_timeline.to_csv(output_file, index=False)
        print(f"\n✓ Saved timeline to {output_file}")
        print(f"\nTimeline summary:")
        print(national_timeline.describe())
        
        # Plot timeline
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(range(len(national_timeline)), national_timeline['Emp'], 
                marker='o', color='darkblue', linewidth=2, markersize=4)
        ax.set_title(f'National Temp Agency Employment (NAICS {analyzer.temp_naics})', 
                     fontsize=14, fontweight='bold')
        ax.set_xlabel('Quarter', fontsize=12)
        ax.set_ylabel('Total Employees', fontsize=12)
        
        # Set x-axis labels (show every 4th quarter)
        tick_positions = range(0, len(national_timeline), 4)
        tick_labels = [national_timeline.iloc[i]['period'] for i in tick_positions]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right')
        
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        plot_file = '/m/Temp_agencies/national_timeline.png'
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved plot to {plot_file}")
        plt.close()
    else:
        print("\n✗ Could not retrieve timeline data - skipping demographic analysis")
        return
    
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nGenerated files:")
    files_created = [
        "national_temp_employment.csv",
        "national_timeline.png"
    ]
    for f in files_created:
        print(f"  ✓ {f}")


if __name__ == "__main__":
    main()