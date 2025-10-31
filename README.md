# Org Clock Analyzer

A comprehensive time tracking analysis tool for org-mode clock data. Parse your org files, analyze time spent across projects, and generate beautiful reports with interactive visualizations.

## Features

### 🔍 Data Analysis
- Parse multiple org files simultaneously
- Track time hierarchically across projects and tasks
- Filter by date ranges
- Analyze by macro areas (org files), topics (first-layer tasks), and tags
- Export to JSON for further processing

### 📊 Rich Reporting
- **Weekly Reports**: Track productivity week by week with trend analysis
- **Monthly Reports**: Comprehensive monthly summaries
- **Yearly Reports**: Annual overview with monthly breakdown
- **Custom Periods**: Analyze any date range
- **Comparison Reports**: Compare multiple time periods side-by-side

### 📈 Interactive Visualizations
- Pie charts for time distribution
- Horizontal bar charts for top topics
- Tag bubble charts
- Treemaps for hierarchical data
- Multi-week/month trend charts
- Stacked area charts for category comparison
- Combined dashboards

### 🌐 Web Interface
- Browse all reports from a single index page
- Interactive Plotly charts
- Responsive design
- Direct links to all visualizations and data exports
- Auto-generated index with metadata

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/valsdav/org-clock-analyzer.git
cd org-clock-analyzer

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Your Org Files

Edit `reports.py` and update the `ORG_FILES` list with paths to your org files:

```python
ORG_FILES = [
    "/path/to/your/Project1.org",
    "/path/to/your/Project2.org",
    # Add your org files here
]
```

### 3. Generate Reports

```bash
# Quick start - Generate all common reports
python quick_reports.py

# All years quick pipeline (generate across every detected year)
python quick_reports_all_years.py

# Or use the CLI for specific reports
python reports.py --week          # Current week
python reports.py --month         # Current month
python reports.py --year 2024     # Specific year

# All years at once (auto-detected from your org files)
python generate_reports.py yearly-all

# Or via Python one-liner
python -c "from generate_reports import generate_yearly_reports_for_all_years; generate_yearly_reports_for_all_years()"
```

### 4. Browse Reports

Open `reports/index.html` in your web browser to browse all generated reports!

## Usage Examples

### Weekly Productivity Review
```bash
# Last 4 weeks with trends
python generate_reports.py weekly 4
```

### Monthly Summary
```bash
# Current month
python reports.py --month --output reports/current_month
```

### Quarterly Analysis
```bash
# Custom Q1 report
python reports.py --custom --start 2024-01-01 --end 2024-03-31 --output reports/Q1_2024
```

### Year in Review
```bash
# Full year with monthly breakdown
python generate_reports.py yearly 2024

# ALL years with data (discovers years from your org clocks)
python generate_reports.py yearly-all
```

### Browse All Reports
```bash
# Generate browsable index page
python generate_index.py

# Generate consolidated weekly view (all weeks in one page)
python weekly_consolidated.py -n 8

# Generate consolidated monthly view (all months in one page)
python monthly_consolidated.py -n 12

# Generate full year monthly view
python monthly_consolidated.py -y 2024

# Open reports/index.html in your browser
```

## Project Structure

```
org_clock_analyzer/
├── org_time.py              # Core parsing and data structures
├── reports.py               # Main reporting CLI
├── generate_reports.py      # Pre-configured report templates
├── quick_reports.py         # One-command report generation
├── generate_index.py        # HTML index page generator
├── weekly_consolidated.py   # Consolidated weekly reports (all weeks in one page)
├── monthly_consolidated.py  # Consolidated monthly reports (all months in one page)
├── examples.py              # Usage examples and API demos
├── server.py                # Flask web server
├── weekly_analysis.py       # Legacy weekly analysis
├── requirements.txt         # Python dependencies
├── REPORTS_README.md        # Detailed reporting documentation
└── reports/                 # Generated reports directory
    ├── index.html           # Browse all reports
    ├── weekly_consolidated.html   # All weekly reports in one page
    ├── monthly_consolidated.html  # All monthly reports in one page
    ├── weekly/
    │   └── Week_XX_YYYY/ (individual week reports)
    ├── monthly/
    │   └── YYYY-MM/ (individual month reports)
    └── yearly/
        └── Year_YYYY/ (individual year reports)
```

## Scripts Overview

### `reports.py` - Main CLI Tool
Full-featured command-line interface for generating any type of report.

