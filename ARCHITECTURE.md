# Application Architecture

This document describes the high-level architecture, data flow, and file structure of the **estraiDiscordHtml** project.

## 1. High-Level Architecture

The application is structured as a **Processing Pipeline** wrapped in a **Web Interface**.

```mermaid
graph TD
    User[User] -->|Browser| WebUI[Web Dashboard\n(HTML/JS)]
    WebUI -->|HTTP Requests| API[FastAPI Backend\n(src/web/app.py)]
    
    subgraph "Extraction Layer"
        API -->|Subprocess| ExtractScript[main_extraction.py]
        ExtractScript -->|Calls| CLI[DiscordChatExporter.Cli]
        CLI -->|Exports| HTML[Raw HTML]
        ExtractScript -->|Parses| TXT[Cleaned Text Logs]
    end
    
    subgraph "Analysis Layer"
        API -->|Subprocess| AnalyzeScript[main_analysis.py]
        AnalyzeScript -->|Reads| TXT
        AnalyzeScript -->|Generates| Stats[Statistics & Charts]
        AnalyzeScript -->|API Call| OpenRouter[OpenRouter / Gemini / Llama]
        Stats & OpenRouter -->|Compiles| Report[HTML + PDF Report]
    end
    
    Report -->|Served by| API
```

## 2. Data Flow

1.  **Selection**: User selects a Guild/Channel in the Web UI.
2.  **Extraction**: 
    *   System invokes `DiscordChatExporter` to download chat history as HTML.
    *   System parses the HTML (BeautifulSoup) into a clean, LLM-friendly Text format.
    *   *Result*: `output/txt/ChannelName_ID.txt`.
3.  **Analysis**:
    *   System reads the Text file.
    *   **Statistical Analysis**: Pandas is used to calculate activity, word counts, and user stats.
    *   **AI Enrichment**: The text is sent to an LLM via **OpenRouter** to extract summaries, sentiment, and highlights.
    *   **Visualization**: Plotly creates charts (Heatmaps, Bar charts).
4.  **Reporting**:
    *   All data is injected into a Jinja2 HTML template.
    *   (Optional) Playwright converts the HTML to PDF.
    *   *Result*: `output/html/ChannelName_Report_Year.html` and `output/pdf/ChannelName_Report_Year.pdf`.

## 3. File Descriptions

### Configuration & Root
*   **`src/config.py`**: Centralized configuration module. Handles **absolute paths** and loads Environment Variables (`.env`) for secrets.
*   **`src/logger.py`**: Standardized logging utility used across all modules.

### Web Layer (`src/web/`)
*   **`app.py`**: The core application server (FastAPI). It serves the frontend, handles API requests for guild/channel lists, manages background tasks (extraction/analysis jobs), and serves the generated reports.
*   **`templates/index.html`**: The Single Page Application (SPA) dashboard. Contains the JavaScript logic for polling job status and displaying logs.

### Extraction Layer (`src/extraction/`)
*   **`main_extraction.py`**: The entry point for extraction. It orchestrates the process: calls the export wrapper, checks filenames, and runs the HTML-to-Text conversion.
*   **`export_discord_html.py`**: A specific wrapper around the `DiscordChatExporter.Cli` executable. Handles command-line arguments and token authentication securely.

### Analysis Layer (`src/analysis/`)
*   **`main_analysis.py`**: The orchestrator for the analysis phase. It loads the text data, calls the statistics and AI modules, and renders the final HTML report.
*   **`parse_and_clean.py`**: Contains Regex patterns and logic to parse the raw text logs into structured DataFrames (Timestamp, Author, Content). Includes log cleaning logic.
*   **`stats_and_visuals.py`**: Logic for generating visualizations using Plotly and WordCloud. Creates the "Top Contributors", "Activity Heatmap", and "Night Owls" charts.
*   **`ai_insights.py`**: Handles interaction with the **OpenRouter API**. Manages context windows, model selection, and prompt templates.
*   **`html_to_pdf.py`**: Uses **Playwright** to capture the generated HTML report (with JavaScript charts) and save it as a PDF.

### Common/Config
*   **`.env`**: (GitIgnored) The source of truth for secrets: `DISCORD_TOKEN`, `OPENROUTER_API_KEY`.
*   **`requirements.txt`**: Python dependencies.


## 4. Visualization Prompt

Use the following prompt with an AI image generator (Midjourney, DALL-E 3) to create a visual representation of the architecture:

> Create a modern, isometric technical illustration of a software architecture on a dark background.
>
> **Scene Composition:**
> 1.  **Left Side (Frontend):** A glowing laptop screen displaying a dashboard interface labeled "**index.html**". A connection line flows from it to the center.
> 2.  **Center (Backend Core):** A central server block or gear icon labeled "**app.py**". It acts as the traffic manager.
> 3.  **Right Branch (Extraction):** A pipeline flowing downwards from the center. It represents "**main_extraction.py**" triggering a command-line terminal icon (CLI) which extracts data into a document file labeled "**Channel.txt**".
> 4.  **Right Branch (Analysis):** Another pipeline flowing from the center (or picking up the TXT file). It represents "**main_analysis.py**" splitting into two sub-processes:
>     *   A chart/graph icon representing statistics modules.
>     *   A brain/AI chip icon glowing blue, representing "**ai_insights.py**" connecting to Gemini.
> 5.  **Output:** All branches converge into a final, polished document icon labeled "**Report.html**" at the bottom right.
>
> **Style:** High-tech, clean lines, neon accents (Blue, Green, Purple), diagrammatic but 3D. No text clutter, just clean icons, flow lines, and the specific filenames as labels.

