#!/usr/bin/env python3
import re
import sys
from datetime import datetime

# --- Configuration ---
valid_weekdays = {"lun", "mar", "mer", "gio", "ven", "sab", "dom",
                  "mon", "tue", "wed", "thu", "fri", "sat", "sun"}

# Match timestamps enclosed in either <...> or [...]
timestamp_re = re.compile(
    r"(?P<open>[<\[])"                       # opening bracket
    r"(?P<date>\d{4}-\d{2}-\d{2})"           # date YYYY-MM-DD
    r"(?:\s+(?P<weekday>[A-Za-zàèéìòù]+))?"  # optional weekday
    r"(?:\s+(?P<start>[0-2]\d:[0-5]\d))?"    # optional start time
    r"(?:-(?P<end>[0-2]\d:[0-5]\d))?"        # optional end time
    r"(?:\s+(?P<repeat>\+\d+[hdwmy]))?"      # optional repeater (+2w, +1d, etc.)
    r"(?P<close>[>\]])"                      # closing bracket
)

def check_timestamp(ts, line_number):
    m = timestamp_re.search(ts)
    if not m:
        print(f"[line {line_number}] ❌ Invalid format: {ts.strip()}")
        return

    # Make sure brackets match: <...> or [...]
    open_b, close_b = m.group("open"), m.group("close")
    if (open_b == "<" and close_b != ">") or (open_b == "[" and close_b != "]"):
        print(f"[line {line_number}] ❌ Mismatched brackets: {ts.strip()}")

    date_str = m.group("date")
    weekday = m.group("weekday")
    start_time = m.group("start")
    end_time = m.group("end")

    # Validate date
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"[line {line_number}] ❌ Invalid date: {date_str}")
        return

    # Validate weekday
    if weekday and weekday.lower() not in valid_weekdays:
        print(f"[line {line_number}] ⚠ Unknown weekday: {weekday}")

    # Validate times
    for t in (start_time, end_time):
        if t:
            h, m = map(int, t.split(":"))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                print(f"[line {line_number}] ❌ Invalid time: {t}")

def main():
    if len(sys.argv) != 2:
        print("Usage: check_org_timestamps.py <file.org>")
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            for ts in re.findall(r"[<\[][^\]>]+[\]>]", line):
                check_timestamp(ts, lineno)

if __name__ == "__main__":
    main()
