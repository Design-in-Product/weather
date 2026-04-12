#!/usr/bin/env python3
"""
NOAA Rainfall Tracker for Palo Alto, CA

Fetches daily precipitation data from the NOAA NCEI public API (no token required)
for the current rain season (October 1 through today) and generates a report.
Can optionally send the report via email.

Usage:
    python noaa_rainfall.py                    # Print report to console
    python noaa_rainfall.py --email you@x.com  # Also email the report
    python noaa_rainfall.py --json             # Output raw JSON
    python noaa_rainfall.py --csv              # Output CSV

First-time email setup (stores credentials in macOS Keychain):
    python noaa_rainfall.py --setup-email

Data source:
    NOAA NCEI Access Data Service (public, no auth)
    https://www.ncei.noaa.gov/access/services/data/v1
    Stations tried (in order): Palo Alto, Redwood City, San Jose Airport, SFO Airport
"""

import argparse
import csv
import io
import json
import platform
import smtplib
import subprocess
import sys
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NOAA_API_BASE = "https://www.ncei.noaa.gov/access/services/data/v1"
DATASET = "daily-summaries"
DATA_TYPES = "PRCP"              # Precipitation (tenths of mm from GHCND)
UNITS = "standard"               # API returns inches when units=standard

# Stations to try, in order of preference.
# Redwood City is closest to Palo Alto with reliable data;
# the Palo Alto COOP station (USC00046646) has been inactive.
# Airport stations (USW*) are automated and always reporting.
STATIONS = [
    ("USC00047339", "Redwood City, CA"),
    ("USW00023293", "San Jose Airport, CA"),
    ("USW00023234", "SFO Airport, CA"),
]
DEFAULT_STATION_ID = STATIONS[0][0]
DEFAULT_STATION_NAME = STATIONS[0][1]


def _rain_season_start(today: date) -> date:
    """Return October 1 of the current rain season.

    The rain season runs Oct 1 – Sep 30.  If today is Jan–Sep, the season
    started the previous October.
    """
    if today.month >= 10:
        return date(today.year, 10, 1)
    return date(today.year - 1, 10, 1)


def fetch_rainfall(start: date, end: date, station_id: str = DEFAULT_STATION_ID,
                   debug: bool = False) -> list[dict]:
    """Fetch daily precipitation from the NOAA NCEI public API.

    Returns a list of dicts with keys: date, precipitation_in.
    The API caps at ~one year per call, so we chunk if needed.
    """
    all_records: list[dict] = []
    chunk_start = start

    while chunk_start <= end:
        # API allows roughly one year per request
        chunk_end = min(end, chunk_start.replace(year=chunk_start.year + 1) - timedelta(days=1))

        params = {
            "dataset": DATASET,
            "dataTypes": DATA_TYPES,
            "stations": station_id,
            "startDate": chunk_start.isoformat(),
            "endDate": chunk_end.isoformat(),
            "format": "json",
            "units": UNITS,
        }

        url = f"{NOAA_API_BASE}?{urlencode(params)}"
        req = Request(url, headers={"Accept": "application/json"})

        try:
            with urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
        except HTTPError as exc:
            print(f"Error: NOAA API returned HTTP {exc.code}", file=sys.stderr)
            print(f"URL: {url}", file=sys.stderr)
            sys.exit(1)
        except URLError as exc:
            print(f"Error: Could not reach NOAA API: {exc.reason}", file=sys.stderr)
            sys.exit(1)

        if debug:
            print(f"DEBUG URL: {url}", file=sys.stderr)
            print(f"DEBUG response ({len(body)} bytes): {body[:500]}", file=sys.stderr)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            # Empty response means no data for that range (e.g., future dates)
            if debug:
                print(f"DEBUG: JSONDecodeError, body was: {body[:500]!r}", file=sys.stderr)
            data = []

        if isinstance(data, dict):
            # Single record comes back as a dict instead of a list
            data = [data]

        for rec in data:
            rec_date = rec.get("DATE", "")[:10]
            prcp = rec.get("PRCP")
            if rec_date and prcp is not None:
                all_records.append({
                    "date": rec_date,
                    "precipitation_in": float(prcp),
                })

        chunk_start = chunk_end + timedelta(days=1)

    # Sort chronologically
    all_records.sort(key=lambda r: r["date"])
    return all_records


# ---------------------------------------------------------------------------
# IEM (Iowa Environmental Mesonet) — near-real-time ASOS observations
# ---------------------------------------------------------------------------

