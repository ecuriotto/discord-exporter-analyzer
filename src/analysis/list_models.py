import os
from google import genai

def list_models():
    # Load key as before
    current_dir = os.path.dirname(__file__)
    root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
    token_path = os.path.join(root_dir, 'gemini_token.txt')
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key and os.path.exists(token_path):
        with open(token_path, 'r', encoding='utf-8') as f:
            api_key = f.read().strip()
            
    if not api_key:
        print("No API Key found.")
        return

    client = genai.Client(api_key=api_key)
    
    try:
        # According to new SDK docs structure
        # client.models.list() typically returns an iterator
        print("Fetching models...")
        for m in client.models.list():
            # In the new SDK, m might be a different object structure.
            # Let's print the name to see what we have
            print(f"- {m.name}")
            
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()