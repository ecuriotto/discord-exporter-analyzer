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
    # Expanded list to minimize 429 exhaustion
    return [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "microsoft/phi-3-medium-128k-instruct:free",
        "huggingfaceh4/zephyr-7b-beta:free",
        "openchat/openchat-7b:free"
    ]

# Initialize free model list
FREE_MODELS = load_free_models()

def load_pay_models():
    """
    Loads the list of pay models from resources/pay_models.json
    """
    try:
        models_path = os.path.join(ANALYSIS_RESOURCES_DIR, "pay_models.json")
        if os.path.exists(models_path):
            with open(models_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load pay_models.json: {e}")
    
    # Fallback if file missing
    return [
        "google/gemini-2.0-flash-001",
        "deepseek/deepseek-chat"
    ]

# Initialize pay model list
PAY_MODELS = load_pay_models()

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

def summarize_text(text_content, prompt_instructions, max_retries=2, model_type="free"):
    """
    Sends content to OpenRouter API.
    model_type: "free" (rotates free models) or "pay" (rotates pay models)
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
    
    if model_type == "pay":
        models_list = PAY_MODELS
    elif model_type == "free":
        models_list = FREE_MODELS
    else:
        # User specified a specific model ID (e.g. "openai/gpt-4o")
        models_list = [model_type]

    for model in models_list:
        if models_attempted >= max_model_attempts:
            logger.warning(f"Exceeded limit of {max_model_attempts} different models tried. Aborting AI analysis.")
            break
        
        # 1. Health Check Removed
        # We proceed directly to analysis to avoid wasting tokens on pings.
        logger.info(f"Attempting analysis with model: {model} ({model_type} mode)...")
        models_attempted += 1
        
        # 2. Real Analysis Attempt
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
                err_str = str(e)
                
                # Handling "free-models-per-day" hard limit
                if "free-models-per-day" in err_str:
                     logger.error("Daily free model limit reached. Stopping AI analysis.")
                     return "AI Analysis Unavailable: Daily limit reached."
                     
                if "429" in err_str: # Rate limit
                    time.sleep(5) # Increase wait
                else:
                    break # Try next model immediately for non-rate-limit errors
        
        # Check if we should stop completely if we returned earlier
        if "Unavailable" in locals().get('content', ''):
             break
        
        logger.warning(f"Model {model} exhausted all retries. Switching to next model...")

    return "Failed to get AI response from all available models."

def load_prompt_template(template_name='company_chat_prompt.txt'):
    """
    Loads the system prompt from templates directory.
    
    Args:
        template_name: Name of the template file to load. 
                      Default: 'company_chat_prompt.txt' (specialized for financial analysis)
                      Alternative: 'system_prompt.txt' (general Discord chat analysis)
    """
    try:
        # Use centralized config path
        template_path = os.path.join(ANALYSIS_TEMPLATES_DIR, template_name)
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Could not load {template_name}: {e}. Trying fallback...")
        
        # Try the other template as fallback
        fallback_name = 'system_prompt.txt' if template_name != 'system_prompt.txt' else 'company_chat_prompt.txt'
        try:
            fallback_path = os.path.join(ANALYSIS_TEMPLATES_DIR, fallback_name)
            with open(fallback_path, 'r', encoding='utf-8') as f:
                logger.info(f"Loaded fallback template: {fallback_name}")
                return f.read()
        except Exception as e2:
            logger.error(f"Could not load fallback template {fallback_name}: {e2}")
            # Final fallback: hardcoded basic template
            return """
            Analyze these Discord chat logs for {period_label}.
            Output Language: {language}
            Return ONLY valid JSON in this format:
            {{
                "executive_summary": "A short, engaging paragraph summarizing the main vibe and events of this period.",
                "summary": ["bullet 1", "bullet 2", "bullet 3"],
                "sentiment": "One Word Label",
                "impactful_quote": {{ "text": "Quote text", "author": "Username" }}
            }}
            """

def get_quarterly_insights(df, year=None, target_quarter=None, language="Italian", force_single_period=False, period_label_override=None, model_type="free", analysis_type="company"):
    """
    Groups messages by Quarter (Q1, Q2, Q3, Q4) and gets insights from OpenRouter/LLM.
    Returns a dict: { 'Q1': {'summary': [], 'sentiment': '', ...}, ... }
    
    If force_single_period is True, ignores quarters/years and processes entire DF as one block.
    
    analysis_type: "company" (Value Investor) or "general" (Generic Chat)
    """
    if 'timestamp' not in df.columns:
        return {}
        
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Pre-filtering by year is only done if year is provided AND we're not in single period mode
    if year and not force_single_period:
        df_target = df[df['timestamp'].dt.year == year].copy()
        if df_target.empty:
            logger.warning(f"No data found for year {year}. Skipping AI analysis.")
            return {}
    else:
        df_target = df.copy() # Use whatever is passed
    
    if df_target.empty:
         return {}

    # Load Prompt Template based on Analysis Type
    template_name = 'company_chat_prompt.txt' # Default
    if analysis_type == "general":
        template_name = 'generic_chat_prompt.txt'
        
    prompt_template = load_prompt_template(template_name)
    
    insights = {}
    
    # Define processing groups
    if force_single_period:
        # Just one group: the whole dataframe
        # Dummy key for iteration
        sorted_groups = [((0,0), df_target)]
    else:
        # helper to identify quarter
        df_target['quarter'] = df_target['timestamp'].dt.quarter
        df_target['year'] = df_target['timestamp'].dt.year
        
        start_year = df_target['year'].min()
        end_year = df_target['year'].max()
        multi_year = start_year != end_year
        
        if target_quarter:
             df_target = df_target[df_target['quarter'] == target_quarter]
             
        # Get unique couples
        groups = df_target.groupby(['year', 'quarter'])
        # Sort groups by year, then quarter
        sorted_groups = sorted(groups, key=lambda x: (x[0][0], x[0][1]))

    for (y, q), quarter_data in sorted_groups:
        if quarter_data.empty:
            continue
            
        if force_single_period:
             quarter_label = period_label_override if period_label_override else "Analysis Period"
        elif multi_year or year is None:
             quarter_label = f"{y} Q{q}"
        else:
             quarter_label = f"Q{q}"
        
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
        # year_ctx = str(y) if not force_single_period else "the specific period"
        
        prompt = prompt_template.replace("{language}", language) \
                                .replace("{period_label}", quarter_label)

        if force_single_period:
            # Clean up the "of {year}" part if it exists, to avoid "Ultimi 3 mesi of the specific period"
            # Try English pattern
            prompt = prompt.replace(" of {year}", "")
            # Try Italian pattern (in case of custom templates)
            prompt = prompt.replace(" del {year}", "")
            prompt = prompt.replace(" di {year}", "")
            # Fallback for just the tag
            prompt = prompt.replace("{year}", "")
        else:
            prompt = prompt.replace("{year}", str(y))
        
        response = summarize_text(text_blob, prompt, model_type=model_type)
        
        # Check for hard stop signal
        if "Unavailable" in response:
             logger.error("AI Analysis stopped due to API limits.")
             break
             
        time.sleep(5) # Modest buffer
        
        # Enhanced JSON Cleaning
        # 1. Strip Markdown
        clean_json = response.replace("```json", "").replace("```", "").strip()
        
        # 2. Extract JSON object using regex (find first { and last })
        import re
        json_match = re.search(r'(\{.*\})', clean_json, re.DOTALL)
        if json_match:
            clean_json = json_match.group(1)
        
        try:
            data = json.loads(clean_json)
            insights[quarter_label] = data
            logger.info(f"   -> Success! Analyzed {quarter_label}.")
        except json.JSONDecodeError:
            logger.warning(f"   -> JSON Parse Failed for {quarter_label}. Raw response length: {len(response)}")
            # Fallback: Don't put "Analysis failed" in summary if we want to hide it
            insights[quarter_label] = {
                "summary": [], # Empty summary helps hiding the section
                "sentiment": "Unknown",
                "funniest_quotes": [],
                "impactful_quote": {"text": "", "author": ""}
            }
            
    return insights

def generate_yearly_summary(insights, year, language="Italian", model_type="free"):
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
    
    return summarize_text(meta_text, prompt, model_type=model_type)

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
