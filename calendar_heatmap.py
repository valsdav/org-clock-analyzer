#!/usr/bin/env python3
"""
Generate a calendar (GitHub-style) heatmap of daily working hours.
- Computes total hours per day from org-clock entries.
- Renders a compact HTML grid with weeks as columns and weekdays as rows.
- Default range: last 12 full months up to today (inclusive), aligned to Monday.

Outputs to reports/calendar/last_12_months.html by default.
"""
from __future__ import annotations

from datetime import datetime, timedelta, date
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import json

try:
    # orgparse is used to inspect raw clock entries
    from orgparse import load as org_load
except Exception:
    org_load = None

# Reuse configured ORG_FILES and nav helper
from reports import ORG_FILES, add_nav_to_html


def _clamp_interval(start, end, window_start, window_end):
    """Clamp a [start, end) interval to [window_start, window_end); return None if no overlap.
    Uses datetime-like comparisons; types are intentionally loose to accommodate orgparse types.
    """
    s = max(start, window_start)
    e = min(end, window_end)
    if e <= s:
        return None
    return s, e


def _accumulate_by_day(daily: Dict[date, float], start, end) -> None:
    """Accumulate hours of [start, end) into daily[date]. Splits across midnights. Types are datetime-like."""
    cur = start
    while cur.date() < end.date():
        next_midnight = datetime.combine(cur.date() + timedelta(days=1), datetime.min.time())
        seg_end = min(next_midnight, end)
        hours = (seg_end - cur).total_seconds() / 3600.0
        if hours > 0:
            daily[cur.date()] += hours
        cur = seg_end
    # Final same-day tail (or entire if same day)
    if cur < end:
        hours = (end - cur).total_seconds() / 3600.0
        if hours > 0:
            daily[cur.date()] += hours


def compute_activity_detail(files: List[str], start: datetime, end: datetime):
    """
    Compute detailed activity:
    - daily_hours: Dict[date, float]
    - daily_areas: Dict[date, Dict[area, float]]
    - week_hours: Dict[str, float]  (key: "YYYY-WW")
    - week_areas: Dict[str, Dict[area, float]]
    """
    if org_load is None:
        raise RuntimeError("orgparse is required to compute daily hours")

    daily_hours: Dict[date, float] = defaultdict(float)
    daily_areas: Dict[date, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    week_hours: Dict[str, float] = defaultdict(float)
    week_areas: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def week_key(d: date) -> str:
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

    for f in files:
        try:
            root = org_load(f)
        except Exception as e:
            print(f"Error loading {f}: {e}")
            continue

        area_name = Path(f).stem  # Use file base name as macro area

        stack = [root]
        while stack:
            node = stack.pop()
            if hasattr(node, "clock") and node.clock:
                for cl in node.clock:
                    if cl.end is None:
                        continue
                    # Normalize datetimes and clamp
                    s_raw, e_raw = cl.start, cl.end
                    clamped = _clamp_interval(s_raw, e_raw, start, end)
                    if not clamped:
                        continue
                    s, e = clamped
                    # Ensure datetime types
                    if not isinstance(s, datetime):
                        if isinstance(s, date):
                            s = datetime.combine(s, datetime.min.time())
                    if not isinstance(e, datetime):
                        if isinstance(e, date):
                            e = datetime.combine(e, datetime.min.time())
                    # Split across days
                    cur = s
                    while cur.date() < e.date():
                        next_midnight = datetime.combine(cur.date() + timedelta(days=1), datetime.min.time())
                        seg_end = min(next_midnight, e)
                        hours = (seg_end - cur).total_seconds() / 3600.0
                        if hours > 0:
                            d = cur.date()
                            daily_hours[d] += hours
                            daily_areas[d][area_name] += hours
                            wk = week_key(d)
                            week_hours[wk] += hours
                            week_areas[wk][area_name] += hours
                        cur = seg_end
                    if cur < e:
                        hours = (e - cur).total_seconds() / 3600.0
                        if hours > 0:
                            d = cur.date()
                            daily_hours[d] += hours
                            daily_areas[d][area_name] += hours
                            wk = week_key(d)
                            week_hours[wk] += hours
                            week_areas[wk][area_name] += hours
            for child in getattr(node, 'children', []):
                stack.append(child)

    return dict(daily_hours), {k: dict(v) for k, v in daily_areas.items()}, dict(week_hours), {k: dict(v) for k, v in week_areas.items()}


def _monday_on_or_before(dt: datetime) -> datetime:
    return dt - timedelta(days=dt.weekday())


def _next_midnight(dt: datetime) -> datetime:
    return datetime.combine(dt.date() + timedelta(days=1), datetime.min.time())


def _month_abbr(m: int) -> str:
    return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m-1]


