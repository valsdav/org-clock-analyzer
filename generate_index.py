#!/usr/bin/env python3
"""
Generate an index.html page for browsing reports.
Automatically scans the reports directory and creates a navigable interface.
"""

import os
from pathlib import Path
from datetime import datetime
import json
from datetime import datetime as _dt
from datetime import timedelta
from calendar_heatmap import generate_inline_calendar_for_period


def scan_reports_directory(reports_dir="reports"):
    """Scan the reports directory and organize files by type and period."""
    reports_path = Path(reports_dir)
    
    if not reports_path.exists():
        return None
    
    structure = {
        'weekly': [],
        'monthly': [],
        'yearly': [],
        'custom': [],
    }
    
    # Scan directory
    for item in reports_path.iterdir():
        if not item.is_dir():
            continue
        
        dir_name = item.name
        
        # Categorize directories
        if dir_name == 'weekly':
            # Scan weekly reports
            for week_dir in item.iterdir():
                if week_dir.is_dir():
                    files = list_report_files(week_dir, reports_path)
                    if files:
                        structure['weekly'].append({
                            'name': week_dir.name,
                            'path': str(week_dir.relative_to(reports_path)),
                            'files': files,
                        })
        
        elif dir_name == 'monthly':
            # Scan monthly reports
            for month_dir in item.iterdir():
                if month_dir.is_dir():
                    files = list_report_files(month_dir, reports_path)
                    if files:
                        structure['monthly'].append({
                            'name': month_dir.name,
                            'path': str(month_dir.relative_to(reports_path)),
                            'files': files,
                        })
        
        elif dir_name == 'yearly':
            # Scan yearly reports
            for year_dir in item.iterdir():
                if year_dir.is_dir():
                    files = list_report_files(year_dir, reports_path)
                    if files:
                        structure['yearly'].append({
                            'name': year_dir.name,
                            'path': str(year_dir.relative_to(reports_path)),
                            'files': files,
                        })
        
        else:
            # Custom reports
            files = list_report_files(item, reports_path)
            if files:
                structure['custom'].append({
                    'name': dir_name,
                    'path': str(item.relative_to(reports_path)),
                    'files': files,
                })
    
    # Sort reports by name (newest first for dates)
    structure['weekly'].sort(key=lambda x: x['name'], reverse=True)
    structure['monthly'].sort(key=lambda x: x['name'], reverse=True)
    structure['yearly'].sort(key=lambda x: x['name'], reverse=True)
    
    return structure


def list_report_files(directory, reports_base=None):
    """List all report files in a directory."""
    files = {
        'html': [],
        'csv': [],
    }
    
    # If reports_base is provided, make paths relative to it
    # Otherwise use just the filename (for same directory)
    
    for file in directory.iterdir():
        if file.is_file():
            # Create relative path from the reports base directory
            if reports_base:
                try:
                    rel_path = file.relative_to(reports_base)
                    path_str = str(rel_path)
                except ValueError:
                    # If file is not relative to reports_base, use name only
                    path_str = file.name
            else:
                path_str = file.name
            
            if file.suffix == '.html':
                files['html'].append({
                    'name': file.name,
                    'path': path_str,
                    'size': file.stat().st_size,
                    'modified': datetime.fromtimestamp(file.stat().st_mtime),
                })
            elif file.suffix == '.csv':
                files['csv'].append({
                    'name': file.name,
                    'path': path_str,
                    'size': file.stat().st_size,
                    'modified': datetime.fromtimestamp(file.stat().st_mtime),
                })
    
    files['html'].sort(key=lambda x: x['name'])
    files['csv'].sort(key=lambda x: x['name'])
    
    return files


