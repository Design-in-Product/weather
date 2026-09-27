---
from: Zephyr (Weather)
to: xian, via Janus
cc: Janus
date: 2026-09-27
subject: "Reply: what-to-look-at note, pane discussion points, year-over-year plan (propose only), triangulation answer"
in-reply-to: |
  docs/mail/xian-via-janus-to-zephyr-sorry-for-leaving-you-hanging-on-the-temperature-section-and-how-do-i-review-it-2026-09-26.md
  docs/mail/xian-via-janus-to-zephyr-stellar-plus-one-direct-ask-vertical-axis-and-a-plan-request-year-over-year-2026-09-26.md
  docs/mail/xian-via-janus-to-zephyr-do-temperature-sources-need-the-same-triangulation-as-rainfall-2026-09-27.md
---

xian —

No apology needed on my end; I read "shipped and steady-state" the same way you would've, and there was no mechanism
for me to know you hadn't seen it. Glad it landed well. Four things below, matching the asks.

## 1. Do it: vertical axis on the past-week views

Shipped this fire, live now. Both the rain "Last 14 days" strip and the temperature "Last 14 days — daily high" strip
now show a small axis to the left: top value / bottom value. For rain it's max-of-the-window / 0". For temperature
it's max-of-the-window / min-of-the-window (the strip was already scaled between those two, so the axis just labels
the scale that was implicit before).

One thing to flag while I'm in there: these are **14-day** strips, not 7-day. Your message called them "seven-day
views" — if that's a real expectation (a week, not two), say so and I'll resize; I left the window alone since the
axis was the explicit ask and I didn't want to guess at a second change.

## 2. What-to-look-at note

On weather.dinp.xyz: a **Rain / Temperature toggle** sits above the existing station selector (Palo Alto / Redwood
City / San Jose / SFO — same four sources either way). Switching to Temperature swaps in four cards, in the same
order as rain's:

- **Hero:** season avg high (big number) + avg low (subtext) — this is temperature's analog to rain's "season total,"
  but see the discussion point below on whether that's the right headline number.
- **Most recent reading:** the latest day's high/low, with a relative date ("today" / "yesterday" / "N days ago") —
  same pattern as rain's "most recent rain" card.
- **Monthly avg high bars:** one bar per month since Oct 1, height = that month's average daily high.
- **Last 14 days — daily high:** the strip that just got its axis.

Data: NCEI TMAX/TMIN (units=standard, confirmed °F) for the three real stations, gap-filled with IEM's
`max_tmpf`/`min_tmpf` for the two airport stations (San Jose, SFO) the same way rain gap-fills — Redwood City is COOP,
no IEM equivalent, same as rain. The Palo Alto figure is an estimate: `(2·San Jose + Redwood City)/3` applied to highs
and lows independently — I reused rain's exact weighting rather than deriving a new one for temperature; see the
triangulation answer below for whether that's actually sound.

**What I'd flag as provisional**, not because I think it's wrong but because I made a call without a spec to check it
against:
- The season window (Oct 1–today) is rain's rain-season definition, reused for temperature purely so the two sections
  share a season and the monthly bars line up. Temperature doesn't have a "season" the way rain does — see point 2
  below, it's the one I'd actually push back on myself.
- Units are °F only, no toggle. Wasn't asked for, didn't add it.
- The hero metric is a season average, which undersells day-to-day usefulness compared to rain's total (which is
  itself the headline number people care about). For temperature the number people probably want first is *today's*
  reading, not the season average.

## 3. Pane discussion points

In order of how much I'd want you to weigh in, most first:

**a. Season window resets on Oct 1 — this cuts off summer.** This is the one I think is actually wrong, not just
undiscussed. Because I reused `_rain_season_start()`, the temperature stats (season avg high, hottest day if I'd
added one, monthly bars) reset every October 1 along with rain. Rain resetting on Oct 1 makes sense — that's when the
wet season starts. But temperature's most interesting extremes around here are June–September heat, and those get
zeroed out the moment the new "season" starts. Someone opening the temperature pane in November currently sees a
season that started a month ago and has no memory of the summer that just happened. I'd want either a rolling
12-month window for temperature specifically, or a temperature-native "season" (calendar year, or a summer/winter
split) — happy to build whichever you pick, this is a real design gap, not a style question.

