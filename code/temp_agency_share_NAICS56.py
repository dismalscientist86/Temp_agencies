import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
from typing import Optional
import sys
import os

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 7)

class SectorShareAnalyzer:
    """Analyze temp agency share within NAICS 56 sector using Census QWI data"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.census.gov/data/timeseries/qwi/sa"
        
        # NAICS codes
        self.temp_naics = "561320"  # Temporary Help Services
        self.sector_naics = "56"     # Administrative and Support Services
        
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
            "race": "A0",
            "ethnicity": "A0",
            "firmage": "0",
            "firmsize": "0",
            "year": "2023",
            "quarter": "1",
            "key": self.api_key
        }
        
        try:
            print(f"Testing connection to: {self.base_url}")
            response = requests.get(self.base_url, params=test_params, timeout=10)
            
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] API connection successful!")
                print(f"Sample data: {data}")
            elif response.status_code == 204:
                print(f"[OK] API connected (no data for test query)")
            else:
                print(f"[FAILED] Status {response.status_code}")
                print(f"Response: {response.text[:500]}")
                if response.status_code == 400:
                    print("\nTroubleshooting: Check API key and parameters")
                sys.exit(1)
                
        except Exception as e:
            print(f"[FAILED] Error: {e}")
            sys.exit(1)
        
        print("="*70 + "\n")
    
    def get_employment_timeline(
        self,
        naics_code: str,
        start_year: int = 2010,
        end_year: int = 2023
    ) -> Optional[pd.DataFrame]:
        """
        Get employment timeline for a given NAICS code.
        Aggregates state-level data to national level.
        
        Parameters:
        -----------
        naics_code : str
            NAICS code (e.g., "56" or "561320")
        start_year : int
            Starting year
        end_year : int
            Ending year
            
        Returns:
        --------
        pd.DataFrame with columns: year, quarter, period, Emp
        """
        
        # All 50 states + DC
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
        success_count = 0
        
        naics_label = f"NAICS {naics_code}"
        print(f"\nFetching employment data for {naics_label}...")
        print(f"Year range: {start_year}-{end_year}")
        print(f"Total requests: {total_requests}\n")
        
        for state in states:
            for year in range(start_year, end_year + 1):
                for quarter in range(1, 5):
                    request_count += 1
                    
                    # Progress indicator
                    if request_count % 100 == 0:
                        pct = (request_count / total_requests) * 100
                        print(f"  Progress: {request_count}/{total_requests} ({pct:.1f}%) | "
                              f"Data points: {success_count}", end="\r")
                    
                    params = {
                        "get": "Emp",
                        "for": f"state:{state}",
                        "industry": naics_code,
                        "ownercode": "A05",  # All private firms
                        "sex": "0",          # All sexes
                        "agegrp": "A00",     # All age groups
                        "education": "E0",   # All education levels
                        "race": "A0",        # All races
                        "ethnicity": "A0",   # All ethnicities
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
                            if len(data) > 1:
                                row = data[1]
                                emp_value = row[0]
                                
                                # Check for valid employment value
                                if emp_value and emp_value not in ['', 'N', 'D', 'S']:
                                    all_data.append({
                                        'Emp': int(emp_value),
                                        'state': state,
                                        'year': year,
                                        'quarter': quarter
                                    })
                                    success_count += 1
                                    
                    except Exception as e:
                        # Silently skip errors to avoid cluttering output
                        pass
                    
                    # Rate limiting
                    time.sleep(0.08)
        
        print(f"\n  [OK] Completed: {success_count:,} data points retrieved\n")
        
        if not all_data:
            print(f"  [FAILED] No data retrieved for {naics_label}")
            return None
        
        # Aggregate to national level
        df = pd.DataFrame(all_data)
        national_df = df.groupby(['year', 'quarter'])['Emp'].sum().reset_index()
        national_df['period'] = (national_df['year'].astype(str) + 
                                 " Q" + national_df['quarter'].astype(str))
        national_df = national_df.sort_values(['year', 'quarter']).reset_index(drop=True)
        
        return national_df
    
    def calculate_sector_share(
        self,
        start_year: int = 2010,
        end_year: int = 2023
    ) -> Optional[pd.DataFrame]:
        """
        Calculate temp agency employment as share of NAICS 56 sector.
        
        Returns:
        --------
        pd.DataFrame with columns: year, quarter, period, temp_emp, sector_emp, share_pct
        """
        
        print("="*70)
        print("STEP 1: FETCH TEMP AGENCY EMPLOYMENT (NAICS 561320)")
        print("="*70)
        
        temp_df = self.get_employment_timeline(
            self.temp_naics,
            start_year,
            end_year
        )
        
        if temp_df is None:
            return None
        
        print("="*70)
        print("STEP 2: FETCH SECTOR EMPLOYMENT (NAICS 56)")
        print("="*70)
        
        sector_df = self.get_employment_timeline(
            self.sector_naics,
            start_year,
            end_year
        )
        
        if sector_df is None:
            return None
        
        print("="*70)
        print("STEP 3: CALCULATE SHARE")
        print("="*70)
        
        # Merge the datasets
        merged_df = pd.merge(
            temp_df[['year', 'quarter', 'period', 'Emp']],
            sector_df[['year', 'quarter', 'Emp']],
            on=['year', 'quarter'],
            suffixes=('_temp', '_sector')
        )
        
        # Calculate share
        merged_df['share_pct'] = (merged_df['Emp_temp'] / merged_df['Emp_sector']) * 100
        
        # Rename columns for clarity
        merged_df = merged_df.rename(columns={
            'Emp_temp': 'temp_employment',
            'Emp_sector': 'sector_employment'
        })
        
        print(f"\n[OK] Successfully calculated shares for {len(merged_df)} quarters")
        print(f"\nSummary statistics:")
        print(merged_df[['temp_employment', 'sector_employment', 'share_pct']].describe())
        
        return merged_df
    
    def plot_sector_share(self, df: pd.DataFrame, output_file: str = 'M:/Temp_agencies/sector_share_plot.png'):
        """Create visualization of temp agency share over time"""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Plot 1: Absolute employment levels
        x = range(len(df))
        
        ax1.plot(x, df['temp_employment']/1000, 
                marker='o', linewidth=2, markersize=4, 
                label='Temp Agencies (561320)', color='darkblue')
        ax1.plot(x, df['sector_employment']/1000, 
                marker='s', linewidth=2, markersize=4,
                label='Total Sector (56)', color='darkgreen', alpha=0.7)
        
        ax1.set_title('Employment in NAICS 56 Sector - National: Temp Agencies vs. Total Sector', 
                     fontsize=14, fontweight='bold')
        ax1.set_xlabel('Quarter', fontsize=12)
        ax1.set_ylabel('Employment (Thousands)', fontsize=12)
        ax1.legend(loc='best', fontsize=11)
        ax1.grid(True, alpha=0.3)
        
        # Set x-axis labels (every 4 quarters = 1 year)
        tick_positions = range(0, len(df), 4)
        tick_labels = [df.iloc[i]['period'] for i in tick_positions if i < len(df)]
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels(tick_labels, rotation=45, ha='right')
        
        # Plot 2: Share percentage
        ax2.plot(x, df['share_pct'], 
                marker='o', linewidth=2.5, markersize=5, 
                color='darkred')
        ax2.fill_between(x, df['share_pct'], alpha=0.3, color='darkred')
        
        ax2.set_title('Temp Agency Share of NAICS 56 Sector Employment - National', 
                     fontsize=14, fontweight='bold')
        ax2.set_xlabel('Quarter', fontsize=12)
        ax2.set_ylabel('Share (%)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Set x-axis labels
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, rotation=45, ha='right')
        
        # Add horizontal line at mean
        mean_share = df['share_pct'].mean()
        ax2.axhline(y=mean_share, color='gray', linestyle='--', 
                   linewidth=1.5, alpha=0.7,
                   label=f'Mean: {mean_share:.1f}%')
        ax2.legend(loc='best', fontsize=11)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\n[OK] Saved plot to {output_file}")
        plt.close()
    
    def create_summary_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create summary statistics by year"""
        
        # Annual averages
        annual_df = df.groupby('year').agg({
            'temp_employment': 'mean',
            'sector_employment': 'mean',
            'share_pct': 'mean'
        }).round(2)
        
        annual_df = annual_df.reset_index()
        annual_df.columns = ['Year', 'Avg Temp Employment', 
                            'Avg Sector Employment', 'Avg Share (%)']
        
        return annual_df