def _build_weeks(start: datetime, end: datetime) -> List[List[date]]:
    """Return list of weeks (each 7 dates, Mon..Sun) covering [start, end)."""
    weeks: List[List[date]] = []
    cur = _monday_on_or_before(start)
    while cur < end:
        week = [(cur + timedelta(days=i)).date() for i in range(7)]
        weeks.append(week)
        cur += timedelta(days=7)
    return weeks


def _quantile_bins(values: List[float]) -> Tuple[float, float, float]:
    """Return q1, q2, q3 for non-zero values; fallback to simple thresholds if empty."""
    nz = sorted(v for v in values if v > 0)
    if not nz:
        return (0.25, 0.5, 0.75)  # unused; will map everything to zero color
    def q(p: float) -> float:
        idx = max(0, min(len(nz)-1, int(round(p*(len(nz)-1)))))
        return nz[idx]
    return q(0.25), q(0.5), q(0.75)


def _color_for(hours: float, q1: float, q2: float, q3: float) -> str:
    """GitHub-like green scale for activity."""
    if hours <= 0:
        return "#ebedf0"  # empty
    if hours <= q1:
        return "#9be9a8"
    if hours <= q2:
        return "#40c463"
    if hours <= q3:
        return "#30a14e"
    return "#216e39"


def _legend_html(q1: float, q2: float, q3: float) -> str:
    return f'''
    <div class="legend">
      <span class="legend-label">Less</span>
      <span class="swatch" style="background:#ebedf0"></span>
      <span class="swatch" style="background:#9be9a8"></span>
      <span class="swatch" style="background:#40c463"></span>
      <span class="swatch" style="background:#30a14e"></span>
      <span class="swatch" style="background:#216e39"></span>
      <span class="legend-label">More</span>
    </div>
    <div class="legend-note">Bins based on non-zero daily hours quartiles: {q1:.2f}, {q2:.2f}, {q3:.2f} h</div>
    '''


