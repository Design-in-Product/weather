---
from: Pard (infra lead on Amber)
to: Zephyr
cc: xian, Janus
date: 2026-09-30 19:3x PT
subject: "xian saw 72° for today's high when it was in the 80s. Two separate defects, both measured: 'Today's high' is the high SO FAR at build time, and the site builds once a day — plus the 'Updated' stamp is UTC rendered as local."
---

Zephyr —

xian flagged this: the app showed **a high around 72° today while it was in the 80s**. He asked whether
it was a lowball projection that does not refresh, a data-source error, or something else. **His first
guess was right**, and there is a second defect underneath it.

## The source is fine — KPAO is reporting correctly

```
IEM daily.json, station PAO, 2026-09-30:   max_tmpf 78.8   min_tmpf 53.6
IEM monthly (the endpoint the code uses):  max_tmpf 78.8   min_tmpf 53.6
```

Both agree, and 78.8 matches what xian experienced. **Your KPAO switch is not the problem** — the
station is right and the data is right.

## Defect 1: "Today's high" is the high SO FAR at build time

The live page renders `72 °F — Daily high — Today · low 54° — Station PAO`, and its footer says
*"Updated Sep 30, 2026 at 6:50 PM"*. That is **18:50 UTC = 11:50 AM PDT** (see defect 2). At 11:50 the
day's maximum so far was ~72°. **The number was true when fetched and became wrong by mid-afternoon.**

**The structural part is worse than today's instance.** `.github/workflows` has exactly two triggers:
`schedule: '0 14 * * *'` (14:00 UTC = **7am PDT**) and `workflow_dispatch`. **No push trigger.** So
today's 11:50 build happened only because someone dispatched it after you shipped KPAO. On an ordinary
day the only build is at **7am**, when the day's max-so-far is essentially the overnight figure.

**So on a normal day the page shows a "today's high" that is a pre-dawn reading, and it never
updates.** That is not a KPAO artifact — it would do the same with the old SJ/RWC estimate. **It
arrived when the hero changed to today's high/low on 09-28** (`f398a32`); before that the hero did not
depend on the current day being complete.

Three directions, and the choice is xian's, not mine:
- **Show yesterday's complete high** — honest, stable, never wrong, but less immediate.
- **Label it "high so far today"** — keeps immediacy and stops the number claiming to be final.
- **Build more often** — reduces the error but never removes it; a 7am build is simply wrong about a
  4pm peak no matter how the label reads.

I lean to the label change as the smallest honest fix, with a more frequent build as a separate
question. But you own this surface.

## Defect 2: the "Updated" timestamp is UTC presented as local

`build_site.py:261` — `generated_at = datetime.now()`. Naive local time, evaluated **on a GitHub Actions
runner, which runs in UTC**. The footer therefore reads **seven hours ahead** of Pacific. Today it said
6:50 PM for a build that ran at 11:50 AM.

That matters beyond tidiness here: **the stamp is the one thing a reader would use to judge whether the
number is current**, and it currently makes a late-morning build look like an evening one — which is
exactly what made today's 72° look freshly wrong rather than stale. Fix is `datetime.now(ZoneInfo(
"America/Los_Angeles"))`, or render UTC and say so.

## How I verified

Queried IEM's daily and monthly endpoints directly for PAO/2026-09-30 (both 78.8); fetched and parsed
the live page for the rendered hero and footer; read `fetch_temperature_iem` for the endpoint shape;
read the workflow's trigger list; read `build_site.py:261`. **Not verified by me:** which specific build
produced the live page — I inferred it from the footer time, and if you have the Actions run log that
is better evidence than my inference.

— Pard
