from bs4 import BeautifulSoup
import sys
import re
import os
import argparse
from datetime import datetime
try:
    from src.extraction.export_discord_html import export_discord_html
except ImportError:
    # If running directly from src/extraction folder
    try:
        from export_discord_html import export_discord_html
    except ImportError:
         # Fallback for some execution environments
         sys.path.append(os.path.dirname(__file__))
         from export_discord_html import export_discord_html

def extract_discord_messages(html_file, output_file=None):
    """
    Estrae i messaggi da un file HTML esportato da DiscordChatExporter
    
    Args:
        html_file: percorso del file HTML di input
        output_file: percorso del file di output (opzionale)
    
    Returns:
        stringa con il testo estratto
    """
    
    if not os.path.exists(html_file):
        print(f"File non trovato: {html_file}")
        return ""

    # Leggi il file HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse HTML con BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Estrai informazioni dal preamble (intestazione canale)
    preamble = soup.find('div', class_='preamble')
    channel_info = ""
    if preamble:
        entries = preamble.find_all('div', class_='preamble__entry')
        if entries:
            channel_info = " / ".join([entry.get_text(strip=True) for entry in entries])
            channel_info = f"CANALE: {channel_info}\n{'='*80}\n\n"
    
    # Estrai tutti i messaggi
    messages = []
    message_containers = soup.find_all('div', class_='chatlog__message-container')
    for container in message_containers:
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
             messages.append(f"{timestamp_str} {author_name}: {content_text}")
             
    full_text = channel_info + "\n".join(messages)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"Salvato output in {output_file} ({len(messages)} messaggi)")
        
    return full_text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Discord HTML to Text Extractor')
    parser.add_argument('input_file', help='Input HTML file or "input/filename.html"')
    parser.add_argument('--export', help='Channel ID to export first', default=None)
    parser.add_argument('--output', help='Output TXT file', default=None)
    
    args = parser.parse_args()
    
    input_path = args.input_file
    
    # If export is requested
    if args.export:
        print(f"Exporting channel {args.export}...")
        # Assume input_path is the target HTML location
        if not export_discord_html(args.export, input_path):
            print("Export failed. Exiting.")
            sys.exit(1)
            
    # Convert HTML to TXT
    if not args.output:
        # Generate default output name: input.html -> input.txt
        base = os.path.splitext(os.path.basename(input_path))[0]
        # Or better: output/{base}.txt
        os.makedirs('output', exist_ok=True)
        args.output = os.path.join('output', f"{base}.txt")
        
    print(f"Extracting messages from {input_path}...")
    extract_discord_messages(input_path, args.output)
