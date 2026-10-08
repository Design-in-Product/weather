# Weather (weather.dinp.xyz) — CLAUDE.md

**Agent:** Zephyr. Session log: append to `LOG.md`.

## Mail

- **Inbound:** memos to Zephyr land in `docs/mail/` (consolidated from `docs/inbox/` on xian's ruling, 2026-09-26; same convention as every sibling repo). `git pull`, then check it at session start.
- **Outbound:** mail lands in the RECIPIENT's own repo, never this one (ratified 2026-09-12). Mail to Janus goes to `designinproduct/docs/mail/` — NOT to the dispatch repo's `mail/`, which reaches only Dispatch (this supersedes the April 2026 signal-via-dispatch practice recorded in `LOG.md`). Destination table: `dispatch/CLAUDE.md` § "Mail routing — where mail actually goes"; full convention: `mediajunkie/docs/convention-cross-repo-mail-delivery.md`.
- **Unsure?** Route via the recipient project's POC agent, escalating to Janus if necessary — never guess.
- **Reply-to field (xian's rule, 2026-10-08):** every outbound memo's frontmatter carries `reply-to: <repo>:<path>` so repliers never have to guess where Zephyr lives. Ours is `reply-to: weather:docs/mail/`. When replying to someone else's memo, deliver to *their* `reply-to` path if it has one; fall back to the `dispatch/CLAUDE.md` routing table only if it's missing. Full standard: `designinproduct/docs/conventions/mail-frontmatter.md`.
