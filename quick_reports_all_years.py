#!/usr/bin/env python3
"""
Quick script to generate reports for ALL years detected in your org files.

It mirrors the spirit of quick_reports.py, but instead of the last N months,
it iterates across every year found in your clocks and builds:
  1) Yearly reports for each year
  2) Consolidated monthly page for each year (12 months view)
  3) Individual monthly reports for each month that has data
  4) One big calendar heatmap covering all years
  5) A fresh index page collecting everything

You can run it safely multiple times; it only overwrites generated HTML/CSV files.
"""

from pathlib import Path
from datetime import datetime, timedelta
import org_time
from reports import ORG_FILES, TimeAnalyzer

from generate_reports import (
    get_years_with_data,
    generate_yearly_report,
    generate_monthly_report,
    generate_yearly_reports_for_all_years,
    generate_weekly_reports,
)
from monthly_consolidated import generate_consolidated_monthly_report
from weekly_consolidated import generate_consolidated_weekly_report
from generate_index import generate_index_html
from calendar_heatmap import generate_calendar_heatmap
import org_time
from reports import ORG_FILES


def _month_has_data(year: int, month: int) -> bool:
    """Quick check whether a given month has any tracked time."""
    from datetime import datetime
    if month == 12:
        start = datetime(year, 12, 1)
        end = datetime(year + 1, 1, 1)
    else:
        start = datetime(year, month, 1)
        end = datetime(year, month + 1, 1)
    root = org_time.load_files(ORG_FILES, start, end)
    return getattr(root, 'totalTime', 0) > 0


def _get_weeks_in_month(year: int, month: int):
    """Get list of (week_start, week_end, week_num, week_year) for all weeks touching this month."""
    from datetime import datetime, timedelta
    
    if month == 12:
        month_start = datetime(year, 12, 1)
        month_end = datetime(year + 1, 1, 1)
    else:
        month_start = datetime(year, month, 1)
        month_end = datetime(year, month + 1, 1)
    
    weeks = []
    # Start from the Monday on or before month_start
    week_start = month_start - timedelta(days=month_start.weekday())
    
    while week_start < month_end:
        week_end = week_start + timedelta(days=7)
        week_num = week_start.isocalendar()[1]
        week_year = week_start.isocalendar()[0]
        weeks.append((week_start, week_end, week_num, week_year))
        week_start = week_end
    
    return weeks


def _week_has_data(week_start, week_end) -> bool:
    """Check if a week has any tracked time."""
    root = org_time.load_files(ORG_FILES, week_start, week_end)
    return getattr(root, 'totalTime', 0) > 0


