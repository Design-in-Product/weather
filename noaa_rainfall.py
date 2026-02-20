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
