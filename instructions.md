# Instructions: Discord Chat Analysis & Report Generator (2025)

## Context
Analysis of the output `.txt` files exported via DiscordChatExporter.
- **Format:** `[DD-Mon-YY HH:MM AM/PM] Username: Message`
- **Goal:** Create a professional, interactive "Year in Review 2025" HTML report.
- **Hardware:** Optimized for Mac M4 Pro.

## Tech Stack
- **Data:** Python 3, Pandas
- **Visualization:** Plotly, WordCloud
- **AI:** `google-generativeai` (Gemini 1.5 Flash/Pro)
- **Templating:** Jinja2 / Inline HTML/CSS

---

## 🚀 ROADMAP ESECUTIVA (Backlog dei Ticket)

### SPRINT 1: Data Engine & Parsing
- [x] **Ticket 1.1:** Implement regex parsing to convert the `.txt` into a Pandas DataFrame. Columns: `timestamp` (datetime), `user`, `message`.
- [x] **Ticket 1.2:** Data Cleaning: remove system messages, bot commands (e.g., prefix `!`, `/`), and handle multi-line messages.
- [x] **Ticket 1.3:** Integrity Check: print summary stats (total messages, date range) to verify the parsing.

### SPRINT 2: Statistics & Visuals (Local)
- [x] **Ticket 2.1:** **Top Contributors:** Bar chart of the top 10 most active users.
- [x] **Ticket 2.2:** **Activity Heatmap:** Hourly activity distribution (Day of Week vs. Hour of Day).
- [x] **Ticket 2.3:** **Word Cloud:** Generate a WordCloud image using the most frequent terms (exclude common Italian/English stopwords). Save as base64 to embed in HTML.
- [x] **Ticket 2.4:** **Timeline:** Line chart showing message volume per month in 2025.

### SPRINT 3: Gemini API Integration (Intelligence)
- [x] **Ticket 3.1:** API Setup: Securely load `GEMINI_API_KEY`. Implement `summarize_text()` with exponential backoff for Rate Limits.
- [x] **Ticket 3.2:** **Monthly Analysis:** Chunk messages by month. Send to Gemini to extract:
    - A 3-bullet summary of main topics.
    - Dominant sentiment (e.g., "Excited", "Productive", "Chill").
    - "Funniest" or "Most Impactful" quote.
- [x] **Ticket 3.3:** **Executive Summary:** Pass monthly summaries to Gemini for a final high-level "Yearly Overview" (or Quarterly in case the quarter parameter is passed).

### SPRINT 3.5: Rework & Enhancements
- [x] **Ticket 3.4:** **Refactoring & Localization:**
    - **Language:** AI output must be in Italian by default, but parameterizable via CLI (e.g., `--lang it`).
    - **Prompts:** Move hardcoded AI prompts into a separate file (e.g., `src/analysis/templates/system_prompt.txt`).
    - **Quotes Update:** Rework Monthly Analysis to extract **1 Funniest** AND **1 Most Impactful** quote.
- [x] **Ticket 3.5:** **New Stat - The Spammer:** Identify and visualize users who share the most links (articles/videos).
- [x] **Ticket 3.6:** **Quarter Selection:** Add a `--quarter` (e.g., `Q1`) argument to analyze specific quarters only. If omitted, full year (default) or last year is used.

### SPRINT 4: UI & Report Export
- [x] **Ticket 4.1:** **Modern UI:** Create a Dark Mode HTML template with responsive CSS.
    - **Report Layout Spec:** **Single Column (Stacked) Layout** for linear reading.
        - **Header:** Title + Date.
        - **Block 1:** Executive Summary.
        - **Block 2:** Top Contributors & Spammers.
        - **Block 3:** Activity Timeline & Heatmap.
        - **Block 4:** Word Cloud & Funniest/Impactful Quotes.
- [x] **Ticket 4.2:** **Integration:** Embed Plotly charts (JSON/div) and the WordCloud image into the template.
- [x] **Ticket 4.3:** **Final Export:** Compile everything into `Report_Discord_2025.html`.