IEM_API_BASE = "https://mesonet.agron.iastate.edu/api/1/daily.json"


def fetch_rainfall_iem(station_icao: str, network: str,
                       start: date, end: date,
                       debug: bool = False) -> list[dict]:
    """Fetch daily precipitation from the Iowa Environmental Mesonet.

    IEM serves ASOS/AWOS station data with near-zero lag (often same-day),
    filling the gap left by NCEI's multi-day processing pipeline.  The API
    is per-month, so we iterate months in the date range.

    Returns the same [{date, precipitation_in}, ...] format as fetch_rainfall.
    """
    all_records: list[dict] = []
    cur = start.replace(day=1)

    while cur <= end:
        params = {
            "station": station_icao,
            "network": network,
            "year": str(cur.year),
            "month": str(cur.month),
        }
        url = f"{IEM_API_BASE}?{urlencode(params)}"
        req = Request(url, headers={"Accept": "application/json"})

        if debug:
            print(f"DEBUG IEM URL: {url}", file=sys.stderr)

        try:
            with urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
        except (HTTPError, URLError) as exc:
            # Non-fatal: IEM is a supplementary source.
            if debug:
                print(f"DEBUG IEM error for {station_icao} "
                      f"{cur.year}-{cur.month:02d}: {exc}", file=sys.stderr)
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
            continue

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        for rec in data.get("data", []):
            rec_date = rec.get("date", "")[:10]
            precip = rec.get("precip")
            if rec_date and precip is not None:
                # IEM reports trace precipitation as 0.0001; round to
                # hundredths to match NCEI's reporting convention.
                precip_val = round(float(precip), 2)
                if start.isoformat() <= rec_date <= end.isoformat():
                    all_records.append({
                        "date": rec_date,
                        "precipitation_in": precip_val,
                    })

        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)

    all_records.sort(key=lambda r: r["date"])
    return all_records


def merge_rainfall_records(primary: list[dict],
                           supplement: list[dict]) -> list[dict]:
    """Merge two record lists, preferring *primary* (NCEI) for any shared date."""
    primary_dates = {r["date"] for r in primary}
    merged = list(primary)
    for r in supplement:
        if r["date"] not in primary_dates:
            merged.append(r)
    merged.sort(key=lambda r: r["date"])
    return merged


def format_report(records: list[dict], season_start: date, today: date,
                  station_id: str = DEFAULT_STATION_ID,
                  station_name: str = DEFAULT_STATION_NAME) -> str:
    """Build a human-readable rainfall report."""
    lines: list[str] = []

    lines.append("=" * 62)
    lines.append(f"  NOAA Daily Rainfall Report — {station_name}")
    lines.append(f"  Rain season: {season_start.strftime('%b %d, %Y')} – {today.strftime('%b %d, %Y')}")
    lines.append(f"  Station: {station_id}")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 62)
    lines.append("")

    if not records:
        lines.append("  No precipitation data available for this period.")
        return "\n".join(lines)

    # Monthly summaries
    monthly: dict[str, float] = {}
    for r in records:
        month_key = r["date"][:7]  # YYYY-MM
        monthly[month_key] = monthly.get(month_key, 0) + r["precipitation_in"]

    total = sum(r["precipitation_in"] for r in records)
    rainy_days = sum(1 for r in records if r["precipitation_in"] > 0)

    lines.append("  MONTHLY TOTALS")
    lines.append("  " + "-" * 30)
    for month_key in sorted(monthly):
        dt = datetime.strptime(month_key, "%Y-%m")
        label = dt.strftime("%B %Y")
        lines.append(f"  {label:<20s}  {monthly[month_key]:6.2f} in")
    lines.append("  " + "-" * 30)
    lines.append(f"  {'Season total':<20s}  {total:6.2f} in")
    lines.append(f"  {'Days with rain':<20s}  {rainy_days:>6d}")
    lines.append("")

    # Daily detail
    lines.append("  DAILY DETAIL")
    lines.append("  " + "-" * 40)
    lines.append(f"  {'Date':<14s} {'Day':<5s} {'Precip (in)':>11s}  Bar")
    lines.append("  " + "-" * 40)

    for r in records:
        dt = datetime.strptime(r["date"], "%Y-%m-%d")
        day_name = dt.strftime("%a")
        val = r["precipitation_in"]
        bar = "#" * int(val * 10) if val > 0 else ""
        marker = f"  {r['date']}  {day_name:<5s} {val:8.2f}    {bar}"
        lines.append(marker)

    lines.append("")
    lines.append(f"  Season total: {total:.2f} inches over {len(records)} days reported")
    lines.append("")
    return "\n".join(lines)