def generate_calendar_heatmap(output_file: str = "reports/calendar/last_12_months.html", months: int = 12, files: List[str] | None = None) -> str:
    """
    Generate a calendar heatmap HTML for the last `months` months (inclusive of today).
    Returns the absolute file path of the generated HTML.
    """
    files = files or ORG_FILES

    # End at next midnight to include today fully
    today = datetime.today()
    end = _next_midnight(today)
    # Start at first day of the month (months-1 ago), then align to Monday
    start_month = (today.replace(day=1) - timedelta(days=0))
    # Move back months-1 and set day=1
    for _ in range(months-1):
        prev_month_last_day = start_month - timedelta(days=1)
        start_month = prev_month_last_day.replace(day=1)
    start = _monday_on_or_before(start_month)

    # Compute detailed activity
    daily, daily_areas, week_totals, week_areas = compute_activity_detail(files, start, end)

    # Build week grid covering range
    weeks = _build_weeks(start, end)

    # Compute bins
    values = [daily.get(d, 0.0) for wk in weeks for d in wk]
    q1, q2, q3 = _quantile_bins(values)

    # Month labels (at first Monday column that contains the 1st day)
    month_labels: List[Tuple[str, int]] = []  # (abbr, column_index)
    seen_months: set[Tuple[int,int]] = set()
    for idx, wk in enumerate(weeks):
        # If this week contains the first of any month and not yet labeled, add label
        for d in wk:
            if d.day == 1:
                key = (d.year, d.month)
                if key not in seen_months:
                    seen_months.add(key)
                    month_labels.append((_month_abbr(d.month), idx))
                break

    # Prebuild summaries to embed in HTML
    # Map date string -> week key for quick lookup
    day_to_week: Dict[str, str] = {}
    def week_key(d: date) -> str:
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

    # Build day summaries
    day_summaries: Dict[str, dict] = {}
    for wk in weeks:
        for d in wk:
            ds = d.isoformat()
            day_to_week[ds] = week_key(d)
            total = daily.get(d, 0.0)
            areas = daily_areas.get(d, {})
            # Top 5 areas with percentage
            top = sorted(areas.items(), key=lambda x: x[1], reverse=True)[:5]
            top = [
                {
                    'name': name,
                    'h': round(h, 2),
                    'pct': round((h/total*100.0), 1) if total > 0 else 0.0
                }
                for name, h in top
            ]
            day_summaries[ds] = {
                'total': round(total, 2),
                'areas': top,
            }

    # Build week summaries for weeks present in grid
    week_summaries: Dict[str, dict] = {}
    weeks_in_grid = sorted({week_key(d) for wk in weeks for d in wk})
    for wkkey in weeks_in_grid:
        total = week_totals.get(wkkey, 0.0)
        areas = week_areas.get(wkkey, {})
        top = sorted(areas.items(), key=lambda x: x[1], reverse=True)[:5]
        top = [
            {
                'name': name,
                'h': round(h, 2),
                'pct': round((h/total*100.0), 1) if total > 0 else 0.0
            }
            for name, h in top
        ]
        # Potential link to weekly dashboard if it exists
        # Compute week number and year from key
        year, wnum = wkkey.split('-W')
        week_dir_name = f"Week_{int(wnum)}_{int(year)}"
        weekly_dashboard_rel = f"../weekly/{week_dir_name}/dashboard_{week_dir_name}.html"
        # Check existence relative to output path
        weekly_dashboard_abs = (Path(output_file).parent.parent / 'weekly' / week_dir_name / f'dashboard_{week_dir_name}.html')
        link = weekly_dashboard_rel if weekly_dashboard_abs.exists() else None
        week_summaries[wkkey] = {
            'total': round(total, 2),
            'areas': top,
            'link': link,
            'label': f"Week {int(wnum)} {year}",
        }

    embedded_data = {
        'days': day_summaries,
        'weeks': week_summaries,
        'dayToWeek': day_to_week,
    }

    # Build HTML
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"UTF-8\">",
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        "  <title>Calendar Heatmap - Last 12 Months</title>",
    "  <style>",
        "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: #fff; color: #333; padding: 20px; }",
        "    .container { max-width: 1100px; margin: 0 auto; }",
        "    h1 { font-size: 1.8em; margin-bottom: 6px; }",
        "    .subtitle { color: #666; margin-bottom: 16px; }",
        "    .cal-wrapper { display: inline-block; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; background: #fafafa; }",
        "    .months { display: grid; grid-auto-flow: column; grid-auto-columns: 12px; margin-left: 32px; margin-bottom: 6px; }",
        "    .month { font-size: 10px; color: #555; text-align: left; }",
        "    .grid { display: grid; grid-auto-flow: column; grid-auto-columns: 12px; gap: 2px; }",
        "    .week { display: grid; grid-template-rows: repeat(7, 12px); gap: 2px; }",
        "    .day { width: 12px; height: 12px; border-radius: 2px; background: #ebedf0; position: relative; }",
        "    .day:hover::after { content: attr(data-tooltip); position: absolute; left: 100%; top: 50%; transform: translateY(-50%); margin-left: 8px; background: rgba(0,0,0,0.8); color: #fff; padding: 4px 6px; border-radius: 4px; font-size: 11px; white-space: nowrap; z-index: 10; }",
        "    .labels { display: grid; grid-template-rows: repeat(7, 12px); gap: 2px; margin-right: 8px; font-size: 10px; color: #666; }",
        "    .legend { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #555; margin-top: 10px; }",
        "    .legend .swatch { width: 12px; height: 12px; border-radius: 2px; display: inline-block; }",
        "    .legend-label { margin: 0 4px; }",
    "    .legend-note { font-size: 11px; color: #777; margin-top: 4px; }",
        "    .actions { margin-top: 10px; font-size: 12px; color: #666; }",
        "    a { color: #667eea; text-decoration: none; }",
    "    /* Modal */",
    "    .modal { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: none; align-items: center; justify-content: center; z-index: 10000; }",
    "    .modal.active { display: flex; }",
    "    .modal-card { background: #fff; width: 680px; max-width: 95vw; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); overflow: hidden; }",
    "    .modal-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #f8f9fa; border-bottom: 1px solid #eee; }",
    "    .modal-title { font-weight: 600; }",
    "    .modal-body { padding: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }",
    "    .section-title { font-size: 14px; font-weight: 600; color: #555; margin-bottom: 8px; }",
    "    .row { display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; border-bottom: 1px dashed #eee; }",
    "    .row:last-child { border-bottom: none; }",
    "    .bar { height: 6px; background: #e9ecef; border-radius: 3px; overflow: hidden; margin-top: 2px; }",
    "    .bar > span { display: block; height: 100%; background: #40c463; }",
    "    .muted { color: #777; font-size: 12px; }",
    "    .link { color: #667eea; text-decoration: none; font-size: 12px; }",
    "    .close-btn { cursor: pointer; border: none; background: transparent; font-size: 18px; }",
        "  </style>",
    f"  <script>var CAL_DATA = {json.dumps(embedded_data)};</script>",
        "</head>",
        "<body>",
        "  <div class=\"container\">",
        f"    <h1>Calendar Heatmap</h1>",
        f"    <div class=\"subtitle\">Last {months} months up to {today.strftime('%Y-%m-%d')}</div>",
        "    <div class=\"cal-wrapper\">",
        "      <div class=\"months\">",
    ]

    # Render month labels row: empty cells up to the column index then label
    last_col = 0
    for label, col in month_labels:
        # add empty columns between last_col and col
        gap = col - last_col
        if gap > 0:
            html.append("        " + ("<div class=\"month\"></div>" * gap))
        html.append(f"        <div class=\"month\">{label}</div>")
        last_col = col + 1
    html.append("      </div>")

    # Weekday labels (Mon, Wed, Fri only to reduce clutter)
    html += [
        "      <div style=\"display:flex;\">",
        "        <div class=\"labels\">",
        "          <div>Mon</div>",
        "          <div></div>",
        "          <div>Wed</div>",
        "          <div></div>",
        "          <div>Fri</div>",
        "          <div></div>",
        "          <div>Sun</div>",
        "        </div>",
        "        <div class=\"grid\">",
    ]

    # Render weeks and days
    for wk in weeks:
        html.append("          <div class=\"week\">")
        for d in wk:
            hrs = daily.get(d, 0.0)
            color = _color_for(hrs, q1, q2, q3)
            tooltip = f"{d.isoformat()}: {hrs:.2f} h"
            html.append(f'            <div class="day" style="background:{color}" data-tooltip="{tooltip}" data-date="{d.isoformat()}" onclick="showSummary(\'{d.isoformat()}\')"></div>')
        html.append("          </div>")

    # Close grid and wrapper
    html += [
        "        </div>",
        "      </div>",
        _legend_html(q1, q2, q3),
        "      <div class=\"actions\">",
        f"        Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • Range: {start.date()} to {(end - timedelta(seconds=1)).date()} (inclusive)",
        "      </div>",
        "    </div>",
        "  </div>",
        "  <div id=\"modal\" class=\"modal\">",
        "    <div class=\"modal-card\">",
        "      <div class=\"modal-header\">",
        "        <div class=\"modal-title\" id=\"modal-title\">Summary</div>",
        "        <button class=\"close-btn\" onclick=\"closeModal()\">×</button>",
        "      </div>",
        "      <div class=\"modal-body\">",
        "        <div>",
        "          <div class=\"section-title\">Day Summary</div>",
        "          <div id=\"day-total\" class=\"muted\"></div>",
        "          <div id=\"day-areas\"></div>",
        "        </div>",
        "        <div>",
        "          <div class=\"section-title\">Week Summary</div>",
        "          <div id=\"week-label\" class=\"muted\"></div>",
        "          <div id=\"week-total\" class=\"muted\"></div>",
        "          <div id=\"week-areas\"></div>",
        "          <div id=\"week-link\" style=\"margin-top:8px;\"></div>",
        "        </div>",
        "      </div>",
        "    </div>",
        "  </div>",
        "  <script>",
        "    function closeModal(){ document.getElementById('modal').classList.remove('active'); }",
        "    function showSummary(dateStr){",
        "      const modal = document.getElementById('modal');",
        "      const ds = CAL_DATA.days[dateStr] || {total:0, areas:[]};",
        "      const wkKey = CAL_DATA.dayToWeek[dateStr];",
        "      const ws = (wkKey && CAL_DATA.weeks[wkKey]) ? CAL_DATA.weeks[wkKey] : {total:0, areas:[], label:'', link:null};",
        "      document.getElementById('modal-title').innerText = 'Summary for ' + dateStr;",
        "      document.getElementById('day-total').innerText = 'Total: ' + ds.total.toFixed(2) + ' h';",
        "      document.getElementById('day-areas').innerHTML = ds.areas.map(a => `\n            <div class=\"row\">\n              <div>${a.name}</div>\n              <div>${a.h.toFixed(2)} h (${a.pct.toFixed(1)}%)</div>\n            </div>\n            <div class=\"bar\"><span style=\"width:${a.pct}%\"></span></div>`).join('');",
        "      document.getElementById('week-label').innerText = ws.label || '';",
        "      document.getElementById('week-total').innerText = ws.total ? ('Total: ' + ws.total.toFixed(2) + ' h') : 'Total: 0 h';",
        "      document.getElementById('week-areas').innerHTML = (ws.areas||[]).map(a => `\n            <div class=\"row\">\n              <div>${a.name}</div>\n              <div>${a.h.toFixed(2)} h (${a.pct.toFixed(1)}%)</div>\n            </div>\n            <div class=\"bar\"><span style=\"width:${a.pct}%\"></span></div>`).join('');",
        "      document.getElementById('week-link').innerHTML = ws.link ? (`<a class=\"link\" target=\"_blank\" href=\"${ws.link}\">Open weekly dashboard →</a>`) : '<span class=\"muted\">Weekly dashboard not found for this week.</span>';",
        "      modal.classList.add('active');",
        "    }",
        "    // Close modal on backdrop click",
        "    document.getElementById('modal').addEventListener('click', (e)=>{ if(e.target.id==='modal'){ closeModal(); } });",
        "  </script>",
        "</body>",
        "</html>",
    ]

    out_path.write_text("\n".join(html), encoding="utf-8")
    try:
        # Add consistent navigation bar
        add_nav_to_html(str(out_path))
    except Exception:
        pass

    print(f"✓ Calendar heatmap generated: {out_path.absolute()}")
    return str(out_path.absolute())


