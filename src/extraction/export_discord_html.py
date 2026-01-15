import subprocess
import os

def export_discord_html(channel_id, output_html, token_file='discord_token.txt', cli_path='DiscordChatExporterCli/DiscordChatExporter.Cli'):
    """
    Export Discord channel messages to HTML using DiscordChatExporter CLI.
    Args:
        channel_id: Discord channel ID to export
        output_html: Path to output HTML file
        token_file: Path to file containing Discord token
        cli_path: Path to DiscordChatExporter CLI executable
    Returns:
        True if export succeeded, False otherwise
    """
    # Ensure the token file exists
    if not os.path.isfile(token_file):
        print(f"Token file '{token_file}' not found.")
        return False
    with open(token_file, 'r') as f:
        token = f.read().strip()
    if not token:
        print("Discord token is empty.")
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
    
    cmd = [
        cli_path,
        'export',
        '-t', token,
        '-c', channel_id,
        '-f', 'HtmlDark',
        '-o', output_html_path
    ]
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
            print(f"[SUCCESS] Exported HTML to {output_html_path}")
            return True
        else:
            print(f"[ERROR] Export failed with return code {process.returncode}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception running DiscordChatExporter: {e}")
        return False
