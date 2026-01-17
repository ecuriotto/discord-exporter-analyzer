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
project_root = os.path.dirname(os.path.dirname(current_dir))

if project_root not in sys.path:
    sys.path.append(project_root)

if current_dir not in sys.path:
    sys.path.append(current_dir)

from parse_and_clean import parse_and_clean_discord_txt
from stats_and_visuals import get_top_contributors_chart, get_activity_heatmap, get_wordcloud_img, get_timeline_chart, get_yap_o_meter_chart, get_night_owls_chart, get_spammer_chart
from ai_insights import get_quarterly_insights, generate_yearly_summary
try:
    from html_to_pdf import convert_html_to_pdf
except ImportError:
    # Just in case imports are weird
    from src.analysis.html_to_pdf import convert_html_to_pdf

# Import centralized configuration
from src.config import (
    INPUT_DIR, 
    OUTPUT_DIR, 
    OUTPUT_HTML_DIR,
    OUTPUT_PDF_DIR,
    OUTPUT_TXT_DIR,
    ANALYSIS_TEMPLATES_DIR as TEMPLATE_DIR, 
    CLI_PATH,
    DISCORD_TOKEN_FILE
)
from src.logger import setup_logger

logger = setup_logger("analysis")

def get_channel_name(channel_id, token_path=DISCORD_TOKEN_FILE):
    """
    Uses DiscordChatExporter.Cli to fetch the channel name.
    """
    # 1. Environment Variable
    token = os.getenv("DISCORD_TOKEN")
    
    # 2. File Fallback
    if not token:
        if os.path.exists(token_path):
            try:
                with open(token_path, 'r') as f:
                    token = f.read().strip()
            except Exception:
                pass
    
    if not token:
        logger.warning(f"No Discord token found. Using ID as name.")
        return f"Channel_{channel_id}"

    try:
        logger.info(f"Fetching channel name for ID: {channel_id}...")
        
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

        logger.warning("Could not parse channel name. Fallback to ID.")
        return f"Channel_{channel_id}"
        
    except Exception as e:
        logger.warning(f"Failed to fetch channel name: {e}")
        return f"Channel_{channel_id}"

def find_input_file(specific_path=None):
    """
    Finds the first suitable .txt file in input/ or output/.
    Or uses the specific path if provided.
    Returns (file_path, channel_id).
    """
    if specific_path:
        if not os.path.exists(specific_path):
             logger.error(f"Specified file not found: {specific_path}")
             return None, None
        target_file = specific_path
    else:
        # Look for TXT in input/
        txt_files = glob.glob(os.path.join(INPUT_DIR, "*.txt"))
        
        # Check output/txt/
        if not txt_files:
             txt_files = glob.glob(os.path.join(OUTPUT_TXT_DIR, "*.txt"))
        
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
    logger.info(f"Target Year for Analysis: {target_year}")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 2. Find Input
    input_path, channel_id = find_input_file(args.input)
    if not input_path:
        logger.error("No input .txt file found in input/ or output/.")
        return
    
    logger.info(f"Processing file: {input_path}")
    logger.info(f"Channel ID: {channel_id}")

    # 3. Get Metadata
    # Try to extract name from filename first (Name_ID.txt)
    base_name = os.path.basename(input_path)
    # Check if filename roughly matches "Name_ID.txt" pattern
    # Assuming ID is at the end preceded by "_" or just the ID itself
    # E.g. "circolo-dei-value-investor_12345.txt"
    name_match = re.search(r"^(.*)_(\d{17,20})\.txt$", base_name)
    
    if name_match:
        # Extract name part
        potential_name = name_match.group(1)
        # Verify it's not just "%n" or generic
        if potential_name and "%n" not in potential_name:
            channel_name = potential_name
            logger.info(f"Using Channel Name from filename: {channel_name}")
        else:
            channel_name = get_channel_name(channel_id)
            logger.info(f"Resolved Channel Name (via CLI): {channel_name}")
    else:
        channel_name = get_channel_name(channel_id)
        logger.info(f"Resolved Channel Name (via CLI): {channel_name}")

    # 4. Parse Data & Filter by Year
    df = parse_and_clean_discord_txt(input_path)
    if df.empty:
        logger.warning("DataFrame is empty. Check parsing logic.")
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
    logger.info("Generating charts...")
    top_contributors_html = get_top_contributors_chart(df)
    activity_heatmap_html = get_activity_heatmap(df)
    wordcloud_html = get_wordcloud_img(df)
    timeline_html = get_timeline_chart(df)
    yap_html = get_yap_o_meter_chart(df)
    night_owls_html = get_night_owls_chart(df)
    spammer_html = get_spammer_chart(df)

    # 5b. AI Insights (Quarterly)
    logger.info(f"Generating AI Quarterly Insights ({args.lang})...")
    quarterly_insights = {}
    yearly_summary_text = None

    if not df.empty:
        try:
            # We already have target_year from args/default
            # Pass target_quarter if set
            quarterly_insights = get_quarterly_insights(df, year=target_year, target_quarter=target_quarter, language=args.lang)
            
            # Generate Executive Summary if we have any output
            if quarterly_insights:
                 logger.debug(f"AI Insights keys: {list(quarterly_insights.keys())}")
                 
                 # Optimization: If only 1 quarter, use the "executive_summary" directly from that quarter if available
                 if len(quarterly_insights) == 1:
                     single_key = list(quarterly_insights.keys())[0]
                     single_data = quarterly_insights[single_key]
                     if "executive_summary" in single_data and single_data["executive_summary"]:
                         logger.info(f"Single quarter detected ({single_key}). Using pre-generated Executive Summary.")
                         yearly_summary_text = single_data["executive_summary"]
                     else:
                         # Fallback if old prompt or missing field
                         logger.info(f"Single quarter detected, but 'executive_summary' missing. Generating fallback.")
                         yearly_summary_text = generate_yearly_summary(quarterly_insights, target_year, args.lang)
                 else:
                     # Multiple quarters: We must synthesize them
                     yearly_summary_text = generate_yearly_summary(quarterly_insights, target_year, args.lang)
            else:
                 logger.warning("AI Insights dictionary is EMPTY. Skipping AI summary generation.")
        except Exception as e:
            logger.error(f"Critical error during AI Analysis: {e}")
            logger.info("Proceeding with report generation without AI insights.")
            # Ensure safe fallback values
            quarterly_insights = {}
            yearly_summary_text = "AI Analysis failed to generate a summary for this period."
    
    # 6. Render Report
    logger.info("Rendering HTML report...")
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
    
    # Organize in subfolders (using centralized config paths)
    # OUTPUT_HTML_DIR, OUTPUT_PDF_DIR are imported from config
    
    output_path = os.path.join(OUTPUT_HTML_DIR, output_filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    logger.info(f"Report generated: {output_path}")

    # 8. Generate PDF
    if convert_html_to_pdf:
        # PDF filename
        pdf_filename = output_filename.replace(".html", ".pdf")
        pdf_path = os.path.join(OUTPUT_PDF_DIR, pdf_filename)
        
        logger.info(f"Generating PDF: {pdf_path}...")
        try:
            convert_html_to_pdf(output_path, pdf_path)
            logger.info(f"PDF generated: {pdf_path}")
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            logger.info("Try running 'playwright install' if this is the first run.")

if __name__ == "__main__":
    main()

