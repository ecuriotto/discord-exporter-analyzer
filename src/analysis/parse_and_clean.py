import re
import pandas as pd
from datetime import datetime

# Regex patterns for Discord message formats
# Full: [14/04/2024 13:10] User: Message
MESSAGE_REGEX_FULL = re.compile(r"^\[(\d{2}/\d{2}/\d{4} \d{2}:\d{2})]\s*(.+?):\s*(.*)$")
# Short: [13:10] User: Message
MESSAGE_REGEX_SHORT = re.compile(r"^\[(\d{2}:\d{2})]\s*(.+?):\s*(.*)$")

# Patterns for system messages and bot commands
SYSTEM_PATTERNS = [
    re.compile(r"^\*\*.+ (added|removed|changed|pinned|unpinned|joined|left|started|ended|created|deleted|updated).+\*\*$", re.IGNORECASE),
    re.compile(r"^\*\*.+\*\*$", re.IGNORECASE),  # generic bold system messages
]
BOT_COMMAND_PREFIXES = ('!', '/')

def is_system_message(message):
    for pat in SYSTEM_PATTERNS:
        if pat.match(message):
            return True
    return False

def is_bot_command(message):
    return message.strip().startswith(BOT_COMMAND_PREFIXES)

def parse_and_clean_discord_txt(txt_path):
    """
    Parse Discord .txt export into a cleaned DataFrame with columns: timestamp, user, message
    Removes system messages, bot commands, and handles multi-line messages.
    """
    rows = []
    buffer = None
    last_full_date = None

    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[ERROR] Could not read file {txt_path}: {e}")
        return pd.DataFrame()

    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        m_full = MESSAGE_REGEX_FULL.match(line)
        m_short = MESSAGE_REGEX_SHORT.match(line)

        if m_full:
            # print(f"[DEBUG] Line {idx}: FULL MATCH: {line}")
            # Save previous buffered message
            if buffer:
                if not is_system_message(buffer['message']) and not is_bot_command(buffer['message']):
                    rows.append(buffer)
            ts_str, user, message = m_full.groups()
            try:
                ts = datetime.strptime(ts_str, "%d/%m/%Y %H:%M")
                last_full_date = ts.date()
            except Exception:
                ts = None
            buffer = {'timestamp': ts, 'user': user, 'message': message}
        elif m_short:
            # print(f"[DEBUG] Line {idx}: SHORT MATCH: {line}")
            if buffer:
                if not is_system_message(buffer['message']) and not is_bot_command(buffer['message']):
                    rows.append(buffer)
            time_str, user, message = m_short.groups()
            # Use last seen date for short format
            if last_full_date:
                try:
                    ts = datetime.strptime(f"{last_full_date} {time_str}", "%Y-%m-%d %H:%M")
                except Exception:
                    ts = None
            else:
                ts = None
            buffer = {'timestamp': ts, 'user': user, 'message': message}
        else:
            if line.startswith('[') and ']' in line:
                # Potential match failure warning, but keeping silent for production
                pass
            # Multi-line message continuation
            if buffer:
                buffer['message'] += '\n' + line
    
    # Save last buffered message
    if buffer and not is_system_message(buffer['message']) and not is_bot_command(buffer['message']):
        rows.append(buffer)

    df = pd.DataFrame(rows, columns=['timestamp', 'user', 'message'])
    return df
