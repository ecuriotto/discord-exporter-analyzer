import os
import sys
import time
import subprocess
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import CLI_PATH, DISCORD_TOKEN_FILE

def get_discord_token():
    # 1. Environment Variable
    token = os.getenv("DISCORD_TOKEN")
    if token:
        return token

    # 2. File
    if not os.path.exists(DISCORD_TOKEN_FILE):
        return None
    with open(DISCORD_TOKEN_FILE, 'r') as f:
        return f.read().strip()

def run_command(args, label):
    token = get_discord_token()
    if not token:
        print("Error: No token found.")
        sys.exit(1)
        
    cmd = [CLI_PATH] + args + ["--token", token]
    
    # Dotnet fallback logic similar to app.py
    # Check if CLI_PATH is executable directly
    if not os.access(CLI_PATH, os.X_OK):
         dll_path = f"{CLI_PATH}.dll"
         if os.path.exists(dll_path):
             # Ensure we start with dotnet
             cmd = ["dotnet", dll_path] + args + ["--token", token]
    
    print(f"\n--- Running [{label}] ---")
    # Mask token in print
    print_cmd = list(cmd)
    if "--token" in print_cmd:
        idx = print_cmd.index("--token")
        if idx + 1 < len(print_cmd):
            print_cmd[idx+1] = "REDACTED"
            
    print(f"Command: {' '.join(print_cmd)}")
    
    start_time = time.time()
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180 # Generous timeout for benchmark
        )
        duration = time.time() - start_time
        
        if process.returncode != 0:
            print(f"FAILED (RC={process.returncode})")
            print("Stderr:", process.stderr)
            return None, duration
            
        output = process.stdout.strip().splitlines()
        count = 0
        for line in output:
            if "|" in line:
                count += 1
                
        print(f"SUCCESS: Found {count} items")
        print(f"Duration: {duration:.4f} seconds")
        return output, duration
        
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after 180s")
        return None, 180.0
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return None, 0.0

def main():
    print("Starting Benchmark...")
    
    # 1. Get Guilds
    guilds_lines, _ = run_command(["guilds"], "Fetch Guilds")
    
    if not guilds_lines:
        print("Could not fetch guilds. Exiting.")
        return

    guilds = []
    for line in guilds_lines:
        if "|" in line:
            parts = line.split("|", 1)
            guilds.append((parts[0].strip(), parts[1].strip()))
    
    if not guilds:
        print("No guilds found.")
        return

    results = []
    
    # Filter only for the guilds we care about if list is long? 
    # For now test all of them.
    for gid, gname in guilds:
        print(f"\nTesting Guild: {gname} ({gid})")
        
        # Test WITHOUT threads
        _, t_no_threads = run_command(["channels", "--guild", gid], "Channels (No Threads)")
        
        # Test WITH threads
        _, t_threads = run_command(["channels", "--guild", gid, "--include-threads", "true"], "Channels (With Threads)")
        
        diff = t_threads - t_no_threads
        percent = (diff / t_no_threads * 100) if t_no_threads > 0 else 0
        
        results.append({
            "guild": gname,
            "no_threads": t_no_threads,
            "threads": t_threads,
            "diff": diff,
            "percent": percent
        })

    print("\n\n=== SUMMARY ===")
    print(f"{'Guild':<30} | {'No Threads (s)':<15} | {'Threads (s)':<15} | {'Diff':<10} | {'Increase'}")
    print("-" * 90)
    for r in results:
        print(f"{r['guild']:<30} | {r['no_threads']:<15.4f} | {r['threads']:<15.4f} | {r['diff']:<10.4f} | {r['percent']:.1f}%")

if __name__ == "__main__":
    main()
