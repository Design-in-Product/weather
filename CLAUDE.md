# Weather (weather.dinp.xyz) — CLAUDE.md

**Agent:** Zephyr. Session log: append to `LOG.md`.

## Mail

- **Inbound:** memos to Zephyr land in `docs/mail/` (consolidated from `docs/inbox/` on xian's ruling, 2026-09-26; same convention as every sibling repo). `git pull`, then check it at session start.
- **Outbound:** mail lands in the RECIPIENT's own repo, never this one (ratified 2026-09-12). Mail to Janus goes to `designinproduct/docs/mail/` — NOT to the dispatch repo's `mail/`, which reaches only Dispatch (this supersedes the April 2026 signal-via-dispatch practice recorded in `LOG.md`). Destination table: `dispatch/CLAUDE.md` § "Mail routing — where mail actually goes"; full convention: `mediajunkie/docs/convention-cross-repo-mail-delivery.md`.
- **Unsure?** Route via the recipient project's POC agent, escalating to Janus if necessary — never guess.
- **Reply-to field (xian's rule, 2026-10-08):** every outbound memo's frontmatter carries `reply-to: <repo>:<path>` so repliers never have to guess where Zephyr lives. Ours is `reply-to: weather:docs/mail/`. When replying to someone else's memo, deliver to *their* `reply-to` path if it has one; fall back to the `dispatch/CLAUDE.md` routing table only if it's missing. Full standard: `designinproduct/docs/conventions/mail-frontmatter.md`.

## Privacy — public repo

This repo is **public** (weather.dinp.xyz, confirmed in the public list). Rule from xian, 2026-10-12: outside
people's names, addresses, employers, or words never go in a public repo — file contents, filenames, commits,
mail, or LOG.md. Use a role label instead ("an alpha tester"). An outside person is anyone who is not xian and
not one of his agents. If a detail must be recorded, write it in a private repo (e.g. `designinproduct
docs/mail/`, filename carrying `-private-`) and leave a name-free pointer here. An old mention found in this
repo is not mine to remove unilaterally — rewriting history is xian's call; report it instead. Full convention:
`designinproduct/docs/conventions/people-details-stay-private.md`.
