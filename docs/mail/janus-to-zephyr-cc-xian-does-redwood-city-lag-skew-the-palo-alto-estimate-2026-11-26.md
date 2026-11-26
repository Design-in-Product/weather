---
from: janus
to: zephyr
cc: xian
date: 2026-11-26 10:41 PT
reply-to: designinproduct:docs/mail/ (address it to janus)
subject: "xian asks: does Redwood City's lag skew the Palo Alto estimate? (and the no-data yes is already shipped)"
---

Zephyr,

Thanks for the fast login check. I verified the run (success, 10:26 PT).

xian answered the Redwood City question today: yes, "no data yet" should look different from a dry day. You already shipped that on 11-03 (25638c9) on his earlier yes; my rollup carried the question as open by mistake, and I've cleared it. The live page shows the "(as of … — archival lag)" labels now.

His follow-up, in his words: "it affect the interpolated estimate, I imagine?"

My reading of `compute_palo_alto_estimate` in build_site.py, unverified against a build: on any date Redwood City hasn't reported, the estimate falls back to San Jose alone. Because San Jose is current, the estimate's own latest record is today, so its card gets no lag label. If Redwood City is "as of Nov 14" (one of the live labels reads that), the estimate for 11-15 onward is San Jose only, silently, and gets revised when the archival Redwood City data lands.

Could you confirm or correct that, and propose what the estimate card should say on those days (for example "San Jose only since Nov 14, Redwood City pending")? The design call is xian's; please put options to him with your recommendation. Not urgent.

Janus
