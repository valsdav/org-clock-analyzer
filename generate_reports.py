#!/usr/bin/env python3
"""
Example script to generate various time tracking reports.
Demonstrates different use cases of the reporting system.
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import org_time
from reports import TimeAnalyzer, ReportGenerator, ORG_FILES


def generate_last_n_weeks_comparison(n=4, output_dir="reports/weekly_comparison"):
    """Generate and compare reports for the last N weeks."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"GENERATING LAST {n} WEEKS COMPARISON")
    print(f"{'='*80}\n")
    
    weekly_data = []
    
    for i in range(n):
        # Calculate week dates (going backwards)
        today = datetime.today()
        week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=n-1-i)
        week_end = week_start + timedelta(days=7)
        
        week_num = week_start.isocalendar()[1]
        year = week_start.year
        period_name = f"Week_{week_num}_{year}"
        
        print(f"\nLoading Week {week_num} ({week_start.date()} to {week_end.date()})...")
        
        # Load data
        clock_root = org_time.load_files(ORG_FILES, week_start, week_end)
        
        if clock_root.totalTime == 0:
            print(f"  No data for this week")
            continue
        
        # Analyze
        analyzer = TimeAnalyzer(clock_root)
        
        # Store summary data
        weekly_data.append({
            'week': f"W{week_num}",
            'start_date': week_start,
            'total_hours': clock_root.totalTime,
            'areas': analyzer.get_time_by_macro_area(),
            'topics': analyzer.get_time_by_topic(),
            'tags': analyzer.get_time_by_tags(),
        })
        
        # Generate individual report
        report_gen = ReportGenerator(analyzer, period_name, week_start, week_end)
        week_dir = output_dir / period_name
        week_dir.mkdir(exist_ok=True)
        report_gen.generate_full_report(week_dir)
    
    # Create comparison visualizations
    if weekly_data:
        create_weekly_comparison_plots(weekly_data, output_dir)
    
    print(f"\n{'='*80}")
    print(f"Weekly comparison reports generated in: {output_dir}")
    print(f"{'='*80}\n")