def output_csv(records: list[dict]) -> str:
    """Return records as CSV text."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["date", "precipitation_in"])
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# HTML rendering (mobile-first, self-contained — used by build_site.py)
# ---------------------------------------------------------------------------

_HTML_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html { -webkit-text-size-adjust: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  background: #f4f7fa;
  color: #1a2733;
  line-height: 1.4;
  padding: 16px 16px 48px;
  max-width: 480px;
  margin: 0 auto;
}
header { margin-bottom: 16px; }
h1 { font-size: 20px; font-weight: 600; margin-bottom: 4px; }
.subtitle { font-size: 13px; color: #6a7785; }
.selector {
  display: flex;
  gap: 4px;
  background: #e3e9f0;
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 16px;
}
.src-btn {
  flex: 1 1 auto;
  min-height: 44px;
  padding: 8px 6px;
  border: none;
  background: transparent;
  color: #4a5663;
  font-size: 12px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
}
.src-btn.active {
  background: white;
  color: #1a2733;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.hero { text-align: center; padding: 28px 20px; }
.hero .number {
  font-size: 64px;
  font-weight: 700;
  color: #2563eb;
  line-height: 1;
  letter-spacing: -2px;
}
.hero .unit { font-size: 24px; font-weight: 500; color: #6a7785; }
.hero .label { font-size: 11px; color: #6a7785; margin-top: 8px; text-transform: uppercase; letter-spacing: 0.8px; }
.hero .meta { font-size: 13px; color: #4a5663; margin-top: 12px; }
.hero .note { font-size: 11px; color: #8a96a3; margin-top: 8px; font-style: italic; }
.section-title {
  font-size: 11px; font-weight: 600; color: #6a7785;
  text-transform: uppercase; letter-spacing: 0.8px;
  margin-bottom: 12px;
}
.recent { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.recent .date { font-size: 14px; color: #4a5663; }
.recent .amount { font-size: 28px; font-weight: 600; color: #2563eb; white-space: nowrap; }
.recent .amount .unit { font-size: 14px; color: #6a7785; font-weight: 400; }
.monthly-bars { display: flex; align-items: flex-end; gap: 6px; height: 140px; }
.monthly-bars .bar {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}
.monthly-bars .bar .month-val {
  font-size: 10px; color: #1a2733; font-weight: 600;
  margin-bottom: 2px;
}
.monthly-bars .bar .fill-wrap {
  flex: 1 1 auto;
  width: 100%;
  display: flex;
  align-items: flex-end;
}
.monthly-bars .bar .fill {
  width: 100%;
  background: linear-gradient(180deg, #60a5fa 0%, #2563eb 100%);
  border-radius: 4px 4px 0 0;
  min-height: 1px;
}
.monthly-bars .bar .month-label {
  font-size: 10px; color: #6a7785;
  margin-top: 4px;
}
.daily-strip {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 60px;
}
.daily-strip .day {
  flex: 1 1 0;
  background: #e3e9f0;
  border-radius: 1px;
  min-height: 2px;
}
.daily-strip .day.rain { background: linear-gradient(180deg, #60a5fa 0%, #2563eb 100%); }
.daily-strip-labels {
  display: flex; justify-content: space-between;
  font-size: 10px; color: #6a7785; margin-top: 6px;
}
.source-section { display: none; }
.source-section.active { display: block; }
footer {
  margin-top: 24px;
  font-size: 11px;
  color: #8a96a3;
  text-align: center;
  line-height: 1.6;
}
footer a { color: #4a5663; text-decoration: none; border-bottom: 1px solid #c8d2dc; }
footer a:hover { color: #2563eb; border-bottom-color: #2563eb; }
"""

_HTML_JS = """
document.querySelectorAll('.src-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const key = btn.dataset.source;
    document.querySelectorAll('.src-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.source === key);
    });
    document.querySelectorAll('.source-section').forEach(s => {
      s.classList.toggle('active', s.dataset.source === key);
    });
  });
});
"""


