"""Grays (grays.com). Keyword search: /search?q=<kw>&tab=items&page=<n>.

Each result is one link containing an h3 title, an "Ends in 2d: 01h: 16m" <time>,
"Current bid: $X" and, for Grays' own lots, a location line like "Hexham, NSW".
Grays also shows Slattery Auctions lots: those link through
/redirection/interimPage?url=<slattery url> and have no location on the card, so the
Slattery lot page is opened once to read "Location ... SA 5095".
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import parse_qs, quote_plus, urlparse

from ..filters import parse_year
from ..models import Listing
from .common import (LEAF_LINES_JS, location_from_lines, parse_relative, price_from_lines,
                     state_from_address_page)

NAME = "grays"
BASE = "https://www.grays.com"
MAX_PAGES = 4


def search_url(keyword: str, page: int = 1) -> str:
    return f"{BASE}/search?q={quote_plus(keyword)}&tab=items&page={page}"


WAIT_SELECTOR = 'a[href*="/lot/"] h3, a[href*="interimPage"] h3'

EXTRACT_JS = "() => {" + LEAF_LINES_JS + r"""
  const out = [], seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/lot/"], a[href*="interimPage"]')) {
    const h = a.querySelector('h3');
    if (!h || seen.has(a.href)) continue;
    seen.add(a.href);
    const t = a.querySelector('time');
    out.push({ href: a.href, title: h.innerText.trim(), lines: leafLines(a),
               time: t ? t.innerText.trim() : null });
  }
  return out;
}
"""

_LOT_ID = re.compile(r"/lot/([^/?#]+)")


def _slattery(href: str) -> Optional[tuple[str, str]]:
    """interimPage link -> (asset id, clean Slattery URL)."""
    q = parse_qs(urlparse(href).query)
    target = (q.get("url") or [""])[0]
    m = re.search(r"slatteryauctions\.com\.au/assets/([A-Za-z0-9]+)", target)
    if not m:
        return None
    t = urlparse(target)
    auction = parse_qs(t.query).get("auctionId", [""])[0]
    clean = f"https://www.slatteryauctions.com.au/assets/{m.group(1)}"
    return m.group(1), clean + (f"?auctionId={auction}" if auction else "")


def parse_cards(raw: list[dict], now: datetime) -> list[Listing]:
    listings = []
    for card in raw:
        href = card.get("href") or ""
        if "interimPage" in href:
            s = _slattery(href)
            if not s:
                continue
            lid, url, source = f"slattery-{s[0]}", s[1], "Slattery"
        else:
            m = _LOT_ID.search(href)
            if not m:
                continue
            lid, url, source = m.group(1), href.split("?")[0], "Grays"
        lines = card.get("lines") or []
        title = (card.get("title") or "").strip()
        location, state = location_from_lines(lines)
        delta = parse_relative(card.get("time"))
        listings.append(Listing(
            site=NAME, id=lid, title=title, url=url, year=parse_year(title),
            state=state, location=location, price=price_from_lines(lines),
            time_at=(now + delta) if delta else None, time_kind="ends" if delta else None,
            text=title + "\n" + "\n".join(lines), extra={"source": source},
        ))
    return listings


def state_from_lot_page(text: str) -> Optional[str]:
    return state_from_address_page(text)
