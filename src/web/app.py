import os
import sys
import uuid
import subprocess
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import tempfile

import glob
import re
from datetime import datetime
import requests

import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import centralized configuration
from src.config import (
    BASE_DIR, 
    OUTPUT_DIR, 
    INPUT_DIR, 
    WEB_TEMPLATES_DIR as TEMPLATES_DIR, 
    DISCORD_TOKEN_FILE as TOKEN_FILE, 
    CLI_PATH, 
    CHANNEL_NAMES_FILE as CACHE_FILE,
    CHANNELS_CACHE_FILE
)
from src.analysis.ai_insights import load_openrouter_key
from src.logger import setup_logger

logger = setup_logger("web_app")

# In-memory Job Store
JOBS = {}

# Thread Pool for blocking CLI operations
cli_executor = ThreadPoolExecutor(max_workers=3)

app = FastAPI(title="Discord Analytics Dashboard")

@app.get("/api/models")
async def get_models():
    """Fetch available models from OpenRouter."""
    api_key = load_openrouter_key()
    if not api_key:
        return {"status": "error", "message": "OpenRouter API Key not found."}

    try:
        response = requests.get("https://openrouter.ai/api/v1/models")
        if response.status_code == 200:
            data = response.json().get("data", [])
            # Sort by name
            data.sort(key=lambda x: x.get("name", ""))
            return {"status": "success", "data": data}
        else:
            return {"status": "error", "message": f"OpenRouter API Error: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/robots.txt", response_class=HTMLResponse)
async def robots_txt():
    return "User-agent: *\nAllow: /"

def load_name_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_name_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def resolve_channel_name_cli(channel_id):
    """Fetch channel name using CLI export hack."""
    token = get_discord_token()
    if not token:
        return None

    # Using a temp directory to export 1 message and see the filename
    with tempfile.TemporaryDirectory() as temp_dir:
        # Patter %n gives just the name
        output_pattern = os.path.join(temp_dir, "%n.txt")
        
        args = [
            "export",
            "-t", token,
            "-c", channel_id,
            "-o", output_pattern,
            "-p", "1", # Limit to 1 message
            "--format", "PlainText"
        ]
        
        # We reuse run_cli_command logic but we need custom args structure not fully supported by it
        # because run_cli_command injects token at end, but here we construct it carefully.
        # Actually run_cli_command appends token. 
        # Let's just use subprocess directly here for control.
        
        cmd = [CLI_PATH] + args
        # Check dotnet fallback
        if not os.path.isfile(CLI_PATH):
             # Try dotnet
             cmd = ["dotnet", f"{CLI_PATH}.dll"] + args
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            
            # Find the generated file
            files = glob.glob(os.path.join(temp_dir, "*.txt"))
            if files:
                # The filename IS the channel name
                filename = os.path.splitext(os.path.basename(files[0]))[0]
                # Filter out bad names where CLI failed to replace placeholder
                if "%n" in filename:
                    return None
                return filename
        except Exception as e:
            logger.error(f"Error resolving name for {channel_id}: {e}")
            return None
    return None

class NameResolutionRequest(BaseModel):
    channel_ids: list[str]

@app.post("/api/resolve-names")
async def resolve_names(request: NameResolutionRequest):
    """Resolve names for a list of channel IDs, using cache or CLI."""
    cache = load_name_cache()
    results = {}
    updated = False
    
    for cid in request.channel_ids:
        if cid in cache:
            results[cid] = cache[cid]
        else:
            # Fallback for now: we don't want to block too long.
            # But let's try to resolve one by one?
            # Or better: if not in cache, we return None for now, 
            # and maybe trigger a background task? 
            # For this MVP, let's try to resolve it synchronously strictly.
            # It might take time (~1s per ID).
            name = resolve_channel_name_cli(cid)
            if name:
                results[cid] = name
                cache[cid] = name
                updated = True
            else:
                results[cid] = None
    
    if updated:
        save_name_cache(cache)
        
    return {"status": "success", "names": results}

def get_discord_token():
    # 1. Environment Variable
    token = os.getenv("DISCORD_TOKEN")
    if token:
        return token

    # 2. File
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, 'r') as f:
        return f.read().strip()

