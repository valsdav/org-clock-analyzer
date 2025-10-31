#!/usr/bin/env python3
"""
Comprehensive reporting system for org-clock data.
Generates weekly, monthly, and yearly reports with tables and graphs.
Analyzes time spent by:
- Macro area (org file)
- Topic (first-layer tasks)
- Tags
"""

import argparse
import sys
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path
from collections import defaultdict
import json

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

import org_time


def add_nav_to_html(html_file, relative_index_path=None):
    """Add navigation bar to an HTML file.
    If relative_index_path is not provided, compute a path to reports/index.html
    relative to the html_file location.
    """
    try:
        html_path = Path(html_file)
        # Find the 'reports' folder in the path and compute depth from there
        parts = html_path.parts
        if 'reports' in parts:
            reports_idx = parts.index('reports')
            # How many segments after 'reports' before the file name
            depth_after_reports = len(parts) - reports_idx - 2  # exclude 'reports' and filename
            if depth_after_reports <= 0:
                rel_index = 'index.html'
            else:
                rel_index = '../' * depth_after_reports + 'index.html'
        else:
            # Fallback: assume sibling index.html
            rel_index = '../index.html'
    except Exception:
        rel_index = '../index.html'
    
    if relative_index_path is None:
        relative_index_path = rel_index
    nav_html = """
    <style>
        .report-nav-bar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: white;
            border-bottom: 2px solid #667eea;
            padding: 12px 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .report-nav-bar a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 5px;
            transition: color 0.3s;
        }
        .report-nav-bar a:hover {
            color: #764ba2;
        }
        .report-nav-bar .nav-title {
            color: #666;
            font-size: 13px;
            margin-left: auto;
        }
        body {
            padding-top: 60px !important;
        }
    </style>
    <div class="report-nav-bar">
        <a href="%s">← Back to Index</a>
        <span class="nav-title">Org Clock Analyzer Reports</span>
    </div>
    """ % relative_index_path
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Insert navigation after <body> tag
    if '<body>' in content:
        content = content.replace('<body>', '<body>\n' + nav_html, 1)
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(content)


# Configuration: List of org files to analyze
ORG_FILES = [
    "/home/valsdav/org/Clustering.org",
    "/home/valsdav/org/ETH.org",
    "/home/valsdav/org/CMS.org",
    "/home/valsdav/org/ttHbb.org",
    "/home/valsdav/org/PocketCoffea.org",
    "/home/valsdav/org/MEMFlow.org",
    "/home/valsdav/org/Mails.org",
    "/home/valsdav/org/Publications.org",
    "/home/valsdav/org/Meetings.org",
    "/home/valsdav/org/L3_ML_production.org",
    "/home/valsdav/org/Reading.org",
    "/home/valsdav/org/Learning.org",
    "/home/valsdav/org/TICL.org",
    "/home/valsdav/org/NextGenerationTrigger.org",
    "/home/valsdav/org/Events.org",
    "/home/valsdav/org/Teaching.org",
    "/home/valsdav/org/EGamma.org",
    "/home/valsdav/org/ScaleFactorsML.org",
]


