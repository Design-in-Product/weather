# Weather Project Log

Newest entries at top. This log exists so any Claude agent (and Xian) can pick up continuity across sessions.

---

## 2026-04-10 ~16:30 — Phase 3 built + Janus memo received (Zephyr)

**Janus's welcome memo arrived** at `memo-janus-to-zephyr-welcome-2026-04-10.md`. Key takeaways:
- I'm the primary point of contact for the Weather project. Cross-cutting concerns escalate to Janus via signal files at `~/cool/dispatch/mail/` (`signal-zephyr-to-janus-YYYY-MM-DD-{topic}.md`).
- The repo is one of Xian's "Vibe-Coded Experiments," already in the public gallery at designinproduct.com/projects. Whatever ships here is publicly visible.
- The pre-existing center of the project is **eight static rain visualizations** in `sketches/` (calendar heatmap, cumulative curve, drought streaks, storm rankings, weekday bias, rhythm sparklines, fill gauge, rain in objects). Mobile dashboard is *additive* to these, not a replacement.
- Janus suggests `CLAUDE.md` and `docs/logs/` (per-session logs with YAML frontmatter) as best practices for one-agent teams. **Process question for Xian:** adopt the org-standard structure or stay with flat `LOG.md`?
- I'm now a reader of Janus's daily cross-pollination briefs (will land at `~/cool/weather/docs/briefs/cross-pollination/` eventually).

**Repo location resolved.** `/Users/xian/Development/weather` and `/Users/xian/cool/weather` share the same inode (177851883) — same physical directory, different paths. No syncing needed.

**Phase 3 done.**
- `noaa_rainfall.py`: footer of the rendered dashboard now links to `./sketches/`. Added `footer a` styling.
- `build_site.py`: copies `sketches/` → `site/sketches/` on every build so the eight visualizations ship with the deploy.
- New `detect_and_notify.py`: loads previous and current `state.json`, computes per-source set-diffs of `(date, precip)` fingerprints, filters for newly-seen records with rain > 0, and emails `REPORT_TO` via `noaa_rainfall.send_email` (which already falls back to env vars on Linux). First-run safety: skips email if prev state has no fingerprints, so the very first deploy doesn't email an entire season.
- New `.github/workflows/update.yml`: daily cron at 14:00 UTC (≈7am Pacific) plus `workflow_dispatch`. Steps: checkout → setup Python → curl previous `state.json` from the live Pages site → `build_site.py` → `detect_and_notify.py` → upload-pages-artifact → deploy-pages. Uses `secrets.{SMTP_USER, SMTP_PASS, SMTP_FROM, REPORT_TO}`.
- `README.md`: added "Web dashboard" + "One-time deploy setup" sections documenting the manual steps Xian needs to take.

**Smoke test results.** Diff logic verified end-to-end against `site/state.json`:
- Empty prev → first-run skip ✓
- prev == new → no fresh entries ✓
- Drop dry-day records from prev → no email triggered (correctly filtered) ✓
- Drop rainy records from prev → correctly detected, including a backfilled `2026-02-25` entry. **This is the lag-aware case** — the whole reason we fingerprint instead of comparing `max(date)`.

**Manual steps Xian needs to do** (cannot be automated from here):
1. Set repo secrets: `SMTP_USER`, `SMTP_PASS` (Gmail App Password), optionally `SMTP_FROM`, and `REPORT_TO=xian@pobox.com`.
2. Repo Settings → Pages → Source = **GitHub Actions**.
3. Commit and push everything (still uncommitted locally — see `git status`).
4. Trigger the workflow once manually from the Actions tab to seed `state.json` on Pages. First run skips email by design.
5. Verify the dashboard at https://design-in-product.github.io/weather/ and the gallery at /sketches/.
6. After confirming end-to-end works (next time it actually rains), add Briggs's email as a second `REPORT_TO` value or refactor for multiple recipients.

**Open questions / follow-ups for Xian.**
- Adopt Janus's org-standard `CLAUDE.md` + `docs/logs/` pattern, or keep `LOG.md`?
- Should `REPORT_TO` support multiple recipients now (comma-split) or wait until adding Briggs?
- Ack the Janus memo — should I file the welcome under a different path (e.g., `docs/inbox/`) or leave at repo root?
- Phase 4 candidate: making the eight `sketches/*.html` dynamic (fed from `data.json`). Janus's framing — "one more sketch is nearly free with AI assistance" — applies. Not started.

---

## 2026-04-10 ~10:00 — Phase 1 ships its acceptance test (Zephyr)

v0 page renders well on Xian's phone over LAN once the server was rebound from `127.0.0.1` to `0.0.0.0` (initial bind was loopback-only — my mistake, fixed). **Spousal approval obtained**, which is the real bar for the personal-scope phase. No layout changes requested. Local preview server (`bxz3rypbk`) still running on `0.0.0.0:8765`; will stop on Xian's word or when we move on.