def generate_inline_calendar_for_period(start: datetime, end: datetime, files: List[str] | None = None,
                                        cell_size: int = 8, gap: int = 1,
                                        enable_click: bool = False,
                                        id_suffix: str | None = None,
                                        weekly_link_prefix_to_weekly: str = 'weekly/',
                                        include_month_summary: bool = False,
                                        monthly_link_prefix_to_monthly: str = 'monthly/') -> str:
    """
    Return a small inline HTML snippet of a calendar heatmap for [start, end).
    - self-contained styles (inline) to avoid index.css conflicts
    - uses simple title attribute for tooltips (native browser tooltip)
    - when enable_click=True, embeds a small modal and JS to show day+week summary and link to the weekly dashboard
      weekly_link_prefix_to_weekly should be a relative href to the 'reports/weekly' folder from the page where this snippet is inserted, e.g.:
        - 'weekly/' when the page is at reports/ (index or consolidated pages)
        - '../../weekly/' when the page is at reports/monthly/YYYY-MM/ or reports/yearly/Year_YYYY/
        - when include_month_summary=True, also shows a Month Summary with a link to the monthly dashboard. monthly_link_prefix_to_monthly should be
            relative to the page where this snippet is inserted (e.g. 'monthly/' from reports/index.html).
    """
    files = files or ORG_FILES
    daily, daily_areas, week_totals, week_areas = compute_activity_detail(files, start, end)

    weeks = _build_weeks(start, end)
    values = [daily.get(d, 0.0) for wk in weeks for d in wk]
    q1, q2, q3 = _quantile_bins(values)

    month_labels = []
    seen_months = set()
    for idx, wk in enumerate(weeks):
        for d in wk:
            if d.day == 1:
                key = (d.year, d.month)
                if key not in seen_months:
                    seen_months.add(key)
                    month_labels.append((_month_abbr(d.month), idx))
                break

    # Inline styles
    cs = cell_size
    g = gap

    html = []
    html.append('<div style="display:inline-block; padding:6px; border:1px solid #e5e7eb; border-radius:8px; background:#fff;">')
    # Month labels row
    html.append(f'<div style="display:grid; grid-auto-flow:column; grid-auto-columns:{cs}px; margin-left:{int(cs*2.5)}px; margin-bottom:4px;">')
    last_col = 0
    for label, col in month_labels:
        gap_cols = col - last_col
        if gap_cols > 0:
            html.append("<div></div>" * gap_cols)
        html.append(f'<div style="font-size:10px; color:#666;">{label}</div>')
        last_col = col + 1
    html.append("</div>")

    # Left weekday labels + grid
    html.append('<div style="display:flex;">')
    # Weekday labels
    html.append(f'<div style="display:grid; grid-template-rows:repeat(7,{cs}px); row-gap:{g}px; margin-right:{g*4}px; font-size:10px; color:#666;">')
    html.extend(["<div>Mon</div>", "<div></div>", "<div>Wed</div>", "<div></div>", "<div>Fri</div>", "<div></div>", "<div>Sun</div>"])
    html.append("</div>")

    # Grid
    html.append(f'<div style="display:grid; grid-auto-flow:column; grid-auto-columns:{cs}px; column-gap:{g}px;">')
    for wk in weeks:
        html.append(f'<div style="display:grid; grid-template-rows:repeat(7,{cs}px); row-gap:{g}px;">')
        for d in wk:
            hrs = daily.get(d, 0.0)
            color = _color_for(hrs, q1, q2, q3)
            title = f"{d.isoformat()}: {hrs:.2f} h"
            if enable_click:
                suffix = id_suffix or f"{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}"
                js_fn = f"showSummary_{suffix}"
                html.append(f'<div title="{title}" data-date="{d.isoformat()}" onclick="{js_fn}(\'{d.isoformat()}\')" style="cursor:pointer; width:{cs}px; height:{cs}px; border-radius:2px; background:{color};"></div>')
            else:
                html.append(f'<div title="{title}" style="width:{cs}px; height:{cs}px; border-radius:2px; background:{color};"></div>')
        html.append("</div>")
    html.append("</div>")  # grid
    html.append("</div>")  # flex

    # If clickable, embed modal + data + JS
    if enable_click:
        suffix = id_suffix or f"{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}"
        # Build data for this snippet
        def week_key(d: date) -> str:
            iso = d.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        day_to_week: Dict[str, str] = {}
        for wk in weeks:
            for d in wk:
                day_to_week[d.isoformat()] = week_key(d)
        day_summaries: Dict[str, dict] = {}
        for ds, wkkey in day_to_week.items():
            d_date = datetime.fromisoformat(ds).date()
            total = daily.get(d_date, 0.0)
            areas = daily_areas.get(d_date, {})
            top = sorted(areas.items(), key=lambda x: x[1], reverse=True)[:5]
            top = [{ 'name': n, 'h': round(h,2), 'pct': round((h/total*100.0),1) if total>0 else 0.0 } for n,h in top]
            day_summaries[ds] = { 'total': round(total,2), 'areas': top }
        week_summaries: Dict[str, dict] = {}
        for wkkey in sorted(set(day_to_week.values())):
            total = week_totals.get(wkkey, 0.0)
            areas = week_areas.get(wkkey, {})
            top = sorted(areas.items(), key=lambda x: x[1], reverse=True)[:5]
            top = [{ 'name': n, 'h': round(h,2), 'pct': round((h/total*100.0),1) if total>0 else 0.0 } for n,h in top]
            year, wnum = wkkey.split('-W')
            week_dir_name = f"Week_{int(wnum)}_{int(year)}"
            rel = f"{weekly_link_prefix_to_weekly}{week_dir_name}/dashboard_{week_dir_name}.html"
            abs_path = Path('reports/weekly') / week_dir_name / f'dashboard_{week_dir_name}.html'
            link = rel if abs_path.exists() else None
            week_summaries[wkkey] = { 'total': round(total,2), 'areas': top, 'link': link, 'label': f"Week {int(wnum)} {year}" }

        # Optional month summaries
        months_payload = None
        day_to_month: Dict[str, str] = {}
        if include_month_summary:
            def month_key(d: date) -> str:
                return f"{d.year}-{d.month:02d}"
            # Aggregate month totals and areas
            month_totals: Dict[str, float] = {}
            month_area_accum: Dict[str, Dict[str, float]] = {}
            for wk in weeks:
                for d in wk:
                    mk = month_key(d)
                    day_to_month[d.isoformat()] = mk
                    total = daily.get(d, 0.0)
                    if total > 0:
                        month_totals[mk] = month_totals.get(mk, 0.0) + total
                    areas = daily_areas.get(d, {})
                    if areas:
                        acc = month_area_accum.setdefault(mk, {})
                        for n, h in areas.items():
                            acc[n] = acc.get(n, 0.0) + h
            # Build month summaries with links
            months_payload = {}
            for mk in sorted(month_totals.keys()):
                total = month_totals.get(mk, 0.0)
                areas = month_area_accum.get(mk, {})
                top = sorted(areas.items(), key=lambda x: x[1], reverse=True)[:5]
                top = [{ 'name': n, 'h': round(h,2), 'pct': round((h/total*100.0),1) if total>0 else 0.0 } for n,h in top]
                # monthly link
                month_dir = mk
                relm = f"{monthly_link_prefix_to_monthly}{month_dir}/dashboard_{month_dir}.html"
                abs_month = Path('reports/monthly') / month_dir / f'dashboard_{month_dir}.html'
                mlink = relm if abs_month.exists() else None
                # Label like 'October 2025'
                y, m = mk.split('-')
                try:
                    label = datetime(int(y), int(m), 1).strftime('%B %Y')
                except Exception:
                    label = mk
                months_payload[mk] = { 'total': round(total,2), 'areas': top, 'link': mlink, 'label': label }

        payload = { 'days': day_summaries, 'weeks': week_summaries, 'dayToWeek': day_to_week }
        if include_month_summary and months_payload is not None:
            payload['months'] = months_payload
            payload['dayToMonth'] = day_to_month
        data_json = json.dumps(payload)
        html.append(f'''<div id="modal-{suffix}" style="position:fixed; inset:0; background:rgba(0,0,0,0.5); display:none; align-items:center; justify-content:center; z-index:10000;">
    <div class="card" style="background:#fff; width:680px; max-width:95vw; border-radius:10px; box-shadow:0 10px 30px rgba(0,0,0,0.2); overflow:hidden;">
        <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 16px; background:#f8f9fa; border-bottom:1px solid #eee;">
            <div id="modal-title-{suffix}" style="font-weight:600;">Summary</div>
            <button onclick="closeModal_{suffix}()" style="cursor:pointer; border:none; background:transparent; font-size:18px;">×</button>
        </div>
        <div style="padding:16px; display:grid; grid-template-columns:1fr 1fr; gap:16px;">
            <div>
                <div style="font-size:14px; font-weight:600; color:#555; margin-bottom:8px;">Day Summary</div>
                <div id="day-total-{suffix}" style="color:#777; font-size:12px;"></div>
                <div id="day-areas-{suffix}"></div>
            </div>
            <div>
                <div style="font-size:14px; font-weight:600; color:#555; margin-bottom:8px;">Week Summary</div>
                <div id="week-label-{suffix}" style="color:#777; font-size:12px;"></div>
                <div id="week-total-{suffix}" style="color:#777; font-size:12px;"></div>
                <div id="week-areas-{suffix}"></div>
                <div id="week-link-{suffix}" style="margin-top:8px;"></div>
            </div>
        </div>
        <div style="padding:0 16px 16px 16px;">
            <div style="font-size:14px; font-weight:600; color:#555; margin-bottom:8px;">Month Summary</div>
            <div id="month-label-{suffix}" style="color:#777; font-size:12px;"></div>
            <div id="month-total-{suffix}" style="color:#777; font-size:12px;"></div>
            <div id="month-areas-{suffix}"></div>
            <div id="month-link-{suffix}" style="margin-top:8px;"></div>
        </div>
    </div>
</div>
<script>
    const CAL_DATA_{suffix} = {data_json};
    function closeModal_{suffix}(){{ document.getElementById('modal-{suffix}').style.display = 'none'; }}
    function showSummary_{suffix}(dateStr){{
        const modal = document.getElementById('modal-{suffix}');
        const ds = (CAL_DATA_{suffix}.days[dateStr]) || {{ total:0, areas:[] }};
        const wkKey = CAL_DATA_{suffix}.dayToWeek[dateStr];
        const ws = (wkKey && CAL_DATA_{suffix}.weeks[wkKey]) ? CAL_DATA_{suffix}.weeks[wkKey] : {{ total:0, areas:[], label:'', link:null }};
        document.getElementById('modal-title-{suffix}').innerText = 'Summary for ' + dateStr;
        document.getElementById('day-total-{suffix}').innerText = 'Total: ' + ds.total.toFixed(2) + ' h';
        var dayAreasHtml = '';
        for (var i=0; i<ds.areas.length; i++) {{
            var a = ds.areas[i];
            dayAreasHtml += '<div style="display:flex; justify-content:space-between; font-size:13px; padding:4px 0; border-bottom:1px dashed #eee;">' +
                                            '<div>' + a.name + '</div>' +
                                            '<div>' + a.h.toFixed(2) + ' h (' + a.pct.toFixed(1) + '%)</div>' +
                                            '</div>' +
                                            '<div style="height:6px; background:#e9ecef; border-radius:3px; overflow:hidden; margin-top:2px;"><span style="display:block; height:100%; background:#40c463; width:' + a.pct + '%;"></span></div>';
        }}
        document.getElementById('day-areas-{suffix}').innerHTML = dayAreasHtml;
        document.getElementById('week-label-{suffix}').innerText = ws.label || '';
        document.getElementById('week-total-{suffix}').innerText = ws.total ? ('Total: ' + ws.total.toFixed(2) + ' h') : 'Total: 0 h';
        var weekAreasHtml = '';
        for (var j=0; j<(ws.areas||[]).length; j++) {{
            var b = ws.areas[j];
            weekAreasHtml += '<div style="display:flex; justify-content:space-between; font-size:13px; padding:4px 0; border-bottom:1px dashed #eee;">' +
                                             '<div>' + b.name + '</div>' +
                                             '<div>' + b.h.toFixed(2) + ' h (' + b.pct.toFixed(1) + '%)</div>' +
                                             '</div>' +
                                             '<div style="height:6px; background:#e9ecef; border-radius:3px; overflow:hidden; margin-top:2px;"><span style="display:block; height:100%; background:#40c463; width:' + b.pct + '%;"></span></div>';
        }}
        document.getElementById('week-areas-{suffix}').innerHTML = weekAreasHtml;
        document.getElementById('week-link-{suffix}').innerHTML = ws.link ? ('<a style="color:#667eea; text-decoration:none; font-size:12px;" target="_blank" href="' + ws.link + '">Open weekly dashboard →</a>') : '<span style="color:#777; font-size:12px;">Weekly dashboard not found for this week.</span>';
        if (CAL_DATA_{suffix}.months && CAL_DATA_{suffix}.dayToMonth) {{
            const mk = CAL_DATA_{suffix}.dayToMonth[dateStr];
            const ms = mk ? CAL_DATA_{suffix}.months[mk] : {{ total:0, areas:[], label:'', link:null }};
            document.getElementById('month-label-{suffix}').innerText = ms.label || '';
            document.getElementById('month-total-{suffix}').innerText = ms.total ? ('Total: ' + ms.total.toFixed(2) + ' h') : 'Total: 0 h';
            var monthAreasHtml = '';
            for (var k=0; k<(ms.areas||[]).length; k++) {{
                var c = ms.areas[k];
                monthAreasHtml += '<div style="display:flex; justify-content:space-between; font-size:13px; padding:4px 0; border-bottom:1px dashed #eee;">' +
                                  '<div>' + c.name + '</div>' +
                                  '<div>' + c.h.toFixed(2) + ' h (' + c.pct.toFixed(1) + '%)</div>' +
                                  '</div>' +
                                  '<div style="height:6px; background:#e9ecef; border-radius:3px; overflow:hidden; margin-top:2px;"><span style="display:block; height:100%; background:#40c463; width:' + c.pct + '%;"></span></div>';
            }}
            document.getElementById('month-areas-{suffix}').innerHTML = monthAreasHtml;
            document.getElementById('month-link-{suffix}').innerHTML = ms.link ? ('<a style="color:#667eea; text-decoration:none; font-size:12px;" target="_blank" href="' + ms.link + '">Open monthly dashboard →</a>') : '<span style="color:#777; font-size:12px;">Monthly dashboard not found.</span>';
        }}
        modal.style.display = 'flex';
    }}
    document.getElementById('modal-{suffix}').addEventListener('click', function(e){{ if (e.target.id === 'modal-{suffix}') {{ closeModal_{suffix}(); }} }});
</script>
''')

    html.append("</div>")  # wrapper
    return "".join(html)
    
    


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a calendar heatmap of daily hours")
    parser.add_argument("-o", "--output", default="reports/calendar/last_12_months.html", help="Output HTML path")
    parser.add_argument("-m", "--months", type=int, default=12, help="Number of months to include (default: 12)")
    args = parser.parse_args()
    generate_calendar_heatmap(args.output, args.months)