class TimeAnalyzer:
    """Analyzes org-clock data and extracts metrics by area, topic, and tags."""
    
    def __init__(self, clock_root):
        self.clock_root = clock_root
        self.total_time = clock_root.totalTime
        
    def get_time_by_macro_area(self):
        """Extract time spent per macro area (org file)."""
        areas = {}
        for child in self.clock_root.children:
            area_name = child.name
            areas[area_name] = child.totalTime
        return areas
    
    def get_time_by_topic(self):
        """Extract time spent per topic (first-layer tasks under each org file)."""
        topics = defaultdict(float)
        for area_child in self.clock_root.children:
            area_name = area_child.name
            for topic_child in area_child.children:
                topic_name = f"{area_name}/{topic_child.name}"
                topics[topic_name] = topic_child.totalTime
        return dict(topics)
    
    def get_time_by_subtask(self):
        """Extract time spent per subtask (second-layer tasks under topics)."""
        subtasks = defaultdict(float)
        for area_child in self.clock_root.children:
            area_name = area_child.name
            for topic_child in area_child.children:
                topic_name = topic_child.name
                for subtask_child in topic_child.children:
                    subtask_name = f"{area_name}/{topic_name}/{subtask_child.name}"
                    subtasks[subtask_name] = subtask_child.totalTime
        return dict(subtasks)
    
    def get_time_by_tags(self):
        """Extract time spent per tag across all tasks.
        Rules:
        - Use localTime only (time directly recorded on the node) to avoid double counting.
        - If a node has multiple tags, split its local time evenly across its tags.
        This guarantees that the sum of tag hours equals total tracked hours (up to rounding).
        """
        tags = defaultdict(float)

        def traverse(node):
            # Distribute only the direct time logged on this node
            if getattr(node, 'localTime', 0) and node.tags:
                t = float(getattr(node, 'localTime', 0))
                n = len(node.tags)
                if n > 0 and t > 0:
                    share = t / n
                    for tag in node.tags:
                        tags[tag] += share
            # Recurse into children
            for child in node.children:
                traverse(child)

        traverse(self.clock_root)
        return dict(tags)
    
    def get_detailed_breakdown(self):
        """Get a detailed breakdown combining area, topic, and tags."""
        breakdown = []
        
        for area_child in self.clock_root.children:
            area_name = area_child.name
            for topic_child in area_child.children:
                topic_name = topic_child.name
                
                def flatten_tasks(node, parent_path=""):
                    path = f"{parent_path}/{node.name}" if parent_path else node.name
                    
                    breakdown.append({
                        'area': area_name,
                        'topic': topic_name,
                        'task': node.name,
                        'full_path': f"{area_name}/{topic_name}/{path}",
                        'tags': ','.join(node.tags) if node.tags else '',
                        'time': node.totalTime,
                        'local_time': node.localTime,
                        'level': node.level
                    })
                    
                    for child in node.children:
                        flatten_tasks(child, path)
                
                flatten_tasks(topic_child)
        
        return pd.DataFrame(breakdown)


