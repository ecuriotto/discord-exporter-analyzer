import os
import time
from google import genai

def load_gemini_key():
    current_dir = os.path.dirname(__file__)
    root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
    token_path = os.path.join(root_dir, 'gemini_token.txt')
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key and os.path.exists(token_path):
        with open(token_path, 'r', encoding='utf-8') as f:
            api_key = f.read().strip()
    return api_key

def check_models():
    api_key = load_gemini_key()
    if not api_key:
        print("No API Key.")
        return

    client = genai.Client(api_key=api_key)
    
    # List of likely candidates
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-flash-latest",
        "gemini-1.5-pro",
        "gemini-pro",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite-preview-02-05"
    ]
    
    # Add some from the list_models output if not already there
    candidates.extend([
        "gemini-2.5-flash", 
        "gemini-2.0-flash-001"
    ])

    print(f"Testing {len(candidates)} models for availability (sending 'Hello')...\n")
    
    for model in candidates:
        print(f"--- Testing {model} ---")
        try:
            response = client.models.generate_content(
                model=model,
                contents="Hello"
            )
            if response and response.text:
                print(f"✅ SUCCESS: {model} worked! Response: {response.text.strip()[:20]}...")
                # If we find one that works, we might just stop or continue to see all options
                # Let's stop at the first working one to save time/quota
                print(f"\n>>> RECOMMENDED MODEL: {model} <<<")
                return
        except Exception as e:
            err = str(e)
            if "404" in err:
                print(f"❌ Not Found (404)")
            elif "429" in err:
                print(f"⚠️ Quota Exceeded (429) - Limit might be 0 or exhausted.")
            else:
                print(f"❌ Error: {err.split(' details:')[0]}") # Shorten error
        
        # small sleep to avoid rate limiting the checker itself
        time.sleep(1)

if __name__ == "__main__":
    check_models()