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

## Usage

### Run Analysis
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
- Sentiment Analysis graphs.
