import os
import sys
import subprocess
import pytest
from pathlib import Path

# Constants for paths
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Add src to path just in case we need to import something, 
# although we will run scripts via subprocess to test the CLI interface properly.
sys.path.append(str(SRC_DIR))

@pytest.fixture
def sample_html_file():
    # Attempt to find a real HTML file in input/
    html_files = list(INPUT_DIR.glob("*.html"))
    if not html_files:
        pytest.skip("No HTML files found in input/ for E2E test")
    
    # Sort by size (smallest first) to ensure fast testing
    html_files.sort(key=lambda f: f.stat().st_size)
    
    selected = html_files[0]
    print(f"\n[E2E] Selected sample file: {selected.name} ({selected.stat().st_size / 1024:.1f} KB)")
    return selected
    
@pytest.fixture
def output_txt_path():
    path = OUTPUT_DIR / "e2e_test_chat.txt"
    yield path
    # Cleanup
    if path.exists():
        path.unlink()

@pytest.fixture
def extracted_file(sample_html_file, output_txt_path):
    # Setup: Run extraction
    cmd = [
        sys.executable, 
        str(SRC_DIR / "extraction" / "main_extraction.py"),
        str(sample_html_file),
        "--output", str(output_txt_path)
    ]
    subprocess.run(cmd, check=True)
    
    assert output_txt_path.exists()
    yield output_txt_path
    
    # Teardown handled by output_txt_path fixture

def test_full_pipeline(extracted_file):
    """
    Test Step 2: Analysis & Report Generation
    Runs main_analysis.py on the extracted TXT file.
    Checks for HTML output.
    """
    print(f"\n[E2E] Testing Analysis on {extracted_file.name}...")
    
    cmd = [
        sys.executable,
        str(SRC_DIR / "analysis" / "main_analysis.py"),
        "--input", str(extracted_file),
        "--year", "2025", 
        "--quarter", "Q1",
        "--lang", "English"
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    
    assert result.returncode == 0, f"Analysis failed: {result.stderr}"
    
    # Check for generated HTML
    # Assuming output to OUTPUT_DIR
    generated_reports = list((OUTPUT_DIR / "html").glob("*.html"))
    if not generated_reports:
        # Fallback to checking root output/ if logic changed
        generated_reports = list(OUTPUT_DIR.glob("*.html"))
    
    import time
    now = time.time()
    recent_reports = [f for f in generated_reports if now - f.stat().st_mtime < 60]
    
    assert len(recent_reports) > 0, "No HTML report was generated recently."
    print(f"[E2E] Generated report: {recent_reports[0].name}")
    
