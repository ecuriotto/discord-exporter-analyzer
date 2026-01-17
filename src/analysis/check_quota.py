import os
import requests
import sys

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.analysis.ai_insights import load_openrouter_key

def check_quota():
    api_key = load_openrouter_key()
    if not api_key:
        print("No OpenRouter API Key found.")
        return

    print("Checking OpenRouter quota...")
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            label = data.get("label", "Unknown")
            usage = data.get("usage", 0)
            limit = data.get("limit")
            is_free = data.get("is_free_tier", False)
            
            print(f"Key Label: {label}")
            print(f"Current Usage: ${usage}")
            
            if limit is not None:
                remaining = data.get("limit_remaining")
                print(f"Credit Limit: ${limit}")
                print(f"Remaining: ${remaining}")
            else:
                print("Credit Limit: Unlimited (or checking not supported)")
                
            if is_free:
                print("Tier: Free")
            
        else:
             print(f"Error checking quota: {response.status_code} - {response.text}")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_quota()