def _run_cli_command_sync(args, timeout=60):
    """
    Blocking helper to run CLI commands safely.
    Includes timeout to prevent hanging.
    """
    token = get_discord_token()
    if not token:
        raise Exception("Token not found")
        
    full_cmd = [CLI_PATH] + args + ["--token", token]
    
    try:
        # Check if direct executable or needs dotnet
        # If CLI_PATH is a dll or script logic
        # Usually full_cmd is fine if CLI_PATH is executable
        
        process = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # If execution failed (e.g. not executable or wrong format), try dotnet fallback
        if process.returncode != 0:
             # Heuristic: if stderr mentions "cannot execute binary file" or similar, or just try dotnet
             # Or if raw command failed.
             # We can just try dotnet blindly if returncode != 0
             
             dll_path = f"{CLI_PATH}.dll"
             # If we haven't tried dotnet yet (check cmd[0])
             if "dotnet" not in full_cmd and os.path.exists(dll_path):
                 full_cmd = ["dotnet", dll_path] + args + ["--token", token]
                 process = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                 )

        if process.returncode != 0:
            raise Exception(f"CLI Error: {process.stderr}")
            
        return process.stdout.strip().splitlines()
        
    except subprocess.TimeoutExpired:
        raise Exception(f"CLI timed out after {timeout} seconds")
    except Exception as e:
        raise e

