import os

# Base Directory: Root of the project (parent of src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data Directories
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
OUTPUT_HTML_DIR = os.path.join(OUTPUT_DIR, "html")
OUTPUT_PDF_DIR = os.path.join(OUTPUT_DIR, "pdf")
OUTPUT_TXT_DIR = os.path.join(OUTPUT_DIR, "txt")

# Configuration Files
DISCORD_TOKEN_FILE = os.path.join(BASE_DIR, "discord_token.txt")
GEMINI_TOKEN_FILE = os.path.join(BASE_DIR, "gemini_token.txt")
CHANNEL_NAMES_FILE = os.path.join(BASE_DIR, "channel_names.json")

# External Tools
CLI_DIR = os.path.join(BASE_DIR, "DiscordChatExporterCli")
# On macOS/Linux it's usually just "DiscordChatExporter.Cli" (the executable script)
# On Windows it might be "DiscordChatExporter.Cli.exe"
CLI_PATH = os.path.join(CLI_DIR, "DiscordChatExporter.Cli")

# Module Paths
SRC_DIR = os.path.join(BASE_DIR, "src")
ANALYSIS_DIR = os.path.join(SRC_DIR, "analysis")
WEB_DIR = os.path.join(SRC_DIR, "web")

# Templates
ANALYSIS_TEMPLATES_DIR = os.path.join(ANALYSIS_DIR, "templates")
WEB_TEMPLATES_DIR = os.path.join(WEB_DIR, "templates")
WEB_STATIC_DIR = os.path.join(WEB_DIR, "static")

# Ensure core directories exist
for d in [INPUT_DIR, OUTPUT_DIR, OUTPUT_HTML_DIR, OUTPUT_PDF_DIR, OUTPUT_TXT_DIR]:
    os.makedirs(d, exist_ok=True)