def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def generate_index_html(output_file="reports/index.html", reports_dir="reports"):
    """Generate the index.html file."""
    reports_path = Path(reports_dir)
    structure = scan_reports_directory(reports_dir)
    
    if structure is None:
        print(f"Reports directory '{reports_dir}' not found.")
        return
    
    # Count total reports
    total_html = sum(
        len(report['files']['html']) 
        for category in structure.values() 
        for report in category
    )
    total_csv = sum(
        len(report['files']['csv']) 
        for category in structure.values() 
        for report in category
    )
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Org Clock Analyzer - Reports Index</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        h1 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        
        .subtitle {{
            color: #666;
            font-size: 1.1em;
            margin-bottom: 20px;
        }}
        
        .stats {{
            display: flex;
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            flex: 1;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .section-title {{
            color: #333;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}

        /* Tabs */
        .tabs {{ margin-top: 10px; }}
        .tab-buttons {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }}
        .tab-buttons button {{
            border: 1px solid #dfe3ea;
            background: #f5f7fb;
            color: #444;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
        }}
        .tab-buttons button.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
            box-shadow: 0 2px 6px rgba(102,126,234,0.35);
        }}
        .tab-panel {{ display: none; }}
        .tab-panel.active {{ display: block; }}
        
        .year-calendar-row {{
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .year-calendar-row:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }}
        
        .year-calendar-row h3 {{
            margin-bottom: 15px;
            color: #667eea;
            font-size: 1.4em;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .year-calendar-row h3::before {{
            content: "📅";
            font-size: 1.2em;
        }}
        
        .report-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .report-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #667eea;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .report-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}

        .card-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr; /* equal columns as requested */
            gap: 16px;
            align-items: start;
        }}
        .card-left {{ min-width: 0; }}
        .card-right {{ min-width: 0; }}
        
        .report-card-title {{
            font-size: 1.2em;
            color: #333;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        
        .dashboard-btn {{
            display: block;
            width: 100%;
            padding: 15px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 1.1em;
            font-weight: 600;
            text-align: center;
            margin-bottom: 15px;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 10px rgba(102, 126, 234, 0.3);
        }}
        
        .dashboard-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(102, 126, 234, 0.4);
        }}
        
        .dashboard-btn .icon {{
            font-size: 1.3em;
            margin-right: 10px;
        }}
        
        .collapsible {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            margin-top: 10px;
            overflow: hidden;
        }}
        
        .collapsible-header {{
            padding: 12px 15px;
            background: #f8f9fa;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
            color: #555;
            user-select: none;
            transition: background 0.2s;
        }}
        
        .collapsible-header:hover {{
            background: #e9ecef;
        }}
        
        .collapsible-header .toggle {{
            transition: transform 0.3s;
            font-size: 0.8em;
        }}
        
        .collapsible-header.active .toggle {{
            transform: rotate(180deg);
        }}
        
        .collapsible-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background: white;
        }}
        
        .collapsible-content.active {{
            max-height: 2000px;
            transition: max-height 0.5s ease-in;
        }}
        
        .collapsible-body {{
            padding: 15px;
        }}
        
        .file-link {{
            display: block;
            padding: 8px 12px;
            margin-bottom: 5px;
            background: #f8f9fa;
            border-radius: 4px;
            text-decoration: none;
            color: #333;
            transition: background 0.2s;
            font-size: 0.9em;
        }}
        
        .file-link:hover {{
            background: #667eea;
            color: white;
        }}
        
        .file-link-html {{
            border-left: 3px solid #28a745;
        }}
        
        .file-link-csv {{
            border-left: 3px solid #ffc107;
        }}
        
        .file-meta {{
            font-size: 0.8em;
            opacity: 0.7;
            margin-left: 10px;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
        
        .empty-state-icon {{
            font-size: 3em;
            margin-bottom: 10px;
        }}
        
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding: 20px;
            opacity: 0.8;
        }}
        
        .icon {{
            margin-right: 8px;
        }}
        
        @media (max-width: 768px) {{
            .report-grid {{
                grid-template-columns: 1fr;
            }}
            
            .stats {{
                flex-direction: column;
            }}
            .card-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Org Clock Analyzer</h1>
            <div class="subtitle">Time Tracking Reports Browser</div>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{total_html}</div>
                    <div class="stat-label">HTML Reports</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_csv}</div>
                    <div class="stat-label">CSV Exports</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{sum(len(cat) for cat in structure.values())}</div>
                    <div class="stat-label">Report Periods</div>
                </div>
            </div>
        </div>
"""
    # Add calendar section with one row per year
    try:
        # Collect all years from reports
        years_set = set()
        
        if structure['monthly']:
            for r in structure['monthly']:
                try:
                    y, m = map(int, r['name'].split('-'))
                    years_set.add(y)
                except Exception:
                    pass
        
        if structure['yearly']:
            for r in structure['yearly']:
                nm = r['name']
                if nm.lower().startswith('year_'):
                    try:
                        years_set.add(int(nm.split('_', 1)[1]))
                    except Exception:
                        pass
                else:
                    try:
                        years_set.add(int(nm))
                    except Exception:
                        pass
        
        if structure['weekly']:
            for r in structure['weekly']:
                nm = r['name']  # Week_NN_YYYY
                try:
                    parts = nm.split('_')
                    years_set.add(int(parts[-1]))
                except Exception:
                    pass
        
        # Generate calendar section with one row per year
        if years_set:
            years_sorted = sorted(years_set, reverse=True)  # Most recent first
            
            html_content += """
        <div class="section">
            <h2 class="section-title">🗓️ Activity Calendar by Year</h2>
"""
            
            for year in years_sorted:
                try:
                    year_start = _dt(year, 1, 1)
                    year_end = _dt(year + 1, 1, 1)
                    
                    cal_snippet = generate_inline_calendar_for_period(
                        year_start, year_end,
                        files=None,
                        cell_size=12, gap=2,
                        enable_click=True,
                        id_suffix=f'year_{year}',
                        weekly_link_prefix_to_weekly='weekly/',
                        include_month_summary=True,
                        monthly_link_prefix_to_monthly='monthly/'
                    )
                    
                    html_content += f"""
            <div class="year-calendar-row">
                <h3>{year}</h3>
                <div style="overflow-x:auto;">{cal_snippet}</div>
            </div>
"""
                except Exception as e:
                    print(f"Warning: Failed to generate calendar for year {year}: {e}")
            
            html_content += """
        </div>
"""
    except Exception as e:
        print(f"Warning: Failed to generate calendar section: {e}")
    
    # Weekly Reports Section (grouped by year with month tabs)
    # Detect consolidated pages
    consolidated_weekly_global = reports_path / "weekly_consolidated.html"
    consolidated_weekly_year = {y: (reports_path / f"weekly_consolidated_{y}.html") for y in range(1900, 3000)}
    consolidated_weekly_month = lambda y,m: (reports_path / f"weekly_consolidated_{y}-{m:02d}.html")

    if structure['weekly'] or consolidated_weekly_global.exists():
        html_content += """
        <div class="section">
            <h2 class="section-title">📅 Weekly Reports</h2>
"""
        # Global weekly comparison
        if consolidated_weekly_global.exists():
            html_content += f"""
            <div style="margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px;">
                <a href="weekly_consolidated.html" style="color: white; text-decoration: none; display: flex; align-items: center; justify-content: space-between;" target="_blank">
                    <div>
                        <div style="font-size: 1.3em; font-weight: bold; margin-bottom: 5px;">📊 Weekly Comparison (All)</div>
                        <div style="opacity: 0.9;">All recent weeks in one page</div>
                    </div>
                    <div style="font-size: 1.5em;">→</div>
                </a>
            </div>
"""

        # Group weeks by year and month
        weekly_grouped = {}
        for report in structure['weekly']:
            nm = report['name']  # Week_NN_YYYY
            try:
                parts = nm.split('_')
                wk = int(parts[1]); yr = int(parts[2])
                wk_start = datetime.fromisocalendar(yr, wk, 1)
                mon = wk_start.month
            except Exception:
                continue
            weekly_grouped.setdefault(yr, {}).setdefault(mon, []).append((report, wk_start))

        for yr in sorted(weekly_grouped.keys(), reverse=True):
            # Year header with consolidated button if available
            yr_cons = reports_path / f"weekly_consolidated_{yr}.html"
            yr_btn = f"<a href='weekly_consolidated_{yr}.html' class='dashboard-btn' target='_blank'><span class='icon'>📊</span>Weekly Comparison {yr}</a>" if yr_cons.exists() else ""
            html_content += f"""
            <div style="display:flex; align-items:center; justify-content:space-between; margin: 12px 0 6px 0;">
                <h3 style="color:#333;">Year {yr}</h3>
                <div style="min-width:260px;">{yr_btn}</div>
            </div>
            <div class="tabs" id="weekly-tabs-{yr}">
                <div class="tab-buttons">
"""
            months = sorted(weekly_grouped[yr].keys())
            for i, m in enumerate(months):
                label = _dt(yr, m, 1).strftime('%b')
                active = 'active' if i == 0 else ''
                html_content += f"<button class='tab-button {active}' onclick=\"showTab('weekly-tabs-{yr}','weekly-{yr}-{m}')\">{label}</button>"
            html_content += "</div>"

            # Panels per month
            for i, m in enumerate(months):
                panel_active = 'active' if i == 0 else ''
                html_content += f"<div class='tab-panel {panel_active}' id='weekly-{yr}-{m}'>"

                # Month consolidated button if present
                mon_cons = reports_path / f"weekly_consolidated_{yr}-{m:02d}.html"
                if mon_cons.exists():
                    html_content += f"""
                    <div style="margin: 10px 0 16px 0;">
                        <a href="weekly_consolidated_{yr}-{m:02d}.html" class="dashboard-btn" target="_blank">
                            <span class="icon">📊</span>Weekly Comparison {yr}-{m:02d}
                        </a>
                    </div>
"""
                # Cards grid for that month
                html_content += "<div class='report-grid'>"
                # Sort weeks within month by start date descending
                for (report, wk_start) in sorted(weekly_grouped[yr][m], key=lambda t: t[1], reverse=True):
                    # Build card (reuse previous pattern)
                    dashboard_file = None
                    other_html = []
                    for file in report['files']['html']:
                        if 'dashboard' in file['name'].lower():
                            dashboard_file = file
                        else:
                            other_html.append(file)
                    nm = report['name']
                    parts = nm.split('_')
                    week_num = int(parts[1]); year_val = int(parts[2])
                    week_start = wk_start
                    week_end = week_start + timedelta(days=7)
                    html_content += f"""
                    <div class="report-card">
                        <div class="report-card-title">{report['name']}</div>
                        <div class="card-grid">
                            <div class="card-left">
                    """
                    try:
                        cal_snippet = generate_inline_calendar_for_period(
                            week_start, week_end, files=None, cell_size=14, gap=2,
                            enable_click=True, id_suffix=f"wk_{week_num}_{year_val}",
                            weekly_link_prefix_to_weekly='weekly/',
                            include_month_summary=True,
                            monthly_link_prefix_to_monthly='monthly/'
                        )
                        html_content += f"<div style=\"margin-bottom:10px; overflow-x:auto;\">{cal_snippet}</div>"
                    except Exception:
                        pass
                    html_content += """
                            </div>
                            <div class="card-right">
                    """
                    if dashboard_file:
                        html_content += f"""
                                <a href="{dashboard_file['path']}" class="dashboard-btn" target="_blank">
                                    <span class="icon">📊</span>View Dashboard
                                </a>
                        """
                    # Other visuals
                    if other_html:
                        html_content += """
                                <div class="collapsible">
                                    <div class="collapsible-header" onclick="toggleCollapsible(this)">
                                        <span>📈 Other Visualizations</span>
                                        <span class="toggle">▼</span>
                                    </div>
                                    <div class="collapsible-content">
                                        <div class="collapsible-body">
                        """
                        for file in other_html:
                            html_content += f"""
                                                <a href="{file['path']}" class="file-link file-link-html" target="_blank">
                                                    <span class="icon">📊</span>{file['name']}
                                                    <span class="file-meta">{format_file_size(file['size'])}</span>
                                                </a>
                            """
                        html_content += """
                                        </div>
                                    </div>
                                </div>
                        """
                    # CSVs
                    if report['files']['csv']:
                        html_content += """
                                <div class="collapsible">
                                    <div class="collapsible-header" onclick="toggleCollapsible(this)">
                                        <span>📄 Data Exports</span>
                                        <span class="toggle">▼</span>
                                    </div>
                                    <div class="collapsible-content">
                                        <div class="collapsible-body">
                        """
                        for file in report['files']['csv']:
                            html_content += f"""
                                                <a href="{file['path']}" class="file-link file-link-csv" download>
                                                    <span class="icon">📋</span>{file['name']}
                                                    <span class="file-meta">{format_file_size(file['size'])}</span>
                                                </a>
                            """
                        html_content += """
                                        </div>
                                    </div>
                                </div>
                        """
                    html_content += """
                            </div>
                        </div>
                    </div>
                    """
                html_content += "</div>"  # report-grid
                html_content += "</div>"  # tab-panel

            html_content += "</div>"  # tabs
        html_content += "</div>"  # section
    
    # Monthly Reports Section (grouped by year with comparison button)
    consolidated_monthly_global = reports_path / "monthly_consolidated.html"
    if structure['monthly'] or consolidated_monthly_global.exists():
        html_content += """
        <div class="section">
            <h2 class="section-title">📆 Monthly Reports</h2>
        """
        if consolidated_monthly_global.exists():
            html_content += f"""
            <div style="margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 8px;">
                <a href="monthly_consolidated.html" style="color: white; text-decoration: none; display: flex; align-items: center; justify-content: space-between;" target="_blank">
                    <div>
                        <div style="font-size: 1.3em; font-weight: bold; margin-bottom: 5px;">📅 Monthly Comparison (Recent)</div>
                        <div style="opacity: 0.9;">Recent months in a single dashboard</div>
                    </div>
                    <div style="font-size: 1.5em;">→</div>
                </a>
            </div>
            """

        # Group months by year
        monthly_grouped = {}
        for report in structure['monthly']:
            try:
                y, m = map(int, report['name'].split('-'))
            except Exception:
                continue
            monthly_grouped.setdefault(y, []).append(report)

        for yr in sorted(monthly_grouped.keys(), reverse=True):
            yr_cons = reports_path / f"monthly_consolidated_{yr}.html"
            yr_btn = f"<a href='monthly_consolidated_{yr}.html' class='dashboard-btn' target='_blank'><span class='icon'>📅</span>Monthly Comparison {yr}</a>" if yr_cons.exists() else ""
            html_content += f"""
            <div style=\"display:flex; align-items:center; justify-content:space-between; margin: 12px 0 6px 0;\"> 
                <h3 style=\"color:#333;\">Year {yr}</h3>
                <div style=\"min-width:260px;\">{yr_btn}</div>
            </div>
            <div class='report-grid'>
            """
            for report in sorted(monthly_grouped[yr], key=lambda r: r['name'], reverse=True):
                dashboard_file = None
                other_html = []
                for file in report['files']['html']:
                    if 'dashboard' in file['name'].lower():
                        dashboard_file = file
                    else:
                        other_html.append(file)
                html_content += f"""
                <div class=\"report-card\">
                    <div class=\"report-card-title\">{report['name']}</div>
                    <div class=\"card-grid\">
                        <div class=\"card-left\">
                """
                try:
                    year, month = map(int, report['name'].split('-'))
                    start = _dt(year, month, 1)
                    end = _dt(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
                    cal_snippet = generate_inline_calendar_for_period(
                        start, end, files=None, cell_size=14, gap=2,
                        enable_click=True,
                        weekly_link_prefix_to_weekly='weekly/',
                        include_month_summary=True,
                        monthly_link_prefix_to_monthly='monthly/'
                    )
                    html_content += f"<div style=\\\"margin-bottom:10px; overflow-x:auto;\\\">{cal_snippet}</div>"
                except Exception:
                    pass
                html_content += """
                        </div>
                        <div class=\"card-right\">
                """
                if dashboard_file:
                    html_content += f"""
                            <a href=\"{dashboard_file['path']}\" class=\"dashboard-btn\" target=\"_blank\">
                                <span class=\"icon\">📊</span>View Dashboard
                            </a>
                    """
                if other_html:
                    html_content += """
                            <div class=\"collapsible\">
                                <div class=\"collapsible-header\" onclick=\"toggleCollapsible(this)\"> 
                                    <span>📈 Other Visualizations</span>
                                    <span class=\"toggle\">▼</span>
                                </div>
                                <div class=\"collapsible-content\">
                                    <div class=\"collapsible-body\">
                    """
                    for file in other_html:
                        html_content += f"""
                                            <a href=\"{file['path']}\" class=\"file-link file-link-html\" target=\"_blank\">
                                                <span class=\"icon\">📊</span>{file['name']}
                                                <span class=\"file-meta\">{format_file_size(file['size'])}</span>
                                            </a>
                        """
                    html_content += """
                                    </div>
                                </div>
                            </div>
                    """
                if report['files']['csv']:
                    html_content += """
                            <div class=\"collapsible\">
                                <div class=\"collapsible-header\" onclick=\"toggleCollapsible(this)\">
                                    <span>📄 Data Exports</span>
                                    <span class=\"toggle\">▼</span>
                                </div>
                                <div class=\"collapsible-content\">
                                    <div class=\"collapsible-body\">
                    """
                    for file in report['files']['csv']:
                        html_content += f"""
                                            <a href=\"{file['path']}\" class=\"file-link file-link-csv\" download>
                                                <span class=\"icon\">📋</span>{file['name']}
                                                <span class=\"file-meta\">{format_file_size(file['size'])}</span>
                                            </a>
                        """
                    html_content += """
                                    </div>
                                </div>
                            </div>
                    """
                html_content += """
                        </div>
                    </div>
                </div>
                """
            html_content += "</div>"  # report-grid
        html_content += "</div>"  # section
    
    # Custom Reports Section
    if structure['custom']:
        html_content += """
        <div class="section">
            <h2 class="section-title">🔧 Custom Reports</h2>
            <div class="report-grid">
"""
        for report in structure['custom']:
            # Find dashboard file
            dashboard_file = None
            other_html = []
            for file in report['files']['html']:
                if 'dashboard' in file['name'].lower():
                    dashboard_file = file
                else:
                    other_html.append(file)
            
            html_content += f"""
                <div class="report-card">
                    <div class="report-card-title">{report['name']}</div>
"""
            
            # Dashboard button
            if dashboard_file:
                html_content += f"""
                    <a href="{dashboard_file['path']}" class="dashboard-btn" target="_blank">
                        <span class="icon">📊</span>View Dashboard
                    </a>
"""
            
            # Collapsible for other HTML reports
            if other_html:
                html_content += """
                    <div class="collapsible">
                        <div class="collapsible-header" onclick="toggleCollapsible(this)">
                            <span>📈 Other Visualizations</span>
                            <span class="toggle">▼</span>
                        </div>
                        <div class="collapsible-content">
                            <div class="collapsible-body">
"""
                for file in other_html:
                    html_content += f"""
                                <a href="{file['path']}" class="file-link file-link-html" target="_blank">
                                    <span class="icon">📊</span>{file['name']}
                                    <span class="file-meta">{format_file_size(file['size'])}</span>
                                </a>
"""
                html_content += """
                            </div>
                        </div>
                    </div>
"""
            
            # Collapsible for CSV files
            if report['files']['csv']:
                html_content += """
                    <div class="collapsible">
                        <div class="collapsible-header" onclick="toggleCollapsible(this)">
                            <span>📄 Data Exports</span>
                            <span class="toggle">▼</span>
                        </div>
                        <div class="collapsible-content">
                            <div class="collapsible-body">
"""
                for file in report['files']['csv']:
                    html_content += f"""
                                <a href="{file['path']}" class="file-link file-link-csv" download>
                                    <span class="icon">📋</span>{file['name']}
                                    <span class="file-meta">{format_file_size(file['size'])}</span>
                                </a>
"""
                html_content += """
                            </div>
                        </div>
                    </div>
"""
            
            html_content += """
                </div>
"""
        
        html_content += """
            </div>
        </div>
"""
    
    # Empty state if no reports
    if not any(structure.values()):
        html_content += """
        <div class="section">
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <h2>No Reports Found</h2>
                <p>Generate some reports first using the reporting tools!</p>
                <p style="margin-top: 20px; color: #667eea;">
                    Try: <code>python quick_reports.py</code>
                </p>
            </div>
        </div>
"""
    
    html_content += f"""
        <div class="footer">
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Org Clock Analyzer Reports Browser</p>
        </div>
    </div>
    
    <script>
        function toggleCollapsible(header) {{
            const content = header.nextElementSibling;
            header.classList.toggle('active');
            content.classList.toggle('active');
        }}
        function showTab(groupId, panelId) {{
            const group = document.getElementById(groupId);
            if (!group) return;
            const buttons = group.querySelectorAll('.tab-buttons .tab-button');
            const panels = group.querySelectorAll('.tab-panel');
            buttons.forEach(btn => btn.classList.remove('active'));
            panels.forEach(p => p.classList.remove('active'));
            // Activate clicked button (by matching its onclick arg)
            const targetBtn = Array.from(buttons).find(b => (b.getAttribute('onclick')||'').includes(panelId));
            if (targetBtn) targetBtn.classList.add('active');
            const panel = document.getElementById(panelId);
            if (panel) panel.classList.add('active');
        }}
    </script>
</body>
</html>
"""
    
    # Write the file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✓ Index page generated: {output_path.absolute()}")
    print(f"  Found {total_html} HTML reports and {total_csv} CSV files")
    return str(output_path.absolute())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate index.html for browsing reports')
    parser.add_argument('-o', '--output', default='reports/index.html', 
                       help='Output file path (default: reports/index.html)')
    parser.add_argument('-d', '--reports-dir', default='reports',
                       help='Reports directory to scan (default: reports)')
    
    args = parser.parse_args()
    
    index_path = generate_index_html(args.output, args.reports_dir)
    
    print(f"\n📂 Open in browser: file://{index_path}")