def _compute_summary(records: list[dict], today: date) -> dict:
    """Compute season summary stats from a list of daily records."""
    total = sum(r["precipitation_in"] for r in records)
    rainy_days = sum(1 for r in records if r["precipitation_in"] > 0)
    monthly: dict[str, float] = {}
    for r in records:
        key = r["date"][:7]  # YYYY-MM
        monthly[key] = monthly.get(key, 0) + r["precipitation_in"]
    last_rain: Optional[dict] = None
    for r in reversed(records):
        if r["precipitation_in"] > 0:
            last_rain = r
            break
    days_since_rain: Optional[int] = None
    if last_rain:
        last_dt = datetime.strptime(last_rain["date"], "%Y-%m-%d").date()
        days_since_rain = (today - last_dt).days
    return {
        "total": total,
        "rainy_days": rainy_days,
        "monthly": monthly,
        "last_rain": last_rain,
        "days_since_rain": days_since_rain,
    }


def _iter_season_months(season_start: date, today: date) -> list[str]:
    """Return YYYY-MM strings for every month in the season range."""
    months: list[str] = []
    cur = season_start.replace(day=1)
    while cur <= today:
        months.append(cur.strftime("%Y-%m"))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return months


def _render_source_section(source: dict, season_start: date, today: date,
                            is_default: bool) -> str:
    """Render one <section> for a single source/station."""
    summary = _compute_summary(source["records"], today)
    active_cls = " active" if is_default else ""
    total = summary["total"]
    rainy = summary["rainy_days"]
    rainy_lbl = "day" if rainy == 1 else "days"
    note = source.get("note", "")
    note_html = f'<div class="note">{note}</div>' if note else ""

    # Recent rain card
    last_rain = summary["last_rain"]
    if last_rain:
        last_dt = datetime.strptime(last_rain["date"], "%Y-%m-%d")
        days_since = summary["days_since_rain"]
        if days_since == 0:
            ago_lbl = "today"
        elif days_since == 1:
            ago_lbl = "yesterday"
        else:
            ago_lbl = f"{days_since} days ago"
        recent_html = (
            '<div class="section-title">Most recent rain</div>'
            '<div class="recent">'
            f'<div class="date">{last_dt.strftime("%a %b %-d")} · {ago_lbl}</div>'
            f'<div class="amount">{last_rain["precipitation_in"]:.2f}<span class="unit"> in</span></div>'
            '</div>'
        )
    else:
        recent_html = (
            '<div class="section-title">Most recent rain</div>'
            '<div class="recent"><div class="date">No rain recorded this season</div></div>'
        )

    # Monthly bars
    monthly = summary["monthly"]
    months = _iter_season_months(season_start, today)
    max_month = max((monthly.get(m, 0) for m in months), default=0) or 1
    bars_html = ""
    for m in months:
        v = monthly.get(m, 0)
        height_pct = (v / max_month * 100) if max_month > 0 else 0
        label = datetime.strptime(m, "%Y-%m").strftime("%b")
        bars_html += (
            '<div class="bar">'
            f'<div class="month-val">{v:.1f}</div>'
            '<div class="fill-wrap">'
            f'<div class="fill" style="height: {height_pct:.0f}%"></div>'
            '</div>'
            f'<div class="month-label">{label}</div>'
            '</div>'
        )

    # Daily strip — last 14 days
    recent_records = source["records"][-14:]
    max_day = max((r["precipitation_in"] for r in recent_records), default=0)
    strip_html = ""
    for r in recent_records:
        v = r["precipitation_in"]
        if v > 0 and max_day > 0:
            h_pct = max(10, v / max_day * 100)
            cls = " rain"
        else:
            h_pct = 8
            cls = ""
        strip_html += f'<div class="day{cls}" style="height: {h_pct:.0f}%"></div>'
    if recent_records:
        first = datetime.strptime(recent_records[0]["date"], "%Y-%m-%d").strftime("%b %-d")
        last = datetime.strptime(recent_records[-1]["date"], "%Y-%m-%d").strftime("%b %-d")
        strip_labels = f'<div class="daily-strip-labels"><span>{first}</span><span>{last}</span></div>'
    else:
        strip_labels = ""

    return (
        f'<section class="source-section{active_cls}" data-source="{source["key"]}">'
        '<div class="card hero">'
        f'<div><span class="number">{total:.2f}</span><span class="unit"> in</span></div>'
        '<div class="label">Season total</div>'
        f'<div class="meta">{rainy} {rainy_lbl} with rain · since {season_start.strftime("%b %-d, %Y")}</div>'
        f'{note_html}'
        '</div>'
        f'<div class="card">{recent_html}</div>'
        '<div class="card">'
        '<div class="section-title">Monthly totals (in)</div>'
        f'<div class="monthly-bars">{bars_html}</div>'
        '</div>'
        '<div class="card">'
        '<div class="section-title">Last 14 days</div>'
        f'<div class="daily-strip">{strip_html}</div>'
        f'{strip_labels}'
        '</div>'
        '</section>'
    )


