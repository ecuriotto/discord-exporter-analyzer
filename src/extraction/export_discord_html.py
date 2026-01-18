import subprocess
import os

def get_discord_token(token_file='discord_token.txt'):
    # 1. Environment Variable
    token = os.getenv("DISCORD_TOKEN")
    if token:
        return token
        
    # 2. File
    if os.path.isfile(token_file):
        with open(token_file, 'r') as f:
            return f.read().strip()
            
    return None

def export_discord_html(channel_id, output_html, token_file='discord_token.txt', cli_path='DiscordChatExporterCli/DiscordChatExporter.Cli', after_date=None):
    """
    Export Discord channel messages to HTML using DiscordChatExporter CLI.
    Args:
        channel_id: Discord channel ID to export
        output_html: Path to output HTML file
        token_file: Path to file containing Discord token
        cli_path: Path to DiscordChatExporter CLI executable
        after_date: Optional ISO 8601 date string. If set, only messages after this date are exported.
    Returns:
        True if export succeeded, False otherwise
    """
    # Get Token
    token = get_discord_token(token_file)
    if not token:
        print(f"Discord token not found in env 'DISCORD_TOKEN' or file '{token_file}'.")
        return False

    # Compose the command to run the DiscordChatExporter CLI
    if not os.path.isfile(cli_path):
        print(f"DiscordChatExporter CLI '{cli_path}' not found.")
        return False
    # Ensure output_html is in input/ directory
    # If this file is in src/extraction/, we need to go up two levels to reach root, then into input
    input_dir = os.path.join(os.path.dirname(__file__), '../../input')
    os.makedirs(input_dir, exist_ok=True)
    
    # Process output path
    # If it's a template (has %), we trust the caller knows what they are doing, but we ensure it lands in input_dir
    filename = os.path.basename(output_html)
    output_html_path = os.path.join(input_dir, filename)
    
    # [FIX] If INCREMENTAL (after_date is set), we MUST use a temporary file to avoid the "Overwrite?" prompt.
    # The prompt appears if the file exists. 
    # Even if we want to overwrite, -o forces it usually? No, it asks.
    # We should render to a temp file, then move/rename it.
    
    final_target_path = output_html_path
    
    # If we are in incremental mode, or simply want to avoid issues, always write to temp first.
    # We use a temp prefix even for template patterns (%n). 
    # Example: output_html="input/%n_%c.html" -> temp_output="input/temp_%n_%c.html"
    # CLI will generate "input/temp_RealName_ID.html".
    # We won't be able to simple rename it here because we don't know RealName, 
    # but the calling script (main_extraction) uses glob to find the file, so it will pick up the temp file correctly.
    
    use_temp = False
    if after_date:
        use_temp = True
        dir_name = os.path.dirname(output_html_path)
        base_name = os.path.basename(output_html_path)
        temp_name = f"temp_{base_name}"
        output_html_path = os.path.join(dir_name, temp_name)
    
    cmd = [
        cli_path,
        'export',
        '-t', token,
        '-c', channel_id,
        '-f', 'HtmlDark',
        '-o', output_html_path
    ]

    if after_date:
        print(f"[INFO] Incremental export: Fetching messages after {after_date}")
        cmd.extend(['--after', after_date])

    try:
        print(f"[INFO] Starting Discord export for channel {channel_id}...")
        print(f"[INFO] Command: {' '.join(cmd)}")
        
        # Use Popen to stream output line by line
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Print output in real-time, filtering out progress bars
        print("[CLI] Detailed progress hidden to reduce noise (exporting in background)...")
        for line in process.stdout:
            clean_line = line.strip()
            # Skip progress bar lines (contain block characters or look like percentages only)
            if "━" in clean_line or (clean_line.endswith("%") and "Warn" not in clean_line):
                continue
            if not clean_line:
                continue
            print(f"[CLI] {clean_line}")
            
        process.wait()
        
        if process.returncode == 0:
            if use_temp:
                 # Move temp to final
                 if os.path.exists(output_html_path):
                     if os.path.exists(final_target_path):
                         os.remove(final_target_path)
                     os.rename(output_html_path, final_target_path)
                     print(f"[SUCCESS] Exported HTML to {final_target_path} (via temp)")
                 else:
                     print(f"[WARN] Temp file {output_html_path} not found after success?")
            else:
                 print(f"[SUCCESS] Exported HTML to {output_html_path}")
            return True
        else:
            print(f"[ERROR] Export failed with return code {process.returncode}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception running DiscordChatExporter: {e}")
        return False