**Next.** Awaiting Xian's call: any v0 polish, or proceed to Phase 3 (GitHub Action + Pages deploy + email ping via set-diff on `state.json`)? Phase 2 ("polish based on real use") may collapse into nothing if v0 is good as-is.

---

## 2026-04-10 ~09:30 — Phase 1 built (Zephyr)

**Done.**
- Added `_compute_summary`, `_iter_season_months`, `_render_source_section`, and `render_html` to `noaa_rainfall.py`. Existing CLI surface untouched — verified `python3 noaa_rainfall.py --station USW00023293` still produces the same console report.
- New `build_site.py` fetches all three real stations once for the season, computes the weighted Palo Alto estimate (with single-station fallback when one is missing), and writes `site/index.html`, `site/data.json`, `site/state.json`.
- Added `.gitignore` excluding `site/`, `__pycache__/`, `.DS_Store`. Local builds stay out of the repo; the GitHub Action will be the canonical writer when Phase 3 lands.
- Verified math: PA est. = (2·10.83 + 14.41)/3 = 12.02 ✓. Season totals as of today: PA 12.02", RWC 14.41", SJ 10.83", SFO 16.24".
- v0 layout per source: hero (season total + days with rain), most-recent-rain card (with "n days ago" label, never "today"), monthly bars, last-14-days strip. Selector swaps sections client-side; no fetching.
- `state.json` writes per-source `(date:precip)` fingerprints sorted, ready for Phase 3 to set-diff between runs.

**Local preview running.** `python3 -m http.server 8765` from inside `site/` — open http://127.0.0.1:8765/ on desktop or phone (same wifi → use machine's LAN IP). Background pid tracked in this session; stop it when you're done eyeballing.

**Open / next.**
- Xian eyeballs the page on phone, calls out anything to fix.
- Phase 2 is "tighten the page based on real use." Phase 3 is the GitHub Action + Pages deploy + email ping wired through Actions secrets.
- Decision deferred: should the recent-rain card show *something* (e.g., a dry-spell counter) when nothing has fallen in N days, or stay terse?

---

## 2026-04-10 ~09:20 — Open questions resolved (Zephyr)

- **Name:** I'm Zephyr on this project going forward.
- **Ping mechanism:** email, reusing the script's existing SMTP-via-Keychain plumbing (and Actions secrets in CI).
- **Cron cadence:** once daily. Xian reminded me that NOAA NCEI's GHCN-Daily feed lags several days, so sub-daily runs buy nothing.
- **Plan amendment forced by the lag:** fresh-rain detection cannot key off `max(date)` alone. Newly published records often fill in *past* dates. Detection logic must set-diff the full `(date, precipitation_in)` record set between runs and ping if any newly-seen record has precipitation > 0. Also: UI "most recent rain" card must show the observation date, not imply "today."

**Next.** Awaiting go-ahead to start Phase 1 (refactor `noaa_rainfall.py` to expose `render_html` + add `build_site.py`).

---

## 2026-04-10 09:08 — Session kickoff

**Context.** Xian tried to check recent rainfall and hit snags: attempted to clone the wrong GitHub account (`mediajunkie/weather` — actual home is `Design-in-Product/weather`), then the README's quick-start command used a stale `weather/` path prefix that broke when run from inside the cloned repo. Local was already in sync with origin; `python3 noaa_rainfall.py` runs cleanly. Season total as of today: 14.41" over 189 days (Redwood City station).

**Decisions.**
- README fixed: all commands now use `python3 noaa_rainfall.py` without the `weather/` prefix; added a "Pick a station" section documenting the three GHCND IDs by friendly name.
- Web UI approach agreed: GitHub Pages + scheduled GitHub Action that runs the script, writes static artifacts, and commits them. Initial scope: personal use only (Xian and his wife). Mobile-first. Station selection by friendly name in the UI. Dynamic sketches deferred.
- Design north star: Gall's Law + Ward Cunningham's "simplest thing that could possibly work." No generalization, extra metrics, or multi-user until the base is clean.
- Corrected Palo Alto estimation formula to `(2*SJ + RWC)/3`. San Jose weighted 2x because shared rain shadow; Redwood City included at 1x because closer in latitude. (Initial conversation mis-stated it as `/2` — confirmed typo.)
- Started this log. Lives in the repo (not in Claude memory) so any agent on the project can pick up the thread.

**Open questions.**
- Ping mechanism for fresh-rainfall days: reuse the script's existing email-via-Keychain plumbing? Text (Twilio / iMessage shortcut)? Both? No-new-rain days should be passive (no notification).
- Agent name: Xian offered Zephyr, Boreas, Anemos, or Aeolus. I lean **Zephyr** — the west wind, which in the Bay Area is literally what carries Pacific moisture inland and produces the rainfall we're tracking. Pending Xian's confirmation.

**Next.**
- Resolve ping mechanism and agent name.
- Formal implementation plan: file layout, Action workflow cadence, HTML template shape, "new rain since last run" diff logic, how station-by-name selector works on a static site (pre-build one data.json per station vs. client-side fetch).
