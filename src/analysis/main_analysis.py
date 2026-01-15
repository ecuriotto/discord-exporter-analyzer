import os
import sys
import glob
import re
import argparse
import subprocess
import tempfile
import pandas as pd
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# Local modules
# Add src/analysis to sys.path if running from root
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from parse_and_clean import parse_and_clean_discord_txt
from stats_and_visuals import get_top_contributors_chart, get_activity_heatmap, get_wordcloud_img, get_timeline_chart, get_yap_o_meter_chart, get_night_owls_chart, get_spammer_chart
from ai_insights import get_quarterly_insights, generate_yearly_summary

# Config
INPUT_DIR = "input"
OUTPUT_DIR = "output"
TEMPLATE_DIR = "src/analysis/templates"
CLI_PATH = "./DiscordChatExporterCli/DiscordChatExporter.Cli"

def get_channel_name(channel_id, token_path="discord_token.txt"):
    """
    Uses DiscordChatExporter.Cli to fetch the channel name.
    """
    if not os.path.exists(token_path):
        print(f"[WARN] Token file not found at {token_path}. Using ID as name.")
        return f"Channel_{channel_id}"

    try:
        with open(token_path, 'r') as f:
            token = f.read().strip()
            
        print(f"[INFO] Fetching channel name for ID: {channel_id}...")
        
        # Create a temporary directory to avoid polluting the workspace
        with tempfile.TemporaryDirectory() as temp_dir:
            # We output to the temp dir with just %n.txt
            # This ensures we get just the name
            output_pattern = os.path.join(temp_dir, "%n.txt")
            
            cmd = [
                CLI_PATH, "export",
                "-t", token,
                "-c", channel_id,
                "-o", output_pattern, 
                "--after", "2099-01-01", # Future date -> 0 messages
                "--format", "PlainText"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check for generated file in temp_dir
            # The CLI tool will generate a file named "ChannelName.txt"
            files = os.listdir(temp_dir)
            if files:
                filename = files[0]
                # splitext to remove .txt extension
                possible_name = os.path.splitext(filename)[0]
                # If name is empty or just spaces, fallback
                # Also fallback if it's literally "%n" or generic default
                if possible_name.strip() and possible_name != "%n":
                    return possible_name
            
            # Fallback strategy: CLI Output Regex
            combined_output = result.stdout + result.stderr
            match = re.search(r"Channel '(.+?)' of guild", combined_output)
            if match:
                return match.group(1)

        print("[WARN] Could not parse channel name. Fallback to ID.")
        return f"Channel_{channel_id}"
        
    except Exception as e:
        print(f"[WARN] Failed to fetch channel name: {e}")
        return f"Channel_{channel_id}"

    except Exception as e:
        print(f"[ERROR] Failed to run CLI: {e}")
        return f"Channel_{channel_id}"

def find_input_file(specific_path=None):
    """
    Finds the first suitable .txt file in input/ or output/.
    Or uses the specific path if provided.
    Returns (file_path, channel_id).
    """
    if specific_path:
        if not os.path.exists(specific_path):
             print(f"[ERROR] Specified file not found: {specific_path}")
             return None, None
        target_file = specific_path
    else:
        # Look for TXT in input/
        txt_files = glob.glob(os.path.join(INPUT_DIR, "*.txt"))
        if not txt_files:
            # Fallback to output/ (dev convenience)
            txt_files = glob.glob(os.path.join(OUTPUT_DIR, "*.txt"))
            # Exclude generated reports or thread files
            txt_files = [f for f in txt_files if "_20" in f or re.search(r"\d{18}", f)]
        
        if not txt_files:
            return None, None
        
        target_file = txt_files[0]
        if len(txt_files) > 1:
            print(f"[WARN] Multiple files found. Using: {target_file}. Use --input to specify.")

    # Extract ID from filename (assuming format ID_Date.txt or just ID...)
    # Regex for 17-19 digit ID
    match = re.search(r"(\d{17,20})", os.path.basename(target_file))
    channel_id = match.group(1) if match else "UnknownID"
    
    return target_file, channel_id

def main():
    # 1. Argument Parsing & Setup
    parser = argparse.ArgumentParser(description="Generate Discord Chat Report")
    parser.add_argument("--year", type=int, help="Specific year to analyze (default: previous year)")
    parser.add_argument("--quarter", type=str, help="Specific quarter to analyze (e.g., Q1)")
    parser.add_argument("--lang", default="Italian", help="Language for AI output (default: Italian)")
    parser.add_argument("--input", default=None, help="Specific input .txt file path")
    args = parser.parse_args()

    # Determine target year (Default: Previous Year)
    target_year = args.year if args.year else (datetime.now().year - 1)
    print(f"[INFO] Target Year for Analysis: {target_year}")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 2. Find Input
    input_path, channel_id = find_input_file(args.input)
    if not input_path:
        print("[ERROR] No input .txt file found in input/ or output/.")
        sys.exit(1)
    
    print(f"[INFO] Processing file: {input_path}")
    print(f"[INFO] Channel ID: {channel_id}")

    # 3. Get Metadata
    channel_name = get_channel_name(channel_id)
    print(f"[INFO] Resolved Channel Name: {channel_name}")

    # 4. Parse Data & Filter by Year
    df = parse_and_clean_discord_txt(input_path)
    if df.empty:
        print("[WARN] DataFrame is empty. Check parsing logic.")
    else:
        # Filter for the target year
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        total_msgs = len(df)
        df = df[df['timestamp'].dt.year == target_year]
        
        # Filter for Quarter if specified
        target_quarter = None
        if args.quarter:
            q_clean = args.quarter.strip().upper()
            if q_clean.startswith('Q') and q_clean[1].isdigit():
                target_quarter = int(q_clean[1])
            elif q_clean.isdigit():
                target_quarter = int(q_clean)
                
            if target_quarter and 1 <= target_quarter <= 4:
                print(f"[INFO] Filtering for Quarter {target_quarter}...")
                df = df[df['timestamp'].dt.quarter == target_quarter]
            else:
                 print(f"[WARN] Invalid quarter format '{args.quarter}'. Ignoring.")
                 target_quarter = None

        filtered_msgs = len(df)
        
        print(f"[INFO] Parsed {total_msgs} total messages.")
        print(f"[INFO] Keeping {filtered_msgs} messages for Year {target_year}" + (f" Q{target_quarter}" if target_quarter else "") + ".")
        
        if df.empty:
            print(f"[WARN] No messages found for year {target_year}! Charts/AI will be empty.")

    # 5. Generate Visuals
    print("[INFO] Generating charts...")
    top_contributors_html = get_top_contributors_chart(df)
    activity_heatmap_html = get_activity_heatmap(df)
    wordcloud_html = get_wordcloud_img(df)
    timeline_html = get_timeline_chart(df)
    yap_html = get_yap_o_meter_chart(df)
    night_owls_html = get_night_owls_chart(df)
    spammer_html = get_spammer_chart(df)

    # 5b. AI Insights (Quarterly)
    print(f"[INFO] Generating AI Quarterly Insights ({args.lang})...")
    quarterly_insights = {}
    yearly_summary_text = None

    if not df.empty:
        # We already have target_year from args/default
        # Pass target_quarter if set
        quarterly_insights = get_quarterly_insights(df, year=target_year, target_quarter=target_quarter, language=args.lang)
        
        # Generate Executive Summary if we have any output
        if quarterly_insights:
             print(f"[DEBUG] AI Insights keys: {list(quarterly_insights.keys())}")
             
             # Optimization: If only 1 quarter, use the "executive_summary" directly from that quarter if available
             if len(quarterly_insights) == 1:
                 single_key = list(quarterly_insights.keys())[0]
                 single_data = quarterly_insights[single_key]
                 if "executive_summary" in single_data and single_data["executive_summary"]:
                     print(f"[INFO] Single quarter detected ({single_key}). Using pre-generated Executive Summary.")
                     yearly_summary_text = single_data["executive_summary"]
                 else:
                     # Fallback if old prompt or missing field
                     print(f"[INFO] Single quarter detected, but 'executive_summary' missing. Generating fallback.")
                     yearly_summary_text = generate_yearly_summary(quarterly_insights, target_year, args.lang)
             else:
                 # Multiple quarters: We must synthesize them
                 yearly_summary_text = generate_yearly_summary(quarterly_insights, target_year, args.lang)
        else:
             print("[DEBUG] AI Insights dictionary is EMPTY.")
    
    # 6. Render Report
    print("[INFO] Rendering HTML report...")
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template('report_template.html')
    
    html_content = template.render(
        channel_name=channel_name,
        generation_date=datetime.now().strftime("%d %B %Y"),
        top_contributors_chart=top_contributors_html,
        activity_heatmap=activity_heatmap_html,
        wordcloud_img=wordcloud_html,
        timeline_chart=timeline_html,
        yap_chart=yap_html,
        night_owls_chart=night_owls_html,
        spammer_chart=spammer_html,
        quarterly_insights=quarterly_insights,
        yearly_summary=yearly_summary_text
    )

    # 7. Save Output
    # Sanitize channel name for filename
    safe_name = "".join([c for c in channel_name if c.isalnum() or c in (' ', '-', '_')]).strip()
    if not safe_name: safe_name = f"Channel_{channel_id}"
    
    # Use the target_year for the filename
    suffix = f"_Q{target_quarter}" if target_quarter else ""
    output_filename = f"{safe_name}_Report_{target_year}{suffix}.html"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"[SUCCESS] Report generated: {output_path}")

if __name__ == "__main__":
    main()