def create_weekly_comparison_plots(weekly_data, output_dir):
    """Create comparison plots across multiple weeks."""
    output_dir = Path(output_dir)
    
    # Total hours trend
    weeks = [w['week'] for w in weekly_data]
    total_hours = [w['total_hours'] for w in weekly_data]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=weeks,
        y=total_hours,
        marker_color='steelblue',
        text=[f"{h:.1f}h" for h in total_hours],
        textposition='auto',
    ))
    fig.update_layout(
        title="Total Hours Tracked - Weekly Trend",
        xaxis_title="Week",
        yaxis_title="Hours",
        height=400,
    )
    fig.write_html(output_dir / "weekly_total_trend.html")
    
    # Area comparison across weeks
    all_areas = set()
    for w in weekly_data:
        all_areas.update(w['areas'].keys())
    
    fig = go.Figure()
    for area in sorted(all_areas):
        hours_per_week = [w['areas'].get(area, 0) for w in weekly_data]
        fig.add_trace(go.Bar(
            name=area,
            x=weeks,
            y=hours_per_week,
        ))
    
    fig.update_layout(
        title="Time by Area - Weekly Comparison",
        xaxis_title="Week",
        yaxis_title="Hours",
        barmode='stack',
        height=500,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
    )
    fig.write_html(output_dir / "weekly_areas_comparison.html")
    
    # Export comparison table
    comparison_data = []
    for w in weekly_data:
        row = {
            'Week': w['week'],
            'Date': w['start_date'].strftime('%Y-%m-%d'),
            'Total Hours': f"{w['total_hours']:.2f}",
        }
        # Add top 5 areas
        top_areas = sorted(w['areas'].items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (area, hours) in enumerate(top_areas, 1):
            row[f'Top{i}'] = f"{area}: {hours:.1f}h"
        comparison_data.append(row)
    
    df = pd.DataFrame(comparison_data)
    df.to_csv(output_dir / "weekly_comparison_summary.csv", index=False)
    print(f"\n{df.to_string(index=False)}")


def generate_weekly_reports(n=4, output_dir="reports/weekly"):
    """Generate individual weekly reports for the last N weeks."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"GENERATING LAST {n} WEEKLY REPORTS")
    print(f"{'='*80}\n")
    
    for i in range(n):
        # Calculate week dates (going backwards)
        today = datetime.today()
        week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=n-1-i)
        week_end = week_start + timedelta(days=7)
        
        week_num = week_start.isocalendar()[1]
        year = week_start.year
        period_name = f"Week_{week_num}_{year}"
        
        print(f"\nGenerating Week {week_num} ({week_start.date()} to {week_end.date()})...")
        
        # Load data
        clock_root = org_time.load_files(ORG_FILES, week_start, week_end)
        
        if clock_root.totalTime == 0:
            print(f"  No data for this week")
            continue
        
        # Analyze
        analyzer = TimeAnalyzer(clock_root)
        
        # Generate individual report
        report_gen = ReportGenerator(analyzer, period_name, week_start, week_end)
        week_dir = output_dir / period_name
        week_dir.mkdir(exist_ok=True)
        report_gen.generate_full_report(week_dir)
        
        print(f"  ✓ Report saved to: {week_dir}")
    
    print(f"\n{'='*80}")
    print(f"Weekly reports generated in: {output_dir}")
    print(f"{'='*80}\n")


def generate_monthly_report(year=None, month=None, output_dir="reports/monthly"):
    """Generate a monthly report."""
    if year is None or month is None:
        today = datetime.today()
        year = today.year
        month = today.month
    
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    period_name = f"{start_date.strftime('%Y-%m')}"
    output_dir = Path(output_dir) / period_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"GENERATING MONTHLY REPORT - {period_name}")
    print(f"{'='*80}\n")
    
    clock_root = org_time.load_files(ORG_FILES, start_date, end_date)
    
    if clock_root.totalTime == 0:
        print(f"No time tracked in {period_name}")
        return
    
    analyzer = TimeAnalyzer(clock_root)
    report_gen = ReportGenerator(analyzer, period_name, start_date, end_date)
    report_gen.generate_full_report(output_dir)
    
    print(f"\nMonthly report generated in: {output_dir}")


def generate_monthly_reports(n=12, output_dir="reports/monthly"):
    """Generate individual monthly reports for the last N months."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"GENERATING LAST {n} MONTHLY REPORTS")
    print(f"{'='*80}\n")
    
    today = datetime.today()
    
    for i in range(n):
        # Calculate month dates (going backwards)
        # Start from the first day of the current month, then go back
        year = today.year
        month = today.month
        
        # Go back i months
        for _ in range(n - 1 - i):
            month -= 1
            if month < 1:
                month = 12
                year -= 1
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        period_name = f"{start_date.strftime('%Y-%m')}"
        month_dir = output_dir / period_name
        month_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nGenerating {start_date.strftime('%B %Y')} ({period_name})...")
        
        # Load data
        clock_root = org_time.load_files(ORG_FILES, start_date, end_date)
        
        if clock_root.totalTime == 0:
            print(f"  No data for this month")
            continue
        
        # Analyze
        analyzer = TimeAnalyzer(clock_root)
        
        # Generate individual report
        report_gen = ReportGenerator(analyzer, period_name, start_date, end_date)
        report_gen.generate_full_report(month_dir)
        
        print(f"  ✓ Report saved to: {month_dir}")
    
    print(f"\n{'='*80}")
    print(f"Monthly reports generated in: {output_dir}")
    print(f"{'='*80}\n")


def generate_yearly_report(year=None, output_dir="reports/yearly"):
    """Generate a yearly report with monthly breakdown."""
    if year is None:
        year = datetime.today().year
    
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + 1, 1, 1)
    
    period_name = f"Year_{year}"
    output_dir = Path(output_dir) / period_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"GENERATING YEARLY REPORT - {year}")
    print(f"{'='*80}\n")
    
    # Overall year analysis
    clock_root = org_time.load_files(ORG_FILES, start_date, end_date)
    
    if clock_root.totalTime == 0:
        print(f"No time tracked in {year}")
        return
    
    analyzer = TimeAnalyzer(clock_root)
    report_gen = ReportGenerator(analyzer, period_name, start_date, end_date)
    report_gen.generate_full_report(output_dir)
    
    # Monthly breakdown
    print(f"\n\nGenerating monthly breakdown for {year}...")
    monthly_data = []
    
    for month in range(1, 13):
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, month + 1, 1)
        
        month_clock_root = org_time.load_files(ORG_FILES, month_start, month_end)
        
        if month_clock_root.totalTime > 0:
            month_analyzer = TimeAnalyzer(month_clock_root)
            monthly_data.append({
                'month': month,
                'month_name': month_start.strftime('%B'),
                'total_hours': month_clock_root.totalTime,
                'areas': month_analyzer.get_time_by_macro_area(),
            })
    
    # Create monthly trend visualization
    if monthly_data:
        months = [m['month_name'] for m in monthly_data]
        hours = [m['total_hours'] for m in monthly_data]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=months,
            y=hours,
            marker_color='teal',
            text=[f"{h:.0f}h" for h in hours],
            textposition='auto',
        ))
        fig.update_layout(
            title=f"Monthly Time Tracking - {year}",
            xaxis_title="Month",
            yaxis_title="Hours",
            height=400,
        )
        fig.write_html(output_dir / f"monthly_trend_{year}.html")
        
        # Stacked area chart by category
        all_areas = set()
        for m in monthly_data:
            all_areas.update(m['areas'].keys())
        
        fig = go.Figure()
        for area in sorted(all_areas):
            area_hours = [m['areas'].get(area, 0) for m in monthly_data]
            fig.add_trace(go.Bar(
                name=area,
                x=months,
                y=area_hours,
            ))
        
        fig.update_layout(
            title=f"Time by Area - Monthly Breakdown {year}",
            xaxis_title="Month",
            yaxis_title="Hours",
            barmode='stack',
            height=500,
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
        )
        fig.write_html(output_dir / f"monthly_areas_breakdown_{year}.html")
        
        # Export monthly summary
        monthly_df = pd.DataFrame([
            {
                'Month': m['month_name'],
                'Total Hours': f"{m['total_hours']:.2f}",
                'Top Area': max(m['areas'].items(), key=lambda x: x[1])[0] if m['areas'] else 'N/A',
                'Top Area Hours': f"{max(m['areas'].values()):.2f}" if m['areas'] else '0',
            }
            for m in monthly_data
        ])
        monthly_df.to_csv(output_dir / f"monthly_summary_{year}.csv", index=False)
        print(f"\n{monthly_df.to_string(index=False)}")
    
    print(f"\nYearly report generated in: {output_dir}")


