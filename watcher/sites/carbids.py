"""Carbids (carbids.com.au) — the car side of Allbids, so it covers Allbids' vehicles too.

Search isn't a plain URL (it's an Angular page), so the scraper types the keyword
into the "Show me results for..." box. Each result has an h2 title link ending in
the item id (…-1681082), a suburb line then a state line ("Moorebank" / "NSW"),
the current bid, and "4d 1h left (Tuesday 7:35 AM)".
Titles start with the build date, e.g. "02/2006 Toyota Landcruiser Prado ...".
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from ..filters import parse_year
from ..models import Listing
from .common import LEAF_LINES_JS, location_from_lines, parse_relative, price_from_lines

NAME = "carbids"
BASE = "https://www.carbids.com.au"
SEARCH_BOX = 'input[placeholder^="Show me results"]'
WAIT_SELECTOR = 'a[href*="/c/"] h2'

# Climbs from each title link to the largest ancestor holding only that item.
EXTRACT_JS = "() => {" + LEAF_LINES_JS + r"""
  const itemId = href => (href.match(/-(\d+)(?:[?#].*)?$/) || [])[1];
  const titleLinks = [...document.querySelectorAll('a[href*="/c/"]')]
    .filter(a => a.querySelector('h2') && itemId(a.href));
  const idsIn = el => new Set([...el.querySelectorAll('a[href*="/c/"]')]
    .map(a => itemId(a.href)).filter(Boolean)).size;
  const out = [], seen = new Set();
  for (const a of titleLinks) {
    const id = itemId(a.href);
    if (seen.has(id)) continue;
    seen.add(id);
    let card = a;
    while (card.parentElement && idsIn(card.parentElement) <= 1) card = card.parentElement;
    out.push({ id, href: a.href, title: a.querySelector('h2').innerText.trim(), lines: leafLines(card) });
  }
  return out;
}
"""

_TIME_LEFT = re.compile(r"^(?:\d+\s*[dhms]\s*)+left\b", re.I)  # "4d 1h left", "45m left"
_YEAR_AFTER_SLASH =re.compile(r"^\s*\d{1,2}/((?:19|20)\d{2})\b")


def year_from_title(title: str) -> Optional[int]:
    m = _YEAR_AFTER_SLASH.match(title or "")
    return int(m.group(1)) if m else parse_year(title)


def parse_cards(raw: list[dict], now: datetime) -> list[Listing]:
    listings = []
    for card in raw:
        lid = card.get("id")
        if not lid:
            continue
        title = (card.get("title") or "").strip()
        lines = card.get("lines") or []
        time_line = next((l for l in lines if _TIME_LEFT.search(l)), None)
        delta = parse_relative(time_line)
        location, state = location_from_lines(lines)
        listings.append(Listing(
            site=NAME, id=str(lid), title=title, url=(card.get("href") or "").split("?")[0],
            year=year_from_title(title), state=state, location=location,
            price=price_from_lines(lines),
            time_at=(now + delta) if delta else None, time_kind="ends" if delta else None,
            text=title + "\n" + "\n".join(lines),
        ))
    return listings
