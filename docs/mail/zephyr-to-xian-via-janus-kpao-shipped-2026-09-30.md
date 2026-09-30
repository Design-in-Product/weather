---
from: Zephyr (Weather)
to: xian, via Janus
cc: Janus
date: 2026-09-30
subject: "Shipped: Palo Alto temperature now reads directly from KPAO — live now"
in-reply-to: docs/mail/xian-via-janus-to-zephyr-go-use-kpao-for-palo-alto-temperature-2026-09-29.md
---

xian — live now. Palo Alto's temperature row reads directly from KPAO via IEM; its note says "Station PAO (Palo Alto
Airport)". Rain's Palo Alto row is untouched — still the (2·SJ+RWC)/3 weighted estimate, since KPAO doesn't report
usable precipitation.

On Janus's like-for-like question: yes, I switched it. The year-over-year comparison data (last season's cached
snapshot) now also uses KPAO for Palo Alto's temperature, so this season's KPAO numbers compare against last
season's KPAO numbers, not against the old estimate. Regenerated `history/2024-2025.json` to match before shipping,
so the faint overlay bar was never comparing two different sources.

One number worth knowing, not a problem to fix: Palo Alto's season-average high is now noticeably lower than before
(69° vs. the estimate's earlier 73°) — KPAO sits right on the bay shoreline, so it likely runs cooler than the
SJ/RWC blend did. That's not a bug, it's the whole point: San Jose and Redwood City were never quite the right
place, and now the number reflects the actual airport instead of a blend of two nearby-but-not-quite-right ones.

— Zephyr
