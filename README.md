# estraiDiscordHtml

A toolset to export Discord chats, extract clean text for LLMs, and generate rich HTML analytics reports (Year in Review).

## Features

### 1. Data Extraction (`src/extraction`)
- Wrapper around **DiscordChatExporter.Cli** to export channels to text.
- Parses HTML/JSON exports into clean, line-by-line text files optimized for LLM analysis.

### 2. Analytics & Visualization (`src/analysis`)
- Generates a "Year in Review" HTML report with AI insights.
- **Charts:** Top Contributors, Activity Heatmap, Word Cloud, Timeline, Night Owls, Link Spammers.
- **AI Insights:** Summaries, sentiment analysis, and highlight quotes (Funniest/Most Impactful) powered by Gemini.
- **Languages:** Default output in Italian, parameterizable.

## Project Structure
```
.
├── src/
│   ├── extraction/         # Tools for exporting/parsing Discord data
│   └── analysis/           # Tools for stats, AI insights, and HTML generation
├── input/                  # Place your source .txt files here
├── output/                 # Generated HTML Reports
├── DiscordChatExporterCli/ # External CLI tool (Required)
├── discord_token.txt       # Your Discord User Token (Required for extraction)
└── gemini_token.txt        # Gemini API Key (Required for AI insights)
```

## Requirements
- Python 3.9+
- [`DiscordChatExporter.Cli`](https://github.com/Tyrrrz/DiscordChatExporter) (placed in `DiscordChatExporterCli/`)
- Dependencies: `pandas`, `plotly`, `wordcloud`, `jinja2`, `google-generativeai`

## Setup
1. **Discord Token:** Create `discord_token.txt` in the root with your Discord user token.
2. **Gemini Key:** Create `gemini_token.txt` in the root with your Google Gemini API key.
3. **CLI Tool:** Ensure the DiscordChatExporter executable is in `DiscordChatExporterCli/`.
4. **Dependencies:** Install the required Python packages.
   ```bash
   pip install -r requirements.txt
   ```


## Usage

### End-to-End Workflow (Extract + Analyze)

You can run the full process from extraction to report generation.

1. **Extract Channel Data**  
   Use the extraction tool to download the channel history.
   ```bash
   # Syntax: python src/extraction/main_extraction.py --export <CHANNEL_ID>
   # NOTE: You don't need to specify the output filename; it auto-generates based on ID.

   python src/extraction/main_extraction.py --export 1134530128517550231
   ```
   *   This downloads the HTML (e.g., `input/1134530128517550231.html`) and converts it to `output/1134530128517550231.txt`.

2. **Run Analysis**  
   Run the analysis script.
   ```bash
   python src/analysis/main_analysis.py --year 2025
   ```
   *   It automatically detects the `.txt` file in `output/`.
   *   **Note:** If you have multiple files, specify one:
       ```bash
       python src/analysis/main_analysis.py --input output/1134530128517550231.txt --year 2025
       ```

### Run Analysis (Manual)
Generate the report from an existing `.txt` chat log (found in `input/` or `output/`).

```bash
# Default (Italian, Previous Year)
python src/analysis/main_analysis.py

# Specific Year
python src/analysis/main_analysis.py --year 2024

# Specific Quarter (e.g., Q1)
python src/analysis/main_analysis.py --year 2024 --quarter Q1

# Specific Language
python src/analysis/main_analysis.py --lang English
```

**Note:** If `--year` is omitted, the script defaults to the **previous year** (e.g., if run in 2026, it analyzes 2025).

### Future Roadmap

#### Sprint 1: Web Application Helper
**Goal:** Create a user-friendly web interface to manage the extraction and analysis workflow, removing the need for terminal commands.

**Key Features:**
- **Dashboard:** View available channels and previous reports.
- **Workflow Selector:**
    1.  **Extract Only:** Download channel history to local text files.
    2.  **Analyze Only:** Run reports on existing data (filter by Year/Quarter).
    3.  **End-to-End:** Run extraction followed immediately by analysis.
- **Channel Manager:** visual selection of channels (saved in config).
- **Log Viewer:** Real-time visibility into the background process (like the CLI progress bars).

#### Backlog
- Sentiment Analysis graphs.
