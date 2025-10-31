#!/usr/bin/env python3
"""
Example script showing how to use the reporting API for custom analysis.
"""

from datetime import datetime, timedelta
import org_time
from reports import TimeAnalyzer, ReportGenerator, ORG_FILES


def example_basic_report():
    """Example 1: Generate a basic weekly report."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Weekly Report")
    print("="*70 + "\n")
    
    # Get current week dates
    today = datetime.today()
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=7)
    
    # Load data
    print(f"Loading data from {start_date.date()} to {end_date.date()}...")
    clock_root = org_time.load_files(ORG_FILES, start_date, end_date)
    
    if clock_root.totalTime == 0:
        print("No time tracked this week.")
        return
    
    # Create analyzer
    analyzer = TimeAnalyzer(clock_root)
    
    # Get data
    areas = analyzer.get_time_by_macro_area()
    topics = analyzer.get_time_by_topic()
    tags = analyzer.get_time_by_tags()
    
    print(f"\nTotal time: {clock_root.totalTime:.2f} hours")
    print(f"\nTop 3 areas:")
    for area, hours in sorted(areas.items(), key=lambda x: x[1], reverse=True)[:3]:
        print(f"  - {area}: {hours:.2f}h ({100*hours/clock_root.totalTime:.1f}%)")
    
    print(f"\nTop 3 topics:")
    for topic, hours in sorted(topics.items(), key=lambda x: x[1], reverse=True)[:3]:
        print(f"  - {topic}: {hours:.2f}h ({100*hours/clock_root.totalTime:.1f}%)")
    
    if tags:
        print(f"\nTop 3 tags:")
        for tag, hours in sorted(tags.items(), key=lambda x: x[1], reverse=True)[:3]:
            print(f"  - {tag}: {hours:.2f}h ({100*hours/clock_root.totalTime:.1f}%)")


def example_custom_analysis():
    """Example 2: Custom analysis - find tasks with specific characteristics."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Custom Analysis - Tasks over 2 hours")
    print("="*70 + "\n")
    
    # Get last month
    today = datetime.today()
    start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    end_date = today.replace(day=1)
    
    # Load data
    clock_root = org_time.load_files(ORG_FILES, start_date, end_date)
    
    if clock_root.totalTime == 0:
        print("No time tracked last month.")
        return
    
    # Create analyzer and get detailed breakdown
    analyzer = TimeAnalyzer(clock_root)
    detailed_df = analyzer.get_detailed_breakdown()
    
    # Find tasks with more than 2 hours
    big_tasks = detailed_df[detailed_df['time'] > 2.0].sort_values('time', ascending=False)
    
    print(f"Found {len(big_tasks)} tasks with more than 2 hours:\n")
    for idx, row in big_tasks.head(10).iterrows():
        print(f"  {row['time']:.2f}h - {row['full_path']}")
        if row['tags']:
            print(f"         Tags: {row['tags']}")


