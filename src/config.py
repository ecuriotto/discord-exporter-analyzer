import os
from dotenv import load_dotenv

# Base Directory: Root of the project (parent of src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Data Directories
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
OUTPUT_HTML_DIR = os.path.join(OUTPUT_DIR, "html")
OUTPUT_PDF_DIR = os.path.join(OUTPUT_DIR, "pdf")
OUTPUT_TXT_DIR = os.path.join(OUTPUT_DIR, "txt")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Configuration Files
DISCORD_TOKEN_FILE = os.path.join(BASE_DIR, "discord_token.txt")
OPENROUTER_TOKEN_FILE = os.path.join(BASE_DIR, "openRouter_token.txt")
CHANNEL_NAMES_FILE = os.path.join(OUTPUT_DIR, "channel_cache.json")

# External Tools
CLI_DIR = os.path.join(BASE_DIR, "DiscordChatExporterCli")
# On macOS/Linux it's usually just "DiscordChatExporter.Cli" (the executable script)
# On Windows it might be "DiscordChatExporter.Cli.exe"
CLI_PATH = os.path.join(CLI_DIR, "DiscordChatExporter.Cli")

# Module Paths
SRC_DIR = os.path.join(BASE_DIR, "src")
ANALYSIS_DIR = os.path.join(SRC_DIR, "analysis")
EXTRACTION_DIR = os.path.join(SRC_DIR, "extraction")
WEB_DIR = os.path.join(SRC_DIR, "web")

# Templates and Resources
ANALYSIS_TEMPLATES_DIR = os.path.join(ANALYSIS_DIR, "templates")
ANALYSIS_RESOURCES_DIR = os.path.join(ANALYSIS_DIR, "resources")
EXTRACTION_RESOURCES_DIR = os.path.join(EXTRACTION_DIR, "resources")
WEB_TEMPLATES_DIR = os.path.join(WEB_DIR, "templates")
WEB_STATIC_DIR = os.path.join(WEB_DIR, "static")

# Cache Files
CHANNELS_CACHE_FILE = os.path.join(EXTRACTION_RESOURCES_DIR, "channels_cache.json")

# Ensure core directories exist, LOGS_DIR
for d in [INPUT_DIR, OUTPUT_DIR, OUTPUT_HTML_DIR, OUTPUT_PDF_DIR, OUTPUT_TXT_DIR, EXTRACTION_RESOURCES_DIR]:
    os.makedirs(d, exist_ok=True)
