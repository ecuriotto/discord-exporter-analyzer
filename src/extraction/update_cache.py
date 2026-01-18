import os
import sys
import json
import argparse
import subprocess
import asyncio

# Fix imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import CLI_PATH, DISCORD_TOKEN_FILE, CHANNELS_CACHE_FILE

def get_discord_token():
    token = os.getenv("DISCORD_TOKEN")
    if token:
        return token
    if not os.path.exists(DISCORD_TOKEN_FILE):
        return None
    with open(DISCORD_TOKEN_FILE, 'r') as f:
        return f.read().strip()

def run_command_sync(args, timeout=300):
    token = get_discord_token()
    if not token:
        raise Exception("Token not found")
        
    full_cmd = [CLI_PATH] + args + ["--token", token]
    
    # Dotnet fallback
    if not os.access(CLI_PATH, os.X_OK):
         dll_path = f"{CLI_PATH}.dll"
         if os.path.exists(dll_path):
             full_cmd = ["dotnet", dll_path] + args + ["--token", token]
    
    print(f"Running: {' '.join(full_cmd)}")
    
    process = subprocess.run(
        full_cmd,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    
    if process.returncode != 0:
        raise Exception(f"CLI Error: {process.stderr}")
        
    return process.stdout.strip().splitlines()

def parse_cli_list(lines):
    items = []
    for line in lines:
        if "|" in line:
            parts = line.split("|", 1)
            raw_id = parts[0].strip()
            # Clean ID: Remove '*' markers and distinct digits
            # DiscordChatExporter sometimes marks active threads with '*'
            clean_id = "".join(filter(str.isdigit, raw_id))
            
            if clean_id:
                items.append({
                    "id": clean_id,
                    "name": parts[1].strip()
                })
    return items

def load_cache():
    if os.path.exists(CHANNELS_CACHE_FILE):
        try:
            with open(CHANNELS_CACHE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_cache(cache):
    with open(CHANNELS_CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Update Discord channels cache")
    parser.add_argument("--guild", required=True, help="Guild ID to update")
    args = parser.parse_args()
    
    guild_id = args.guild
    print(f"Updating cache for guild: {guild_id}")
    
    try:
        # Fetch channels WITH threads
        if guild_id == "0":
             lines = run_command_sync(["dm"])
        else:
             lines = run_command_sync(["channels", "--guild", guild_id, "--include-threads", "true"])
             
        channels = parse_cli_list(lines)
        print(f"Found {len(channels)} channels/threads")
        
        # Update Cache
        cache = load_cache()
        cache[guild_id] = channels
        save_cache(cache)
        
        print("Cache updated successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
