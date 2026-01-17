# estraiDiscordHtml

A toolset to export Discord chats, extract clean text for LLMs, and generate rich HTML analytics reports (Year in Review).

## Features

### 1. Web Dashboard (`src/web`)
- **User Friendly Interface:** Manage the entire workflow from a browser.
- **Server/Channel Explorer:** Automatically lists joined servers and channels.
- **Real-time Logs:** Monitor extraction and analysis progress live.
- **Report Viewer:** View generated HTML summaries directly in the dashboard.
- **Smart Formatting:** Handles file naming and clean text conversion automatically.

### 2. Data Extraction (`src/extraction`)
- Wrapper around **DiscordChatExporter.Cli** to export channels to text.
- Parses HTML/JSON exports into clean, line-by-line text files optimized for LLM analysis.
- Supports naming files with actual channel names (e.g., `ChannelName_ID.txt`).

### 3. Analytics & Visualization (`src/analysis`)
- Generates a "Year in Review" HTML report with AI insights.
- **Charts:** Top Contributors, Activity Heatmap, Word Cloud, Timeline, Night Owls, Link Spammers.
- **AI Insights:** Summaries, sentiment analysis, and highlight quotes (Funniest/Most Impactful) powered by **OpenRouter** (using free models like Gemini 2.0 Flash, Llama 3, DeepSeek R1).
- **Languages:** Default output in Italian, parameterizable.

## Project Structure
```
.
├── src/
│   ├── web/                # FastAPI Web Application
│   ├── extraction/         # Tools for exporting/parsing Discord data
│   └── analysis/           # Tools for stats, AI insights, and HTML generation
├── input/                  # Extracted source .html/.txt files
├── output/                 # Generated HTML Reports & Cleaned text
├── DiscordChatExporterCli/ # External CLI tool (Required)
├── discord_token.txt       # Your Discord User Token (Required for extraction)
└── openRouter_token.txt    # OpenRouter API Key (Required for AI insights)
```

## Requirements
- Python 3.10+
- [`DiscordChatExporter.Cli`](https://github.com/Tyrrrz/DiscordChatExporter) (placed in `DiscordChatExporterCli/`)
- Dependencies: `pandas`, `plotly`, `wordcloud`, `jinja2`, `openai`, `fastapi`, `uvicorn`, `beautifulsoup4`

## Setup
1. **Environment Variables (.env):** 
   Create a `.env` file in the project root (copied from `.env.example` if available).
   ```bash
   DISCORD_TOKEN=your_discord_user_token_here
   OPENROUTER_API_KEY=your_openrouter_key_here
   ```
   *Note: For backward compatibility, `discord_token.txt` and `openRouter_token.txt` are still supported if `.env` is missing.*

2. **CLI Tool:** 
   Download [DiscordChatExporter.Cli](https://github.com/Tyrrrz/DiscordChatExporter/releases) (cross-platform zip) and extract it into a folder named `DiscordChatExporterCli/` in the project root.
   *   **macOS/Linux:** Ensure the binary `DiscordChatExporter.Cli` has execute permissions (`chmod +x DiscordChatExporterCli/DiscordChatExporter.Cli`).
   *   **Dotnet Runtime:** You may need the [.NET 8 Runtime](https://dotnet.microsoft.com/en-us/download/dotnet/8.0) installed.

3. **Dependencies:** 
   Install the required Python packages from `requirements.txt`.
   ```bash
   pip install -r requirements.txt
   playwright install  # Required for PDF export
   ```

## Usage

### Method 1: Web Dashboard (Recommended)

1. **Start the Server:**
   ```bash
   # Run from the project root
   python -m uvicorn src.web.app:app --reload
   ```
2. **Open Dashboard:**
   Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
3. **Select & Extract:**
   - Choose a Server and Channel from the dropdowns.
   - Click **Start Extraction**. The tool will download the channel history and convert it to text.
4. **Analyze:**
   - Switch to the "Analysis" tab.
   - Select the extracted file (e.g., `ChannelName_12345.txt`).
   - Choose a Year/Quarter (optional) and Language.
   - Click **Run Analysis** to generate the report.
   - View the result (HTML and PDF) in the "Reports" list.

### Method 2: Command Line (Advanced)

#### 1. Checking Quota / Models
Check your OpenRouter credit status or list available free models:
```bash
python src/analysis/check_quota.py
python src/analysis/list_models.py
```

#### 2. Extract Channel Data
Downloads the channel history and converts it to text.
```bash
# Syntax: python src/extraction/main_extraction.py --export <CHANNEL_ID>

python src/extraction/main_extraction.py --export 1134530128517550231
```
*   This creates a file like `output/txt/ChannelName_1134530128517550231.txt`.

#### 3. Run Analysis
Generates the HTML/PDF report from a text file.

```bash
# Default (Italian, Previous Year)
python src/analysis/main_analysis.py --input output/txt/ChannelName.txt

# Specific Year & Options
python src/analysis/main_analysis.py --input output/txt/ChannelName.txt --year 2025 --quarter Q1 --lang English
```

## Testing
To run the automated test suite (Unit Tests and End-to-End Pipeline):
```bash
python -m pytest tests/
```
