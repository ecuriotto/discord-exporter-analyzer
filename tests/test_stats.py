import pytest
import pandas as pd
from datetime import datetime
import os
import sys

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis.stats_and_visuals import (
    get_top_contributors_chart,
    get_activity_heatmap,
    get_yap_o_meter_chart,
    get_night_owls_chart,
    get_spammer_chart
)

@pytest.fixture
def sample_df():
    data = {
        'timestamp': [
            '2025-01-01 10:00:00',
            '2025-01-01 10:05:00',
            '2025-01-01 10:10:00',
            '2025-01-01 23:00:00',
        ],
        'user': ['Alice', 'Bob', 'Alice', 'NightOwl'],
        'message': [
            'Hello world this is a long message',
            'Hi',
            'Another message',
            'Late night http://example.com'
        ]
    }
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def test_top_contributors(sample_df):
    html = get_top_contributors_chart(sample_df)
    assert "Alice" in html
    assert "Bob" in html
    assert "NightOwl" in html
    assert "plot-" in html or "div id=" in html # Check for Plotly div

def test_activity_heatmap(sample_df):
    html = get_activity_heatmap(sample_df)
    # Checks for hour labels or structure
    assert "Hour of Day" in html
    # assert "Monday" in html # Depending on locale/date logic 2025-01-01 is Wednesday
    
def test_yap_o_meter(sample_df):
    # Need enough data (>10 msgs) for yap, or it returns fallback
    # Bob has 1 msg per sample. Need >10 msgs, so duplicate 11 times.
    large_df = pd.concat([sample_df] * 11, ignore_index=True) 
    html = get_yap_o_meter_chart(large_df)
    
    assert "The Novelists" in html
    assert "Alice" in html # Longest average
    assert "Bob" in html # Shortest average

def test_night_owls(sample_df):
    html = get_night_owls_chart(sample_df)
    assert "Night (00-06)" in html
    assert "NightOwl" in html
    
def test_spammer_chart(sample_df):
    html = get_spammer_chart(sample_df)
    assert "Links Shared" in html
    assert "NightOwl" in html # Has http link
    assert "Alice" not in html # No link
