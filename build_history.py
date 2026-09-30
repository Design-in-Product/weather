#!/usr/bin/env python3
"""Freeze a completed rain season's rain + temperature records into history/.

A completed season (Oct 1 – Sep 30, fully in the past) never changes, so
there's no reason for the daily build to re-fetch it from NCEI/IEM every
run. This script fetches it once and writes it to a JSON file under
history/, which build_site.py reads to power the year-over-year overlay on
the monthly bars.

Run manually after a season ends (i.e. any time after Sep 30), or to
backfill an older season:

    python3 build_history.py                    # most recently completed season
    python3 build_history.py --season-start-year 2023   # Oct 2023 - Sep 2024

Commit the resulting history/<start>-<end>.json to the repo.
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from build_site import PALO_ALTO_TEMP_STATION, SOURCES_CONFIG, compute_palo_alto_estimate
from noaa_rainfall import (
    _rain_season_start,
    fetch_rainfall,
    fetch_temperature,
    fetch_temperature_iem,
)

REPO_DIR = Path(__file__).parent
HISTORY_DIR = REPO_DIR / "history"


def build_history_for_season(season_start: date, season_end: date) -> dict:
    """Fetch a completed season's rain + temperature for all real stations.

    No IEM gap-fill: a season this old is long past NCEI's reporting lag,
    so the archival data is already complete.
    """
    rain: dict[str, list[dict]] = {}
    temp: dict[str, list[dict]] = {}
    for src in SOURCES_CONFIG:
        sid = src["station_id"]
        if sid is None:
            continue
        print(f"Fetching {src['name']} rain {season_start} -> {season_end}...",
              file=sys.stderr)
        rain[src["key"]] = fetch_rainfall(season_start, season_end, station_id=sid)
        print(f"Fetching {src['name']} temperature {season_start} -> {season_end}...",
              file=sys.stderr)
        temp[src["key"]] = fetch_temperature(season_start, season_end, station_id=sid)

    rain["palo_alto_estimate"] = compute_palo_alto_estimate(
        rain.get("san_jose", []), rain.get("redwood_city", []))

    # Temperature: direct KPAO reading, matching build_site.py's live
    # pipeline, so the year-over-year overlay compares like-for-like.
    print(f"Fetching Palo Alto temperature (KPAO/PAO) {season_start} -> {season_end}...",
          file=sys.stderr)
    temp["palo_alto_estimate"] = fetch_temperature_iem(
        PALO_ALTO_TEMP_STATION["icao"], PALO_ALTO_TEMP_STATION["network"],
        season_start, season_end,
    )

    return {
        "season_start": season_start.isoformat(),
        "season_end": season_end.isoformat(),
        "rain_records": rain,
        "temp_records": temp,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--season-start-year", type=int, default=None,
        help="Oct 1 of this year through Sep 30 of the following year. "
             "Default: the most recently completed season.",
    )
    args = parser.parse_args()

    if args.season_start_year:
        season_start = date(args.season_start_year, 10, 1)
        season_end = date(args.season_start_year + 1, 9, 30)
    else:
        current_start = _rain_season_start(date.today())
        season_start = date(current_start.year - 1, 10, 1)
        season_end = current_start - timedelta(days=1)

    payload = build_history_for_season(season_start, season_end)
    HISTORY_DIR.mkdir(exist_ok=True)
    out_path = HISTORY_DIR / f"{season_start.year}-{season_end.year}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
