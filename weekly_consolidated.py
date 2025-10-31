#!/usr/bin/env python3
"""
Generate a consolidated weekly report page showing multiple weeks in one view.
"""

from pathlib import Path
import os
from datetime import datetime, timedelta
import json

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

import org_time
from reports import TimeAnalyzer, ORG_FILES
from calendar_heatmap import generate_inline_calendar_for_period


def generate_consolidated_weekly_report(n_weeks=4, output_file="reports/weekly_consolidated.html"):
    """Generate a single HTML page with all weekly reports."""
    
    print(f"\n{'='*80}")
    print(f"GENERATING CONSOLIDATED WEEKLY REPORT - LAST {n_weeks} WEEKS")
    print(f"{'='*80}\n")
    
    weekly_data = []
    
    # Collect data for all weeks
    for i in range(n_weeks):
        # Calculate week dates (going backwards)
        today = datetime.today()
        week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=n_weeks-1-i)
        week_end = week_start + timedelta(days=7)
        
        week_num = week_start.isocalendar()[1]
        year = week_start.year
        
        print(f"Loading Week {week_num} ({week_start.date()} to {week_end.date()})...")
        
        # Load data
        clock_root = org_time.load_files(ORG_FILES, week_start, week_end)
        
        if clock_root.totalTime == 0:
            print(f"  No data for this week")
            weekly_data.append({
                'week_num': week_num,
                'year': year,
                'week_label': f"W{week_num}",
                'start_date': week_start,
                'end_date': week_end,
                'total_hours': 0,
                'avg_per_day': 0,
                'areas': {},
                'topics': {},
                'subtasks': {},
                'tags': {},
                'analyzer': None,
            })
            continue
        
        # Analyze
        analyzer = TimeAnalyzer(clock_root)
        
        weekly_data.append({
            'week_num': week_num,
            'year': year,
            'week_label': f"W{week_num}",
            'start_date': week_start,
            'end_date': week_end,
            'total_hours': clock_root.totalTime,
            'avg_per_day': (clock_root.totalTime / 7.0) if clock_root.totalTime else 0,
            'areas': analyzer.get_time_by_macro_area(),
            'topics': analyzer.get_time_by_topic(),
            'subtasks': analyzer.get_time_by_subtask(),
            'tags': analyzer.get_time_by_tags(),
            'analyzer': analyzer,
        })
        
        print(f"  Total: {clock_root.totalTime:.2f} hours")
    
    # Generate HTML
    html_content = generate_weekly_html(weekly_data, n_weeks, output_file)
    
    # Write file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✓ Consolidated weekly report generated: {output_path.absolute()}")
    print(f"📂 Open in browser: file://{output_path.absolute()}")
    
    return str(output_path.absolute())


