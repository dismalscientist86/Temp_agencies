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

# Save outputs straight into the repo's output/ folder (this file lives in code/)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


class WageAnalyzer:
    """Compare average earnings in temp agencies against broader sectors using Census QWI data"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.census.gov/data/timeseries/qwi/sa"

        # NAICS codes to compare
        self.temp_naics = "561320"   # Temporary Help Services
        self.sector_naics = "56"     # Administrative and Support Services
        self.private_naics = "00"    # Total private sector

        # All 50 states + DC
        self.states = [
            '01', '02', '04', '05', '06', '08', '09', '10', '11', '12',
            '13', '15', '16', '17', '18', '19', '20', '21', '22', '23',
            '24', '25', '26', '27', '28', '29', '30', '31', '32', '33',
            '34', '35', '36', '37', '38', '39', '40', '41', '42', '44',
            '45', '46', '47', '48', '49', '50', '51', '53', '54', '55', '56'
        ]

        # Test API connectivity
        self._test_api_connection()

    def _test_api_connection(self):
        """Test if API is accessible and credentials work"""
        print("\n" + "="*70)
        print("TESTING API CONNECTION")
        print("="*70)

        test_params = {
            "get": "Emp,EarnS,EarnHirAS",
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

    def get_earnings_timeline(
        self,
        naics_code: str,
        start_year: int = 2010,
        end_year: int = 2023
    ) -> Optional[pd.DataFrame]:
        """
        Fetch Emp, EarnS, and EarnHirAS for all 51 states and aggregate nationally.
        Earnings are employment-weighted: national_avg = sum(Emp_i * EarnS_i) / sum(Emp_i)

        Parameters:
        -----------
        naics_code : str
            NAICS code (e.g., "561320", "56", or "00" for total private)
        start_year : int
            Starting year
        end_year : int
            Ending year

        Returns:
        --------
        pd.DataFrame with columns: year, quarter, period, Emp, EarnS, EarnHirAS
        """

        all_data = []
        total_requests = len(self.states) * (end_year - start_year + 1) * 4
        request_count = 0
        success_count = 0

        naics_label = f"NAICS {naics_code}" if naics_code != "00" else "Total Private"
        print(f"\nFetching earnings data for {naics_label}...")
        print(f"Year range: {start_year}-{end_year}")
        print(f"Total requests: {total_requests}\n")

        for state in self.states:
            for year in range(start_year, end_year + 1):
                for quarter in range(1, 5):
                    request_count += 1

                    # Progress indicator
                    if request_count % 100 == 0:
                        pct = (request_count / total_requests) * 100
                        print(f"  Progress: {request_count}/{total_requests} ({pct:.1f}%) | "
                              f"Data points: {success_count}", end="\r")

                    params = {
                        "get": "Emp,EarnS,EarnHirAS",
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
                                header = data[0]
                                row = data[1]

                                # Map columns by header position
                                col_map = {h: i for i, h in enumerate(header)}
                                emp_val = row[col_map['Emp']]
                                earns_val = row[col_map['EarnS']]
                                earnhiras_val = row[col_map['EarnHirAS']]

                                # Check for valid values
                                suppressed = {'', 'N', 'D', 'S', None}
                                if emp_val not in suppressed and earns_val not in suppressed:
                                    record = {
                                        'Emp': int(emp_val),
                                        'EarnS': int(earns_val),
                                        'state': state,
                                        'year': year,
                                        'quarter': quarter
                                    }
                                    # EarnHirAS may be suppressed even when EarnS is not
                                    if earnhiras_val not in suppressed:
                                        record['EarnHirAS'] = int(earnhiras_val)
                                    else:
                                        record['EarnHirAS'] = None

                                    all_data.append(record)
                                    success_count += 1

                    except Exception:
                        # Silently skip errors to avoid cluttering output
                        pass

                    # Rate limiting
                    time.sleep(0.08)

        print(f"\n  [OK] Completed: {success_count:,} data points retrieved\n")

        if not all_data:
            print(f"  [FAILED] No data retrieved for {naics_label}")
            return None

        # Aggregate to national level with employment-weighted earnings
        df = pd.DataFrame(all_data)

        # Employment-weighted national aggregation
        national_records = []
        for (year, quarter), group in df.groupby(['year', 'quarter']):
            total_emp = group['Emp'].sum()

            # Weighted EarnS
            weighted_earns = (group['Emp'] * group['EarnS']).sum() / total_emp

            # Weighted EarnHirAS (only use rows where it's not null)
            hiras_valid = group.dropna(subset=['EarnHirAS'])
            if len(hiras_valid) > 0:
                hiras_emp = hiras_valid['Emp'].sum()
                weighted_earnhiras = (hiras_valid['Emp'] * hiras_valid['EarnHirAS']).sum() / hiras_emp
            else:
                weighted_earnhiras = None

            national_records.append({
                'year': year,
                'quarter': quarter,
                'Emp': total_emp,
                'EarnS': round(weighted_earns),
                'EarnHirAS': round(weighted_earnhiras) if weighted_earnhiras is not None else None
            })

        national_df = pd.DataFrame(national_records)
        national_df['period'] = (national_df['year'].astype(str) +
                                 " Q" + national_df['quarter'].astype(str))
        national_df = national_df.sort_values(['year', 'quarter']).reset_index(drop=True)

        return national_df

    def calculate_wage_comparison(
        self,
        start_year: int = 2010,
        end_year: int = 2023
    ) -> Optional[pd.DataFrame]:
        """
        Fetch earnings for 3 NAICS codes and compute wage gaps and ratios.

        Returns:
        --------
        pd.DataFrame with quarterly wage data and comparison ratios
        """

        print("="*70)
        print("STEP 1: FETCH TEMP AGENCY EARNINGS (NAICS 561320)")
        print("="*70)

        temp_df = self.get_earnings_timeline(self.temp_naics, start_year, end_year)
        if temp_df is None:
            return None

        print("="*70)
        print("STEP 2: FETCH SECTOR EARNINGS (NAICS 56)")
        print("="*70)

        sector_df = self.get_earnings_timeline(self.sector_naics, start_year, end_year)
        if sector_df is None:
            return None

        print("="*70)
        print("STEP 3: FETCH TOTAL PRIVATE SECTOR EARNINGS (ALL NAICS)")
        print("="*70)

        private_df = self.get_earnings_timeline(self.private_naics, start_year, end_year)
        if private_df is None:
            return None

        print("="*70)
        print("STEP 4: MERGE AND COMPUTE WAGE GAPS")
        print("="*70)

        # Merge temp with sector
        merged = pd.merge(
            temp_df[['year', 'quarter', 'period', 'Emp', 'EarnS', 'EarnHirAS']],
            sector_df[['year', 'quarter', 'EarnS', 'EarnHirAS']],
            on=['year', 'quarter'],
            suffixes=('_temp', '_sector')
        )

        # Merge with private sector
        merged = pd.merge(
            merged,
            private_df[['year', 'quarter', 'EarnS', 'EarnHirAS']],
            on=['year', 'quarter']
        )
        merged = merged.rename(columns={
            'Emp': 'temp_emp',
            'EarnS': 'private_earnS',
            'EarnHirAS': 'private_earnHirAS'
        })

        # Compute wage ratios (temp as fraction of comparison group)
        merged['wage_ratio_sector'] = merged['EarnS_temp'] / merged['EarnS_sector']
        merged['wage_ratio_private'] = merged['EarnS_temp'] / merged['private_earnS']

        # Wage gap in dollars
        merged['wage_gap_sector'] = merged['EarnS_temp'] - merged['EarnS_sector']
        merged['wage_gap_private'] = merged['EarnS_temp'] - merged['private_earnS']

        # New hire wage ratios
        merged['hire_ratio_sector'] = merged['EarnHirAS_temp'] / merged['EarnHirAS_sector']
        merged['hire_ratio_private'] = merged['EarnHirAS_temp'] / merged['private_earnHirAS']

        merged = merged.sort_values(['year', 'quarter']).reset_index(drop=True)

        print(f"\n[OK] Successfully computed wage comparisons for {len(merged)} quarters")
        print(f"\nEarnings summary (monthly averages):")
        print(f"  Temp agencies (561320) EarnS: ${merged['EarnS_temp'].mean():,.0f}")
        print(f"  Sector (56) EarnS:            ${merged['EarnS_sector'].mean():,.0f}")
        print(f"  Total private EarnS:          ${merged['private_earnS'].mean():,.0f}")
        print(f"  Temp/Sector ratio:            {merged['wage_ratio_sector'].mean():.3f}")
        print(f"  Temp/Private ratio:           {merged['wage_ratio_private'].mean():.3f}")

        return merged

    def plot_wage_trends(self, df: pd.DataFrame, output_file: str = f'{OUTPUT_DIR}/wage_trends.png'):
        """Create 3-panel plot: absolute earnings, wage ratio, new hire earnings"""

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 14))

        x = range(len(df))

        # Set x-axis labels (every 4 quarters = 1 year)
        tick_positions = list(range(0, len(df), 4))
        tick_labels = [df.iloc[i]['period'] for i in tick_positions if i < len(df)]

        # Panel 1: Absolute earnings (EarnS)
        ax1.plot(x, df['EarnS_temp'], marker='o', linewidth=2, markersize=3,
                 label='Temp Agencies (561320)', color='darkblue')
        ax1.plot(x, df['EarnS_sector'], marker='s', linewidth=2, markersize=3,
                 label='Admin & Support (56)', color='darkgreen', alpha=0.8)
        ax1.plot(x, df['private_earnS'], marker='^', linewidth=2, markersize=3,
                 label='Total Private', color='darkred', alpha=0.8)

        ax1.set_title('Average Monthly Earnings (Full-Quarter Employment) — National',
                      fontsize=14, fontweight='bold')
        ax1.set_ylabel('Monthly Earnings ($)', fontsize=12)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels(tick_labels, rotation=45, ha='right')
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'${v:,.0f}'))

        # Panel 2: Wage ratios
        ax2.plot(x, df['wage_ratio_sector'] * 100, marker='o', linewidth=2, markersize=3,
                 label='Temp / Sector (56)', color='darkgreen')
        ax2.plot(x, df['wage_ratio_private'] * 100, marker='s', linewidth=2, markersize=3,
                 label='Temp / Total Private', color='darkred')
        ax2.axhline(y=100, color='gray', linestyle='--', linewidth=1, alpha=0.7)

        ax2.set_title('Temp Agency Earnings as % of Comparison Groups',
                      fontsize=14, fontweight='bold')
        ax2.set_ylabel('Wage Ratio (%)', fontsize=12)
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, rotation=45, ha='right')

        # Panel 3: New hire earnings (EarnHirAS)
        ax3.plot(x, df['EarnHirAS_temp'], marker='o', linewidth=2, markersize=3,
                 label='Temp Agencies (561320)', color='darkblue')
        ax3.plot(x, df['EarnHirAS_sector'], marker='s', linewidth=2, markersize=3,
                 label='Admin & Support (56)', color='darkgreen', alpha=0.8)
        ax3.plot(x, df['private_earnHirAS'], marker='^', linewidth=2, markersize=3,
                 label='Total Private', color='darkred', alpha=0.8)

        ax3.set_title('Average Monthly Earnings — New Hires (All Hires, Stable)',
                      fontsize=14, fontweight='bold')
        ax3.set_xlabel('Quarter', fontsize=12)
        ax3.set_ylabel('Monthly Earnings ($)', fontsize=12)
        ax3.legend(loc='best', fontsize=10)
        ax3.grid(True, alpha=0.3)
        ax3.set_xticks(tick_positions)
        ax3.set_xticklabels(tick_labels, rotation=45, ha='right')
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'${v:,.0f}'))

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\n[OK] Saved wage trends plot to {output_file}")
        plt.close()

    def plot_wage_gap(self, df: pd.DataFrame, output_file: str = f'{OUTPUT_DIR}/wage_gap.png'):
        """Single panel: temp earnings as % of sector/private earnings over time"""

        fig, ax = plt.subplots(figsize=(14, 7))

        x = range(len(df))

        ax.plot(x, df['wage_ratio_sector'] * 100, marker='o', linewidth=2.5, markersize=4,
                label='Temp / Sector (56)', color='darkgreen')
        ax.fill_between(x, df['wage_ratio_sector'] * 100, 100,
                        alpha=0.15, color='darkgreen')

        ax.plot(x, df['wage_ratio_private'] * 100, marker='s', linewidth=2.5, markersize=4,
                label='Temp / Total Private', color='darkred')
        ax.fill_between(x, df['wage_ratio_private'] * 100, 100,
                        alpha=0.15, color='darkred')

        ax.axhline(y=100, color='gray', linestyle='--', linewidth=1.5, alpha=0.7,
                   label='Parity (100%)')

        # Mean lines
        mean_sector = df['wage_ratio_sector'].mean() * 100
        mean_private = df['wage_ratio_private'].mean() * 100
        ax.axhline(y=mean_sector, color='darkgreen', linestyle=':', linewidth=1, alpha=0.5)
        ax.axhline(y=mean_private, color='darkred', linestyle=':', linewidth=1, alpha=0.5)

        ax.set_title('Temp Agency Wage Gap: Earnings as % of Comparison Groups — National',
                     fontsize=14, fontweight='bold')
        ax.set_xlabel('Quarter', fontsize=12)
        ax.set_ylabel('Temp Earnings as % of Comparison Group', fontsize=12)
        ax.legend(loc='best', fontsize=11)
        ax.grid(True, alpha=0.3)

        # Set x-axis labels
        tick_positions = list(range(0, len(df), 4))
        tick_labels = [df.iloc[i]['period'] for i in tick_positions if i < len(df)]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right')

        # Annotate means
        ax.annotate(f'Mean: {mean_sector:.1f}%',
                    xy=(len(df) - 1, mean_sector), fontsize=9,
                    color='darkgreen', ha='right', va='bottom')
        ax.annotate(f'Mean: {mean_private:.1f}%',
                    xy=(len(df) - 1, mean_private), fontsize=9,
                    color='darkred', ha='right', va='top')

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\n[OK] Saved wage gap plot to {output_file}")
        plt.close()

    def create_summary_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create annual averages table"""

        annual_df = df.groupby('year').agg({
            'temp_emp': 'mean',
            'EarnS_temp': 'mean',
            'EarnS_sector': 'mean',
            'private_earnS': 'mean',
            'EarnHirAS_temp': 'mean',
            'EarnHirAS_sector': 'mean',
            'private_earnHirAS': 'mean',
            'wage_ratio_sector': 'mean',
            'wage_ratio_private': 'mean'
        }).round(2)

        annual_df = annual_df.reset_index()
        annual_df.columns = [
            'Year', 'Avg Temp Emp',
            'Temp EarnS', 'Sector EarnS', 'Private EarnS',
            'Temp Hire Earn', 'Sector Hire Earn', 'Private Hire Earn',
            'Ratio vs Sector', 'Ratio vs Private'
        ]

        return annual_df


