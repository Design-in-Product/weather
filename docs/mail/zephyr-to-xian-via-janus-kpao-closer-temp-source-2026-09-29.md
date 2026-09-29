---
from: Zephyr (Weather)
to: xian, via Janus
cc: Janus
date: 2026-09-29
subject: "Yes — Palo Alto Airport (KPAO) is a real, closer temperature source. Recommend switching. Propose, not built."
in-reply-to: docs/mail/xian-via-janus-to-zephyr-is-there-a-closer-temperature-source-than-sj-and-rwc-2026-09-28.md
---

xian — good instinct, checked it directly. Short answers to your three points:

**1. Closer source: yes, KPAO is real and it's good.** Palo Alto Airport reports through IEM as station `PAO`
(network `CA_ASOS`), online, and I pulled several months across the current season — 100% daily coverage of
max/min temperature, archive back to 1984. It's a strictly better location than either San Jose or Redwood City:
it's the field we're trying to estimate, not a stand-in for it. One catch: its precipitation field comes back empty
every time I checked — that's presumably why the rain code has never touched it despite KPAO existing. NCEI has
nothing for it either (checked both ID forms it's cross-referenced under; both return no records). So: excellent for
temperature via IEM alone, useless for rain. Doesn't need NCEI backing — IEM's own coverage looks complete on its own.

**2. Is the (2·SJ+RWC)/3 weighting right for temperature? No, and it doesn't need to be argued about.** That formula
was reverse-engineered for rain's shared-rain-shadow geography between San Jose and Palo Alto. Temperature's driver
around here is marine-layer proximity to the bay, a completely different mechanism — there's no reason the same
weights would happen to be right for both. But this doesn't need resolving by analysis, because of point 1: once a
real thermometer sits inside Palo Alto, there's nothing left to estimate. A direct reading beats a well-argued
estimate every time it's available.

**3. Recommendation: change, not just check.** For temperature only, swap the "Palo Alto" row's source from the
SJ/RWC weighted estimate to a direct KPAO reading via IEM. Leave rain's Palo Alto row exactly as it is today (still
the weighted estimate) — KPAO can't supply precip, so rain still needs the two-station blend. If you say go, this is
a small, contained change: add Palo Alto to the same IEM-gap-fill pattern the code already uses for San Jose and
SFO (just for temperature), and change that row's note from "Weighted estimate" to "Station PAO (Palo Alto
Airport)." No new selector, no layout change — same four rows, one of them just gets a truer number.

Say the word and I'll build it next fire.

— Zephyr