### SPRINT 5: Web Application Helper
- [x] **Ticket 5.1:** **Web Backend setup:** Create a lightweight web server (e.g., Flask/FastAPI) to expose endpoints for Extraction and Analysis scripts.
- [x] **Ticket 5.2:** **Dashboard - Extraction:** Frontend page has two sections: Extraction and analyze. Extraction shows in input, with a dropdown list all the different channels/threads available, as they can retrieved by the discord server dynamically. It's mandatory to select one of them to allow for the extraction. Another input section is the list of already extracted channels/threads, with the extraction date, they are just visible in readonly. A button will allow to trigger the extraction, that can potentially create a file that's already existing, in this case the replacemebt should occur without notifying the user. Some log should shown as a toaster, in order to let the user know the extraction execution (since this can take several minutes).Python errors should be shown in the page itself. Input and output can be mocked at this stage (implementation will happen in Ticket 5.4)
- [x] **Ticket 5.3:** **Dashboard - Analysis:** Analyze shows in input the extracted channels. It will allow to select some parameters (year (default the previous one), quarter (default the previous one), language (default italian) and anything that can be useful for the main_analysis). A button will allow to trigger the extraction, that can potentially create a file that's already existing, in this case the replacemebt should occur without notifying the user. Some log should shown as a toaster, in order to let the user know the extraction execution (since this can take several minutes). python errors should be shown in the page itself.Input and output can be mocked at this stage (implementation will happen in Ticket 5.5)
- [x] **Ticket 5.4:** **Workflow Selector:** UI controls to trigger:
    - **Extraction Only:** Run `main_extraction.py` for a selected channel.
- [x] **Ticket 5.5:**  
    - **Analysis Only:** Run `main_analysis.py` on existing data (with Year/Quarter selectors).

---

## 🛠 CODING GUIDELINES FOR COPILOT
1. **Efficiency:** Use Pandas vectorization for stats. Avoid large loops for the 2025 dataset.
2. **Context Management:** For Gemini, don't send raw logs if they exceed the context window. Use the "Monthly Chunking" strategy.
3. **WordCloud Cleaning:** Ensure the `WordCloud` library filters out "https", "Discord", "reazioni", and common conjunctions.
4. **Modularity:** Keep functions atomic: `process_data()`, `get_stats()`, `get_ai_insights()`, `render_report()`.

### SPRINT 6: Refactoring & Quality Assurance
- [x] **Ticket 6.1:** **Configuration Centralization:** Create `src/config.py` to define absolute paths (`BASE_DIR`, `INPUT_DIR`, `OUTPUT_DIR`, `TOKEN_PATH`) dynamically. Refactor `app.py`, `main_analysis.py`, `ai_insights.py`, and `html_to_pdf.py` to import configuration from this central file.
- [x] **Ticket 6.2:** **Logging Standardization:** Replace `print()` statements with Python's `logging` module. Configure logging to output to both console and a file (e.g., `logs/app.log`) with appropriate levels (INFO, ERROR, DEBUG).
- [x] **Ticket 6.3:** **Memory Optimization:** Refactor `parse_and_clean.py` and `main_extraction.py` to use lazy loading (generators) for file reading. Process large chat logs line-by-line to reduce RAM usage.
- [x] **Ticket 6.4:** **Error Handling & Resilience:** precise error handling in critical paths (AI service, PDF generation). Ensure the pipeline degrades gracefully (e.g., skip AI insights if API fails but still generate stats).
- [x] **Ticket 6.5:** **Security & Env Utils:** Enhance environment variable handling. Support `.env` file using `python-dotenv` while maintaining backward compatibility with `.txt` token files.

### SPRINT 7: Testing & Documentation
- [x] **Ticket 7.1:** **Unit & Integration Tests:** Create a test suite (`pytest`) for critical components: `parse_and_clean.py` (regex logic), `stats_and_visuals.py` (calculations), and data integrity.
- [x] **Ticket 7.2:** **End-to-End Validation:** Verify the full pipeline: Web UI -> Extraction -> Analysis -> Report Generation. Ensure PDF export works if Playwright is present.
- [x] **Ticket 7.3:** **Documentation Update:** Update `README.md` with final setup instructions (including `.env` usage, OpenRouter configuration), Prerequisites, and Usage examples. Update `ARCHITECTURE.md` to reflect the final project structure. Also be sure that there are instructions for other developers that want replicate the program on their own machines
- [x] **Ticket 7.4:** **Final Polish:** Code formatting (black/flake8), removing any remaining temporary files or unused imports.

### SPRINT 7.5: Performance & Accessibility
- [x] **Ticket 7.5.1:** **Lighthouse Performance:** Fix "First Contentful Paint" and blocking resources.
    - Identify and defer non-critical scripts/CSS.
    - Optimize font loading (if any).
    - Ensure `report_template.html` uses efficient loading for Tailwind/Plotly (explore local assets vs CDN or `defer`).
- [x] **Ticket 7.5.2:** **Accessibility (A11y):**
    - **Semantics:** Wrap the main content in a `<main>` tag.
    - **Contrast:** Improve the contrast ratio for text on dark backgrounds (especially grey `#b9bbbe` on `#202225`).
    - **Touch Targets:** Increase padding for buttons and links to meet minimum touch size requirements.


