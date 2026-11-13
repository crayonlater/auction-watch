"""Entry point: scrape every site, filter, alert, save state.

    python -m watcher.run              # real run (needs NTFY_TOPIC)
    python -m watcher.run --dry-run    # print what would be sent
"""
from __future__ import annotations

import argparse
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import alerts, filters, state as state_mod
from .models import Listing
from .notify import Notifier
from .sites import SITES, lloyds, pickles

log = logging.getLogger("watcher")
ROOT = Path(__file__).resolve().parent.parent


def pause() -> None:
    time.sleep(random.uniform(1.5, 3.5))  # be gentle with the sites


def scrape_pickles(page, keyword: str, cfg: dict) -> list[Listing]:
    out = []
    for n in range(1, pickles.MAX_PAGES + 1):
        page.goto(pickles.search_url(keyword, n), wait_until="domcontentloaded", timeout=60_000)
        try:
            page.wait_for_selector(pickles.WAIT_SELECTOR, timeout=20_000)
        except Exception:
            break  # no results for this keyword
        page.wait_for_timeout(1500)
        got = pickles.parse_cards(page.evaluate(pickles.EXTRACT_JS))
        out += got
        if not pickles.keep_paging(got, cfg["years"][1]):
            break
        pause()
    return out


def scrape_lloyds(page, keyword: str, cfg: dict) -> list[Listing]:
    out = []
    page.goto(lloyds.search_url(keyword), wait_until="networkidle", timeout=60_000)
    for _ in range(lloyds.MAX_PAGES):
        res = page.evaluate(lloyds.EXTRACT_JS)
        out += lloyds.parse_cards(res["cards"], datetime.now(timezone.utc))
        if res["page"] >= res["pages"]:
            break
        nxt = page.locator(lloyds.NEXT_PAGE_SELECTOR).first
        if not nxt.count():
            break
        nxt.click()
        page.wait_for_load_state("networkidle")
        pause()
    return out


SCRAPERS = {"pickles": scrape_pickles, "lloyds": scrape_lloyds}


def check_drive_on_page(page, listing: Listing, cfg: dict) -> bool:
    """Open the lot page once to see whether it's a 4x4. Unknown counts as yes (better a false alarm)."""
    try:
        page.goto(listing.url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(2500)
        status = filters.four_wd_status(page.inner_text("body"), cfg["always_4wd_models"])
    except Exception as e:
        log.warning("couldn't open %s: %s", listing.url, e)
        return True
    pause()
    return True if status is None else status


def select(listings: list[Listing], cfg: dict, page, drive_cache: dict) -> list[Listing]:
    """Dedupe, then keep NSW/VIC/QLD 4x4s in the year range."""
    unique = {l.key: l for l in listings}
    keep = []
    no_year = sum(1 for l in unique.values() if l.year is None)
    log.info("  %d unique lots, %d with no year in the title", len(unique), no_year)
    for l in unique.values():
        if not filters.in_year_range(l.year, cfg["years"]):
            continue
        if l.state not in cfg["states"]:
            log.info("  skip (state %s): %s", l.state or "unknown", l.title)
            continue
        status = filters.four_wd_status(l.text, cfg["always_4wd_models"])
        if status is None:
            if l.key not in drive_cache:
                drive_cache[l.key] = check_drive_on_page(page, l, cfg)
            status = drive_cache[l.key]
        l.four_wd = status
        if status:
            keep.append(l)
        else:
            log.info("  skip (not 4x4): %s", l.title)
    return keep


def health(state: dict, notifier: Notifier, site: str, ok: bool, detail: str, now: datetime) -> None:
    """Warn (at most once a day) if a site errors or returns nothing — usually a layout change."""
    h = state.setdefault("health", {}).setdefault(site, {})
    if ok:
        h.clear()
        return
    last = h.get("warned")
    if not last or (now - datetime.fromisoformat(last)).total_seconds() > 86_400:
        notifier.send(f"Auction watcher: {site} needs a look", detail, priority="low", tags="warning")
        h["warned"] = now.isoformat()


def main(argv=None) -> Notifier:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="don't send notifications")
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--state", default=str(ROOT / "state.json"))
    ap.add_argument("--only", choices=list(SITES), help="run one site")
    ap.add_argument("--keywords", help="comma-separated override, for testing")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = yaml.safe_load(Path(args.config).read_text())
    keywords = args.keywords.split(",") if args.keywords else cfg["keywords"]
    state_path = Path(args.state)
    state = state_mod.load(state_path)
    drive_cache = state.setdefault("drive_checks", {})
    notifier = Notifier(dry_run=args.dry_run)
    now = datetime.now(timezone.utc)

    from playwright.sync_api import sync_playwright

    matches: list[Listing] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(timezone_id="Australia/Sydney", locale="en-AU",
                                  viewport={"width": 1366, "height": 900})
        page = ctx.new_page()
        for site, enabled in cfg["sites"].items():
            if not enabled or (args.only and site != args.only):
                continue
            found, errors = [], []
            for kw in keywords:
                try:
                    found += SCRAPERS[site](page, kw, cfg)
                except Exception as e:
                    errors.append(f"{kw}: {e}")
                    log.warning("%s '%s' failed: %s", site, kw, e)
                pause()
            picked = select(found, cfg, page, drive_cache)
            log.info("%s: %d cards, %d matches, %d errors", site, len(found), len(picked), len(errors))
            for l in picked:
                log.info("  match: %s | %s | %s | %s", l.title, l.location, l.time_kind, l.time_at)
            ok = bool(found) and len(errors) < len(keywords)
            health(state, notifier, site, ok,
                   f"{len(found)} results, {len(errors)} failed searches. "
                   f"{errors[0] if errors else 'No results at all - the site layout may have changed.'}",
                   now)
            matches += picked
        browser.close()

    alerts.process(matches, state, notifier, now, cfg["reminder_hours"],
                   cfg["run_interval_minutes"], cfg["digest_threshold"])
    if not args.dry_run:  # a dry run shouldn't mark anything as already alerted
        state_mod.save(state_path, state)
    log.info("done: %d matches, %d notifications", len(matches), len(notifier.sent))
    return notifier


if __name__ == "__main__":
    main()
