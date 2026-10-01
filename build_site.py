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
from zoneinfo import ZoneInfo

from noaa_rainfall import (
    _rain_season_start,
    fetch_rainfall,
    fetch_rainfall_iem,
    fetch_temperature,
    fetch_temperature_iem,
    merge_rainfall_records,
    merge_temperature_records,
    render_html,
)

# Each entry mirrors what render_html expects, plus station_id for fetching.
# Order here is the order shown in the selector.
SOURCES_CONFIG = [
    {
        "key": "palo_alto_estimate",
        "name": "Palo Alto",
        "station_id": None,  # rain: computed from SJ + RWC below
        "note": "Weighted estimate: (2·San Jose + Redwood City) / 3",
        # Temperature: a direct KPAO reading beats an estimate once a real
        # station sits in Palo Alto itself — ratified 2026-09-29. KPAO has
        # no usable precip data (checked directly), so rain keeps the
        # weighted estimate above; only this note+source differ for temp.
        "temp_note": "Station PAO (Palo Alto Airport)",
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
HISTORY_DIR = REPO_DIR / "history"

# IEM station mapping for gap-filling NCEI with near-real-time ASOS data.
# Only airport (ASOS/AWOS) stations have IEM equivalents.
IEM_MAPPING = {
    "san_jose": {"icao": "SJC", "network": "CA_ASOS"},
    "sfo": {"icao": "SFO", "network": "CA_ASOS"},
    # Redwood City (USC00047339) is a COOP station — no IEM equivalent.
}

# Palo Alto's temperature-only IEM station (KPAO), ratified 2026-09-29.
# Deliberately not in IEM_MAPPING above: that mapping gap-fills an
# NCEI-fetched *rain* baseline for san_jose/sfo, which doesn't apply here —
# no NCEI archival data exists for KPAO under either cross-referenced ID
# (checked directly), but IEM alone has complete daily coverage back to
# 1984, so it's fetched standalone. Not usable for rain: its precip field
# is unpopulated in every response.
PALO_ALTO_TEMP_STATION = {"icao": "PAO", "network": "CA_ASOS"}


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


def load_prior_season_monthlies(season_start: date) -> dict:
    """Load cached prior-season monthly rain totals + avg highs, if any.

    Reads history/<prior_start_year>-<prior_end_year>.json (written by
    build_history.py once a season completes) rather than re-fetching a
    finished season from NCEI/IEM on every daily build. Returns empty dicts
    when no cache exists yet, so the year-over-year overlay simply doesn't
    render — never an error.
    """
    prev_start_year = season_start.year - 1
    prev_end_year = season_start.year
    cache_path = HISTORY_DIR / f"{prev_start_year}-{prev_end_year}.json"
    if not cache_path.is_file():
        return {"rain": {}, "temp": {}}

    payload = json.loads(cache_path.read_text(encoding="utf-8"))

    rain_monthly: dict[str, dict[str, float]] = {}
    for key, records in payload.get("rain_records", {}).items():
        monthly: dict[str, float] = {}
        for r in records:
            mk = r["date"][:7]
            monthly[mk] = monthly.get(mk, 0) + r["precipitation_in"]
        rain_monthly[key] = monthly

    temp_monthly: dict[str, dict[str, float]] = {}
    for key, records in payload.get("temp_records", {}).items():
        buckets: dict[str, list[float]] = {}
        for r in records:
            if r.get("tmax_f") is None:
                continue
            mk = r["date"][:7]
            buckets.setdefault(mk, []).append(r["tmax_f"])
        temp_monthly[key] = {k: sum(v) / len(v) for k, v in buckets.items()}

    return {"rain": rain_monthly, "temp": temp_monthly}


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

    # Year-over-year: cached prior-season monthlies, if history/ has one.
    prior = load_prior_season_monthlies(season_start)

    # Assemble the source list render_html wants.
    sources = []
    for src in SOURCES_CONFIG:
        sources.append({
            "key": src["key"],
            "name": src["name"],
            "note": src["note"],
            "records": records_by_key.get(src["key"], []),
            "prior_monthly": prior["rain"].get(src["key"], {}),
        })

    # Temperature: San Jose, Redwood City, SFO use the same NCEI+IEM
    # gap-fill pattern as rain. Palo Alto is handled separately below —
    # a direct KPAO reading, not a weighted estimate of these three.
    fetched_temp: dict[str, list[dict]] = {}
    for src in SOURCES_CONFIG:
        sid = src["station_id"]
        if sid is None:
            continue
        print(f"Fetching {src['name']} temperature from NCEI ({sid})...", file=sys.stderr)
        fetched_temp[src["key"]] = fetch_temperature(season_start, today, station_id=sid)

    for key, iem_info in IEM_MAPPING.items():
        ncei_records = fetched_temp.get(key, [])
        if ncei_records:
            ncei_max = max(r["date"] for r in ncei_records)
            iem_start = datetime.strptime(ncei_max, "%Y-%m-%d").date()
        else:
            iem_start = season_start
        print(f"Gap-filling {key} temperature from IEM ({iem_info['icao']}, "
              f"{iem_start} → {today})...", file=sys.stderr)
        iem_temp_records = fetch_temperature_iem(
            iem_info["icao"], iem_info["network"], iem_start, today,
        )
        before = len(ncei_records)
        fetched_temp[key] = merge_temperature_records(ncei_records, iem_temp_records)
        added = len(fetched_temp[key]) - before
        if added:
            print(f"  +{added} day(s) from IEM", file=sys.stderr)

    # Palo Alto temperature: a direct KPAO reading, not the SJ/RWC weighted
    # estimate — ratified 2026-09-29. No NCEI baseline exists for it, so
    # this is IEM-only (unlike the NCEI+gap-fill pattern above).
    print("Fetching Palo Alto temperature from IEM (KPAO/PAO)...", file=sys.stderr)
    palo_alto_temp = fetch_temperature_iem(
        PALO_ALTO_TEMP_STATION["icao"], PALO_ALTO_TEMP_STATION["network"],
        season_start, today,
    )

    temp_records_by_key: dict[str, list[dict]] = {
        "palo_alto_estimate": palo_alto_temp,
        **fetched_temp,
    }

    temp_sources = []
    for src in SOURCES_CONFIG:
        temp_sources.append({
            "key": src["key"],
            "name": src["name"],
            "note": src.get("temp_note", src["note"]),
            "records": temp_records_by_key.get(src["key"], []),
            "prior_monthly": prior["temp"].get(src["key"], {}),
        })

    # Rendered as a local-looking timestamp in the footer; must be Pacific
    # explicitly since the GitHub Actions runner that builds this is UTC
    # (bug caught by Pard 2026-09-30 — naive datetime.now() was rendering
    # UTC as if it were already Pacific, 7 hours fast).
    generated_at = datetime.now(ZoneInfo("America/Los_Angeles"))

    html = render_html(
        sources=sources,
        season_start=season_start,
        season_end=today,
        generated_at=generated_at,
        default_source_key="palo_alto_estimate",
        temp_sources=temp_sources,
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
        "temperature_records": temp_records_by_key,
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
    avg_highs = {
        k: round(sum(r["tmax_f"] for r in v if r.get("tmax_f") is not None)
                  / max(1, sum(1 for r in v if r.get("tmax_f") is not None)), 1)
        for k, v in temp_records_by_key.items()
    }
    print(f"\nWrote {SITE_DIR}/index.html, data.json, state.json", file=sys.stderr)
    print(f"Season totals: {totals}", file=sys.stderr)
    print(f"Season avg highs: {avg_highs}", file=sys.stderr)


if __name__ == "__main__":
    main()
