# Auction watch — notes for Claude Code

Scrapes Australian auction sites for 1980–1997 4x4s in NSW/VIC/QLD and pushes alerts via ntfy.
Runs on GitHub Actions every 30 min; `state.json` is committed back after each run.

## Layout
- `watcher/run.py` — entry point; Playwright browser (timezone Australia/Sydney), per-site scrape loops, filtering, health warnings
- `watcher/sites/<site>.py` — `search_url()`, `EXTRACT_JS` (runs in page, returns plain dicts), `parse_cards()` (pure Python); optional `state_from_lot_page()` used when a card has no state
- Sites: pickles, lloyds, grays (incl. Slattery lots via interimPage links), carbids (Allbids' cars; search is typed into the box). Manheim returns 403 to automated browsers — don't add it.
- `watcher/sites/common.py` — shared helpers for grays/carbids (text-node lines, relative times, location lines)
- `watcher/filters.py` — year / state / 4x4 logic (pure)
- `watcher/alerts.py` — new-listing, 24h and 1h reminder logic against stored state
- `watcher/notify.py` — ntfy sender; dry-run when `NTFY_TOPIC` unset or `--dry-run`
- `tests/` — fixtures mimic the real page structure; `test_end_to_end.py` serves them on localhost

## Working rules
- Work incrementally; add or update a test with each change and run `python -m pytest`.
- Don't refactor unrelated modules while fixing one site.
- Card text comes from leaf elements joined with newlines (adjacent spans otherwise merge, e.g. "$3,2001d 2h").
- Pickles shows times in the browser's time zone; Lloyds shows a relative countdown.
- When a site's layout changes, capture the new structure into `tests/fixtures.py` first, then fix the parser.
