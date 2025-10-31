#!/usr/bin/env python3
"""
Generate a consolidated monthly report page showing multiple months in one view.
"""

from pathlib import Path
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

import org_time
from reports import TimeAnalyzer, ORG_FILES
from calendar_heatmap import generate_inline_calendar_for_period


def generate_consolidated_monthly_report(n_months=6, output_file="reports/monthly_consolidated.html", year=None):
    """Generate a single HTML page with all monthly reports."""
    
    print(f"\n{'='*80}")
    print(f"GENERATING CONSOLIDATED MONTHLY REPORT - LAST {n_months} MONTHS")
    print(f"{'='*80}\n")
    
    monthly_data = []
    
    # Determine starting point
    if year:
        # Start from January of specified year
        current_date = datetime(year, 1, 1)
        n_months = 12  # Override to show full year
    else:
        # Start from n_months ago
        current_date = datetime.today().replace(day=1)
        current_date = current_date - relativedelta(months=n_months - 1)
    
    # Collect data for all months
    for i in range(n_months):
        month_start = current_date + relativedelta(months=i)
        month_end = month_start + relativedelta(months=1)
        
        # Don't go into the future
        if month_start > datetime.today():
            break
        
        month_name = month_start.strftime('%B %Y')
        month_short = month_start.strftime('%b %Y')
        
        print(f"Loading {month_name} ({month_start.date()} to {month_end.date()})...")
        
        # Load data
        clock_root = org_time.load_files(ORG_FILES, month_start, month_end)
        
        if clock_root.totalTime == 0:
            print(f"  No data for this month")
            monthly_data.append({
                'year': month_start.year,
                'month': month_start.month,
                'month_name': month_name,
                'month_short': month_short,
                'start_date': month_start,
                'end_date': month_end,
                'total_hours': 0,
                'areas': {},
                'topics': {},
                'subtasks': {},
                'tags': {},
                'analyzer': None,
            })
            continue
        
        # Analyze
        analyzer = TimeAnalyzer(clock_root)
        
        # Calculate days in month
        days_in_month = (month_end - month_start).days
        avg_per_day = clock_root.totalTime / days_in_month if days_in_month > 0 else 0
        
        monthly_data.append({
            'year': month_start.year,
            'month': month_start.month,
            'month_name': month_name,
            'month_short': month_short,
            'start_date': month_start,
            'end_date': month_end,
            'total_hours': clock_root.totalTime,
            'days_in_month': days_in_month,
            'avg_per_day': avg_per_day,
            'areas': analyzer.get_time_by_macro_area(),
            'topics': analyzer.get_time_by_topic(),
            'subtasks': analyzer.get_time_by_subtask(),
            'tags': analyzer.get_time_by_tags(),
            'analyzer': analyzer,
        })
        
        print(f"  Total: {clock_root.totalTime:.2f} hours ({avg_per_day:.2f}h/day avg)")
    
    # Generate HTML
    html_content = generate_monthly_html(monthly_data, n_months, year, output_file)
    
    # Write file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✓ Consolidated monthly report generated: {output_path.absolute()}")
    print(f"📂 Open in browser: file://{output_path.absolute()}")
    
    return str(output_path.absolute())


