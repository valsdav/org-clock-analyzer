# Org Clock Time Tracking Reports

A comprehensive reporting system for analyzing time tracked in org-mode files. Generate detailed reports with tables and visualizations organized by macro area (org files), topics (first-layer tasks), and tags.

## Features

- **Multiple Report Types**: Weekly, monthly, yearly, and custom date range reports
- **Rich Visualizations**: Pie charts, bar charts, treemaps, and dashboards
- **Multiple Dimensions**: Analysis by macro area, topics, and tags
- **Export Options**: HTML visualizations and CSV data exports
- **Trend Analysis**: Compare multiple periods to identify patterns

## Installation

Install required dependencies:

```bash
pip install pandas matplotlib plotly orgparse python-dateutil
```

## Usage

### Browsing Reports

After generating reports, you can browse them all from a single page:

```bash
# Generate the index page
python generate_index.py

# Or specify custom paths
python generate_index.py -o reports/index.html -d reports
```

This creates a beautiful, interactive HTML page at `reports/index.html` that:
- Automatically scans all your reports
- Organizes them by type (weekly, monthly, yearly, custom)
- Provides direct links to all HTML visualizations
- Shows CSV data exports with download links
- Displays file sizes and metadata
- Updates automatically when you regenerate

**The index page is automatically generated when you use `quick_reports.py`!**

### Command-Line Reports

The main `reports.py` script provides a flexible CLI for generating reports:

#### Current Week Report
```bash
python reports.py --week
```

#### Specific Week Report
```bash
python reports.py --week --year-val 2024 --week-num 15
```

#### Current Month Report
```bash
python reports.py --month
```

#### Specific Month Report
```bash
python reports.py --month --year-val 2024 --month-num 3
```

#### Yearly Report
```bash
python reports.py --year 2024
```

#### Custom Date Range
```bash
python reports.py --custom --start 2024-01-01 --end 2024-03-31
```

#### Save to Directory
```bash
python reports.py --month --output reports/monthly
```

### Pre-configured Report Generation

The `generate_reports.py` script provides convenience functions:

```bash
# Last 4 weeks comparison
python generate_reports.py weekly

# Last N weeks comparison
python generate_reports.py weekly 8

# Current month
python generate_reports.py monthly

# Specific month
python generate_reports.py monthly 2024 3

# Yearly report with monthly breakdown
python generate_reports.py yearly 2024

# Generate all reports
python generate_reports.py all
```

## Report Contents

Each report includes:

### 1. Summary Tables
- Total time tracked
- Average time per day
- Time by macro area (org files) with percentages
- Top 15 topics with percentages
- Time by tags with percentages

### 2. Visualizations

#### Pie Chart - Macro Areas
Distribution of time across different org files.

#### Bar Chart - Top Topics
Horizontal bar chart showing the most time-intensive topics.

#### Tag Visualization
Bubble chart showing time distribution by tags.

#### Combined Dashboard
Multi-panel dashboard with:
- Pie chart of macro areas
- Top 10 topics bar chart
- Tags breakdown
- Treemap of hierarchical time distribution

### 3. Data Exports (CSV)
- `areas_*.csv`: Time by macro area
- `topics_*.csv`: Time by topics
- `tags_*.csv`: Time by tags
- `detailed_*.csv`: Full hierarchical breakdown

## Output Structure

When saving reports to a directory:

```
reports/
├── index.html                  # Main index page to browse all reports
├── weekly_consolidated.html    # Consolidated view of last 4 weeks
├── monthly_consolidated.html   # Consolidated view of last 6 months
├── weekly/
│   └── Week_XX_YYYY/
│       ├── dashboard_Week_XX_YYYY.html
│       ├── pie_areas_Week_XX_YYYY.html
│       ├── bar_topics_Week_XX_YYYY.html
│       ├── bar_subtasks_Week_XX_YYYY.html
│       ├── tags_Week_XX_YYYY.html
│       ├── areas_Week_XX_YYYY.csv
│       ├── topics_Week_XX_YYYY.csv
│       ├── subtasks_Week_XX_YYYY.csv
│       ├── tags_Week_XX_YYYY.csv
│       └── detailed_Week_XX_YYYY.csv
├── monthly/
│   └── YYYY-MM/
│       ├── dashboard_YYYY-MM.html
│       ├── pie_areas_YYYY-MM.html
│       ├── bar_topics_YYYY-MM.html
│       ├── bar_subtasks_YYYY-MM.html
│       ├── tags_YYYY-MM.html
│       ├── areas_YYYY-MM.csv
│       ├── topics_YYYY-MM.csv
│       ├── subtasks_YYYY-MM.csv
│       ├── tags_YYYY-MM.csv
│       └── detailed_YYYY-MM.csv
└── yearly/
    └── Year_YYYY/
        ├── [yearly report files]
        ├── monthly_trend_YYYY.html
        ├── monthly_areas_breakdown_YYYY.html
        └── monthly_summary_YYYY.csv
```

## Configuration

Edit the `ORG_FILES` list in `reports.py` to specify which org files to analyze:

```python
ORG_FILES = [
    "/path/to/your/Project1.org",
    "/path/to/your/Project2.org",
    # ... add your org files
]
```

## Python API

You can also use the reporting system programmatically:

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

# Generate report
report_gen = ReportGenerator(analyzer, "March_2024", start_date, end_date)
report_gen.generate_full_report("reports/march")
```

## Analysis Dimensions

### Macro Area
- Corresponds to the org file itself
- Example: "ETH.org", "CMS.org", "Learning.org"
- Represents broad categories of work

### Topics
- First-layer tasks under each org file
- Format: "AreaName/TopicName"
- Example: "ETH/Research", "CMS/Analysis"
- Represents specific projects or activities

### Tags
- Org-mode tags attached to tasks
- Aggregated across all levels
- Example: `:meeting:`, `:coding:`, `:writing:`
- Represents activity types or contexts

## Examples

### Weekly Productivity Review
```bash
# Generate last 4 weeks to see trends
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
```

## Tips

1. **Regular Reviews**: Set up weekly reports to track productivity patterns
2. **Tag Consistency**: Use consistent tags across org files for better analysis
3. **Hierarchical Structure**: Organize tasks with clear first-layer topics for better topic analysis
4. **Compare Periods**: Use the comparison features to identify trends and changes
5. **Export Data**: Use CSV exports for further analysis in spreadsheet tools

## Troubleshooting

**No data in report:**
- Check that the date range includes clocked time entries
- Verify org files are accessible at the specified paths
- Ensure org files contain valid clock entries

**Import errors:**
- Install missing packages: `pip install pandas matplotlib plotly orgparse python-dateutil`

**Wrong time zone:**
- Org-clock times are parsed as-is from the org files
- Ensure your org files have consistent time zones

## License

This tool is part of the org-clock-analyzer project.
