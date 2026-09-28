---
from: Zephyr (Weather)
to: xian, via Janus
cc: Janus
date: 2026-09-28
subject: "Shipped: today's high/low hero, year-over-year faint-bar overlay — live now"
in-reply-to: docs/mail/xian-via-janus-to-zephyr-rulings-hero-is-today-14-days-stays-yoy-faint-bar-go-2026-09-27.md
---

xian — both rulings are live at weather.dinp.xyz:

- **Temperature hero is now today's (or most recent) high/low.** Season avg high/low moved to a plain card right
  below it — same information, just not the headline number anymore.
- **Year-over-year: faint overlay bar on the monthly charts**, both rain and temperature. I built the "cache, don't
  re-fetch" version you approved: a new `build_history.py` fetches one *completed* season and writes it to
  `history/<start>-<end>.json`; the daily build reads that file instead of hitting NCEI/IEM again for data that can't
  change. I ran it for the most recently completed season (Oct 2024–Sep 2025), so the overlay has real data starting
  today, not just plumbing waiting for next year. When the current season ends (after Sep 30, 2026), someone runs
  `python3 build_history.py` once to freeze it and commits the result — that's the only manual step going forward.
- **14-day strips stay 14 days**, per your call. Noted for later: you want a way to scroll further back in time —
  nothing built there yet, just logged so it doesn't get lost.

Season window (your point a) — still yours; nothing changed there, waiting on you.

— Zephyr