def generate_weekly_html(weekly_data, n_weeks, output_file):
    """Generate the HTML content for consolidated weekly report."""
    # Compute relative link to reports/index.html based on output location
    try:
        output_dir = Path(output_file).parent
        rel_index_link = os.path.relpath(Path('reports/index.html'), output_dir)
    except Exception:
        # Fallback to default same-folder index
        rel_index_link = 'index.html'
    
    # Create overview chart - total hours trend
    weeks = [w['week_label'] for w in weekly_data]
    total_hours = [w['total_hours'] for w in weekly_data]
    dates = [w['start_date'].strftime('%b %d') for w in weekly_data]
    avg_per_day = [w.get('avg_per_day', 0) for w in weekly_data]
    
    # Overview with dual axis: bars for total hours, line for avg/day
    fig_overview = make_subplots(specs=[[{"secondary_y": True}]])
    fig_overview.add_trace(
        go.Bar(
            x=weeks,
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
            x=weeks,
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
        title=f"Total Hours & Daily Average - Last {n_weeks} Weeks",
        xaxis_title="Week",
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
    for w in weekly_data:
        all_areas.update(w['areas'].keys())
    
    fig_areas = go.Figure()
    colors = ['#667eea', '#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', 
              '#f0932b', '#eb4d4b', '#6ab04c', '#c44569', '#574b90',
              '#f8b500', '#00a8cc', '#9980fa', '#ff6348', '#26de81']
    
    for idx, area in enumerate(sorted(all_areas)):
        area_hours = [w['areas'].get(area, 0) for w in weekly_data]
        # Calculate percentages for each week
        area_percentages = []
        for i, w in enumerate(weekly_data):
            total = sum(w['areas'].values())
            if total > 0:
                area_percentages.append((w['areas'].get(area, 0) / total) * 100)
            else:
                area_percentages.append(0)
        
        color = colors[idx % len(colors)]
        fig_areas.add_trace(go.Scatter(
            name=area,
            x=weeks,
            y=area_hours,
            mode='lines+markers',
            line=dict(width=3, color=color),
            marker=dict(size=8, color=color),
            hovertemplate=f'{area}: %{{y:.1f}}h<extra></extra>',
            customdata=area_percentages,  # Store percentages for toggle
        ))
    
    fig_areas.update_layout(
        title=f"Time by Macro Area - Weekly Trends",
        xaxis_title="Week",
        yaxis_title="Hours",
        height=500,
        margin=dict(t=60, b=50, l=50, r=50),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    areas_html = fig_areas.to_html(include_plotlyjs=False, div_id='areas-chart')

    # Create line chart for top 15 topics across weeks
    all_topics = set()
    for w in weekly_data:
        all_topics.update(w['topics'].keys())
    topic_totals = {}
    for w in weekly_data:
        for topic, hours in w['topics'].items():
            topic_totals[topic] = topic_totals.get(topic, 0) + hours
    top_topics = sorted(topic_totals.items(), key=lambda x: x[1], reverse=True)[:15]
    top_topic_names = [t[0] for t in top_topics]
    
    fig_topics = go.Figure()
    for idx, topic in enumerate(top_topic_names):
        topic_hours = [w['topics'].get(topic, 0) for w in weekly_data]
        # Calculate percentages for each week
        topic_percentages = []
        for i, w in enumerate(weekly_data):
            total = sum(w['topics'].values())
            if total > 0:
                topic_percentages.append((w['topics'].get(topic, 0) / total) * 100)
            else:
                topic_percentages.append(0)
        
        color = colors[idx % len(colors)]
        fig_topics.add_trace(go.Scatter(
            name=topic,
            x=weeks,
            y=topic_hours,
            mode='lines+markers',
            line=dict(width=2.5, color=color),
            marker=dict(size=7, color=color),
            hovertemplate=f'{topic}: %{{y:.1f}}h<extra></extra>',
            customdata=topic_percentages,  # Store percentages for toggle
        ))
    fig_topics.update_layout(
        title=f"Top 15 Topics - Weekly Trends",
        xaxis_title="Week",
        yaxis_title="Hours",
        height=550,
        margin=dict(t=60, b=50, l=50, r=50),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    topics_html = fig_topics.to_html(include_plotlyjs=False, div_id='topics-chart')

    # Create line chart for top 15 subtasks across weeks
    all_subtasks = set()
    for w in weekly_data:
        all_subtasks.update(w['subtasks'].keys())
    subtask_totals = {}
    for w in weekly_data:
        for subtask, hours in w['subtasks'].items():
            subtask_totals[subtask] = subtask_totals.get(subtask, 0) + hours
    top_subtasks = sorted(subtask_totals.items(), key=lambda x: x[1], reverse=True)[:15]
    top_subtask_names = [t[0] for t in top_subtasks]
    
    fig_subtasks = go.Figure()
    for idx, subtask in enumerate(top_subtask_names):
        subtask_hours = [w['subtasks'].get(subtask, 0) for w in weekly_data]
        # Calculate percentages for each week
        subtask_percentages = []
        for i, w in enumerate(weekly_data):
            total = sum(w['subtasks'].values())
            if total > 0:
                subtask_percentages.append((w['subtasks'].get(subtask, 0) / total) * 100)
            else:
                subtask_percentages.append(0)
        
        color = colors[idx % len(colors)]
        fig_subtasks.add_trace(go.Scatter(
            name=subtask,
            x=weeks,
            y=subtask_hours,
            mode='lines+markers',
            line=dict(width=2.5, color=color),
            marker=dict(size=7, color=color),
            hovertemplate=f'{subtask}: %{{y:.1f}}h<extra></extra>',
            customdata=subtask_percentages,  # Store percentages for toggle
        ))
    fig_subtasks.update_layout(
        title=f"Top 15 Subtasks - Weekly Trends",
        xaxis_title="Week",
        yaxis_title="Hours",
        height=550,
        margin=dict(t=60, b=50, l=50, r=50),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    subtasks_html = fig_subtasks.to_html(include_plotlyjs=False, div_id='subtasks-chart')

    # Heatmap of top topics across weeks
    heatmap_data = []
    for topic in top_topic_names:
        row = [w['topics'].get(topic, 0) for w in weekly_data]
        heatmap_data.append(row)
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=weeks,
        y=top_topic_names,
        colorscale='Viridis',
        hoverongaps=False,
        hovertemplate='%{y}<br>%{x}: %{z:.1f}h<extra></extra>',
    ))
    fig_heatmap.update_layout(
        title="Top 15 Topics - Weekly Heatmap",
        xaxis_title="Week",
        yaxis_title="Topic",
        height=500,
        margin=dict(t=60, b=50, l=250, r=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    heatmap_html = fig_heatmap.to_html(include_plotlyjs=False, div_id='heatmap-chart')
    
    # Build calendar heatmap snippet spanning the period of data
    try:
        if weekly_data:
            period_start = min(w['start_date'] for w in weekly_data)
            period_end = max(w['end_date'] for w in weekly_data)
        else:
            # Fallback to last 4 weeks
            today = datetime.today()
            period_end = today
            period_start = today - timedelta(days=28)
        cal_id = f"wc_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}"
        calendar_html = generate_inline_calendar_for_period(
            period_start,
            period_end,
            files=None,
            cell_size=8,
            gap=1,
            enable_click=True,
            id_suffix=cal_id,
            weekly_link_prefix_to_weekly='weekly/',
            include_month_summary=True,
            monthly_link_prefix_to_monthly='monthly/'
        )
    except Exception:
        calendar_html = ''

    # Start HTML
    # Calculate summary statistics
    total_all_weeks = sum(total_hours)
    nonzero_weeks = [w for w in weekly_data if w['total_hours'] > 0]
    avg_weekly = (total_all_weeks / len(nonzero_weeks)) if nonzero_weeks else 0
    max_week = max(weekly_data, key=lambda x: x['total_hours']) if weekly_data else None
    min_week = min(nonzero_weeks, key=lambda x: x['total_hours']) if nonzero_weeks else None

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Reports - Last {n_weeks} Weeks</title>
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
        
            .toggle-container {{
                background: white;
                border-radius: 12px;
                padding: 15px 30px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 15px;
            }}
            
            .toggle-label {{
                font-weight: 500;
                color: #333;
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
                background-color: #ccc;
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
                background-color: #667eea;
            }}
            
            input:checked + .slider:before {{
                transform: translateX(30px);
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
        
        .section-title {{
            color: #333;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        .week-section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            border-left: 5px solid #667eea;
        }}
        
        .week-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        .week-title {{
            font-size: 1.8em;
            color: #333;
            font-weight: 600;
        }}
        
        .week-date {{
            color: #666;
            font-size: 1em;
        }}
        
        .week-total {{
            font-size: 1.5em;
            color: #667eea;
            font-weight: bold;
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
            border-left: 4px solid #667eea;
        }}
        
        .stat-card h3 {{
            color: #667eea;
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
            color: #667eea;
            font-weight: 600;
            white-space: nowrap;
        }}
        
        .chart-container {{
            margin: 20px 0;
        }}
        
        .empty-week {{
            text-align: center;
            padding: 40px;
            color: #999;
            font-style: italic;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            padding: 20px;
            opacity: 0.8;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            
            .week-section {{
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
            <span class="nav-title">Weekly Consolidated Report</span>
        </div>
        
        <div class="header">
            <h1>📊 Weekly Reports Consolidated</h1>
            <div class="subtitle">Last {n_weeks} Weeks Overview</div>
            <div class="summary-stats">
                <div class="stat-box">
                    <div class="stat-value">{total_all_weeks:.0f}h</div>
                    <div class="stat-label">Total Hours</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{avg_weekly:.0f}h</div>
                    <div class="stat-label">Avg per Week</div>
                </div>
    """

    if max_week:
        html += f"""
                <div class="stat-box">
                    <div class="stat-value">{max_week['total_hours']:.0f}h</div>
                    <div class="stat-label">Peak: {max_week['week_label']}</div>
                </div>
    """

    if min_week:
        html += f"""
                <div class="stat-box">
                    <div class="stat-value">{min_week['total_hours']:.0f}h</div>
                    <div class="stat-label">Low: {min_week['week_label']}</div>
                </div>
    """

    html += f"""
            </div>
        </div>
        
        <!-- Calendar Heatmap over Period -->
        <div class="section">
            <div class="section-title">Calendar Heatmap</div>
            <div class="chart-container">
                {calendar_html}
            </div>
        </div>

        <script>
            // Anchors for week sections aligned with chart x values
            var WEEK_LABELS = {json.dumps(weeks)};
            var WEEK_ANCHORS = {json.dumps([f"week-{w['year']}-W{int(w['week_num']):02d}" for w in weekly_data])};
            function goToAnchor(id) {{
                var el = document.getElementById(id);
                if (el) {{
                    history.replaceState(null, null, '#' + id);
                    el.scrollIntoView({{behavior:'smooth', block:'start'}});
                }}
            }}
            function bindClickToAnchor(divId) {{
                var gd = document.getElementById(divId);
                if (!gd || !gd.on) return;
                gd.on('plotly_click', function(evt) {{
                    try {{
                        var pt = evt.points && evt.points[0];
                        if (!pt) return;
                        var idx = (typeof pt.pointIndex === 'number') ? pt.pointIndex : (WEEK_LABELS.indexOf(pt.x));
                        if (idx >= 0 && idx < WEEK_ANCHORS.length) {{
                            goToAnchor(WEEK_ANCHORS[idx]);
                        }}
                    }} catch (e) {{}}
                }});
            }}
            document.addEventListener('DOMContentLoaded', function() {{
                ['overview-chart','areas-chart','topics-chart','subtasks-chart','heatmap-chart'].forEach(bindClickToAnchor);
            }});
        </script>

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
        
        <!-- Top 15 Topics - Weekly Heatmap -->
        <div class="section">
            <div class="chart-container">
                {heatmap_html}
            </div>
        </div>

        <div class="section">
```
"""
    
    # Generate individual week sections
    for week_data in weekly_data:
        html += generate_week_section(week_data)
    
    # Footer
    html += f"""
        <div class="footer">
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Org Clock Analyzer - Consolidated Weekly Reports</p>
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


def generate_week_section(week_data):
    """Generate HTML for a single week section."""
    week_label = week_data['week_label']
    week_num = week_data['week_num']
    year = week_data['year']
    start_date = week_data['start_date'].strftime('%b %d, %Y')
    end_date = week_data['end_date'].strftime('%b %d, %Y')
    total_hours = week_data['total_hours']
    
    section_id = f"week-{year}-W{int(week_num):02d}"
    if total_hours == 0:
        return f"""
        <div class="week-section" id="{section_id}">
            <div class="week-header">
                <div>
                    <div class="week-title">Week {week_num} - {year}</div>
                    <div class="week-date">{start_date} - {end_date}</div>
                </div>
            </div>
            <div class="empty-week">
                No time tracked this week
            </div>
        </div>
"""
    
    areas = week_data['areas']
    topics = week_data['topics']
    tags = week_data['tags']
    
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
    
    # Create pie chart for this week's areas
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
                title=f"Week {week_num} - Time Distribution by Area",
                height=400,
                margin=dict(t=50, b=50, l=50, r=50),
                showlegend=True,
            )
            pie_html = fig.to_html(include_plotlyjs=False, div_id=f'pie-week-{week_num}')
        else:
            pie_html = ""
    else:
        pie_html = ""
    
    return f"""
        <div class="week-section" id="{section_id}">
            <div class="week-header">
                <div>
                    <div class="week-title">Week {week_num} - {year}</div>
                    <div class="week-date">{start_date} - {end_date}</div>
                </div>
                <div class="week-total">{total_hours:.1f} hours</div>
            </div>
            
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
    
    parser = argparse.ArgumentParser(description='Generate consolidated weekly report')
    parser.add_argument('-n', '--weeks', type=int, default=4,
                       help='Number of weeks to include (default: 4)')
    parser.add_argument('-o', '--output', default='reports/weekly_consolidated.html',
                       help='Output file path (default: reports/weekly_consolidated.html)')
    
    args = parser.parse_args()
    
    generate_consolidated_weekly_report(args.weeks, args.output)
