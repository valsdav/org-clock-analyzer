#!/usr/bin/env python3
"""
Simple script to open the reports index in the default browser.
"""

import webbrowser
from pathlib import Path
import sys


def open_reports_index(index_path="reports/index.html"):
    """Open the reports index in the default web browser."""
    index_file = Path(index_path)
    
    if not index_file.exists():
        print(f"❌ Index file not found: {index_file}")
        print("\nGenerate it first with:")
        print("  python generate_index.py")
        print("\nOr generate reports with:")
        print("  python quick_reports.py")
        return False
    
    # Get absolute path
    abs_path = index_file.absolute()
    url = f"file://{abs_path}"
    
    print(f"📂 Opening reports index...")
    print(f"   {url}")
    
    try:
        webbrowser.open(url)
        print("\n✓ Opened in your default browser!")
        return True
    except Exception as e:
        print(f"\n❌ Error opening browser: {e}")
        print(f"\nManually open: {url}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        index_path = sys.argv[1]
    else:
        index_path = "reports/index.html"
    
    open_reports_index(index_path)