def generate_custom_comparison(periods, output_dir="reports/custom_comparison"):
    """
    Generate comparison report for custom periods.
    
    periods: list of tuples (period_name, start_date, end_date)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    comparison_data = []
    
    for period_name, start_date, end_date in periods:
        print(f"\nLoading {period_name} ({start_date.date()} to {end_date.date()})...")
        
        clock_root = org_time.load_files(ORG_FILES, start_date, end_date)
        
        if clock_root.totalTime == 0:
            print(f"  No data for {period_name}")
            continue
        
        analyzer = TimeAnalyzer(clock_root)
        
        comparison_data.append({
            'period': period_name,
            'start': start_date,
            'end': end_date,
            'total_hours': clock_root.totalTime,
            'areas': analyzer.get_time_by_macro_area(),
            'topics': analyzer.get_time_by_topic(),
        })
    
    if not comparison_data:
        print("No data to compare")
        return
    
    # Create comparison visualizations
    periods = [c['period'] for c in comparison_data]
    total_hours = [c['total_hours'] for c in comparison_data]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=periods,
        y=total_hours,
        marker_color='coral',
        text=[f"{h:.1f}h" for h in total_hours],
        textposition='auto',
    ))
    fig.update_layout(
        title="Total Hours - Period Comparison",
        xaxis_title="Period",
        yaxis_title="Hours",
        height=400,
    )
    fig.write_html(output_dir / "period_comparison.html")
    
    print(f"\nComparison report generated in: {output_dir}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "weekly":
            # Generate last 4 weeks comparison
            n_weeks = int(sys.argv[2]) if len(sys.argv) > 2 else 4
            generate_last_n_weeks_comparison(n_weeks)
        
        elif command == "monthly":
            # Generate current month or specified month
            if len(sys.argv) > 3:
                year = int(sys.argv[2])
                month = int(sys.argv[3])
                generate_monthly_report(year, month)
            else:
                generate_monthly_report()
        
        elif command == "yearly":
            # Generate current year or specified year
            year = int(sys.argv[2]) if len(sys.argv) > 2 else None
            generate_yearly_report(year)
        
        elif command == "all":
            # Generate all reports
            print("Generating all reports...")
            generate_last_n_weeks_comparison(4)
            generate_monthly_report()
            generate_yearly_report()
        
        else:
            print(f"Unknown command: {command}")
            print("Usage: python generate_reports.py [weekly|monthly|yearly|all] [args...]")
    
    else:
        # Default: generate current week report
        print("Generating current week report...")
        generate_last_n_weeks_comparison(1)