```bash
python reports.py --help
python reports.py --week
python reports.py --month --year-val 2024 --month-num 3
python reports.py --year 2024 --output reports/year_2024
```

### `generate_reports.py` - Convenience Functions
Pre-configured report generation with comparison features.

```bash
python generate_reports.py weekly [n_weeks]
python generate_reports.py monthly [year] [month]
python generate_reports.py yearly [year]
python generate_reports.py yearly-all         # Generate yearly reports for all years with data
python generate_reports.py all
```

### `quick_reports.py` - One-Command Setup
Generate all common reports with a single command.

```bash
python quick_reports.py
```

Generates:
- Last 4 weeks comparison
- Consolidated weekly view (all weeks in one page)
- Current month report
- Consolidated monthly view (last 6 months in one page)
- Current year report
- Index page for browsing

Tip: To build yearly reports for every year, run `python generate_reports.py yearly-all` after this.

### `quick_reports_all_years.py` - All Years Pipeline
Generate a comprehensive set of reports across ALL detected years.

What it does:
- Yearly reports for each year
- Consolidated monthly page for each year (12 months per page)
- Consolidated weekly page for each year (all weeks per page)
- Individual monthly reports for months that have data
- Consolidated weekly page for each month (all weeks touching the month)
- One big all-years calendar heatmap
- Regenerates the index page

Usage:

```bash
python quick_reports_all_years.py
```

### `generate_index.py` - Index Page Generator
Create a browsable HTML index of all your reports.

```bash
python generate_index.py
python generate_index.py -o custom/path/index.html -d reports
```

### `examples.py` - API Examples
Interactive examples showing how to use the Python API for custom analyses.

```bash
python examples.py
```

## Python API

```python
from datetime import datetime
import org_time
from reports import TimeAnalyzer, ReportGenerator

# Load data
start_date = datetime(2024, 3, 1)
end_date = datetime(2024, 4, 1)
clock_root = org_time.load_files(files, start_date, end_date)

# Analyze
analyzer = TimeAnalyzer(clock_root)
areas = analyzer.get_time_by_macro_area()
topics = analyzer.get_time_by_topic()
tags = analyzer.get_time_by_tags()
detailed_df = analyzer.get_detailed_breakdown()

# Generate report
report_gen = ReportGenerator(analyzer, "March_2024", start_date, end_date)
report_gen.generate_full_report("reports/march")
```

## Analysis Dimensions

### Macro Area (Org Files)
The org file itself represents a broad category of work.
- Example: "Research.org", "Teaching.org", "Administration.org"

### Topics (First-Layer Tasks)
First-layer headings under each org file represent specific projects.
- Format: "AreaName/TopicName"
- Example: "Research/Paper A", "Teaching/Course B"

### Tags
Org-mode tags on tasks represent activity types or contexts.
- Example: `:meeting:`, `:coding:`, `:writing:`, `:reading:`
- Aggregated across all task levels

## Output Files

### HTML Visualizations
- `dashboard_*.html` - Combined multi-panel dashboard
- `pie_areas_*.html` - Pie chart of time by macro area
- `bar_topics_*.html` - Bar chart of top topics
- `tags_*.html` - Tag bubble chart
- `*_trend.html` - Trend analysis charts
- `*_comparison.html` - Multi-period comparison charts

### CSV Data Exports
- `areas_*.csv` - Time by macro area
- `topics_*.csv` - Time by topics
- `tags_*.csv` - Time by tags
- `detailed_*.csv` - Full hierarchical breakdown
- `*_summary.csv` - Period summary data

## Dependencies

- `orgparse` - Parse org-mode files
- `pandas` - Data manipulation
- `matplotlib` - Basic plotting
- `plotly` - Interactive visualizations
- `python-dateutil` - Date handling
- `flask` - Web server (optional)
- `flask-cors` - CORS support (optional)

## Tips for Better Reports

1. **Consistent Tags**: Use consistent tags across org files for accurate tag analysis
2. **Clear Hierarchy**: Organize tasks with meaningful first-layer topics
3. **Regular Reviews**: Generate weekly reports to track productivity patterns
4. **Date Ranges**: Use custom date ranges for project-specific analysis
5. **Export Data**: Use CSV exports for further analysis in spreadsheet tools

## Web Server

Run the Flask web server for a dynamic API:

```bash
python server.py
```

Access the API at `http://localhost:5000/data?start=2024-01-01&end=2024-12-31`

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests



---

For detailed reporting documentation, see [REPORTS_README.md](REPORTS_README.md).
