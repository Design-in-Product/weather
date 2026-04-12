#!/usr/bin/env python3
"""Build the static rainfall site under ./site/.

Fetches all three NOAA stations once for the current rain season, computes
the weighted Palo Alto estimate, and writes:
    site/index.html  – mobile-first page
    site/data.json   – raw records (for future dynamic features)
    site/state.json  – fingerprints used by the GitHub Action to detect new data

Usage:
    python3 build_site.py
"""

import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

from noaa_rainfall import (
    _rain_season_start,
    fetch_rainfall,
    fetch_rainfall_iem,
    merge_rainfall_records,
    render_html,
)

# Each entry mirrors what render_html expects, plus station_id for fetching.
# Order here is the order shown in the selector.
SOURCES_CONFIG = [
    {
        "key": "palo_alto_estimate",
        "name": "Palo Alto",
        "station_id": None,  # computed from SJ + RWC below
        "note": "Weighted estimate: (2·San Jose + Redwood City) / 3",
    },
    {
        "key": "redwood_city",
        "name": "Redwood City",
        "station_id": "USC00047339",
        "note": "Station USC00047339",
    },
    {
        "key": "san_jose",
        "name": "San Jose",
        "station_id": "USW00023293",
        "note": "Station USW00023293 (San Jose Airport)",
    },
    {
        "key": "sfo",
        "name": "SFO",
        "station_id": "USW00023234",
        "note": "Station USW00023234 (SFO Airport)",
    },
]

REPO_DIR = Path(__file__).parent
SITE_DIR = REPO_DIR / "site"
SKETCHES_DIR = REPO_DIR / "sketches"

# IEM station mapping for gap-filling NCEI with near-real-time ASOS data.
# Only airport (ASOS/AWOS) stations have IEM equivalents.
IEM_MAPPING = {
    "san_jose": {"icao": "SJC", "network": "CA_ASOS"},
    "sfo": {"icao": "SFO", "network": "CA_ASOS"},
    # Redwood City (USC00047339) is a COOP station — no IEM equivalent.
}


def compute_palo_alto_estimate(sj_records: list[dict],
                                rwc_records: list[dict]) -> list[dict]:
    """Combine San Jose and Redwood City records into the PA estimate.

    Formula: (2*SJ + RWC) / 3 when both are present.
    Falls back to whichever single station is available on a given date.
    """
    sj_map = {r["date"]: r["precipitation_in"] for r in sj_records}
    rwc_map = {r["date"]: r["precipitation_in"] for r in rwc_records}
    all_dates = sorted(set(sj_map) | set(rwc_map))
    estimate: list[dict] = []
    for d in all_dates:
        sj = sj_map.get(d)
        rwc = rwc_map.get(d)
        if sj is not None and rwc is not None:
            v = (2 * sj + rwc) / 3
        elif sj is not None:
            v = sj
        else:
            v = rwc  # type: ignore[assignment]
        estimate.append({"date": d, "precipitation_in": round(v, 3)})
    return estimate


def main() -> None:
    today = date.today()
    season_start = _rain_season_start(today)

    # Fetch each real station from NCEI (archival, may lag a few days).
    fetched: dict[str, list[dict]] = {}
    for src in SOURCES_CONFIG:
        sid = src["station_id"]
        if sid is None:
            continue
        print(f"Fetching {src['name']} from NCEI ({sid})...", file=sys.stderr)
        fetched[src["key"]] = fetch_rainfall(season_start, today, station_id=sid)

    # Gap-fill airport stations with IEM (near-real-time, same-day freshness).
    # Only fetch the months where NCEI has gaps — typically the last 1-2 months.
    for key, iem_info in IEM_MAPPING.items():
        ncei_records = fetched.get(key, [])
        if ncei_records:
            ncei_max = max(r["date"] for r in ncei_records)
            iem_start = datetime.strptime(ncei_max, "%Y-%m-%d").date()
        else:
            iem_start = season_start
        print(f"Gap-filling {key} from IEM ({iem_info['icao']}, "
              f"{iem_start} → {today})...", file=sys.stderr)
        iem_records = fetch_rainfall_iem(
            iem_info["icao"], iem_info["network"], iem_start, today,
        )
        before = len(ncei_records)
        fetched[key] = merge_rainfall_records(ncei_records, iem_records)
        added = len(fetched[key]) - before
        if added:
            print(f"  +{added} day(s) from IEM", file=sys.stderr)

    # Build the PA estimate from SJ + RWC.
    pa_estimate = compute_palo_alto_estimate(
        fetched.get("san_jose", []),
        fetched.get("redwood_city", []),
    )

    records_by_key: dict[str, list[dict]] = {
        "palo_alto_estimate": pa_estimate,
        **fetched,
    }

    # Assemble the source list render_html wants.
    sources = []
    for src in SOURCES_CONFIG:
        sources.append({
            "key": src["key"],
            "name": src["name"],
            "note": src["note"],
            "records": records_by_key.get(src["key"], []),
        })

    generated_at = datetime.now()

    html = render_html(
        sources=sources,
        season_start=season_start,
        season_end=today,
        generated_at=generated_at,
        default_source_key="palo_alto_estimate",
    )

    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / "index.html").write_text(html, encoding="utf-8")

    # Mirror the eight static rain sketches into the deploy at /sketches/.
    # The dashboard footer links to ./sketches/ so they're discoverable.
    if SKETCHES_DIR.is_dir():
        dest = SITE_DIR / "sketches"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(SKETCHES_DIR, dest)

    # Preserve the custom-domain CNAME in the deployed artifact. Only `site/`
    # is uploaded to Pages, so CNAME at the repo root must be copied in or
    # the custom domain binding drops on the next deploy.
    cname_src = REPO_DIR / "CNAME"
    if cname_src.is_file():
        shutil.copy2(cname_src, SITE_DIR / "CNAME")

    data_payload = {
        "metadata": {
            "generated_at": generated_at.isoformat(timespec="seconds"),
            "season_start": season_start.isoformat(),
            "season_end": today.isoformat(),
            "sources": [
                {
                    "key": s["key"],
                    "name": s["name"],
                    "note": s["note"],
                    "station_id": s["station_id"],
                }
                for s in SOURCES_CONFIG
            ],
        },
        "records": records_by_key,
    }
    (SITE_DIR / "data.json").write_text(
        json.dumps(data_payload, indent=2), encoding="utf-8"
    )

    # Fingerprints let a future Action set-diff between runs to detect new
    # records (which may backfill past dates due to NOAA's lag).
    state_payload = {
        "last_run": generated_at.isoformat(timespec="seconds"),
        "fingerprints": {
            key: sorted(f"{r['date']}:{r['precipitation_in']}" for r in records)
            for key, records in records_by_key.items()
        },
    }
    (SITE_DIR / "state.json").write_text(
        json.dumps(state_payload, indent=2), encoding="utf-8"
    )

    totals = {k: round(sum(r["precipitation_in"] for r in v), 2)
              for k, v in records_by_key.items()}
    print(f"\nWrote {SITE_DIR}/index.html, data.json, state.json", file=sys.stderr)
    print(f"Season totals: {totals}", file=sys.stderr)


if __name__ == "__main__":
    main()