def _generate_year_weekly_consolidated(year: int, output_file: str):
    """Generate consolidated weekly report for all weeks in a year."""
    year_start = datetime(year, 1, 1)
    year_end = datetime(year + 1, 1, 1)
    
    # Find first Monday on or before Jan 1
    first_monday = year_start - timedelta(days=year_start.weekday())
    
    # Collect all weeks in the year
    weekly_data = []
    current = first_monday
    
    while current < year_end:
        week_end = current + timedelta(days=7)
        week_num = current.isocalendar()[1]
        week_year = current.isocalendar()[0]
        
        # Load data for this week
        clock_root = org_time.load_files(ORG_FILES, current, week_end)
        
        if clock_root.totalTime > 0:
            analyzer = TimeAnalyzer(clock_root)
            weekly_data.append({
                'week_num': week_num,
                'year': week_year,
                'week_label': f"W{week_num}",
                'start_date': current,
                'end_date': week_end,
                'total_hours': clock_root.totalTime,
                'avg_per_day': clock_root.totalTime / 7.0,
                'areas': analyzer.get_time_by_macro_area(),
                'topics': analyzer.get_time_by_topic(),
                'subtasks': analyzer.get_time_by_subtask(),
                'tags': analyzer.get_time_by_tags(),
                'analyzer': analyzer,
            })
        
        current = week_end
    
    # Use the weekly_consolidated HTML generator
    from weekly_consolidated import generate_weekly_html
    html = generate_weekly_html(weekly_data, len(weekly_data), output_file)
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_month_weekly_consolidated(year: int, month: int, weeks: list, output_file: str):
    """Generate consolidated weekly report for all weeks touching a month."""
    weekly_data = []
    
    for week_start, week_end, week_num, week_year in weeks:
        # Load data for this week
        clock_root = org_time.load_files(ORG_FILES, week_start, week_end)
        
        if clock_root.totalTime > 0:
            analyzer = TimeAnalyzer(clock_root)
            weekly_data.append({
                'week_num': week_num,
                'year': week_year,
                'week_label': f"W{week_num}",
                'start_date': week_start,
                'end_date': week_end,
                'total_hours': clock_root.totalTime,
                'avg_per_day': clock_root.totalTime / 7.0,
                'areas': analyzer.get_time_by_macro_area(),
                'topics': analyzer.get_time_by_topic(),
                'subtasks': analyzer.get_time_by_subtask(),
                'tags': analyzer.get_time_by_tags(),
                'analyzer': analyzer,
            })
    
    if not weekly_data:
        return
    
    # Use the weekly_consolidated HTML generator
    from weekly_consolidated import generate_weekly_html
    html = generate_weekly_html(weekly_data, len(weekly_data), output_file)
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_all_weeks_consolidated(first_year: int, output_file: str):
    """Generate a consolidated weekly report spanning all years from first_year to today."""
    # Range: from Monday on/before Jan 1 of first_year to Monday after today
    today = datetime.today()
    start_of_first_year = datetime(first_year, 1, 1)
    first_monday = start_of_first_year - timedelta(days=start_of_first_year.weekday())
    # Compute next Monday after today to cap the range
    this_monday = today - timedelta(days=today.weekday())
    next_monday = this_monday + timedelta(days=7)

    weekly_data = []
    cur = first_monday
    while cur < next_monday:
        week_end = cur + timedelta(days=7)
        week_num = cur.isocalendar()[1]
        week_year = cur.isocalendar()[0]

        clock_root = org_time.load_files(ORG_FILES, cur, week_end)
        if getattr(clock_root, 'totalTime', 0) > 0:
            analyzer = TimeAnalyzer(clock_root)
            weekly_data.append({
                'week_num': week_num,
                'year': week_year,
                'week_label': f"W{week_num}",
                'start_date': cur,
                'end_date': week_end,
                'total_hours': clock_root.totalTime,
                'avg_per_day': clock_root.totalTime / 7.0,
                'areas': analyzer.get_time_by_macro_area(),
                'topics': analyzer.get_time_by_topic(),
                'subtasks': analyzer.get_time_by_subtask(),
                'tags': analyzer.get_time_by_tags(),
                'analyzer': analyzer,
            })

        cur = week_end

    from weekly_consolidated import generate_weekly_html
    html = generate_weekly_html(weekly_data, len(weekly_data), output_file)
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)


