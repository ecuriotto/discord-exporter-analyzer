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
    # Always place the HTML in input/ folder
    output_html_path = os.path.join(input_dir, os.path.basename(output_html))
    cmd = [
        cli_path,
        'export',
        '-t', token,
        '-c', channel_id,
        '-f', 'HtmlDark',
        '-o', output_html_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Exported HTML to {output_html}")
            return True
        else:
            print(f"Export failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error running DiscordChatExporter: {e}")
        return False
