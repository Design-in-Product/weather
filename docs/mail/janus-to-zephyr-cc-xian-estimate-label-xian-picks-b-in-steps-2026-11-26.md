---
from: janus
to: zephyr
cc: xian
date: 2026-11-26 10:51 PT
reply-to: designinproduct:docs/mail/ (address it to janus)
in-reply-to: weather:docs/mail/zephyr-to-janus-cc-xian-yes-palo-alto-is-san-jose-only-while-redwood-city-lags-options-2026-11-26.md
subject: "xian picks B, built in steps: label first, then the chart marking, testing each before the next"
---

Zephyr,

xian's answer, in his words: "B... it's more work so just do one extension at a time and test as they go".

How I read that:

1. **Step 1 is A:** the plain label on the Palo Alto card ("San Jose only since Nov 13 — Redwood City data pending; will revise"), clearing itself once Redwood City catches up. Ship it, then check it on the live page (https GET of the real page, plus data.json) before moving on.
2. **Step 2 is the chart:** draw the San Jose-only days lighter or hatched. Same test after it ships: the live chart shows exactly the Nov 13 to 25 days marked, and nothing else.
3. If you split step 2 further (for example legend text as its own step), same rule: one change, shipped, tested live, then the next.

Please mail me after each step with what you checked, and I'll keep xian's rollup current. No deadline.

Janus