def generate_monthly_html(monthly_data, n_months, year=None, output_file=None):
    """Generate the HTML content for consolidated monthly report."""
    # Compute relative link to reports/index.html based on output location
    try:
        output_dir = Path(output_file).parent if output_file else Path('reports')
        rel_index_link = os.path.relpath(Path('reports/index.html'), output_dir)
    except Exception:
        rel_index_link = 'index.html'
    
    # Create overview chart - total hours trend
    months = [m['month_short'] for m in monthly_data]
    total_hours = [m['total_hours'] for m in monthly_data]
    avg_per_day = [m.get('avg_per_day', 0) for m in monthly_data]
    
    # Overview figure with dual axis
    fig_overview = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig_overview.add_trace(
        go.Bar(
            x=months,
            y=total_hours,
            name='Total Hours',
            marker_color='#667eea',
            text=[f"{h:.0f}h" for h in total_hours],
            textposition='outside',
        ),
        secondary_y=False,
    )
    
    fig_overview.add_trace(
        go.Scatter(
            x=months,
            y=avg_per_day,
            name='Avg/Day',
            mode='lines+markers',
            line=dict(color='#ff6b6b', width=3),
            marker=dict(size=8),
            text=[f"{a:.1f}h" for a in avg_per_day],
            hovertemplate='%{text}/day<extra></extra>',
        ),
        secondary_y=True,
    )
    
    fig_overview.update_layout(
        title=f"Total Hours & Daily Average - Last {n_months} Months" if not year else f"Monthly Overview - {year}",
        xaxis_title="Month",
        height=350,
        margin=dict(t=60, b=50, l=50, r=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig_overview.update_yaxes(title_text="Total Hours", secondary_y=False)
    fig_overview.update_yaxes(title_text="Average Hours/Day", secondary_y=True)
    
    overview_html = fig_overview.to_html(include_plotlyjs='cdn', div_id='overview-chart')
    
    # Create line chart by macro area
    all_areas = set()
    for m in monthly_data:
        all_areas.update(m['areas'].keys())
    
    fig_areas = go.Figure()
    
    # Define a color palette for different areas
    colors = ['#667eea', '#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', 
              '#f0932b', '#eb4d4b', '#6ab04c', '#c44569', '#574b90',
              '#f8b500', '#00a8cc', '#9980fa', '#ff6348', '#26de81']
    
    for idx, area in enumerate(sorted(all_areas)):
        area_hours = [m['areas'].get(area, 0) for m in monthly_data]
        # Calculate percentages for each month
        area_percentages = []
        for i, m in enumerate(monthly_data):
            total = sum(m['areas'].values())
            if total > 0:
                area_percentages.append((m['areas'].get(area, 0) / total) * 100)
            else:
                area_percentages.append(0)
        
        color = colors[idx % len(colors)]
        fig_areas.add_trace(go.Scatter(
            name=area,
            x=months,
            y=area_hours,
            mode='lines+markers',
            line=dict(width=3, color=color),
            marker=dict(size=8, color=color),
            hovertemplate=f'{area}: %{{y:.1f}}h<extra></extra>',
            customdata=area_percentages,  # Store percentages for toggle
        ))
    
    fig_areas.update_layout(
        title=f"Time by Macro Area - Monthly Trends",
        xaxis_title="Month",
        yaxis_title="Hours",
        height=500,
        margin=dict(t=60, b=50, l=50, r=50),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    areas_html = fig_areas.to_html(include_plotlyjs=False, div_id='areas-chart')
    
    # Create line chart for top 15 topics
    all_topics = set()
    for m in monthly_data:
        all_topics.update(m['topics'].keys())
    
    # Get top 15 topics overall
    topic_totals = {}
    for m in monthly_data:
        for topic, hours in m['topics'].items():
            topic_totals[topic] = topic_totals.get(topic, 0) + hours
    
    top_topics = sorted(topic_totals.items(), key=lambda x: x[1], reverse=True)[:15]
    top_topic_names = [t[0] for t in top_topics]
    
    fig_topics = go.Figure()
    
    # Use same color palette as areas
    for idx, topic in enumerate(top_topic_names):
        topic_hours = [m['topics'].get(topic, 0) for m in monthly_data]
        # Calculate percentages for each month
        topic_percentages = []
        for i, m in enumerate(monthly_data):
            total = sum(m['topics'].values())
            if total > 0:
                topic_percentages.append((m['topics'].get(topic, 0) / total) * 100)
            else:
                topic_percentages.append(0)
        
        color = colors[idx % len(colors)]
        fig_topics.add_trace(go.Scatter(
            name=topic,
            x=months,
            y=topic_hours,
            mode='lines+markers',
            line=dict(width=2.5, color=color),
            marker=dict(size=7, color=color),
            hovertemplate=f'{topic}: %{{y:.1f}}h<extra></extra>',
            customdata=topic_percentages,  # Store percentages for toggle
        ))
    
    fig_topics.update_layout(
        title=f"Top 15 Topics - Monthly Trends",
        xaxis_title="Month",
        yaxis_title="Hours",
        height=550,
        margin=dict(t=60, b=50, l=50, r=50),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    topics_html = fig_topics.to_html(include_plotlyjs=False, div_id='topics-chart')
    
    # Create line chart for top 15 subtasks
    all_subtasks = set()
    for m in monthly_data:
        all_subtasks.update(m['subtasks'].keys())
    
    # Get top 15 subtasks overall
    subtask_totals = {}
    for m in monthly_data:
        for subtask, hours in m['subtasks'].items():
            subtask_totals[subtask] = subtask_totals.get(subtask, 0) + hours
    
    top_subtasks = sorted(subtask_totals.items(), key=lambda x: x[1], reverse=True)[:15]
    top_subtask_names = [t[0] for t in top_subtasks]
    
    fig_subtasks = go.Figure()
    
    # Use same color palette
    for idx, subtask in enumerate(top_subtask_names):
        subtask_hours = [m['subtasks'].get(subtask, 0) for m in monthly_data]
        # Calculate percentages for each month
        subtask_percentages = []
        for i, m in enumerate(monthly_data):
            total = sum(m['subtasks'].values())
            if total > 0:
                subtask_percentages.append((m['subtasks'].get(subtask, 0) / total) * 100)
            else:
                subtask_percentages.append(0)
        
        color = colors[idx % len(colors)]
        fig_subtasks.add_trace(go.Scatter(
            name=subtask,
            x=months,
            y=subtask_hours,
            mode='lines+markers',
            line=dict(width=2.5, color=color),
            marker=dict(size=7, color=color),
            hovertemplate=f'{subtask}: %{{y:.1f}}h<extra></extra>',
            customdata=subtask_percentages,  # Store percentages for toggle
        ))
    
    fig_subtasks.update_layout(
        title=f"Top 15 Subtasks - Monthly Trends",
        xaxis_title="Month",
        yaxis_title="Hours",
        height=550,
        margin=dict(t=60, b=50, l=50, r=50),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    subtasks_html = fig_subtasks.to_html(include_plotlyjs=False, div_id='subtasks-chart')
    
    # Create comparison heatmap for top topics across months (keeping original heatmap)
    heatmap_data = []
    for topic in top_topic_names:
        row = [m['topics'].get(topic, 0) for m in monthly_data]
        heatmap_data.append(row)
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=months,
        y=top_topic_names,
        colorscale='Viridis',
        hoverongaps=False,
        hovertemplate='%{y}<br>%{x}: %{z:.1f}h<extra></extra>',
    ))
    
    fig_heatmap.update_layout(
        title="Top 15 Topics - Monthly Heatmap",
        xaxis_title="Month",
        yaxis_title="Topic",
        height=500,
        margin=dict(t=60, b=50, l=250, r=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    heatmap_html = fig_heatmap.to_html(include_plotlyjs=False, div_id='heatmap-chart')
    
    # Calculate summary statistics
    total_all_months = sum(total_hours)
    avg_monthly = total_all_months / len([m for m in monthly_data if m['total_hours'] > 0]) if monthly_data else 0
    max_month = max(monthly_data, key=lambda x: x['total_hours']) if monthly_data else None
    min_month = min([m for m in monthly_data if m['total_hours'] > 0], key=lambda x: x['total_hours']) if any(m['total_hours'] > 0 for m in monthly_data) else None
    
    # Start HTML
    title = f"Monthly Reports - Last {n_months} Months" if not year else f"Monthly Reports - {year}"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
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
            max-width: 1600px;
            margin: 0 auto;
        }}
        
            .nav-bar {{
                background: white;
                border-radius: 12px;
                padding: 15px 30px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                gap: 20px;
            }}
        
            .nav-bar a {{
                color: #667eea;
                text-decoration: none;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: color 0.3s;
            }}
        
            .nav-bar a:hover {{
                color: #764ba2;
            }}
        
            .nav-bar .nav-title {{
                color: #333;
                font-size: 0.9em;
                margin-left: auto;
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
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .stat-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
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
        
        .month-section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            border-left: 5px solid #667eea;
        }}
        
        .month-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        .month-title {{
            font-size: 1.8em;
            color: #333;
            font-weight: 600;
        }}
        
        .month-stats {{
            text-align: right;
        }}
        
        .month-total {{
            font-size: 1.5em;
            color: #f093fb;
            font-weight: bold;
        }}
        
        .month-avg {{
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #f093fb;
        }}
        
        .stat-card h3 {{
            color: #f093fb;
            font-size: 1em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .stat-list {{
            list-style: none;
        }}
        
        .stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .stat-item:last-child {{
            border-bottom: none;
        }}
        
        .stat-name {{
            color: #333;
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-right: 10px;
        }}
        
        .stat-value {{
            color: #f093fb;
            font-weight: 600;
            white-space: nowrap;
        }}
        
        .chart-container {{
            margin: 20px 0;
        }}
        
        .empty-month {{
            text-align: center;
            padding: 40px;
            color: #999;
            font-style: italic;
        }}
        
        .comparison-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .comparison-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .comparison-card h4 {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        
        .comparison-card .value {{
            font-size: 1.8em;
            font-weight: bold;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            padding: 20px;
            opacity: 0.8;
        }}
        
        /* Toggle Switch Styles */
        .toggle-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            margin: 20px 0;
            padding: 15px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .toggle-label {{
            font-size: 1em;
            color: #333;
            font-weight: 500;
        }}
        
        .toggle-switch {{
            position: relative;
            display: inline-block;
            width: 60px;
            height: 30px;
        }}
        
        .toggle-switch input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}
        
        .slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #667eea;
            transition: 0.4s;
            border-radius: 30px;
        }}
        
        .slider:before {{
            position: absolute;
            content: "";
            height: 22px;
            width: 22px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: 0.4s;
            border-radius: 50%;
        }}
        
        input:checked + .slider {{
            background-color: #f093fb;
        }}
        
        input:checked + .slider:before {{
            transform: translateX(30px);
        }}
        
        .slider:hover {{
            box-shadow: 0 0 8px rgba(102, 126, 234, 0.5);
        }}
        
        input:checked + .slider:hover {{
            box-shadow: 0 0 8px rgba(240, 147, 251, 0.5);
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            
            .month-section {{
                page-break-inside: avoid;
                break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="nav-bar">
            <a href="{rel_index_link}">← Back to Index</a>
            <span class="nav-title">Monthly Consolidated Report</span>
        </div>
        
        <div class="header">
            <h1>📅 Monthly Reports Consolidated</h1>
            <div class="subtitle">{title}</div>
            
            <div class="summary-stats">
                <div class="stat-box">
                    <div class="stat-value">{total_all_months:.0f}h</div>
                    <div class="stat-label">Total Hours</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{avg_monthly:.0f}h</div>
                    <div class="stat-label">Avg per Month</div>
                </div>
"""
    
    if max_month:
        html += f"""
                <div class="stat-box">
                    <div class="stat-value">{max_month['total_hours']:.0f}h</div>
                    <div class="stat-label">Peak: {max_month['month_short']}</div>
                </div>
"""
    
    if min_month:
        html += f"""
                <div class="stat-box">
                    <div class="stat-value">{min_month['total_hours']:.0f}h</div>
                    <div class="stat-label">Low: {min_month['month_short']}</div>
                </div>
"""
    
    html += f"""
            </div>
        </div>
        
        <div class="toggle-container">
            <span class="toggle-label">Hours</span>
            <label class="toggle-switch">
                <input type="checkbox" id="percentageToggle" onchange="togglePercentage()">
                <span class="slider"></span>
            </label>
            <span class="toggle-label">Percentages</span>
        </div>
        
        <div class="section">
            <div class="chart-container">
                {overview_html}
            </div>
        </div>
        
        <div class="section">
            <div class="chart-container">
                {areas_html}
            </div>
        </div>
        
        <div class="section">
            <div class="chart-container">
                {topics_html}
            </div>
        </div>
        
        <div class="section">
            <div class="chart-container">
                {subtasks_html}
            </div>
        </div>
        
        <div class="section">
            <div class="chart-container">
                {heatmap_html}
            </div>
        </div>
"""
    
    # Generate individual month sections
    for month_data in monthly_data:
        html += generate_month_section(month_data)
    
    # Footer
    html += f"""
        <div class="footer">
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Org Clock Analyzer - Consolidated Monthly Reports</p>
        </div>
    </div>
    
    <script>
    function togglePercentage() {{
        const isPercentage = document.getElementById('percentageToggle').checked;
        
        // Toggle areas chart
        const areasDiv = document.getElementById('areas-chart');
        if (areasDiv) {{
            const areasData = areasDiv.data;
            const areasLayout = areasDiv.layout;
            
            areasData.forEach(trace => {{
                // Store original hours on first toggle
                if (!trace.originalY) {{
                    trace.originalY = [...trace.y];
                }}
                
                if (isPercentage && trace.customdata) {{
                    trace.y = trace.customdata; // Use percentage data
                    trace.hovertemplate = trace.name + ': %{{y:.1f}}%<extra></extra>';
                }} else {{
                    trace.y = trace.originalY; // Use hours data
                    trace.hovertemplate = trace.name + ': %{{y:.1f}}h<extra></extra>';
                }}
            }});
            
            areasLayout.yaxis.title.text = isPercentage ? 'Percentage (%)' : 'Hours';
            Plotly.react(areasDiv, areasData, areasLayout);
        }}
        
        // Toggle topics chart
        const topicsDiv = document.getElementById('topics-chart');
        if (topicsDiv) {{
            const topicsData = topicsDiv.data;
            const topicsLayout = topicsDiv.layout;
            
            topicsData.forEach(trace => {{
                // Store original hours on first toggle
                if (!trace.originalY) {{
                    trace.originalY = [...trace.y];
                }}
                
                if (isPercentage && trace.customdata) {{
                    trace.y = trace.customdata;
                    trace.hovertemplate = trace.name + ': %{{y:.1f}}%<extra></extra>';
                }} else {{
                    trace.y = trace.originalY;
                    trace.hovertemplate = trace.name + ': %{{y:.1f}}h<extra></extra>';
                }}
            }});
            
            topicsLayout.yaxis.title.text = isPercentage ? 'Percentage (%)' : 'Hours';
            Plotly.react(topicsDiv, topicsData, topicsLayout);
        }}
        
        // Toggle subtasks chart
        const subtasksDiv = document.getElementById('subtasks-chart');
        if (subtasksDiv) {{
            const subtasksData = subtasksDiv.data;
            const subtasksLayout = subtasksDiv.layout;
            
            subtasksData.forEach(trace => {{
                // Store original hours on first toggle
                if (!trace.originalY) {{
                    trace.originalY = [...trace.y];
                }}
                
                if (isPercentage && trace.customdata) {{
                    trace.y = trace.customdata;
                    trace.hovertemplate = trace.name + ': %{{y:.1f}}%<extra></extra>';
                }} else {{
                    trace.y = trace.originalY;
                    trace.hovertemplate = trace.name + ': %{{y:.1f}}h<extra></extra>';
                }}
            }});
            
            subtasksLayout.yaxis.title.text = isPercentage ? 'Percentage (%)' : 'Hours';
            Plotly.react(subtasksDiv, subtasksData, subtasksLayout);
        }}
    }}
    </script>
</body>
</html>
"""
    
    return html


def generate_month_section(month_data):
    """Generate HTML for a single month section."""
    month_name = month_data['month_name']
    month_short = month_data['month_short']
    total_hours = month_data['total_hours']
    avg_per_day = month_data.get('avg_per_day', 0)
    days_in_month = month_data.get('days_in_month', 0)
    
    if total_hours == 0:
        # Still show a mini calendar for the month
        try:
            cal_snippet = generate_inline_calendar_for_period(month_data['start_date'], month_data['end_date'], files=None, cell_size=8, gap=1, enable_click=True, weekly_link_prefix_to_weekly='weekly/')
        except Exception:
            cal_snippet = ''
        return f"""
        <div class="month-section">
            <div class="month-header">
                <div>
                    <div class="month-title">{month_name}</div>
                </div>
            </div>
            <div style="margin:8px 0;">{cal_snippet}</div>
            <div class="empty-month">
                No time tracked this month
            </div>
        </div>
"""
    
    areas = month_data['areas']
    topics = month_data['topics']
    tags = month_data['tags']
    
    # Top areas
    top_areas = sorted(areas.items(), key=lambda x: x[1], reverse=True)[:5]
    areas_html = ""
    for area, hours in top_areas:
        pct = 100 * hours / total_hours
        areas_html += f"""
                <li class="stat-item">
                    <span class="stat-name">{area}</span>
                    <span class="stat-value">{hours:.1f}h ({pct:.0f}%)</span>
                </li>"""
    
    # Top topics
    top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
    topics_html = ""
    for topic, hours in top_topics:
        pct = 100 * hours / total_hours
        topics_html += f"""
                <li class="stat-item">
                    <span class="stat-name">{topic}</span>
                    <span class="stat-value">{hours:.1f}h ({pct:.0f}%)</span>
                </li>"""
    
    # Top tags
    tags_html = ""
    if tags:
        top_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:5]
        for tag, hours in top_tags:
            pct = 100 * hours / total_hours
            tags_html += f"""
                <li class="stat-item">
                    <span class="stat-name">{tag}</span>
                    <span class="stat-value">{hours:.1f}h ({pct:.0f}%)</span>
                </li>"""
    else:
        tags_html = '<li class="stat-item"><span class="stat-name">No tags found</span></li>'
    
    # Create pie chart for this month's areas
    if areas:
        # Filter out areas with 0 hours
        filtered_areas = {k: v for k, v in areas.items() if v > 0}
        
        if filtered_areas:
            fig = go.Figure(data=[go.Pie(
                labels=list(filtered_areas.keys()),
                values=list(filtered_areas.values()),
                hole=0.3,
            )])
            fig.update_layout(
                title=f"{month_name} - Time Distribution by Area",
                height=400,
                margin=dict(t=50, b=50, l=50, r=50),
                showlegend=True,
            )
            pie_html = fig.to_html(include_plotlyjs=False, div_id=f'pie-month-{month_data["year"]}-{month_data["month"]}')
        else:
            pie_html = ""
    else:
        pie_html = ""
    
    # Calendar snippet for this month
    try:
        cal_snippet = generate_inline_calendar_for_period(month_data['start_date'], month_data['end_date'], files=None, cell_size=8, gap=1, enable_click=True, weekly_link_prefix_to_weekly='weekly/')
    except Exception:
        cal_snippet = ''

    return f"""
        <div class="month-section">
            <div class="month-header">
                <div>
                    <div class="month-title">{month_name}</div>
                </div>
                <div class="month-stats">
                    <div class="month-total">{total_hours:.1f} hours</div>
                    <div class="month-avg">{avg_per_day:.2f}h/day avg ({days_in_month} days)</div>
                </div>
            </div>
            <div style="margin:8px 0;">{cal_snippet}</div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Top 5 Areas</h3>
                    <ul class="stat-list">
                        {areas_html}
                    </ul>
                </div>
                
                <div class="stat-card">
                    <h3>Top 5 Topics</h3>
                    <ul class="stat-list">
                        {topics_html}
                    </ul>
                </div>
                
                <div class="stat-card">
                    <h3>Top 5 Tags</h3>
                    <ul class="stat-list">
                        {tags_html}
                    </ul>
                </div>
            </div>
            
            {f'<div class="chart-container">{pie_html}</div>' if pie_html else ''}
        </div>
"""


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate consolidated monthly report')
    parser.add_argument('-n', '--months', type=int, default=6,
                       help='Number of months to include (default: 6)')
    parser.add_argument('-y', '--year', type=int,
                       help='Show full year (overrides -n)')
    parser.add_argument('-o', '--output', default='reports/monthly_consolidated.html',
                       help='Output file path (default: reports/monthly_consolidated.html)')
    
    args = parser.parse_args()
    
    generate_consolidated_monthly_report(args.months, args.output, args.year)
