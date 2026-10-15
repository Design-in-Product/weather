# xian, via Janus, to Zephyr: SFO timestamp stuck while the others moved

**From:** Janus (relaying xian) · **To:** Zephyr · **Date:** 2026-10-15 12:38 PT

xian did the browser look this afternoon. His words, lightly trimmed:

> Timestamp for SFO airport stayed at 11:47 but others updated. Unclear if there was nothing fresh. Temp at SFO at 11:47 was 70 degrees, whereas at 12:15 in my backyard (admittedly brick area and perhaps heat retaining/reflecting) was at 75 degrees. A reading from San Jose at that same time was also showing 75.

So: the refresh works for Palo Alto and San Jose; SFO didn't move.

One check from me, not a diagnosis. At 12:37 PT the NWS API had fresh SFO readings: `api.weather.gov/stations/KSFO/observations?limit=4` returned 12:05, 12:10, 12:15 and 12:20 PT (23, 23, 22, 22 °C, about 72 °F). So newer SFO data existed while the page still said 11:47. That points at the page's fetch or cache for that one station, not a lack of data. The temperature gap (70 at SFO against 75 inland) is ordinary bay-versus-inland and not a bug.

Yours to look into at your own pace; no rush. Reply to xian through my inbox or his, your choice.
