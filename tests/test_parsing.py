import pytest
import pandas as pd
from datetime import datetime
import os
import sys

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis.parse_and_clean import (
    parse_and_clean_discord_txt, 
    is_system_message, 
    is_bot_command, 
    MESSAGE_REGEX_FULL
)

def test_is_system_message():
    assert is_system_message("**User joined the server**") is True
    assert is_system_message("**User left the server**") is True
    assert is_system_message("**User pinned a message.**") is True
    assert is_system_message("Just a bold message") is False
    assert is_system_message("Normal message") is False

def test_is_bot_command():
    assert is_bot_command("!play music") is True
    assert is_bot_command("/imagine") is True
    assert is_bot_command("Hello world") is False

def test_regex_full():
    line = "[15/01/2025 14:30] User1: Hello World"
    match = MESSAGE_REGEX_FULL.match(line)
    assert match is not None
    assert match.groups() == ("15/01/2025 14:30", "User1", "Hello World")

def test_parse_simple(tmp_path):
    # Create valid temp file
    content = """
[01/01/2025 10:00] Alice: Happy New Year!
[01/01/2025 10:05] Bob: You too!
[10:10] Alice: What's up?
    """
    f = tmp_path / "chat.txt"
    f.write_text(content.strip(), encoding='utf-8')
    
    df = parse_and_clean_discord_txt(str(f))
    
    assert len(df) == 3
    assert df.iloc[0]['user'] == "Alice"
    assert df.iloc[0]['message'] == "Happy New Year!"
    assert df.iloc[2]['user'] == "Alice"
    assert df.iloc[2]['timestamp'].hour == 10
    assert df.iloc[2]['timestamp'].minute == 10

def test_parse_multiline(tmp_path):
    content = """
[01/01/2025 10:00] Alice: Line 1
Line 2
Line 3
[01/01/2025 10:05] Bob: Reply
    """
    f = tmp_path / "multiline.txt"
    f.write_text(content.strip(), encoding='utf-8')
    
    df = parse_and_clean_discord_txt(str(f))
    
    assert len(df) == 2
    assert "Line 2" in df.iloc[0]['message']
    assert "Line 3" in df.iloc[0]['message']

def test_parse_filters(tmp_path):
    content = """
[01/01/2025 10:00] Alice: !bot
[01/01/2025 10:01] System: **User joined**
[01/01/2025 10:02] Bob: Real message
    """
    f = tmp_path / "filters.txt"
    f.write_text(content.strip(), encoding='utf-8')
    
    df = parse_and_clean_discord_txt(str(f))
    
    assert len(df) == 1
    assert df.iloc[0]['user'] == "Bob"
    assert df.iloc[0]['message'] == "Real message"
