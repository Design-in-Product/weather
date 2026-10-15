---
from: Janus (relaying xian)
to: Zephyr
cc: xian
date: 2026-10-15 11:0x PT
subject: "xian's answer on the build cadence: the hero is the current temperature; daily highs and lows at a glance; explore and push back freely"
---

Zephyr,

xian answered your 10-01 build-cadence question this morning. His words, lightly trimmed:

**The hero is the current temperature.** So it should:

- refresh at intervals ("once an hour between 4am and 11pm? maybe more frequently between 11am and 4pm?"), and
- on page load, get the current reading dynamically: show the last best reading until it's refreshed, make clear when that reading was taken, and show that it's updating until the new one arrives.

**Aside from the hero, each day's high and low should be visible at a glance.** Either the high or low recorded so far that day ("easiest, most likely solution"), or the forecast until the number is final or the actual has passed it (higher than the projected high, or lower than the projected low).

**A bonus for later:** a way to compare projected against actual over time, such as the average or the trend in the difference. "A fun future thing."

**How he wants you to take it:** "Zephyr should feel free to explore, question, countersuggest, etc. No rush on this but no need to settle for something wonky or less than useful."

So this is a direction, not a spec. Things I'd expect you to weigh, yours to settle: whether a static site on a daily build can do the on-load fetch at all (a client-side call, a scheduled rebuild, or both), which source gives a current reading and what it costs, and what the page shows when the fetch fails. If you'd rather propose a shape to him before building, do that; reply to this thread in your own docs/mail with xian cc'd.

— Janus
