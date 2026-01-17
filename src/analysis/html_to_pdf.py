import sys
import os
import argparse
import time
from src.logger import setup_logger

logger = setup_logger("html_to_pdf")

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("'playwright' module not found. PDF generation will be skipped.")
    logger.warning("To enable PDF, run: pip install playwright && playwright install")
    PLAYWRIGHT_AVAILABLE = False

def convert_html_to_pdf(html_path, output_pdf_path=None):
    """
    Converts a local HTML file to PDF using Playwright (headless Chromium).
    This handles JS rendering (Plotly charts) which static converters miss.
    
    Returns: True if successful, False otherwise.
    """
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("PDF generation skipped: Playwright not installed.")
        return False

    if not output_pdf_path:
        output_pdf_path = html_path.replace(".html", ".pdf")

    abs_html_path = os.path.abspath(html_path)
    if not os.path.exists(abs_html_path):
        logger.error(f"File not found: {abs_html_path}")
        return

    logger.info(f"Converting '{os.path.basename(html_path)}' to PDF...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Open the local file
            # We use file:// to access local filesystem
            page.goto(f"file://{abs_html_path}")
            
            # Wait for potential JS to load charts
            # 'networkidle' is good, but sometimes Plotly takes a bit more.
            page.wait_for_load_state("networkidle")
            
            # Explicit wait to let animations/resizing settle
            time.sleep(2) 

            # Generate PDF
            # We set formatting options here
            page.pdf(
                path=output_pdf_path,
                format="A4",
                print_background=True,
                margin={
                    "top": "0.5in",
                    "right": "0.5in",
                    "bottom": "0.5in",
                    "left": "0.5in"
                }
            )
            
            browser.close()
        
        logger.info(f"PDF successfully created: {output_pdf_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert HTML report to PDF with JS support.")
    parser.add_argument("html_file", help="Path to the HTML file to convert")
    parser.add_argument("-o", "--output", help="Path to the output PDF file (optional)", default=None)
    
    args = parser.parse_args()
    
    convert_html_to_pdf(args.html_file, args.output)
