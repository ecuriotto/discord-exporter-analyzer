import os
import sys
import glob

# Setup path to import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
# If running from root, src/analysis is where this script is.
sys.path.append(current_dir)

from parse_and_clean import parse_and_clean_discord_txt
from ai_insights import get_monthly_insights

def test_monthly_analysis():
    # 1. Find latest output file
    # Go up two levels from src/analysis/test... to root
    root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
    output_dir = os.path.join(root_dir, 'output')
    
    txt_files = glob.glob(os.path.join(output_dir, "*.txt"))
    # Exclude thread.txt if it exists and prefer the one with ID
    # simpler: just get the most recently modified txt file that isn't thread.txt if possible
    
    if not txt_files:
        print("[ERROR] No TXT files found in output/ to analyze.")
        return

    # Sort by modification time
    latest_file = max(txt_files, key=os.path.getmtime)
    print(f"[INFO] Testing AI on file: {latest_file}")
    
    # 2. Parse Data
    print("[INFO] Parsing data...")
    df = parse_and_clean_discord_txt(latest_file)
    print(f"[INFO] DataFrame shape: {df.shape}")
    
    if df.empty:
        print("[ERROR] DataFrame is empty.")
        return

    # 3. Run Monthly Analysis
    print("[INFO] Running get_monthly_insights (this calls Gemini API)...")
    try:
        # We assume the data is 2025 based on filenames/context, 
        # but let's check the df timestamps using the year present in data
        # If the data is from 2026 (as per context date), we should use that year.
        # The user said "Year in Review 2025", but the context date is Jan 2026.
        # The sample data file is "1134530128517550231_20260108.txt".
        # Let's check what years are available.
        
        years = df['timestamp'].dt.year.unique()
        target_year = 2025
        if 2025 not in years:
             if len(years) > 0:
                 target_year = years[0] # Pick the first available year if 2025 is missing
                 print(f"[WARN] 2025 not found in data. Switching to year {target_year}")
    
        # Scan for an active month to test
        sample_month = None
        for m in range(1, 13):
            if not df[df['timestamp'].dt.month == m].empty:
                sample_month = m
                break
        
        if not sample_month:
            print("[ERROR] No data in any month.")
            return

        print(f"[INFO] Testing single month index: {sample_month}")
        insights = get_monthly_insights(df, year=target_year, target_month=sample_month)
        
        # 4. Print Results
        print("\n" + "="*40)
        print(f"AI INSIGHTS REPORT FOR {target_year} (Month {sample_month})")
        print("="*40 + "\n")
        
        if not insights:
            print("No insights generated.")
        
        for month, data in insights.items():
            print(f"📅 {month.upper()}")
            print(f"   Mood: {data.get('sentiment', 'N/A')}")
            print(f"   Quote: \"{data.get('quote', 'N/A')}\" — {data.get('quote_author', 'Unknown')}")
            print("   Summary:")
            for point in data.get('summary', []):
                print(f"    - {point}")
            print("-" * 20)
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_monthly_analysis()