def render_html(sources: list[dict], season_start: date, season_end: date,
                generated_at: datetime,
                default_source_key: str = "palo_alto_estimate") -> str:
    """Render a self-contained mobile-first HTML page.

    Each entry in `sources` should be a dict with keys:
        key      – stable identifier used for selector buttons
        name     – short friendly label shown in the selector
        records  – list of {date, precipitation_in} dicts
        note     – optional caption (e.g., station ID or formula)
    """
    if not any(s["key"] == default_source_key for s in sources):
        default_source_key = sources[0]["key"]

    selector_html = ""
    for s in sources:
        active = " active" if s["key"] == default_source_key else ""
        selector_html += (
            f'<button class="src-btn{active}" data-source="{s["key"]}">{s["name"]}</button>'
        )

    sections_html = "".join(
        _render_source_section(s, season_start, season_end,
                                is_default=(s["key"] == default_source_key))
        for s in sources
    )

    generated_str = generated_at.strftime("%b %-d, %Y at %-I:%M %p")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#2563eb">
<title>Palo Alto Rainfall</title>
<style>{_HTML_CSS}</style>
</head>
<body>
<header>
  <h1>Palo Alto Rainfall</h1>
  <div class="subtitle">Rain season {season_start.strftime("%b %Y")} – {season_end.strftime("%b %Y")}</div>
</header>
<div class="selector">{selector_html}</div>
{sections_html}
<footer>
  Data: NOAA NCEI + <a href="https://mesonet.agron.iastate.edu/">Iowa Environmental Mesonet</a> · Updated {generated_str}<br>
  Stations: USC00047339 (Redwood City) · USW00023293 / SJC (San Jose) · USW00023234 / SFO<br>
  <a href="./sketches/">Eight ways to look at rain →</a>
</footer>
<script>{_HTML_JS}</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# macOS Keychain helpers
# ---------------------------------------------------------------------------

KEYCHAIN_SERVICE = "noaa-rainfall-tracker"


