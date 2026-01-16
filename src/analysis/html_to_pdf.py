import sys
import os
import argparse
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: 'playwright' module not found. Please install it using:")
    print("  pip install playwright")
    print("  playwright install")
    sys.exit(1)

def convert_html_to_pdf(html_path, output_pdf_path=None):
    """
    Converts a local HTML file to PDF using Playwright (headless Chromium).
    This handles JS rendering (Plotly charts) which static converters miss.
    """
    if not output_pdf_path:
        output_pdf_path = html_path.replace(".html", ".pdf")

    abs_html_path = os.path.abspath(html_path)
    if not os.path.exists(abs_html_path):
        print(f"Error: File not found: {abs_html_path}")
        return

    print(f"Converting '{os.path.basename(html_path)}' to PDF...")

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
    
    print(f"✅ PDF successfully created: {output_pdf_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert HTML report to PDF with JS support.")
    parser.add_argument("html_file", help="Path to the HTML file to convert")
    parser.add_argument("-o", "--output", help="Path to the output PDF file (optional)", default=None)
    
    args = parser.parse_args()
    
    convert_html_to_pdf(args.html_file, args.output)
