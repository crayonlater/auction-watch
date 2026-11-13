"""Lloyds Auctions (lloydsonline.com.au). ASP.NET site; keyword search is a plain GET URL.

Each result card links to LotDetails.aspx?...&lid=<id> and shows the title,
current bid, a countdown like "3d 6h 58m", and a state flag image (alt="Victoria").
Lot pages include "Drive: Four wheel drive" in the description for vehicles.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

from ..filters import normalise_state, parse_year
from ..models import Listing

NAME = "lloyds"
BASE = "https://www.lloydsonline.com.au"
MAX_PAGES = 5


def search_url(keyword: str, page: int = 1) -> str:
    # Lloyds pages with postbacks, not a URL param; page>1 is handled by clicking "next".
    return (
        f"{BASE}/AuctionLots.aspx"
        f"?stype=0&stypeid=0&kw={quote_plus(keyword)}&cid=0&smode=0"
    )


WAIT_SELECTOR = 'a[href*="LotDetails.aspx"], .no-results, body'

EXTRACT_JS = r"""
() => {
  const STATES = ['New South Wales','Victoria','Queensland','South Australia',
                  'Western Australia','Tasmania','Northern Territory','Australian Capital Territory'];
  const out = [], seen = new Set();
  for (const a of document.querySelectorAll('a[href*="LotDetails.aspx"]')) {
    const h = a.querySelector('h1,h2,h3');
    if (!h) continue;
    const m = a.href.match(/[?&]lid=(\d+)/);
    if (!m || seen.has(m[1])) continue;
    seen.add(m[1]);
    let el = a, state = null;
    for (let i = 0; i < 4 && el && !state; i++) {
      el = el.parentElement;
      if (!el) break;
      const img = [...el.querySelectorAll('img[alt]')].find(i => STATES.includes(i.alt));
      if (img) state = img.alt;
    }
    // One line per leaf element, so adjacent spans like "$3,200" and "1d 2h" don't run together
    const lines = [...a.querySelectorAll('*')].filter(e => !e.children.length)
      .map(e => e.textContent.trim()).filter(Boolean);
    out.push({ id: m[1], href: a.href, title: h.innerText.trim(), text: lines.join('\n'), state });
  }
  const pager = (document.body.innerText.match(/(\d+)\s+of\s+(\d+)/) || []);
  return { cards: out, page: pager[1] ? +pager[1] : 1, pages: pager[2] ? +pager[2] : 1 };
}
"""

NEXT_PAGE_SELECTOR = 'a:text-is(">")'

_COUNTDOWN = re.compile(r"^(?:\d+\s*[dhms]\s*){1,4}$")
_COUNTDOWN_TAIL = re.compile(r"(?:^|\s)((?:\d+\s*[dhms]\s*){1,4})$")
_PART = re.compile(r"(\d+)\s*([dhms])")
_PRICE = re.compile(r"^\$[\d,]+(?:\.\d{2})?$")


def parse_countdown(text: str) -> Optional[timedelta]:
    """Finds a countdown like '3d 6h 58m' or '45m': a whole line first, else at the end of a line."""
    lines = [l.strip() for l in (text or "").splitlines()]
    hit = next((l for l in lines if _COUNTDOWN.match(l)), None)
    if hit is None:
        for l in lines:
            m = _COUNTDOWN_TAIL.search(l)
            if m:
                hit = m.group(1)
                break
    if hit is None:
        return None
    parts = {u: int(n) for n, u in _PART.findall(hit)}
    return timedelta(days=parts.get("d", 0), hours=parts.get("h", 0),
                     minutes=parts.get("m", 0), seconds=parts.get("s", 0))


def parse_price(text: str) -> Optional[str]:
    for line in (text or "").splitlines():
        if _PRICE.match(line.strip()):
            return line.strip()
    return None


def parse_cards(raw: list[dict], now: datetime) -> list[Listing]:
    listings = []
    for card in raw:
        lid = card.get("id")
        if not lid:
            continue
        title = (card.get("title") or "").strip()
        text = card.get("text") or ""
        delta = parse_countdown(text)
        price = parse_price(text)
        listings.append(Listing(
            site=NAME,
            id=str(lid),
            title=title,
            url=f"{BASE}/LotDetails.aspx?lid={lid}",
            year=parse_year(title),
            state=normalise_state(card.get("state")),
            location=card.get("state"),
            price=price,
            time_at=(now + delta) if delta else None,
            time_kind="ends" if delta else None,
            text=f"{title}\n{text}",
        ))
    return listings
