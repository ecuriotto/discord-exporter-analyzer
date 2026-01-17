import os
import time
import json
import pandas as pd
from openai import OpenAI

# Import centralized configuration
from src.config import OPENROUTER_TOKEN_FILE, ANALYSIS_TEMPLATES_DIR, ANALYSIS_RESOURCES_DIR
from src.logger import setup_logger

logger = setup_logger("ai_insights")

def load_free_models():
    """
    Loads the list of free models from resources/free_models.json
    """
    try:
        models_path = os.path.join(ANALYSIS_RESOURCES_DIR, "free_models.json")
        if os.path.exists(models_path):
            with open(models_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load free_models.json: {e}")
    
    # Fallback default list if file fails
    return [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free"
    ]

# Initialize model list
FREE_MODELS = load_free_models()

def load_openrouter_key():
    """
    Loads OpenRouter API Key from environment variable or 'openRouter_token.txt' file in root.
    """
    # 1. Environment Variable
    env_key = os.getenv("OPENROUTER_API_KEY")
    if env_key:
        return env_key
    
    # 2. File in project root
    if os.path.exists(OPENROUTER_TOKEN_FILE):
        try:
            with open(OPENROUTER_TOKEN_FILE, 'r', encoding='utf-8') as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception as e:
            logger.warning(f"Error reading openRouter_token.txt: {e}")
            
    logger.warning("OPENROUTER_API_KEY not found in env or openRouter_token.txt.")
    return None

def summarize_text(text_content, prompt_instructions, max_retries=2):
    """
    Sends content to OpenRouter API with fallback to different free models.
    """
    api_key = load_openrouter_key()
    if not api_key:
        return "AI Analysis Unavailable: No API Key found."

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    full_prompt = f"{prompt_instructions}\n\nDATA:\n{text_content}"
    
    models_attempted = 0
    max_model_attempts = 5

    for model in FREE_MODELS:
        if models_attempted >= max_model_attempts:
            logger.warning(f"Exceeded limit of {max_model_attempts} different models tried. Aborting AI analysis.")
            break
            
        logger.info(f"Trying model: {model}...")
        models_attempted += 1
        
        for attempt in range(max_retries):
            try:
                chat_completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": full_prompt}
                    ],
                    extra_headers={
                        "HTTP-Referer": "http://localhost:3000", 
                        "X-Title": "Discord Analysis Tool",
                    }
                )
                
                content = chat_completion.choices[0].message.content
                if content:
                    logger.info(f"Successfully generated insights using model: {model}")
                    return content.strip()
                
            except Exception as e:
                logger.error(f"Model {model} failed (Attempt {attempt+1}): {e}")
                if "429" in str(e): # Rate limit
                    time.sleep(2)
                else:
                    break # Try next model immediately for non-rate-limit errors
        
        logger.warning(f"Model {model} exhausted all retries. Switching to next model...")

    return "Failed to get AI response from all available models."

def load_prompt_template():
    """Loads the system prompt from templates/system_prompt.txt"""
    try:
        # Use centralized config path
        template_path = os.path.join(ANALYSIS_TEMPLATES_DIR, 'system_prompt.txt')
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[WARN] Could not load system_prompt.txt: {e}")
        # Fallback template
        return """
        Analyze these Discord chat logs for {period_label} of {year}.
        Output Language: {language}
        Return ONLY valid JSON in this format:
        {{
            "executive_summary": "A short, engaging paragraph summarizing the main vibe and events of this period.",
            "summary": ["bullet 1", "bullet 2", "bullet 3"],
            "sentiment": "One Word Label",
            "funniest_quote": {{ "text": "Quote text", "author": "Username" }},
            "impactful_quote": {{ "text": "Quote text", "author": "Username" }}
        }}
        """

