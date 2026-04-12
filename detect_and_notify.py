#!/usr/bin/env python3
"""Compare two state.json files; email a fresh-rain report if appropriate.

Run after build_site.py inside the GitHub Action:
    python3 detect_and_notify.py prev/state.json site/state.json

Reads SMTP_USER, SMTP_PASS, SMTP_FROM, REPORT_TO from environment.
Exits 0 in normal cases (whether it sent or not). Exits non-zero only on
unexpected errors so the workflow doesn't fail loudly when there's just no
rain to report.
"""

import json
import os
import sys
from typing import Optional

# Reuse the script's existing SMTP plumbing — it falls back to env vars on
# non-macOS systems, which is exactly what the GitHub Action needs.
from noaa_rainfall import send_email


SOURCE_LABELS = {
    "palo_alto_estimate": "Palo Alto (estimate)",
    "redwood_city": "Redwood City",
    "san_jose": "San Jose Apt",
    "sfo": "SFO",
}

# Order in which sources show up in the email.
SOURCE_ORDER = ["palo_alto_estimate", "redwood_city", "san_jose", "sfo"]


def load_state(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def find_fresh_rain(prev_state: dict, new_state: dict) -> dict:
    """Return {source_key: [(date, precip), ...]} for newly-seen rainy records.

    Compares per-source fingerprints (sorted "date:precip" strings) by set
    difference. Backfilled past dates are caught because they were not in the
    previous fingerprint set even if their date is older than the run.
    """
    prev_fps = prev_state.get("fingerprints", {})
    new_fps = new_state.get("fingerprints", {})
    fresh: dict = {}
    for key, new_list in new_fps.items():
        prev_set = set(prev_fps.get(key, []))
        new_set = set(new_list)
        added = new_set - prev_set
        rain = []
        for entry in added:
            try:
                date_str, precip_str = entry.split(":", 1)
                precip = float(precip_str)
            except ValueError:
                continue
            if precip > 0:
                rain.append((date_str, precip))
        if rain:
            fresh[key] = sorted(rain)
    return fresh


def build_report(fresh: dict, new_state: dict, public_url: Optional[str]) -> str:
    lines = []
    lines.append("New rainfall recorded since the last run.")
    lines.append("")
    keys = [k for k in SOURCE_ORDER if k in fresh] + [
        k for k in fresh if k not in SOURCE_ORDER
    ]
    for key in keys:
        label = SOURCE_LABELS.get(key, key)
        lines.append(f"  {label}")
        for date_str, precip in fresh[key]:
            lines.append(f"    {date_str}   {precip:5.2f} in")
        lines.append("")
    last_run = new_state.get("last_run", "(unknown)")
    lines.append(f"Run: {last_run}")
    if public_url:
        lines.append("")
        lines.append(f"Live dashboard: {public_url}")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: detect_and_notify.py PREV_STATE NEW_STATE", file=sys.stderr)
        return 2

    prev = load_state(sys.argv[1])
    new = load_state(sys.argv[2])

    # First-run safety: if there's no previous state at all, every record
    # in `new` would look "fresh" and we'd email the entire season. Skip.
    if not prev.get("fingerprints"):
        print("No previous fingerprints — first run, skipping notification.")
        return 0

    fresh = find_fresh_rain(prev, new)

    if not fresh:
        print("No fresh rain detected — skipping email.")
        return 0

    summary_counts = {k: len(v) for k, v in fresh.items()}
    print(f"Fresh rain detected: {summary_counts}")

    to_addr = os.environ.get("REPORT_TO")
    if not to_addr:
        print("REPORT_TO not set — would have emailed, but cannot.", file=sys.stderr)
        return 0

    if not (os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASS")):
        print(
            "SMTP_USER/SMTP_PASS not set — would have emailed, but cannot.",
            file=sys.stderr,
        )
        return 0

    public_url = os.environ.get("PUBLIC_URL")
    report = build_report(fresh, new, public_url)
    try:
        send_email(report, to_addr)
    except SystemExit as exc:
        # send_email calls sys.exit(1) on bad creds — don't let a notification
        # failure block the site deploy.
        print(f"WARNING: send_email exited: {exc}", file=sys.stderr)
        print("Site deploy will continue without the email.", file=sys.stderr)
        return 0
    except Exception as exc:
        print(f"WARNING: Failed to send email: {exc}", file=sys.stderr)
        print("Site deploy will continue without the email.", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
