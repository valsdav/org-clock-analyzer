#!/usr/bin/env python3
"""
Quick start script for generating common reports.
Run this to quickly generate a set of useful reports.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from generate_reports import (
    generate_weekly_reports,
    generate_monthly_report,
    generate_monthly_reports,
    generate_yearly_report
)
from generate_index import generate_index_html
from weekly_consolidated import generate_consolidated_weekly_report
from monthly_consolidated import generate_consolidated_monthly_report


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          Org Clock Analyzer - Quick Report Generator         ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("This will generate the following reports:")
    print("  1. Last 4 individual weekly reports")
    print("  2. Consolidated weekly view (last 4 weeks)")
    print("  3. Last 12 individual monthly reports")
    print("  4. Consolidated monthly view (last 12 months)")
    print("  5. Current year report")
    print()
    
    response = input("Continue? [Y/n]: ").strip().lower()
    if response and response != 'y':
        print("Cancelled.")
        return
    
    # Create reports directory
    base_dir = Path("reports")
    base_dir.mkdir(exist_ok=True)
    
    print("\n" + "="*70)
    print("STEP 1/6: Generating individual weekly reports...")
    print("="*70)
    try:
        generate_weekly_reports(n=4, output_dir="reports/weekly")
        print("✓ Weekly reports complete!")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*70)
    print("STEP 2/6: Generating consolidated weekly view...")
    print("="*70)
    try:
        generate_consolidated_weekly_report(n_weeks=4, output_file="reports/weekly_consolidated.html")
        print("✓ Consolidated weekly report complete!")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*70)
    print("STEP 3/6: Generating individual monthly reports...")
    print("="*70)
    try:
        generate_monthly_reports(n=12, output_dir="reports/monthly")
        print("✓ Monthly reports complete!")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*70)
    print("STEP 4/6: Generating consolidated monthly view...")
    print("="*70)
    try:
        generate_consolidated_monthly_report(n_months=12, output_file="reports/monthly_consolidated.html")
        print("✓ Consolidated monthly report complete!")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*70)
    print("STEP 5/6: Generating current year report...")
    print("="*70)
    try:
        generate_yearly_report(output_dir="reports/yearly")
        print("✓ Yearly report complete!")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*70)
    print("STEP 6/6: Generating index page...")
    print("="*70)
    try:
        index_path = generate_index_html("reports/index.html", "reports")
        print("✓ Index page generated!")
    except Exception as e:
        print(f"✗ Error: {e}")
        index_path = None
    
    print("\n" + "="*70)
    print("ALL REPORTS GENERATED!")
    print("="*70)
    print(f"\nReports saved to: {base_dir.absolute()}")
    print("\nReport structure:")
    print("  reports/")
    print("  ├── index.html  ← Browse all reports here!")
    print("  ├── weekly_consolidated.html")
    print("  ├── monthly_consolidated.html")
    print("  ├── weekly/")
    print("  │   └── Week_XX_YYYY/ (for each week)")
    print("  ├── monthly/")
    print("  │   └── YYYY-MM/")
    print("  └── yearly/")
    print("      └── Year_YYYY/")
    
    if index_path:
        print(f"\n🌐 Open in browser: file://{index_path}")
    print()


if __name__ == "__main__":
    main()