def main():
    print(
        """
╔══════════════════════════════════════════════════════════════════════╗
║    Org Clock Analyzer - All Years Quick Report Generator             ║
╚══════════════════════════════════════════════════════════════════════╝
        """
    )

    years = get_years_with_data()
    if not years:
        print("No years with data found in the configured ORG_FILES. Nothing to do.")
        return

    first_year, last_year = years[0], years[-1]
    print(f"Discovered years with data: {years}")

    base_dir = Path("reports")
    base_dir.mkdir(exist_ok=True)

    # 1) Yearly reports for each year
    print("\n" + "="*70)
    print("STEP 1/8: Generating yearly reports for all years...")
    print("="*70)
    try:
        generate_yearly_reports_for_all_years(output_dir="reports/yearly")
        print("✓ Yearly reports complete!")
    except Exception as e:
        print(f"✗ Error while generating yearly reports: {e}")

    # 2) Consolidated monthly for each year
    print("\n" + "="*70)
    print("STEP 2/8: Generating consolidated monthly pages (12 months per year)...")
    print("="*70)
    for y in years:
        try:
            out = f"reports/monthly_consolidated_{y}.html"
            generate_consolidated_monthly_report(year=y, output_file=out)
            print(f"  ✓ {y}: {out}")
        except Exception as e:
            print(f"  ✗ {y}: {e}")

    # 3) Consolidated weekly for each year
    print("\n" + "="*70)
    print("STEP 3/8: Generating consolidated weekly pages (all weeks per year)...")
    print("="*70)
    for y in years:
        try:
            # Calculate all weeks in the year
            year_start = datetime(y, 1, 1)
            year_end = datetime(y + 1, 1, 1)
            
            # Find first Monday on or before Jan 1
            first_monday = year_start - timedelta(days=year_start.weekday())
            # Count weeks
            n_weeks = 0
            current = first_monday
            while current < year_end:
                n_weeks += 1
                current += timedelta(days=7)
            
            # Generate consolidated weekly for this year
            # We'll create a custom weekly consolidated for the year
            out = f"reports/weekly_consolidated_{y}.html"
            # Note: weekly_consolidated doesn't take year param, so we'll use a workaround
            # We'll collect all weeks in the year and generate
            _generate_year_weekly_consolidated(y, out)
            print(f"  ✓ {y}: {out}")
        except Exception as e:
            print(f"  ✗ {y}: {e}")

    # 4) Individual monthly reports for months with data
    print("\n" + "="*70)
    print("STEP 4/8: Generating individual monthly reports (only months with data)...")
    print("="*70)
    for y in years:
        for m in range(1, 13):
            try:
                if _month_has_data(y, m):
                    generate_monthly_report(year=y, month=m, output_dir="reports/monthly")
                    print(f"  ✓ {y}-{m:02d}")
            except Exception as e:
                print(f"  ✗ {y}-{m:02d}: {e}")

    # 5) Individual weekly reports and consolidated for each month
    print("\n" + "="*70)
    print("STEP 5/8: Generating weekly reports for each month...")
    print("="*70)
    for y in years:
        for m in range(1, 13):
            if not _month_has_data(y, m):
                continue
            try:
                # Get weeks in this month
                weeks_in_month = _get_weeks_in_month(y, m)
                
                # Generate consolidated weekly for this month
                month_name = datetime(y, m, 1).strftime('%Y-%m')
                out = f"reports/weekly_consolidated_{month_name}.html"
                _generate_month_weekly_consolidated(y, m, weeks_in_month, out)
                
                # Count how many weeks have data
                weeks_with_data = sum(1 for w in weeks_in_month if _week_has_data(w[0], w[1]))
                if weeks_with_data > 0:
                    print(f"  ✓ {month_name}: {weeks_with_data} weeks")
            except Exception as e:
                print(f"  ✗ {y}-{m:02d}: {e}")

    # 6) Consolidated monthly across ALL years
    print("\n" + "="*70)
    print("STEP 6/8: Generating consolidated monthly (ALL years)...")
    print("="*70)
    try:
        today = datetime.today()
        total_months = (today.year - first_year) * 12 + today.month
        all_months_out = "reports/monthly_consolidated_all_years.html"
        generate_consolidated_monthly_report(n_months=total_months, output_file=all_months_out)
        print(f"✓ All-years monthly consolidated: {all_months_out}")
    except Exception as e:
        print(f"✗ Error while generating all-years monthly consolidated: {e}")

    # 7) One big calendar heatmap covering all years

    print("\n" + "="*70)
    print("STEP 7/8: Generating all-years calendar heatmap...")
    print("="*70)
    try:
        # Compute total months from first January to current month (re-use total_months)
        today = datetime.today()
        total_months = (today.year - first_year) * 12 + today.month
        calendar_path = generate_calendar_heatmap(
            output_file="reports/calendar/all_years.html",
            months=total_months,
        )
        print(f"✓ Calendar heatmap complete: {calendar_path}")
    except Exception as e:
        print(f"✗ Error while generating all-years calendar: {e}")

    # 8) Index page
    print("\n" + "="*70)
    print("STEP 8/8: Generating index page...")
    print("="*70)
    try:
        index_path = generate_index_html("reports/index.html", "reports")
        print("✓ Index page generated!")
        print(f"\n🌐 Open in browser: file://{index_path}")
    except Exception as e:
        print(f"✗ Error: {e}")

    print("\n" + "="*70)
    print("ALL-YEARS REPORTS GENERATED!")
    print("="*70)
    print(f"\nReports saved to: {base_dir.absolute()}")


if __name__ == "__main__":
    main()
