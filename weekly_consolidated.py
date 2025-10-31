#!/usr/bin/env python3
"""
Generate a consolidated weekly report page showing multiple weeks in one view.
"""

from pathlib import Path
from datetime import datetime, timedelta
import json

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

import org_time
from reports import TimeAnalyzer, ORG_FILES


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
                'areas': {},
                'topics': {},
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
            'areas': analyzer.get_time_by_macro_area(),
            'topics': analyzer.get_time_by_topic(),
            'tags': analyzer.get_time_by_tags(),
            'analyzer': analyzer,
        })
        
        print(f"  Total: {clock_root.totalTime:.2f} hours")
    
    # Generate HTML
    html_content = generate_weekly_html(weekly_data, n_weeks)
    
    # Write file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✓ Consolidated weekly report generated: {output_path.absolute()}")
    print(f"📂 Open in browser: file://{output_path.absolute()}")
    
    return str(output_path.absolute())


def generate_weekly_html(weekly_data, n_weeks):
    """Generate the HTML content for consolidated weekly report."""
    
    # Create overview chart - total hours trend
    weeks = [w['week_label'] for w in weekly_data]
    total_hours = [w['total_hours'] for w in weekly_data]
    dates = [w['start_date'].strftime('%b %d') for w in weekly_data]
    
    fig_overview = go.Figure()
    fig_overview.add_trace(go.Scatter(
        x=weeks,
        y=total_hours,
        mode='lines+markers',
        name='Total Hours',
        line=dict(color='#667eea', width=3),
        marker=dict(size=10),
        text=[f"{h:.1f}h<br>{d}" for h, d in zip(total_hours, dates)],
        hovertemplate='%{text}<extra></extra>',
    ))
    fig_overview.update_layout(
        title=f"Total Hours Tracked - Last {n_weeks} Weeks",
        xaxis_title="Week",
        yaxis_title="Hours",
        height=300,
        margin=dict(t=50, b=50, l=50, r=50),
    )
    overview_html = fig_overview.to_html(include_plotlyjs='cdn', div_id='overview-chart')
    
    # Create stacked area chart by macro area
    all_areas = set()
    for w in weekly_data:
        all_areas.update(w['areas'].keys())
    
    fig_areas = go.Figure()
    for area in sorted(all_areas):
        area_hours = [w['areas'].get(area, 0) for w in weekly_data]
        fig_areas.add_trace(go.Bar(
            name=area,
            x=weeks,
            y=area_hours,
            hovertemplate=f'{area}: %{{y:.1f}}h<extra></extra>',
        ))
    
    fig_areas.update_layout(
        title=f"Time by Macro Area - Last {n_weeks} Weeks",
        xaxis_title="Week",
        yaxis_title="Hours",
        barmode='stack',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    areas_html = fig_areas.to_html(include_plotlyjs=False, div_id='areas-chart')
    
    # Start HTML
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1600px;
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
        <div class="header">
            <h1>📊 Weekly Reports Consolidated</h1>
            <div class="subtitle">Last {n_weeks} Weeks Overview</div>
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
    
    if total_hours == 0:
        return f"""
        <div class="week-section">
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
        fig = go.Figure(data=[go.Pie(
            labels=list(areas.keys()),
            values=list(areas.values()),
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
    
    return f"""
        <div class="week-section">
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