def example_compare_periods():
    """Example 3: Compare two time periods."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Compare This Month vs Last Month")
    print("="*70 + "\n")
    
    today = datetime.today()
    
    # This month
    this_month_start = today.replace(day=1)
    this_month_end = today
    
    # Last month
    last_month_end = this_month_start
    last_month_start = (last_month_end - timedelta(days=1)).replace(day=1)
    
    # Load both periods
    print("Loading this month...")
    this_month_root = org_time.load_files(ORG_FILES, this_month_start, this_month_end)
    
    print("Loading last month...")
    last_month_root = org_time.load_files(ORG_FILES, last_month_start, last_month_end)
    
    # Analyze
    this_month_analyzer = TimeAnalyzer(this_month_root)
    last_month_analyzer = TimeAnalyzer(last_month_root)
    
    this_month_areas = this_month_analyzer.get_time_by_macro_area()
    last_month_areas = last_month_analyzer.get_time_by_macro_area()
    
    # Compare
    print(f"\nTotal time comparison:")
    print(f"  This month (so far): {this_month_root.totalTime:.2f}h")
    print(f"  Last month: {last_month_root.totalTime:.2f}h")
    
    days_this_month = (this_month_end - this_month_start).days + 1
    days_last_month = (last_month_end - last_month_start).days
    
    print(f"\nAverage per day:")
    print(f"  This month: {this_month_root.totalTime/days_this_month:.2f}h/day")
    print(f"  Last month: {last_month_root.totalTime/days_last_month:.2f}h/day")
    
    # Find areas with biggest changes
    print(f"\nBiggest changes by area:")
    all_areas = set(this_month_areas.keys()) | set(last_month_areas.keys())
    
    changes = []
    for area in all_areas:
        this_hours = this_month_areas.get(area, 0)
        last_hours = last_month_areas.get(area, 0)
        diff = this_hours - last_hours
        changes.append((area, diff, this_hours, last_hours))
    
    changes.sort(key=lambda x: abs(x[1]), reverse=True)
    
    for area, diff, this_hours, last_hours in changes[:5]:
        if diff > 0:
            print(f"  ↑ {area}: +{diff:.1f}h ({last_hours:.1f}h → {this_hours:.1f}h)")
        elif diff < 0:
            print(f"  ↓ {area}: {diff:.1f}h ({last_hours:.1f}h → {this_hours:.1f}h)")
        else:
            print(f"  = {area}: no change ({this_hours:.1f}h)")


def example_tag_analysis():
    """Example 4: Detailed tag analysis."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Tag Analysis - Activity Types")
    print("="*70 + "\n")
    
    # Get last 30 days
    end_date = datetime.today()
    start_date = end_date - timedelta(days=30)
    
    clock_root = org_time.load_files(ORG_FILES, start_date, end_date)
    
    if clock_root.totalTime == 0:
        print("No time tracked in the last 30 days.")
        return
    
    analyzer = TimeAnalyzer(clock_root)
    tags = analyzer.get_time_by_tags()
    
    if not tags:
        print("No tags found in the data.")
        return
    
    print(f"Activity breakdown by tags (last 30 days):\n")
    print(f"{'Tag':<20} {'Hours':<10} {'Percentage':<12} {'Bar'}")
    print("-" * 60)
    
    total = sum(tags.values())
    for tag, hours in sorted(tags.items(), key=lambda x: x[1], reverse=True):
        pct = 100 * hours / total
        bar_length = int(pct / 2)  # Scale for display
        bar = "█" * bar_length
        print(f"{tag:<20} {hours:>6.1f}h   {pct:>5.1f}%      {bar}")
    
    print(f"\nTotal tagged time: {total:.2f}h out of {clock_root.totalTime:.2f}h total")
    print(f"Tagged coverage: {100*total/clock_root.totalTime:.1f}%")


def example_generate_pdf_ready_report():
    """Example 5: Generate a text-based report suitable for PDF conversion."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Text-Based Report (PDF-Ready)")
    print("="*70 + "\n")
    
    # Get current month
    today = datetime.today()
    start_date = today.replace(day=1)
    end_date = today
    
    clock_root = org_time.load_files(ORG_FILES, start_date, end_date)
    
    if clock_root.totalTime == 0:
        print("No time tracked this month.")
        return
    
    analyzer = TimeAnalyzer(clock_root)
    period_name = start_date.strftime("%B %Y")
    
    # Generate report to stdout
    report_gen = ReportGenerator(analyzer, period_name, start_date, end_date)
    report_gen.generate_summary_table()
    
    # Add productivity metrics
    days = (end_date - start_date).days + 1
    avg_per_day = clock_root.totalTime / days
    
    print("\n" + "="*70)
    print("PRODUCTIVITY METRICS")
    print("="*70)
    print(f"\nWorking days in period: {days}")
    print(f"Average hours per day: {avg_per_day:.2f}")
    print(f"Total productive hours: {clock_root.totalTime:.2f}")
    
    # Estimate work weeks (assuming 40h/week)
    work_weeks = clock_root.totalTime / 40
    print(f"Equivalent work weeks (40h): {work_weeks:.2f}")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║             Org Clock Analyzer - Usage Examples              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("This script demonstrates various ways to analyze your time tracking data.")
    print("Choose an example to run:\n")
    print("  1. Basic weekly report")
    print("  2. Custom analysis - Find tasks over 2 hours")
    print("  3. Compare this month vs last month")
    print("  4. Tag analysis - Activity types")
    print("  5. Text-based report (PDF-ready)")
    print("  6. Run all examples")
    print("  0. Exit")
    print()
    
    try:
        choice = input("Enter choice [1-6, 0 to exit]: ").strip()
        
        if choice == '1':
            example_basic_report()
        elif choice == '2':
            example_custom_analysis()
        elif choice == '3':
            example_compare_periods()
        elif choice == '4':
            example_tag_analysis()
        elif choice == '5':
            example_generate_pdf_ready_report()
        elif choice == '6':
            example_basic_report()
            example_custom_analysis()
            example_compare_periods()
            example_tag_analysis()
            example_generate_pdf_ready_report()
        elif choice == '0':
            print("Exiting.")
        else:
            print(f"Invalid choice: {choice}")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
