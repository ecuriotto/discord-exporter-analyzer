from bs4 import BeautifulSoup
import sys
import re
import os
import argparse
import datetime
import glob

# Setup Logger
# We need to add project root to path to import src.logger if running as script
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.logger import setup_logger
from src.config import INPUT_DIR, OUTPUT_TXT_DIR
# logging is configured via setup_logger, but we want to ensure it emits to console for webapp visibility
# setup_logger should handle it, but let's double check or add a stream handler if missing
import logging
logger = setup_logger("extraction")
# Force add stream handler if not present (simple hack)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    logger.addHandler(logging.StreamHandler(sys.stdout))
    
# Ensure we also log to app.log located in logs/
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)
app_log_path = os.path.join(log_dir, "app.log")
file_handler = logging.FileHandler(app_log_path, mode='a')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


try:
    from src.extraction.export_discord_html import export_discord_html
except ImportError:
    # If project root is in sys.path, this should work.
    # Fallback only if strictly necessary or running standalone without package context
    try:
        from export_discord_html import export_discord_html
    except ImportError:
         sys.path.append(os.path.dirname(__file__))
         from export_discord_html import export_discord_html

def get_last_timestamp_from_txt(txt_file):
    """
    Legge l'ultimo timestamp utile dal file TXT esistente.
    Format atteso: [DD/MM/YYYY HH:MM] o varianti.
    Returns datetime object or None.
    """
    if not os.path.exists(txt_file):
        return None
    
    try:
        with open(txt_file, 'rb') as f:
            f.seek(0, 2)
            filesize = f.tell()
            # Read last 20KB to be safe (messages can be long)
            offset = min(20000, filesize)
            f.seek(-offset, 2)
            # Decode ignoring cleanups
            lines = f.read().decode('utf-8', errors='ignore').splitlines()
            
            # Iterate backwards
            for line in reversed(lines):
                text = line.strip()
                # Pattern: [DD/MM/YYYY HH:MM] or [DD-MMM-YY HH:MM PM]
                # We look for the starting bracket and timestamp combo
                match = re.search(r'\[(.*?)\].*?:', text)
                if match:
                    timestamp_str = match.group(1)
                    
                    # Try parsers
                    formats = [
                        "%d/%m/%Y %H:%M",
                        "%d-%b-%y %I:%M %p",
                        "%Y-%m-%d %H:%M",
                        "%Y-%m-%d %H:%M:%S"
                    ]
                    
                    for fmt in formats:
                        try:
                            return datetime.datetime.strptime(timestamp_str, fmt)
                        except ValueError:
                            continue
                            
    except Exception as e:
        logger.warning(f"Failed to read last timestamp from {txt_file}: {e}")
        return None
    
    return None