class ReportGenerator:
    """Generates various reports and visualizations."""
    
    def __init__(self, analyzer, period_name, start_date, end_date):
        self.analyzer = analyzer
        self.period_name = period_name
        self.start_date = start_date
        self.end_date = end_date
        self.total_time = analyzer.total_time
        
    def generate_summary_table(self):
        """Generate a summary table with key metrics."""
        areas = self.analyzer.get_time_by_macro_area()
        topics = self.analyzer.get_time_by_topic()
        subtasks = self.analyzer.get_time_by_subtask()
        tags = self.analyzer.get_time_by_tags()
        
        print(f"\n{'='*80}")
        print(f"TIME TRACKING REPORT - {self.period_name}")
        print(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        print(f"{'='*80}\n")
        
        print(f"Total Time Tracked: {self.total_time:.2f} hours")
        print(f"Average per day: {self.total_time / max(1, (self.end_date - self.start_date).days):.2f} hours")
        print(f"\n{'='*80}\n")
        
        # Macro Areas
        print(f"\nTIME BY MACRO AREA")
        print(f"{'-'*80}")
        areas_sorted = sorted(areas.items(), key=lambda x: x[1], reverse=True)
        # Safe percentage helper to avoid division by zero
        def _pct(v: float) -> float:
            return (100.0 * v / self.total_time) if self.total_time > 0 else 0.0

        area_df = pd.DataFrame([
            {
                'Area': area,
                'Hours': f"{time:.2f}",
                'Percentage': f"{_pct(time):.1f}%"
            }
            for area, time in areas_sorted if time > 0
        ])
        print(area_df.to_string(index=False))
        
        # Top Topics
        print(f"\n\nTOP 15 TOPICS")
        print(f"{'-'*80}")
        topics_sorted = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:15]
        topic_df = pd.DataFrame([
            {
                'Topic': topic,
                'Hours': f"{time:.2f}",
                'Percentage': f"{_pct(time):.1f}%"
            }
            for topic, time in topics_sorted
        ])
        print(topic_df.to_string(index=False))
        
        # Top Subtasks
        subtask_df = None
        if subtasks:
            print(f"\n\nTOP 15 SUBTASKS")
            print(f"{'-'*80}")
            subtasks_sorted = sorted(subtasks.items(), key=lambda x: x[1], reverse=True)[:15]
            subtask_df = pd.DataFrame([
                {
                    'Subtask': subtask,
                    'Hours': f"{time:.2f}",
                    'Percentage': f"{_pct(time):.1f}%"
                }
                for subtask, time in subtasks_sorted
            ])
            print(subtask_df.to_string(index=False))
        
        # Tags
        tag_df = None
        if tags:
            print(f"\n\nTIME BY TAG")
            print(f"{'-'*80}")
            tags_sorted = sorted(tags.items(), key=lambda x: x[1], reverse=True)
            # Filter tags that round to at least 0.1% for cleaner display
            tag_df = pd.DataFrame([
                {
                    'Tag': tag,
                    'Hours': f"{time:.2f}",
                    'Percentage': f"{_pct(time):.1f}%"
                }
                for tag, time in tags_sorted if time > 0 and _pct(time) >= 0.05
            ])
            print(tag_df.to_string(index=False))
            # Count how many tags were filtered out
            filtered_count = sum(1 for tag, time in tags_sorted if time > 0 and _pct(time) < 0.05)
            if filtered_count > 0:
                print(f"\n(+ {filtered_count} tags with < 0.1% not shown; see CSV for full details)")
            print(f"Note: Percentages sum to 100% in CSV exports; display rounded to 1 decimal")
        
        print(f"\n{'='*80}\n")
        
        return {
            'areas': area_df,
            'topics': topic_df,
            'subtasks': subtask_df,
            'tags': tag_df
        }
    
    def plot_macro_areas_pie(self, output_file=None):
        """Create a pie chart of time by macro area."""
        areas = self.analyzer.get_time_by_macro_area()
        areas_sorted = sorted(areas.items(), key=lambda x: x[1], reverse=True)
        
        # Filter out zero values
        areas_filtered = [(name, time) for name, time in areas_sorted if time > 0]
        
        names = [item[0] for item in areas_filtered]
        values = [item[1] for item in areas_filtered]
        
        fig = go.Figure(data=[go.Pie(
            labels=names,
            values=values,
            hole=0.3,
            textinfo='label+percent',
            textposition='auto',
        )])
        
        fig.update_layout(
            title=f"Time Distribution by Macro Area - {self.period_name}",
            height=600,
        )
        
        if output_file:
            fig.write_html(output_file)
            add_nav_to_html(output_file)
        else:
            fig.show()
        
        return fig
    
    def plot_topics_bar(self, top_n=20, output_file=None):
        """Create a horizontal bar chart of top topics."""
        topics = self.analyzer.get_time_by_topic()
        topics_sorted = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        names = [item[0] for item in topics_sorted]
        values = [item[1] for item in topics_sorted]
        
        # Reverse for better display (highest at top)
        names = names[::-1]
        values = values[::-1]
        
        fig = go.Figure(data=[go.Bar(
            x=values,
            y=names,
            orientation='h',
            marker=dict(
                color=values,
                colorscale='Viridis',
            ),
            text=[f"{v:.1f}h" for v in values],
            textposition='auto',
        )])
        
        fig.update_layout(
            title=f"Top {top_n} Topics by Time - {self.period_name}",
            xaxis_title="Hours",
            yaxis_title="Topic",
            height=max(400, top_n * 25),
            showlegend=False,
        )
        
        if output_file:
            fig.write_html(output_file)
            add_nav_to_html(output_file)
        else:
            fig.show()
        
        return fig
    
    def plot_subtasks_bar(self, top_n=20, output_file=None):
        """Create a horizontal bar chart of top subtasks."""
        subtasks = self.analyzer.get_time_by_subtask()
        
        if not subtasks:
            print("No subtasks found in the data.")
            return None
        
        subtasks_sorted = sorted(subtasks.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        names = [item[0] for item in subtasks_sorted]
        values = [item[1] for item in subtasks_sorted]
        
        # Reverse for better display (highest at top)
        names = names[::-1]
        values = values[::-1]
        
        fig = go.Figure(data=[go.Bar(
            x=values,
            y=names,
            orientation='h',
            marker=dict(
                color=values,
                colorscale='Cividis',
            ),
            text=[f"{v:.1f}h" for v in values],
            textposition='auto',
        )])
        
        fig.update_layout(
            title=f"Top {top_n} Subtasks by Time - {self.period_name}",
            xaxis_title="Hours",
            yaxis_title="Subtask",
            height=max(400, top_n * 25),
            showlegend=False,
        )
        
        if output_file:
            fig.write_html(output_file)
            add_nav_to_html(output_file)
        else:
            fig.show()
        
        return fig
    
    def plot_tags_wordcloud_style(self, output_file=None):
        """Create a bubble chart for tags (wordcloud style)."""
        tags = self.analyzer.get_time_by_tags()
        
        if not tags:
            print("No tags found in the data.")
            return None
        
        tags_sorted = sorted(tags.items(), key=lambda x: x[1], reverse=True)
        
        names = [item[0] for item in tags_sorted]
        values = [item[1] for item in tags_sorted]
        
        fig = go.Figure(data=[go.Scatter(
            x=list(range(len(names))),
            y=[1] * len(names),
            mode='markers+text',
            marker=dict(
                size=[v * 100 for v in values],
                sizemode='area',
                sizeref=2.*max(values)/100,
                color=values,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Hours"),
            ),
            text=names,
            textposition='middle center',
            hovertemplate='<b>%{text}</b><br>Hours: %{marker.size:.1f}<extra></extra>',
        )])
        
        fig.update_layout(
            title=f"Time by Tags - {self.period_name}",
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            height=400,
            showlegend=False,
        )
        
        if output_file:
            fig.write_html(output_file)
            add_nav_to_html(output_file)
        else:
            fig.show()
        
        return fig
    
    def plot_combined_dashboard(self, output_file=None):
        """Create a comprehensive dashboard with multiple visualizations."""
        areas = self.analyzer.get_time_by_macro_area()
        topics = self.analyzer.get_time_by_topic()
        subtasks = self.analyzer.get_time_by_subtask()
        tags = self.analyzer.get_time_by_tags()
        
        # Create subplots - 3x2 grid (3 rows, 2 columns)
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=('Time by Macro Area', 'Top 15 Topics',
                          'Top 15 Subtasks', 'Time by Tags',
                          'Area Breakdown (Treemap)', 'Subtask Details'),
            specs=[[{'type': 'pie'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'bar'}],
                   [{'type': 'treemap'}, {'type': 'bar'}]],
            vertical_spacing=0.10,
            horizontal_spacing=0.12,
        )
        
        # 1. Pie chart - Macro areas (Row 1, Col 1)
        areas_sorted = sorted(areas.items(), key=lambda x: x[1], reverse=True)
        areas_filtered = [(name, time) for name, time in areas_sorted if time > 0]
        fig.add_trace(
            go.Pie(labels=[item[0] for item in areas_filtered],
                   values=[item[1] for item in areas_filtered],
                   hole=0.3),
            row=1, col=1
        )
        
        # 2. Bar chart - Top 15 topics (Row 1, Col 2)
        topics_sorted = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:15]
        topics_names = [item[0] for item in topics_sorted][::-1]
        topics_values = [item[1] for item in topics_sorted][::-1]
        fig.add_trace(
            go.Bar(x=topics_values, y=topics_names, orientation='h',
                   marker=dict(color=topics_values, colorscale='Blues')),
            row=1, col=2
        )
        
        # 3. Bar chart - Top 15 subtasks (Row 2, Col 1)
        if subtasks:
            subtasks_sorted = sorted(subtasks.items(), key=lambda x: x[1], reverse=True)[:15]
            subtasks_names = [item[0] for item in subtasks_sorted][::-1]
            subtasks_values = [item[1] for item in subtasks_sorted][::-1]
            fig.add_trace(
                go.Bar(x=subtasks_values, y=subtasks_names, orientation='h',
                       marker=dict(color=subtasks_values, colorscale='Cividis')),
                row=2, col=1
            )
        
        # 4. Bar chart - Top 15 Tags (Row 2, Col 2)
        if tags:
            tags_sorted = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:15]
            tags_names = [item[0] for item in tags_sorted][::-1]
            tags_values = [item[1] for item in tags_sorted][::-1]
            fig.add_trace(
                go.Bar(x=tags_values, y=tags_names, orientation='h',
                       marker=dict(color=tags_values, colorscale='Greens')),
                row=2, col=2
            )
        
        # 5. Treemap - Hierarchical view (Row 3, Col 1)
        # Prepare data for treemap
        treemap_labels = ["All"]
        treemap_parents = [""]
        treemap_values = [0]
        
        for area_name, area_time in areas_sorted[:10]:
            if area_time > 0:
                treemap_labels.append(area_name)
                treemap_parents.append("All")
                treemap_values.append(area_time)
        
        fig.add_trace(
            go.Treemap(
                labels=treemap_labels,
                parents=treemap_parents,
                values=treemap_values,
                marker=dict(colorscale='Reds'),
            ),
            row=3, col=1
        )
        
        # 6. Subtask details from top topics (Row 3, Col 2)
        if subtasks:
            # Show subtasks from top 3 topics
            subtask_details = []
            for topic_name, _ in topics_sorted[:3]:
                for subtask_name, subtask_time in subtasks.items():
                    if subtask_name.startswith(topic_name):
                        subtask_details.append((subtask_name.split('/')[-1], subtask_time))
            
            if subtask_details:
                subtask_details_sorted = sorted(subtask_details, key=lambda x: x[1], reverse=True)[:15]
                sd_names = [item[0] for item in subtask_details_sorted][::-1]
                sd_values = [item[1] for item in subtask_details_sorted][::-1]
                fig.add_trace(
                    go.Bar(x=sd_values, y=sd_names, orientation='h',
                           marker=dict(color=sd_values, colorscale='Oranges')),
                    row=3, col=2
                )
        
        fig.update_layout(
            title_text=f"Time Tracking Dashboard - {self.period_name}",
            height=1400,
            showlegend=False,
        )
        
        if output_file:
            fig.write_html(output_file)
            add_nav_to_html(output_file)
            # Optionally insert a calendar heatmap for monthly/yearly dashboards
            try:
                period = str(self.period_name)
                insert_calendar = False
                # Determine if monthly (YYYY-MM) or yearly (Year_YYYY)
                if len(period) == 7 and period[4] == '-' and period[:4].isdigit() and period[5:7].isdigit():
                    insert_calendar = True
                if period.startswith('Year_'):
                    insert_calendar = True
                if insert_calendar:
                    # Lazy import to avoid circular dependency
                    from calendar_heatmap import generate_inline_calendar_for_period
                    snippet = generate_inline_calendar_for_period(
                        self.start_date,
                        self.end_date,
                        files=None,
                        cell_size=10 if period.startswith('Year_') else 12,
                        gap=2,
                        enable_click=True,
                        id_suffix=period,
                        weekly_link_prefix_to_weekly='../../weekly/'
                    )
                    # Inject snippet right below the nav bar if present, else at top of body
                    try:
                        with open(output_file, 'r', encoding='utf-8') as rf:
                            content = rf.read()
                        anchor = '<div class="report-nav-bar">'
                        idx = content.find(anchor)
                        if idx != -1:
                            # find closing </div> of nav bar
                            close_idx = content.find('</div>', idx)
                            if close_idx != -1:
                                insertion_point = close_idx + len('</div>')
                                insertion = f"\n<div style=\"padding:12px 20px;\"><h3 style=\"margin:4px 0 8px; color:#555;\">Calendar</h3>{snippet}</div>\n"
                                content = content[:insertion_point] + insertion + content[insertion_point:]
                            else:
                                # fallback: prepend after <body>
                                content = content.replace('<body>', f'<body>\n<div style=\"padding:12px 20px;\"><h3 style=\"margin:4px 0 8px; color:#555;\">Calendar</h3>{snippet}</div>\n', 1)
                        else:
                            content = content.replace('<body>', f'<body>\n<div style=\"padding:12px 20px;\"><h3 style=\"margin:4px 0 8px; color:#555;\">Calendar</h3>{snippet}</div>\n', 1)
                        with open(output_file, 'w', encoding='utf-8') as wf:
                            wf.write(content)
                    except Exception:
                        pass
            except Exception:
                # Non-fatal if calendar injection fails
                pass
        else:
            fig.show()
        
        return fig
    
    def export_to_csv(self, output_dir):
        """Export detailed breakdown to CSV files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        # Safe percentage helper
        pct = (lambda v: (100.0 * v / self.total_time) if self.total_time > 0 else 0.0)
        
        # Export by macro area
        areas = self.analyzer.get_time_by_macro_area()
        areas_df = pd.DataFrame([
            {'Area': area, 'Hours': time, 'Percentage': pct(time)}
            for area, time in sorted(areas.items(), key=lambda x: x[1], reverse=True)
            if time > 0
        ])
        areas_df.to_csv(output_dir / f"areas_{self.period_name}.csv", index=False)
        
        # Export topics
        topics = self.analyzer.get_time_by_topic()
        topics_df = pd.DataFrame([
            {'Topic': topic, 'Hours': time, 'Percentage': pct(time)}
            for topic, time in sorted(topics.items(), key=lambda x: x[1], reverse=True)
        ])
        topics_df.to_csv(output_dir / f"topics_{self.period_name}.csv", index=False)
        
        # Export subtasks
        subtasks = self.analyzer.get_time_by_subtask()
        if subtasks:
            subtasks_data = []
            for subtask_path, time in sorted(subtasks.items(), key=lambda x: x[1], reverse=True):
                parts = subtask_path.split('/')
                if len(parts) >= 3:
                    area = parts[0]
                    topic = parts[1]
                    subtask = '/'.join(parts[2:])  # Handle subtasks with / in name
                    subtasks_data.append({
                        'Area': area, 
                        'Topic': topic, 
                        'Subtask': subtask, 
                        'Hours': time, 
                        'Percentage': pct(time)
                    })
            
            if subtasks_data:
                subtasks_df = pd.DataFrame(subtasks_data)
                subtasks_df.to_csv(output_dir / f"subtasks_{self.period_name}.csv", index=False)
        
        # Export tags
        tags = self.analyzer.get_time_by_tags()
        if tags:
            tags_df = pd.DataFrame([
                {'Tag': tag, 'Hours': time, 'Percentage': pct(time)}
                for tag, time in sorted(tags.items(), key=lambda x: x[1], reverse=True)
                if time > 0
            ])
            tags_df.to_csv(output_dir / f"tags_{self.period_name}.csv", index=False)
        
        # Export detailed breakdown
        detailed = self.analyzer.get_detailed_breakdown()
        detailed.to_csv(output_dir / f"detailed_{self.period_name}.csv", index=False)
        
        print(f"\nCSV files exported to: {output_dir}")
        
    def generate_full_report(self, output_dir=None):
        """Generate a complete report with all visualizations and tables."""
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            
            # Generate summary table
            self.generate_summary_table()
            
            # Generate all plots
            self.plot_macro_areas_pie(output_dir / f"pie_areas_{self.period_name}.html")
            self.plot_topics_bar(top_n=20, output_file=output_dir / f"bar_topics_{self.period_name}.html")
            
            subtasks = self.analyzer.get_time_by_subtask()
            if subtasks:
                self.plot_subtasks_bar(top_n=20, output_file=output_dir / f"bar_subtasks_{self.period_name}.html")
            
            tags = self.analyzer.get_time_by_tags()
            if tags:
                self.plot_tags_wordcloud_style(output_dir / f"tags_{self.period_name}.html")
            
            self.plot_combined_dashboard(output_dir / f"dashboard_{self.period_name}.html")
            
            # Export CSV files
            self.export_to_csv(output_dir)
            
            print(f"\nFull report generated in: {output_dir}")
        else:
            # Just show in terminal and display plots
            self.generate_summary_table()
            self.plot_macro_areas_pie()
            self.plot_topics_bar(top_n=20)
            
            subtasks = self.analyzer.get_time_by_subtask()
            if subtasks:
                self.plot_subtasks_bar(top_n=20)
            
            tags = self.analyzer.get_time_by_tags()
            if tags:
                self.plot_tags_wordcloud_style()
            
            self.plot_combined_dashboard()


def get_week_dates(year, week):
    """Get start and end dates for a given week number."""
    # ISO week starts on Monday
    jan_4 = datetime(year, 1, 4)
    week_1_start = jan_4 - timedelta(days=jan_4.weekday())
    start = week_1_start + timedelta(weeks=week - 1)
    end = start + timedelta(days=7)
    return start, end


def get_current_week():
    """Get the current week's start and end dates."""
    today = datetime.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=7)
    return start, end