def get_quarterly_insights(df, year=2025, target_quarter=None, language="Italian"):
    """
    Groups messages by Quarter (Q1, Q2, Q3, Q4) and gets insights from OpenRouter/LLM.
    Returns a dict: { 'Q1': {'summary': [], 'sentiment': '', ...}, ... }
    """
    if 'timestamp' not in df.columns:
        return {}
        
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Create an explicit copy to avoid SettingWithCopyWarning
    df_year = df[df['timestamp'].dt.year == year].copy()
    
    if df_year.empty:
        logger.warning(f"No data found for year {year}. Skipping AI analysis.")
    # helper to identify quarter
    df_year['quarter'] = df_year['timestamp'].dt.quarter
    
    # Load Prompt Template
    prompt_template = load_prompt_template()
    
    # Determine quarters to process
    quarters_to_process = [target_quarter] if target_quarter else sorted(df_year['quarter'].unique())
    
    insights = {}
    
    for q_idx in quarters_to_process:
        quarter_data = df_year[df_year['quarter'] == q_idx]
        if quarter_data.empty:
            continue
            
        quarter_label = f"Q{q_idx}"
        logger.info(f"Analyzer: Processing {quarter_label} ({len(quarter_data)} msgs)...")
        
        # --- Payload / Token Management ---
        # A single quarter might be huge. If > 1500 messages, we risk hitting 
        # standard prompt limits or quality degradation.
        # We will keep sampling to a safe upper bound.
        limit_msgs = 800  # Safe limit for a roughly 30k-50k context window
        
        # If the quarter is extremely sparse (e.g. < 5 messages), maybe skip or just do it?
        # We'll just do it, but the AI summary might be brief.
        
        msgs_to_process = quarter_data
        if len(quarter_data) > limit_msgs:
            # We sample evenly across the quarter if possible, 
            # currently just random sample + sort is fine for general sentiment.
            msgs_to_process = quarter_data.sample(limit_msgs).sort_values('timestamp')
            logger.info(f"   -> Sampled down to {limit_msgs} messages for API safety.")
             
        text_blob = "\n".join(
            (msgs_to_process['user'] + ": " + msgs_to_process['message'].astype(str)).tolist()
        )
        
        # Fill template (Using replace instead of format to avoid KeyError on JSON braces)
        prompt = prompt_template.replace("{period_label}", quarter_label) \
                                .replace("{year}", str(year)) \
                                .replace("{language}", language)
        
        response = summarize_text(text_blob, prompt)
        time.sleep(5) # Modest buffer
        
        # JSON Cleaning
        clean_json = response.replace("```json", "").replace("```", "").strip()
        
        try:
            data = json.loads(clean_json)
            insights[quarter_label] = data
            logger.info(f"   -> Success! Analyzed {quarter_label}.")
        except json.JSONDecodeError:
            logger.warning(f"   -> JSON Parse Failed for {quarter_label}.")
            insights[quarter_label] = {
                "summary": ["Analysis failed to parse."],
                "sentiment": "Unknown",
                "funniest_quotes": [{"text": "N/A", "author": ""}],
                "impactful_quote": {"text": "N/A", "author": ""}
            }
            
    return insights

def generate_yearly_summary(insights, year, language="Italian"):
    """
    Synthesizes a high-level executive summary from the quarterly insights.
    Returns a string (markdown or plain text paragraph).
    """
    if not insights:
        return None

    logger.info(f"Generating Yearly Executive Summary from {len(insights)} quarters...")
    
    # Construct a meta-summary for the AI
    meta_text = f"Year: {year}\nLanguage: {language}\n\n"
    for q, data in insights.items():
        meta_text += f"== {q} ==\n"
        meta_text += f"Sentiment: {data.get('sentiment', 'Unknown')}\n"
        meta_text += f"Key Topics: {', '.join(data.get('summary', []))}\n"
        quote = data.get('impactful_quote', {}).get('text', '')
        if quote:
             meta_text += f"Key Quote: {quote}\n"
        meta_text += "\n"

    prompt = f"""
    You are an expert analyst. Read these quarterly summaries of a Discord community's year.
    Write a brief, engaging "Yearly Executive Summary" (max 150 words) that captures the overall vibe, evolution, and main themes of the year.
    Output directly in {language}. No JSON, just the text paragraph.
    """
    
    return summarize_text(meta_text, prompt)

if __name__ == "__main__":
    # Allows detailed testing without running the full report
    print("Testing AI API connection...")
    
    # We need to test with real data. 
    import glob
    from src.analysis.parse_and_clean import parse_and_clean_discord_txt
    from src.config import OUTPUT_DIR, OUTPUT_TXT_DIR
    
    # Try finding files in txt/ then root output/
    txt_files = glob.glob(os.path.join(OUTPUT_TXT_DIR, "*.txt"))
    if not txt_files:
         txt_files = glob.glob(os.path.join(OUTPUT_DIR, "*.txt"))
         
    # filter out thread.txt if possible (usually thread dumps are not main channels)
    candidates = [f for f in txt_files if "thread.txt" not in f]
    if not candidates:
        candidates = txt_files
        
    if candidates:
        test_file = candidates[0] # Pick first found
        print(f"Loading test data from: {test_file}")
        
        df = parse_and_clean_discord_txt(test_file)
        
        # Determine year
        if not df.empty:
            test_year = df['timestamp'].dt.year.mode()[0]
            
            # Find a quarter that has data
            test_quarter = df['timestamp'].dt.quarter.iloc[0]
            
            print(f"Running single quarter test (Year: {test_year}, Quarter: Q{test_quarter})...")
            # Changed from get_monthly_insights to get_quarterly_insights
            results = get_quarterly_insights(df, year=test_year, target_quarter=test_quarter) 
            print("\n--- RESULTS ---")
            print(json.dumps(results, indent=2))
        else:
            print("DataFrame empty.")
    else:
        print("No TXT found in output/ to test.")
