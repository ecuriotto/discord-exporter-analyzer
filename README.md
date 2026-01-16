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
- **AI Insights:** Summaries, sentiment analysis, and highlight quotes (Funniest/Most Impactful) powered by Gemini.
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
└── gemini_token.txt        # Gemini API Key (Required for AI insights)
```

## Requirements
- Python 3.10+
- [`DiscordChatExporter.Cli`](https://github.com/Tyrrrz/DiscordChatExporter) (placed in `DiscordChatExporterCli/`)
- Dependencies: `pandas`, `plotly`, `wordcloud`, `jinja2`, `google-generativeai`, `fastapi`, `uvicorn`, `beautifulsoup4`

## Setup
1. **Discord Token:** Create `discord_token.txt` in the root with your Discord user token.
2. **Gemini Key:** Create `gemini_token.txt` in the root with your Google Gemini API key.
3. **CLI Tool:** Ensure the DiscordChatExporter executable is in `DiscordChatExporterCli/`.
4. **Dependencies:** Install the required Python packages.
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Method 1: Web Dashboard (Recommended)

The easiest way to use the tool is via the web interface.

1. **Start the Server:**
   ```bash
   python -m uvicorn src.web.app:app --reload
   ```
2. **Open Dashboard:**
   Navigate to [http://localhost:8000](http://localhost:8000) in your browser.
3. **Select & Extract:**
   - Choose a Server and Channel from the dropdowns.
   - Click **Start Extraction**. The tool will download the channel history and convert it to text.
4. **Analyze:**
   - Switch to the "Analysis" tab.
   - Select the extracted file (e.g., `ChannelName_12345.txt`).
   - Choose a Year/Quarter (optional) and Language.
   - Click **Run Analysis** to generate the report.
   - View the result in the "Reports" list.

### Method 2: Command Line (Advanced)

You can run the individual scripts manually for automation or debugging.

#### 1. Extract Channel Data
Downloads the channel history and converts it to text.
```bash
# Syntax: python src/extraction/main_extraction.py --export <CHANNEL_ID>

python src/extraction/main_extraction.py --export 1134530128517550231
```
*   This creates a file like `output/ChannelName_1134530128517550231.txt`.

#### 2. Run Analysis
Generates the HTML report from a text file.

```bash
# Default (Italian, Previous Year)
python src/analysis/main_analysis.py --input output/ChannelName.txt

# Specific Year & Options
python src/analysis/main_analysis.py --input output/ChannelName.txt --year 2025 --quarter Q1 --lang English
```

## Troubleshooting

- **Empty Server List?** Ensure `discord_token.txt` contains a valid user token and `DiscordChatExporter.Cli` is executable (`chmod +x` on macOS/Linux).
- **Extraction Stuck?** Large channels can call take time. Check the console logs.
- **Incorrect Filenames?** The tool attempts to resolve channel names automatically. If it fails, checks the logs for `[WARN]`.
