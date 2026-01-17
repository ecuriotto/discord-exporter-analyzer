import os
import requests
import sys

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.analysis.ai_insights import load_openrouter_key

def list_models():
    api_key = load_openrouter_key()
            
    if not api_key:
        print("No OpenRouter API Key found.")
        return

    print("Fetching free models from OpenRouter...")
    try:
        response = requests.get("https://openrouter.ai/api/v1/models")
        if response.status_code == 200:
            models = response.json().get("data", [])
            # Filter for free models if you want, or just list them all
            # Usually looking for specific pricing or "free" in ID
            count = 0
            for  m in models:
                mid = m.get("id")
                pricing = m.get("pricing", {})
                is_free = False
                
                # Check for zero pricing
                try:
                    prompt = float(pricing.get("prompt", 999))
                    completion = float(pricing.get("completion", 999))
                    if prompt == 0 and completion == 0:
                        is_free = True
                except:
                    pass
                
                if ":free" in mid or is_free:
                    print(f"- {mid}")
                    count += 1
            print(f"\nFound {count} potentially free models.")
        else:
            print(f"Error fetching models: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()