def _keychain_set(account: str, password: str) -> None:
    """Store a secret in the macOS Keychain (login keychain)."""
    # Delete any existing entry first (ignore errors if it doesn't exist)
    subprocess.run(
        ["security", "delete-generic-password",
         "-s", KEYCHAIN_SERVICE, "-a", account],
        capture_output=True,
    )
    result = subprocess.run(
        ["security", "add-generic-password",
         "-s", KEYCHAIN_SERVICE, "-a", account, "-w", password],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Error storing {account} in Keychain: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def _keychain_get(account: str) -> Optional[str]:
    """Retrieve a secret from the macOS Keychain. Returns None if not found."""
    result = subprocess.run(
        ["security", "find-generic-password",
         "-s", KEYCHAIN_SERVICE, "-a", account, "-w"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def setup_email() -> None:
    """Interactive setup: store SMTP credentials in the macOS Keychain."""
    if platform.system() != "Darwin":
        print("Error: Keychain storage is only available on macOS.", file=sys.stderr)
        print("On other systems, use SMTP_USER / SMTP_PASS environment variables.", file=sys.stderr)
        sys.exit(1)

    print("=== NOAA Rainfall Tracker — Email Setup ===")
    print("Credentials will be stored in your macOS Keychain")
    print(f"(service: \"{KEYCHAIN_SERVICE}\")\n")

    smtp_host = input("SMTP host [smtp.gmail.com]: ").strip() or "smtp.gmail.com"
    smtp_port = input("SMTP port [587]: ").strip() or "587"
    smtp_user = input("SMTP username (email): ").strip()
    if not smtp_user:
        print("Error: username is required.", file=sys.stderr)
        sys.exit(1)
    smtp_pass = input("SMTP password (Gmail: use an App Password): ").strip()
    if not smtp_pass:
        print("Error: password is required.", file=sys.stderr)
        sys.exit(1)
    smtp_from = input(f"From address [{smtp_user}]: ").strip() or smtp_user

    _keychain_set("smtp_host", smtp_host)
    _keychain_set("smtp_port", smtp_port)
    _keychain_set("smtp_user", smtp_user)
    _keychain_set("smtp_pass", smtp_pass)
    _keychain_set("smtp_from", smtp_from)

    print(f"\nCredentials saved to Keychain (service: \"{KEYCHAIN_SERVICE}\").")
    print(f"You can now run:  python noaa_rainfall.py --email {smtp_user}")


def _get_smtp_credentials() -> dict:
    """Load SMTP credentials from Keychain (macOS) or environment variables."""
    import os

    # Try macOS Keychain first
    if platform.system() == "Darwin":
        smtp_pass = _keychain_get("smtp_pass")
        if smtp_pass:
            return {
                "smtp_host": _keychain_get("smtp_host") or "smtp.gmail.com",
                "smtp_port": int(_keychain_get("smtp_port") or "587"),
                "smtp_user": _keychain_get("smtp_user") or "",
                "smtp_pass": smtp_pass,
                "from_addr": _keychain_get("smtp_from") or _keychain_get("smtp_user") or "",
            }

    # Fall back to environment variables
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    if smtp_user and smtp_pass:
        return {
            "smtp_host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
            "smtp_user": smtp_user,
            "smtp_pass": smtp_pass,
            "from_addr": os.environ.get("SMTP_FROM", smtp_user),
        }

    return {}


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------

def send_email(report: str, to_addr: str) -> None:
    """Send the rainfall report via email (SMTP/TLS).

    Credentials are read from the macOS Keychain (run --setup-email first)
    or from SMTP_USER/SMTP_PASS environment variables as a fallback.
    """
    creds = _get_smtp_credentials()
    if not creds:
        print(
            "Error: no email credentials found.\n"
            "  macOS:  run  python noaa_rainfall.py --setup-email\n"
            "  Other:  set SMTP_USER and SMTP_PASS environment variables.",
            file=sys.stderr,
        )
        sys.exit(1)

    today_str = date.today().strftime("%b %d, %Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Palo Alto Rainfall Update — {today_str}"
    msg["From"] = creds["from_addr"]
    msg["To"] = to_addr

    # Plain text part
    msg.attach(MIMEText(report, "plain"))

    # Simple HTML part (preformatted)
    html = (
        "<html><body>"
        f"<pre style='font-family:monospace;font-size:13px'>{report}</pre>"
        "</body></html>"
    )
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(creds["smtp_host"], creds["smtp_port"]) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(creds["smtp_user"], creds["smtp_pass"])
        server.sendmail(creds["from_addr"], [to_addr], msg.as_string())

    print(f"Report emailed to {to_addr}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch daily rainfall for Palo Alto from NOAA and report.",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Override start date (YYYY-MM-DD). Default: Oct 1 of current rain season.",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="Override end date (YYYY-MM-DD). Default: today.",
    )
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        metavar="ADDRESS",
        help="Email the report to this address (run --setup-email first).",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON.")
    parser.add_argument("--csv", action="store_true", help="Output CSV.")
    parser.add_argument("--debug", action="store_true", help="Show raw API response.")
    parser.add_argument(
        "--station",
        type=str,
        default=None,
        metavar="ID",
        help="Use a specific GHCND station ID (e.g. USW00023293). Disables fallback.",
    )
    parser.add_argument(
        "--setup-email",
        action="store_true",
        help="Store SMTP credentials in the macOS Keychain, then exit.",
    )
    args = parser.parse_args()

    if args.setup_email:
        setup_email()
        return

    today = date.today()
    season_start = _rain_season_start(today)

    start = datetime.strptime(args.start, "%Y-%m-%d").date() if args.start else season_start
    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else today

    # Determine which station(s) to try
    if args.station:
        stations_to_try = [(args.station, args.station)]
    else:
        stations_to_try = list(STATIONS)

    records: list[dict] = []
    used_id = stations_to_try[0][0]
    used_name = stations_to_try[0][1]

    for sid, sname in stations_to_try:
        print(f"Fetching rainfall data for {sname} ({sid})...", file=sys.stderr)
        print(f"Period: {start} to {end}", file=sys.stderr)
        records = fetch_rainfall(start, end, station_id=sid, debug=args.debug)
        if records:
            used_id, used_name = sid, sname
            break
        if len(stations_to_try) > 1:
            print(f"  No data from {sname}, trying next station...", file=sys.stderr)

    if args.json:
        print(json.dumps(records, indent=2))
    elif args.csv:
        print(output_csv(records), end="")
    else:
        report = format_report(records, start, end,
                               station_id=used_id, station_name=used_name)
        print(report)

        if args.email:
            send_email(report, args.email)


if __name__ == "__main__":
    main()