def main():
    """Main analysis pipeline"""

    # API key from environment variable (set in .env or shell)
    API_KEY = os.environ.get("CENSUS_API_KEY", "")

    print("="*70)
    print("TEMP AGENCY WAGE ANALYSIS")
    print("Comparing earnings: NAICS 561320 vs Sector 56 vs Total Private")
    print("="*70)

    # Initialize analyzer
    analyzer = WageAnalyzer(API_KEY)

    # Calculate wage comparison
    print("\n" + "="*70)
    print("FETCHING DATA AND CALCULATING WAGE GAPS")
    print("="*70)

    wage_df = analyzer.calculate_wage_comparison(
        start_year=2010,
        end_year=2023
    )

    if wage_df is None:
        print("\n[FAILED] Failed to retrieve data")
        return

    # Save quarterly data
    output_csv = f'{OUTPUT_DIR}/temp_agency_wages.csv'
    csv_cols = [
        'year', 'quarter', 'period', 'temp_emp',
        'EarnS_temp', 'EarnS_sector', 'private_earnS',
        'EarnHirAS_temp', 'EarnHirAS_sector', 'private_earnHirAS',
        'wage_ratio_sector', 'wage_ratio_private',
        'wage_gap_sector', 'wage_gap_private',
        'hire_ratio_sector', 'hire_ratio_private'
    ]
    wage_df[csv_cols].to_csv(output_csv, index=False)
    print(f"\n[OK] Saved quarterly data to {output_csv}")

    # Create summary statistics
    print("\n" + "="*70)
    print("ANNUAL SUMMARY STATISTICS")
    print("="*70)

    annual_summary = analyzer.create_summary_statistics(wage_df)
    print("\n" + annual_summary.to_string(index=False))

    annual_csv = f'{OUTPUT_DIR}/temp_agency_wages_annual.csv'
    annual_summary.to_csv(annual_csv, index=False)
    print(f"\n[OK] Saved annual summary to {annual_csv}")

    # Create visualizations
    print("\n" + "="*70)
    print("CREATING VISUALIZATIONS")
    print("="*70)

    analyzer.plot_wage_trends(wage_df)
    analyzer.plot_wage_gap(wage_df)

    # Key insights
    print("\n" + "="*70)
    print("KEY INSIGHTS")
    print("="*70)

    print(f"\nOverall Period: {wage_df['period'].iloc[0]} to {wage_df['period'].iloc[-1]}")
    print(f"\nAverage monthly earnings (EarnS):")
    print(f"  Temp agencies:  ${wage_df['EarnS_temp'].mean():,.0f}")
    print(f"  Sector (56):    ${wage_df['EarnS_sector'].mean():,.0f}")
    print(f"  Total private:  ${wage_df['private_earnS'].mean():,.0f}")

    print(f"\nWage ratios (temp / comparison):")
    print(f"  vs Sector:  {wage_df['wage_ratio_sector'].mean():.1%}")
    print(f"  vs Private: {wage_df['wage_ratio_private'].mean():.1%}")

    print(f"\nWage gap (temp minus comparison, monthly $):")
    print(f"  vs Sector:  ${wage_df['wage_gap_sector'].mean():,.0f}")
    print(f"  vs Private: ${wage_df['wage_gap_private'].mean():,.0f}")

    # Trend analysis
    first_year = wage_df['year'].min()
    last_year = wage_df['year'].max()
    first_ratio = wage_df[wage_df['year'] == first_year]['wage_ratio_private'].mean()
    last_ratio = wage_df[wage_df['year'] == last_year]['wage_ratio_private'].mean()

    print(f"\nTrend (Temp/Private ratio):")
    print(f"  {first_year}: {first_ratio:.1%}")
    print(f"  {last_year}:  {last_ratio:.1%}")
    print(f"  Change: {(last_ratio - first_ratio)*100:+.1f} percentage points")

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nGenerated files:")
    print("  [OK] temp_agency_wages.csv (quarterly data)")
    print("  [OK] temp_agency_wages_annual.csv (annual averages)")
    print("  [OK] wage_trends.png (3-panel: earnings + ratios + new hires)")
    print("  [OK] wage_gap.png (temp earnings as % of comparison groups)")


if __name__ == "__main__":
    main()
