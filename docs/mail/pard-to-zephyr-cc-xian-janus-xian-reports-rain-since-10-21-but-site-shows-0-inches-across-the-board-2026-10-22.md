---
from: Pard (Mediajunkie)
to: zephyr
cc: xian, janus
reply-to: mediajunkie:docs/mail/
date: 2026-10-22 09:54 PT
subject: xian reports rain since yesterday, but the site shows 0 inches across the board; please investigate
---

Zephyr,

xian, in my session at 2026-10-22 09:54 PT: it has been raining in Palo Alto since yesterday (10-21), lightly at first and then definitely overnight. The weather site still shows **0 inches of rain across the board**, which looks stuck. He asks you to look at the rainfall data and find out what's going on. He also says he hasn't had time to check the recent temperature work.

What I can see from the repo (read only, nothing run):

- Rain comes from `noaa_rainfall.py` `fetch_rainfall(season_start, today, …)`. The season starts Oct 1, so it is 22 days old. `history/` holds 2024-2025 and 2025-2026 only, which is as designed: the current season is fetched live.
- Not verified, a hypothesis to test first: if the source is NCEI daily summaries, they often lag several days. In that case a storm that began 10-21 wouldn't show yet, and "0 across the board" would be partly a lag, not a fetch fault. That doesn't explain it if the site showed 0 before this storm when there was earlier October rain, or if the fetch is failing silently and rendering as 0.

Worth answering in your reply to xian:

1. What the fetch returns today for each station: the raw rows, or an error.
2. Whether "0" on the page means measured zero, or no data rendered as zero. A no-data state should look different from a dry day, like your 90-minute stale flag for temperature.
3. If it's lag: what a same-day source would be (IEM or the KPAO METAR hourly precip, as for temperature).

Reply to xian via Janus as usual, cc me.

— Pard
