import os
import time
import json
import pandas as pd
from google import genai
from google.genai import types

def load_gemini_key():
    """
    Loads Gemini API Key from environment variable or 'gemini_token.txt' file in root.
    """
    # 1. Environment Variable
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        return env_key
    
    # 2. File in project root
    # src/analysis/ai_insights.py -> ../../gemini_token.txt
    current_dir = os.path.dirname(__file__)
    root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
    token_path = os.path.join(root_dir, 'gemini_token.txt')
    
    if os.path.exists(token_path):
        try:
            with open(token_path, 'r', encoding='utf-8') as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception as e:
            print(f"[WARN] Error reading gemini_token.txt: {e}")
            
    print("[WARN] GEMINI_API_KEY not found in env or gemini_token.txt.")
    return None

def summarize_text(text_content, prompt_instructions, model_name="gemini-flash-latest", max_retries=1):
    """
    Sends content to Gemini API. Uses 'gemini-flash-latest' which is verified to work.
    """
    api_key = load_gemini_key()
    if not api_key:
        return "AI Analysis Unavailable: No API Key found."

    client = genai.Client(api_key=api_key)
    
    full_prompt = f"{prompt_instructions}\n\nDATA:\n{text_content}"
    
    try:
        # call API once
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt
        )
        
        # Manual extraction to handle 'thought_signature' warnings cleanly
        if response and response.candidates and response.candidates[0].content.parts:
            parts = response.candidates[0].content.parts
            # Join all text parts, ignoring non-text parts (like thought traces)
            full_text = "".join([part.text for part in parts if part.text])
            return full_text.strip()
        elif response and response.text:
            return response.text.strip()
        else:
            return "No text returned from AI."
    
    except Exception as e:
        # Print full error immediately
        print(f"[ERROR] Gemini API Call Failed: {e}")
        return f"Error: {str(e)}"
            
    return "Failed to get AI response after multiple retries."

def load_prompt_template():
    """Loads the system prompt from templates/system_prompt.txt"""
    try:
        current_dir = os.path.dirname(__file__)
        template_path = os.path.join(current_dir, 'templates', 'system_prompt.txt')
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
            "summary": ["bullet 1", "bullet 2", "bullet 3"],
            "sentiment": "One Word Label",
            "funniest_quote": {{ "text": "Quote text", "author": "Username" }},
            "impactful_quote": {{ "text": "Quote text", "author": "Username" }}
        }}
        """

def get_quarterly_insights(df, year=2025, target_quarter=None, language="Italian"):
    """
    Groups messages by Quarter (Q1, Q2, Q3, Q4) and gets insights from Gemini.
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
        print(f"[WARN] No data found for year {year}. Skipping AI analysis.")
        return {}
        
    insights = {}
    
    # helper to identify quarter
    df_year['quarter'] = df_year['timestamp'].dt.quarter
    
    # Load Prompt Template
    prompt_template = load_prompt_template()
    
    # Determine quarters to process
    quarters_to_process = [target_quarter] if target_quarter else sorted(df_year['quarter'].unique())
    
    for q_idx in quarters_to_process:
        quarter_data = df_year[df_year['quarter'] == q_idx]
        if quarter_data.empty:
            continue
            
        quarter_label = f"Q{q_idx}"
        print(f"\n[AI] Analyzer: Processing {quarter_label} ({len(quarter_data)} msgs)...")
        
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
            print(f"   -> Sampled down to {limit_msgs} messages for API safety.")
             
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
            print(f"   -> Success! Analyzed {quarter_label}.")
        except json.JSONDecodeError:
            print(f"   -> [WARN] JSON Parse Failed for {quarter_label}.")
            insights[quarter_label] = {
                "summary": ["Analysis failed to parse."],
                "sentiment": "Unknown",
                "funniest_quote": {"text": "N/A", "author": ""},
                "impactful_quote": {"text": "N/A", "author": ""}
            }
            
    return insights

if __name__ == "__main__":
    # Allows detailed testing without running the full report
    print("Testing Gemini API connection...")
    
    # We need to test with real data. 
    # Let's try to locate the output/ folder and find a txt file.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
    output_dir = os.path.join(root_dir, 'output')
    
    import glob
    from parse_and_clean import parse_and_clean_discord_txt
    
    txt_files = glob.glob(os.path.join(output_dir, "*.txt"))
    # filter out thread.txt if possible
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