def get_current_month():
    """Get the current month's start and end dates."""
    today = datetime.today()
    start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Get first day of next month, then subtract one day
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def get_month_dates(year, month):
    """Get start and end dates for a given month."""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def get_year_dates(year):
    """Get start and end dates for a given year."""
    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)
    return start, end


def main():
    parser = argparse.ArgumentParser(
        description='Generate time tracking reports from org-clock data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Current week report
  python reports.py --week
  
  # Specific week in 2024
  python reports.py --week --year 2024 --week-num 15
  
  # Current month report
  python reports.py --month
  
  # Specific month
  python reports.py --month --year 2024 --month-num 3
  
  # Year report
  python reports.py --year 2024
  
  # Save reports to directory
  python reports.py --month --output reports/monthly
  
  # Custom date range
  python reports.py --start 2024-01-01 --end 2024-03-31 --output reports/q1_2024
        """
    )
    
    # Report type
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--week', action='store_true', help='Generate weekly report')
    group.add_argument('--month', action='store_true', help='Generate monthly report')
    group.add_argument('--year', type=int, help='Generate yearly report for specified year')
    group.add_argument('--custom', action='store_true', help='Use custom date range (requires --start and --end)')
    
    # Date parameters
    parser.add_argument('--year-val', type=int, help='Year for week/month reports')
    parser.add_argument('--week-num', type=int, help='Week number (1-52)')
    parser.add_argument('--month-num', type=int, help='Month number (1-12)')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    
    # Output
    parser.add_argument('-o', '--output', type=str, help='Output directory for reports')
    parser.add_argument('-f', '--files', nargs='+', help='Org files to analyze (default: predefined list)')
    
    args = parser.parse_args()
    
    # Determine date range
    if args.week:
        if args.year_val and args.week_num:
            start_date, end_date = get_week_dates(args.year_val, args.week_num)
            period_name = f"Week_{args.week_num}_{args.year_val}"
        else:
            start_date, end_date = get_current_week()
            period_name = f"Week_{start_date.isocalendar()[1]}_{start_date.year}"
    elif args.month:
        if args.year_val and args.month_num:
            start_date, end_date = get_month_dates(args.year_val, args.month_num)
            period_name = f"{start_date.strftime('%Y-%m')}"
        else:
            start_date, end_date = get_current_month()
            period_name = f"{start_date.strftime('%Y-%m')}"
    elif args.year:
        start_date, end_date = get_year_dates(args.year)
        period_name = f"Year_{args.year}"
    elif args.custom:
        if not args.start or not args.end:
            parser.error("--custom requires both --start and --end dates")
        start_date = datetime.fromisoformat(args.start)
        end_date = datetime.fromisoformat(args.end)
        period_name = f"{args.start}_to_{args.end}"
    else:
        # Default to current week
        start_date, end_date = get_current_week()
        period_name = f"Week_{start_date.isocalendar()[1]}_{start_date.year}"
    
    # Load files
    files = args.files if args.files else ORG_FILES
    
    print(f"Loading org files from {start_date.date()} to {end_date.date()}...")
    clock_root = org_time.load_files(files, start_date, end_date)
    
    if clock_root.totalTime == 0:
        print(f"\nNo time tracked in the specified period.")
        return
    
    # Create analyzer and report generator
    analyzer = TimeAnalyzer(clock_root)
    report_gen = ReportGenerator(analyzer, period_name, start_date, end_date)
    
    # Generate reports
    report_gen.generate_full_report(args.output)


if __name__ == "__main__":
    main()