async def run_cli_command(args, timeout=60):
    """
    Run CLI command asynchronously in thread pool to avoid blocking the event loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    
    # Run in thread pool
    result = await loop.run_in_executor(cli_executor, _run_cli_command_sync, args, timeout)
    return result

def parse_cli_list(lines):
    """Parse 'ID | Name' lines into a list of dicts."""
    items = []
    
    # Debug logging
    if asyncio.iscoroutine(lines):
        logger.error("parse_cli_list received a coroutine! This shouldn't happen.")
        # We can't fix it here easily without await, but logging it confirms the issue.
    
    # Convert/validate lines
    if not isinstance(lines, list):
         logger.error(f"parse_cli_list expected list, got {type(lines)}")
         return []
         
    for line in lines:
        if "|" in line:
            parts = line.split("|", 1)
            raw_id = parts[0].strip()
            # Clean ID: Remove '*' markers or other CLI artifacts
            clean_id = "".join(filter(str.isdigit, raw_id))
            
            if clean_id:
                items.append({
                    "id": clean_id,
                    "name": parts[1].strip()
                })
    return items

@app.get("/api/discord/guilds")
async def get_guilds():
    """Fetch list of guilds (servers)."""
    try:
        logger.info("Fetching guilds...")
        lines = await run_cli_command(["guilds"], timeout=120)
        
        if asyncio.iscoroutine(lines):
             logger.error("get_guilds: lines is coroutine after await!")
             lines = await lines
             
        guilds = parse_cli_list(lines)
        return {"status": "success", "data": guilds}
    except Exception as e:
        logger.error(f"Error fetching guilds: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

def load_channels_cache():
    if os.path.exists(CHANNELS_CACHE_FILE):
        try:
            with open(CHANNELS_CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

@app.get("/api/discord/channels/{guild_id}")
async def get_channels(guild_id: str, include_threads: bool = False, force_refresh: bool = False):
    """
    Fetch channels for a specific guild (or DMs).
    Order of preference:
    1. Cache (if exists and not forced refresh)
    2. Fast CLI Fetch (no threads) if not explicitly requested threads
    3. Slow CLI Fetch (with threads) if explicitly requested or forced
    """
    try:
        logger.info(f"Fetching channels for {guild_id} (Threads: {include_threads}, Force: {force_refresh})")
        
        # 1. Try Cache
        if not force_refresh:
            cache = load_channels_cache()
            if guild_id in cache:
                logger.info(f"Returning cached channels for {guild_id}")
                return {"status": "success", "data": cache[guild_id], "cached": True}

        # 2. CLI Fetch
        if guild_id == "0":
            lines = await run_cli_command(["dm"], timeout=120)
        else:
            args = ["channels", "--guild", guild_id]
            
            # Use a longer timeout if threads are requested
            timeout = 120
            if include_threads or force_refresh:
                # If force refresh, we generally want threads too, or should we assume full update?
                # The user intent "Refresh Cache" implies getting everything.
                # So if force_refresh is True, we enforce threads.
                args.extend(["--include-threads", "true"])
                timeout = 600 # 10 minutes for very large servers
            
            lines = await run_cli_command(args, timeout=timeout)
            
        if asyncio.iscoroutine(lines):
             lines = await lines

        channels = parse_cli_list(lines)
        return {"status": "success", "data": channels, "cached": False}
    except Exception as e:
         logger.error(f"Failed to load channels for guild {guild_id}: {e}", exc_info=True)
         return {"status": "error", "message": str(e)}

class CacheUpdateRequest(BaseModel):
    guild_id: str

def run_cache_update(job_id: str, guild_id: str):
    """
    Runs the cache update script in a subprocess.
    """
    script_path = os.path.join(BASE_DIR, "src", "extraction", "update_cache.py")
    cmd = [sys.executable, "-u", script_path, "--guild", guild_id]
    
    JOBS[job_id]["status"] = "running"
    JOBS[job_id]["log"].append(f"Starting cache update for guild {guild_id}...")
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, 
            text=True, 
            cwd=BASE_DIR,
            bufsize=1, 
            universal_newlines=True
        )
        
        for line in process.stdout:
            cleaned = clean_log(line)
            if cleaned:
                 JOBS[job_id]["log"].append(cleaned)
        
        process.wait()
            
        if process.returncode == 0:
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["message"] = "Cache updated successfully."
        else:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = f"Process exited with code {process.returncode}"
            
    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)
        JOBS[job_id]["log"].append(f"Exception: {str(e)}")

@app.post("/api/discord/refresh-cache")
async def refresh_cache(request: CacheUpdateRequest, background_tasks: BackgroundTasks):
    """Trigger background job to refresh channel cache (incl. threads)."""
    job_id = str(uuid.uuid4())
    
    JOBS[job_id] = {
        "id": job_id,
        "type": "cache_update",
        "guild_id": request.guild_id,
        "status": "pending",
        "log": [],
        "created_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_cache_update, job_id, request.guild_id)
    return {"status": "success", "job_id": job_id, "message": "Cache update started"}


# Ensure Output Dir exists (handled in config.py, but good to keep locally if needed for mounting logic fallback)
# But since we use config.py, we trust it creates folders.
# Still, app.mount needs existing folders sometimes if we point to them directly.

# Mount Static Files
# We mount "output" so we can link to generated HTML reports
# Note: config.OUTPUT_DIR covers the root output folder. 
app.mount("/reports", StaticFiles(directory=OUTPUT_DIR), name="reports")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

def get_files(directory, extension, url_prefix=""):
    """List files with specific extension in directory, sorted by modification time."""
    if not os.path.exists(directory):
        return []
    files = glob.glob(os.path.join(directory, f"*{extension}"))
    # Sort by mtime descending
    files.sort(key=os.path.getmtime, reverse=True)
    results = []
    for f in files:
        stats = os.stat(f)
        filename = os.path.basename(f)
        item = {
            "name": filename,
            "path": f,
            "size": f"{stats.st_size / 1024:.1f} KB",
            "date": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
        }
        if url_prefix:
            item["url"] = f"{url_prefix}{filename}"
        else:
            # Fallback for backward compat if needed, though template should use url
            item["url"] = f"/reports/{filename}" 
            
        results.append(item)
    return results


class ExtractionRequest(BaseModel):
    channel_id: str

class AnalysisRequest(BaseModel):
    file_path: str
    year: int | None = None
    quarter: str | None = None
    month: int | None = None
    months: int | None = None
    ytd: bool = False
    language: str = "it"
    model_mode: str = "free"
    analysis_type: str = "company"


def clean_log(text):
    """Remove ANSI escape sequences and other clutter from logs."""
    # ANSI Escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    
    # Common garbage from progress bars (e.g. cursor movements that weren't fully caught or weird encoding)
    text = re.sub(r'\[\d+[A-Z]', '', text)
    
    return text.strip()

def run_extraction(job_id: str, channel_id: str):
    """
    Runs the extraction script in a subprocess with real-time logging.
    """
    script_path = os.path.join(BASE_DIR, "src", "extraction", "main_extraction.py")
    cmd = [sys.executable, "-u", script_path, "--export", channel_id] # -u for unbuffered output
    
    # Update status to running
    JOBS[job_id]["status"] = "running"
    JOBS[job_id]["log"].append(f"Starting command: {' '.join(cmd)}")
    
    try:
        # Use Popen to stream output
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout for simpler capturing
            text=True, 
            cwd=BASE_DIR,
            bufsize=1, # Line buffered
            universal_newlines=True
        )
        
        # Read output line by line
        for line in process.stdout:
            cleaned = clean_log(line)
            # Filter noise: empty lines or just "[CLI]" tags
            if cleaned and cleaned != "[CLI]" and not cleaned.startswith("[CLI]   |"):
                 JOBS[job_id]["log"].append(cleaned)
        
        process.wait()
            
        if process.returncode == 0:
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["message"] = "Extraction finished successfully."
        else:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = f"Process exited with code {process.returncode}"
            
    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)
        JOBS[job_id]["log"].append(f"Exception: {str(e)}")


@app.post("/api/extract")
async def trigger_extraction(request: ExtractionRequest, background_tasks: BackgroundTasks):
    """
    Trigger the extraction script in the background.
    """
    channel_id = request.channel_id.strip() # Ensure valid format
    
    # Security Check: Channel ID must be numeric
    if not channel_id.isdigit():
        logger.error(f"Invalid Channel ID received: '{channel_id}'")
        return {"status": "error", "message": f"Invalid Channel ID: '{channel_id}'. Must be numeric."}

    job_id = str(uuid.uuid4())
    
    # Initialize Job
    JOBS[job_id] = {
        "id": job_id,
        "type": "extraction",
        "channel_id": channel_id,
        "status": "pending",
        "log": [],
        "error": None,
        "created_at": datetime.now().isoformat()
    }
    
    # Start Background Task
    background_tasks.add_task(run_extraction, job_id, channel_id)

    return {"status": "success", "message": f"Extraction started for channel {channel_id}", "job_id": job_id}

def run_analysis(job_id: str, file_path: str, language: str, year: int = None, quarter: str = None, month: int = None, months: int = None, ytd: bool = False, model_mode: str = "free", analysis_type: str = "company"):
    """
    Runs the analysis script in a subprocess with real-time logging.
    """
    script_path = os.path.join(BASE_DIR, "src", "analysis", "main_analysis.py")
    
    cmd = [sys.executable, "-u", script_path, "--input", file_path, "--lang", language, "--model-mode", model_mode, "--type", analysis_type]
    
    if months:
         cmd.extend(["--months", str(months)])
    elif ytd:
         cmd.append("--ytd")
    elif month:
         cmd.extend(["--month", str(month)])
         if year:
            cmd.extend(["--year", str(year)])
    else:
         # Default Year/Quarter Mode
         if year:
            cmd.extend(["--year", str(year)])
         if quarter:
            cmd.extend(["--quarter", quarter])
    
    # Update status to running
    JOBS[job_id]["status"] = "running"
    JOBS[job_id]["log"].append(f"Starting command: {' '.join(cmd)}")
    
    try:
        # Use Popen to stream output
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, 
            text=True, 
            cwd=BASE_DIR,
            bufsize=1, 
            universal_newlines=True
        )
        
        # Read output line by line
        for line in process.stdout:
            cleaned = clean_log(line)
            if cleaned:
                 JOBS[job_id]["log"].append(cleaned)
        
        process.wait()
            
        if process.returncode == 0:
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["message"] = "Analysis finished successfully."
            
            # Attempt to find output file in logs
            for log in reversed(JOBS[job_id]["log"]):
                if "Report generated:" in log:
                    path = log.split(":")[-1].strip()
                    JOBS[job_id]["output_file"] = os.path.basename(path)
                    break
        else:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = f"Process exited with code {process.returncode}"
            
    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)
        JOBS[job_id]["log"].append(f"Exception: {str(e)}")

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    return JOBS.get(job_id, {"status": "not_found"})

def is_safe_path(path: str, allowed_dirs: list[str]) -> bool:
    """
    Ensure the path is strictly within the allowed directories.
    Prevents directory traversal attacks.
    """
    try:
        # Resolve absolute path
        abs_path = os.path.abspath(path)
        
        for d in allowed_dirs:
            abs_allowed = os.path.abspath(d)
            if abs_path.startswith(abs_allowed):
                return True
        return False
    except Exception:
        return False

@app.post("/api/analyze")
async def trigger_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Trigger the analysis script in the background.
    """
    # Security Check: Ensure file is in INPUT_DIR or OUTPUT_TXT_DIR
    if not is_safe_path(request.file_path, [INPUT_DIR, OUTPUT_DIR]):
        return {"status": "error", "message": "Invalid file path. Access denied."}

    job_id = str(uuid.uuid4())
    file_name = os.path.basename(request.file_path)
    
    # Initialize Job
    JOBS[job_id] = {
        "id": job_id,
        "type": "analysis",
        "file_name": file_name,
        "status": "pending",
        "log": [],
        "error": None,
        "created_at": datetime.now().isoformat()
    }
    
    # Start Background Task
    background_tasks.add_task(
        run_analysis, 
        job_id, 
        request.file_path, 
        request.language,
        request.year,
        request.quarter,
        request.month,
        request.months,
        request.ytd,
        request.model_mode,
        request.analysis_type
    )

    return {
        "status": "success",  
        "message": f"Analysis started for {file_name}", 
        "job_id": job_id
    }

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Dashboard Home.
    """
    # Scan subdirectories
    html_dir = os.path.join(OUTPUT_DIR, "html")
    pdf_dir = os.path.join(OUTPUT_DIR, "pdf")
    txt_dir = os.path.join(OUTPUT_DIR, "txt")
    
    reports = get_files(html_dir, ".html", url_prefix="/reports/html/")
    
    # Check for PDFs and attach info
    for report in reports:
        pdf_name = report["name"].replace(".html", ".pdf")
        pdf_path = os.path.join(pdf_dir, pdf_name)
        if os.path.exists(pdf_path):
             report["pdf_url"] = f"/reports/pdf/{pdf_name}"
    
    # Check legacy root output for backward compatibility
    legacy_reports = get_files(OUTPUT_DIR, ".html", url_prefix="/reports/")
    existing_names = {r["name"] for r in reports}
    for r in legacy_reports:
        if r["name"] not in existing_names:
            reports.append(r)
            
    # Sort again by date because of merging
    reports.sort(key=lambda x: x["date"], reverse=True)

    # Channels (TXT)
    channels = get_files(txt_dir, ".txt")
    
    # Legacy channels (root output)
    legacy_channels = get_files(OUTPUT_DIR, ".txt")
    existing_c_paths = {c["path"] for c in channels}
    
    for c in legacy_channels:
        if c["path"] not in existing_c_paths:
             channels.append(c)

    # Input channels
    input_channels = get_files(INPUT_DIR, ".txt")
    for c in input_channels:
         if not any(x["name"]==c["name"] for x in channels):
             channels.append(c)

    # Simplified display name logic: use filename by default
    for channel in channels:
         channel["display_name"] = channel["name"]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Estrazione Discord HTML - Dashboard",
        "reports": reports,
        "channels": channels
    })

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

class DeleteResponse(BaseModel):
    status: str
    message: str

@app.delete("/api/reports/{filename}")
async def delete_report(filename: str):
    """
    Delete a report (HTML and PDF) by filename.
    """
    # Security check: filename should be just a name, no paths
    if ".." in filename or "/" in filename or "\\" in filename:
        return {"status": "error", "message": "Invalid filename."}

    deleted_files = []
    errors = []
    
    # 1. Try to find/delete HTML
    # Check output/html
    html_path = os.path.join(OUTPUT_DIR, "html", filename)
    legacy_html_path = os.path.join(OUTPUT_DIR, filename)
    
    target_html = None
    if os.path.exists(html_path):
        target_html = html_path
    elif os.path.exists(legacy_html_path):
        target_html = legacy_html_path
        
    if target_html:
        try:
            os.remove(target_html)
            deleted_files.append("HTML")
        except Exception as e:
            errors.append(f"Failed to delete HTML: {str(e)}")
    
    # 2. Try to find/delete PDF
    pdf_filename = filename.replace(".html", ".pdf")
    pdf_path = os.path.join(OUTPUT_DIR, "pdf", pdf_filename)
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
            deleted_files.append("PDF")
        except Exception as e:
            errors.append(f"Failed to delete PDF: {str(e)}")
            
    if not deleted_files and not errors:
        return {"status": "error", "message": "File not found."}
        
    msg = f"Deleted: {', '.join(deleted_files)}"
    if errors:
        msg += f". Errors: {', '.join(errors)}"
        
    return {"status": "success", "message": msg}