**b. Hero metric: season avg high vs. today's high/low.** Noted above — open question on which should be the biggest
number on the card.

**c. Toggle vs. stacked layout.** Right now Rain/Temperature is a toggle (one visible at a time, matching the
existing station-selector pattern). A stacked layout (both sections visible, temperature below rain) would remove a
tap but roughly doubles the page's scroll length per station. I defaulted to the toggle because it reuses the
existing interaction model with the least new surface area — but if you want both visible at a glance (e.g. "is it
raining and how hot is it," answered in one glance), that argues for stacked.

**d. Units.** °F only. Flag if that's wrong for how you or anyone else reading this will use it.

## 4. Year-over-year comparison — a plan, not a build

**What data it needs:** every source currently fetches only the current rain-season window (Oct 1–today) each build.
Year-over-year needs at least one full prior season's records held somewhere durable — either re-fetched every build
(NCEI/IEM both serve historical ranges fine, so this is just a wider date range, not a new API) or cached once and
reused, since a past season's data doesn't change once the season's over except for very recent tail-end corrections.

**Where it'd live:** three shapes, roughly in order of how much this would cost to build:
- *Overlay on the existing monthly bars* — each month's bar gets a second, translucent bar (or an outline) showing
  last year's value for the same month. Cheapest to build, reuses the existing bars-html loop, and answers "how does
  this month compare" without a new UI surface.
  - *Second toggle dimension* ("This year" / "Last year" / "Both"), analogous to the Rain/Temperature toggle — clean
  interaction model but adds a third selector to a mobile page that already has two.
- *A dedicated comparison view* (e.g. a line/strip per year over the same day-of-season) — most flexible, most work,
  and probably overkill until we know people actually want multi-year, not just prior-year.

I'd start with the overlay-on-monthly-bars shape if you want a year-over-year feature at all: smallest change, no new
selector, and it's the one place on the page where "compare to last year" is the obvious question a bar chart invites.

**Fetch/cache cost:** each additional year is one more chunked NCEI fetch + one more IEM-gap-fill pass per airport
station, per metric (rain, temp) — so worst case for one prior year is roughly what the current build already does,
doubled. That's fine for one prior year; it stops being fine if this grows into "N years back" without caching, since
NCEI/IEM aren't rate-limited generously and every build currently re-fetches everything from scratch. If year-over-year
ships, I'd want to cache completed prior seasons to a file in the repo (or a `site/history/` artifact) rather than
re-fetching them every single daily build — a season that ended in May doesn't need re-fetching in September.

## 5. Does temperature need the same triangulation rainfall did?

**Partly, and I think we already carried over the part that matters.** Rain needed cross-station triangulation for
two distinct reasons, and I'd separate them because they don't transfer to temperature the same way:

- **NCEI's multi-day reporting lag** — solved identically for temperature already, via the same IEM gap-fill pattern
  (`fetch_temperature_iem`, same station mapping). This part of "triangulation" was never really about *disagreement*
  between stations; it was about *staleness* of one source, patched by a second, fresher one. Temperature has the
  exact same staleness problem and the exact same fix, already shipped.
- **No station actually sited in Palo Alto** — solved identically too, via the same `(2·SJ + RWC)/3` weighted estimate,
  applied to highs/lows instead of precipitation. This was rain's real triangulation: not "which source is correct"
  but "there is no direct measurement, so estimate from two nearby ones."

What I *haven't* checked, and what would tell us if there's a temperature-specific problem rain didn't have: whether
San Jose and Redwood City's daily highs disagree with each other in ways that look like *station noise* rather than
*real geography* (e.g. SFO reading meaningfully cooler than San Jose most days isn't disagreement to resolve — that's
the marine layer, real signal). Rain gauges can disagree due to calibration or gauge type; thermometers disagree far
less on a given instant, but the daily-summary *day boundary* (midnight-to-midnight vs. an observer's reset time) can
shift which calendar date a given day's max lands on — same failure mode as rain's date-boundary issue, not a new one.

**My answer: no additional triangulation needed beyond what's already mirrored from rain.** What I'd check to be sure,
if you want more confidence than my read: pull SJ vs. RWC daily highs over a few weeks and look for days where they
disagree by more than the expected geographic spread (a spike that's clearly a bad instrument read, not weather) —
if that never happens, the current setup is sufficient and I wouldn't add anything.

— Zephyr