def extract_discord_messages(html_file, output_file=None, append_mode=False):
    """
    Estrae i messaggi da un file HTML esportato da DiscordChatExporter
    
    Args:
        html_file: percorso del file HTML di input
        output_file: percorso del file di output (opzionale)
        append_mode: se True, appende al file di output esistente
    
    Returns:
        stringa con il testo estratto
    """
    
    if not os.path.exists(html_file):
        logger.error(f"File not found: {html_file}")
        return ""

    logger.info(f"Reading HTML file: {html_file}...")
    
    # Use Streaming parsing where possible (pass file handler)
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    logger.info("HTML Structure parsed. Processing messages...")
    
    # Setup Output Stream
    out_f = None
    extracted_buffer_legacy = [] # Fallback if no output_file
    
    mode = 'a' if append_mode else 'w'
    
    if output_file:
        out_f = open(output_file, mode, encoding='utf-8')
        if append_mode:
            out_f.write(f"\n\n--- INCREMENTAL UPDATE: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n\n")
    
    def write_message(text):
        if out_f:
            out_f.write(text + "\n")
        else:
            extracted_buffer_legacy.append(text)

    # Estrai informazioni dal preamble (intestazione canale)
    # If appending, maybe skip header? Or keep it as separator?
    # Usually clean to keep context or maybe minimal separator.
    # The user wants "The final txt file will contain all the content".
    # Duplicate headers are annoying but acceptable.
    # However, for pure storage, we might want to skip header if append_mode is True.
    preamble = soup.find('div', class_='preamble')

    if preamble and not append_mode:
        entries = preamble.find_all('div', class_='preamble__entry')
        if entries:
            channel_info = " / ".join([entry.get_text(strip=True) for entry in entries])
            header = f"CANALE: {channel_info}\n{'='*80}\n\n"
            write_message(header)
    
    # Estrai tutti i messaggi
    message_containers = soup.find_all('div', class_='chatlog__message-container')
    logger.info(f"Found {len(message_containers)} message containers. Processing...")
    
    messages_count = 0
    for i, container in enumerate(message_containers):
        if i > 0 and i % 1000 == 0:
            logger.debug(f"Processed {i} messages...")
            
        message_div = container.find('div', class_='chatlog__message')
        if not message_div:
            continue
            
        # Estrai autore
        author = message_div.find('span', class_='chatlog__author')
        if not author:
            # In alcuni casi l'autore può essere un <span> senza la classe, oppure un <span> con la classe direttamente nel header
            header = message_div.find('div', class_='chatlog__header')
            if header:
                author = header.find('span', class_='chatlog__author')
        author_name = author.get_text(strip=True) if author else "Sconosciuto"
        
        # Estrai timestamp
        timestamp_span = message_div.find('span', class_='chatlog__timestamp')
        timestamp_str = ""
        if timestamp_span:
            # Try to get timestamp from title attribute (usually ISO format) or text
            ts_text = timestamp_span.get_text(strip=True)
            # Standard cleanup if needed, but DiscordChatExporter usually gives "DD/MM/YYYY HH:mm" or similar based on locale
            # We need to enforce a format. Usually it's in the text.
            # Let's assume the text is usable directly, but for the regex in parse_and_clean we need [DD/MM/YYYY HH:MM]
            
            # If the text is like "10/01/2026 14:30", we wrap it in brackets.
            # Example text: "10-gen-26 14:30" or "Today at 2:30 PM".
            # The tool usually exports in a specific format.
            # Let's try to extract ISO from title if available: title="10-Jan-26 2:30 PM"
            
            # For reliability, let's grab the raw text.
            # However, `parse_and_clean.py` expects `[dd/mm/yyyy HH:MM]`.
            # If the HTML contains something else, we might need to parse it.
            # Let's trust the text for now, but ensure brackets.
            timestamp_str = f"[{ts_text}]"
            
        # Estrai contenuto
        content_div = message_div.find('div', class_='chatlog__content')
        content_text = ""
        if content_div:
            # Get text, handling <br> as newlines
            for br in content_div.find_all("br"):
                br.replace_with("\n")
            content_text = content_div.get_text(strip=True)
            
        # Handle attachments (images, etc)
        attachments_div = message_div.find('div', class_='chatlog__attachment')
        if attachments_div:
             # Just note it's an attachment
             if not content_text:
                 content_text = "<Attachment/Image>"
             else:
                 content_text += " <Attachment>"

        if timestamp_str and author_name:
             # Basic clean up of newlines to keep it one line per message if possible, or allow multi-line?
             # The regex allows multi-line if handled keyfully, but usually we want one line or the parser handles it.
             # The parser `parse_and_clean.py` has `MESSAGE_REGEX_FULL` which matches the start, then consumes the rest.
             # So multiline content is fine as long as the next line doesn't start with a timestamp.
             msg = f"{timestamp_str} {author_name}: {content_text}"
             write_message(msg)
             messages_count += 1
             
    if out_f:
        out_f.close()
        logger.info(f"Salvato output in {output_file} ({messages_count} messaggi)")
        return ""
    else:
        return "\n".join(extracted_buffer_legacy)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Discord HTML to Text Extractor')
    # Make input_file optional (nargs='?')
    parser.add_argument('input_file', help='Input HTML file or "input/filename.html"', nargs='?', default=None)
    parser.add_argument('--export', help='Channel ID to export first', default=None)
    parser.add_argument('--output', help='Output TXT file', default=None)
    
    args = parser.parse_args()
    
    # Sanitize Channel ID early (handle input like GuildID/ChannelID)
    if args.export and "/" in args.export:
        raw_export = args.export
        args.export = args.export.split("/")[-1]
        print(f"[INFO] Detected composite ID '{raw_export}'. Using Channel ID: {args.export}")

    # If using export, we can generate a default filename if none provided
    if args.export and not args.input_file:
        # Use a template pattern so the filename includes the channel name
        # We rely on DiscordChatExporter to replace %n with the name
        args.input_file = "%n_%c.html" # e.g. "General_12345.html"

    # If AFTER logic, we still don't have an input file, error out (unless export runs and we want to stop?) 
    # But usually we export AND extract.
    if not args.input_file:
        print("[ERROR] Please provide an input file or a channel ID to export.")
        parser.print_help()
        sys.exit(1)

    input_path = args.input_file
    
    # Variables for incremental update
    append_mode = False
    existing_txt_file = None
    
    # If export is requested
    if args.export:
        print(f"Exporting channel {args.export}...")
        
        # Check for existing TXT data to enable incremental export
        # We look for files ending with _{channel_id}.txt in output/txt/
        if os.path.exists(OUTPUT_TXT_DIR):
            txt_pattern = os.path.join(OUTPUT_TXT_DIR, f"*_{args.export}.txt")
            found_txts = glob.glob(txt_pattern)
            
            if found_txts:
                # Use the most recently modified one
                existing_txt_file = max(found_txts, key=os.path.getmtime)
                last_dt = get_last_timestamp_from_txt(existing_txt_file)
                
                if last_dt:
                    # Add 1 second to avoid duplication if possible, or just exact time
                    # DiscordChatExporter treats after as inclusive or strictly after? 
                    # Usually 'after'. Let's add 1s to be safe.
                    after_str = (last_dt + datetime.timedelta(seconds=1)).isoformat()
                    print(f"[INFO] Found existing extracted data ({os.path.basename(existing_txt_file)}). \n       Last message: {last_dt}. \n       Running incremental export after {after_str}.")
                    
                    # Assume input_path is the target HTML location (or template)
                    # export_discord_html will force it into input/ dir
                    if not export_discord_html(args.export, input_path, after_date=after_str):
                        print("Export failed. Exiting.")
                        sys.exit(1)
                    
                    append_mode = True
                else:
                    # File exists but no timestamp found, full export
                    if not export_discord_html(args.export, input_path):
                         print("Export failed. Exiting.")
                         sys.exit(1)
            else:
                # No existing file, full export
                if not export_discord_html(args.export, input_path):
                    print("Export failed. Exiting.")
                    sys.exit(1)
        else:
             # No output dir, full export
             if not export_discord_html(args.export, input_path):
                 print("Export failed. Exiting.")
                 sys.exit(1)
        
        # If we used a template (contains %), we need to find the actual file created
        if "%" in input_path or args.input_file == "%n_%c.html":
            # We look for files ending with _{channel_id}.html in input/
            # %c is replaced by channel ID.
            # import glob # Already imported at top-level now

            # The pattern to match the file we just created. 
            # Since we used "%n_%c.html", it ends with "_{id}.html"
            search_pattern = os.path.join(INPUT_DIR, f"*_{args.export}.html")
            
            # Find files (list is arbitrary order, so we need to sort by time to get the newest)
            found_files = glob.glob(search_pattern)
            
            if found_files:
                # Get the most recently modified file (the one we just exported)
                input_path = max(found_files, key=os.path.getmtime)
                print(f"[INFO] Resolved exported file to: {input_path}")
                
                # FIX: Check if CLI failed to replace %n (filename still contains %n)
                base_name = os.path.basename(input_path)
                if "%n" in base_name:
                     print("[WARN] CLI failed to replace channel name placeholder. Attempting to fix filename...")
                     try:
                         # Read preamble to find real name
                         # We can't trust full parse yet, just peek
                         with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                             chunk = f.read(8192) # 8KB
                             
                         # Try to find title
                         title_match = re.search(r'<title>(.*?)</title>', chunk, re.IGNORECASE)
                         real_name = "Unknown_Channel"
                         
                         if title_match:
                             full_title = title_match.group(1).strip()
                             # Format: "Guild - Channel"
                             parts = full_title.split(' - ')
                             if len(parts) > 1:
                                 real_name = parts[-1].strip()
                             else:
                                 real_name = full_title
                         
                         # Sanitize
                         real_name = re.sub(r'[<>:"/\\|?*]', '_', real_name).strip()
                         
                         # reconstruct filename: Name_ID.html
                         # Extract ID from current filename "%n_ID.html"
                         id_match = re.search(r'_(\d+)\.html$', base_name)
                         chan_id = id_match.group(1) if id_match else args.export
                         
                         new_filename = f"{real_name}_{chan_id}.html"
                         new_path = os.path.join(os.path.dirname(input_path), new_filename)
                         
                         os.rename(input_path, new_path)
                         print(f"[INFO] Renamed {base_name} -> {new_filename}")
                         input_path = new_path
                         
                     except Exception as e:
                         print(f"[ERROR] Failed to fix filename: {e}")

            else:
                print(f"[ERROR] Could not find the exported file matching pattern: {search_pattern}")
                # Fallback to simple ID check just in case
                fallback = os.path.join(INPUT_DIR, f"{args.export}.html")
                if os.path.exists(fallback):
                     input_path = fallback
                else:
                     sys.exit(1)
        else:
            # If user provided a specific static path, ensure it lives in input/ if simply named
            # But main_extraction is run from root usually, and export script handles input/ logic for creation.
            # We need to ensure we read from correct place.
            if not os.path.exists(input_path):
                 # Check input/
                 candidate = os.path.join(INPUT_DIR, input_path)
                 if os.path.exists(candidate):
                     input_path = candidate
            
    # Convert HTML to TXT
    if not args.output:
        # If append mode, use the existing file as target
        if append_mode and existing_txt_file:
             args.output = existing_txt_file
             print(f"[INFO] Appending new messages to existing archive: {args.output}")
        else:
            # Generate default output name: input.html -> output/txt/input.txt
            base = os.path.splitext(os.path.basename(input_path))[0]
            
            # Organize in subfolder
            txt_out_dir = OUTPUT_TXT_DIR
            os.makedirs(txt_out_dir, exist_ok=True)
            
            args.output = os.path.join(txt_out_dir, f"{base}.txt")
        
    logger.info(f"Extracting messages from {input_path}...")
    extract_discord_messages(input_path, args.output, append_mode=append_mode)