def main():
    """Main analysis pipeline"""
    
    # API key from environment variable (set in .env or shell)
    API_KEY = os.environ.get("CENSUS_API_KEY", "")
    
    print("="*70)
    print("TEMP AGENCY SECTOR SHARE ANALYSIS")
    print("Analyzing NAICS 561320 (Temp Agencies) within NAICS 56 (Admin & Support)")
    print("="*70)
    
    # Initialize analyzer
    analyzer = SectorShareAnalyzer(API_KEY)
    
    # Calculate sector share over time
    print("\n" + "="*70)
    print("FETCHING DATA AND CALCULATING SHARES")
    print("="*70)
    
    share_df = analyzer.calculate_sector_share(
        start_year=2010,
        end_year=2023
    )
    
    if share_df is None:
        print("\n[FAILED] Failed to retrieve data")
        return
    
    # Save detailed quarterly data
    output_csv = 'M:/Temp_agencies/temp_agency_sector_share.csv'
    share_df.to_csv(output_csv, index=False)
    print(f"\n[OK] Saved detailed data to {output_csv}")
    
    # Create summary statistics
    print("\n" + "="*70)
    print("ANNUAL SUMMARY STATISTICS")
    print("="*70)
    
    annual_summary = analyzer.create_summary_statistics(share_df)
    print("\n" + annual_summary.to_string(index=False))
    
    annual_csv = 'M:/Temp_agencies/temp_agency_sector_share_annual.csv'
    annual_summary.to_csv(annual_csv, index=False)
    print(f"\n[OK] Saved annual summary to {annual_csv}")
    
    # Create visualization
    print("\n" + "="*70)
    print("CREATING VISUALIZATION")
    print("="*70)
    
    analyzer.plot_sector_share(share_df)
    
    # Additional insights
    print("\n" + "="*70)
    print("KEY INSIGHTS")
    print("="*70)
    
    # Overall statistics
    print(f"\nOverall Period: {share_df['period'].iloc[0]} to {share_df['period'].iloc[-1]}")
    print(f"Average temp agency share: {share_df['share_pct'].mean():.2f}%")
    print(f"Minimum share: {share_df['share_pct'].min():.2f}% ({share_df.loc[share_df['share_pct'].idxmin(), 'period']})")
    print(f"Maximum share: {share_df['share_pct'].max():.2f}% ({share_df.loc[share_df['share_pct'].idxmax(), 'period']})")
    
    # Trend analysis
    first_year_avg = share_df[share_df['year'] == share_df['year'].min()]['share_pct'].mean()
    last_year_avg = share_df[share_df['year'] == share_df['year'].max()]['share_pct'].mean()
    change = last_year_avg - first_year_avg
    
    print(f"\nTrend Analysis:")
    print(f"  {share_df['year'].min()} average: {first_year_avg:.2f}%")
    print(f"  {share_df['year'].max()} average: {last_year_avg:.2f}%")
    print(f"  Change: {change:+.2f} percentage points")
    
    # Recent vs historical
    recent_years = share_df[share_df['year'] >= 2020]['share_pct'].mean()
    historical_years = share_df[share_df['year'] < 2020]['share_pct'].mean()
    
    print(f"\nRecent (2020+) average: {recent_years:.2f}%")
    print(f"Historical (pre-2020) average: {historical_years:.2f}%")
    print(f"Difference: {recent_years - historical_years:+.2f} percentage points")
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nGenerated files:")
    print("  [OK] temp_agency_sector_share.csv (quarterly data)")
    print("  [OK] temp_agency_sector_share_annual.csv (annual averages)")
    print("  [OK] sector_share_plot.png (visualization)")


if __name__ == "__main__":
    main()