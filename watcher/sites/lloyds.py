"""Lloyds Auctions (lloydsonline.com.au). ASP.NET site; keyword search is a plain GET URL.

Each result card links to LotDetails.aspx?...&lid=<id> and shows the title,
current bid, a countdown like "3d 6h 58m", and a state flag image (shown as "Victoria").
Lot pages say "Location of item: <address>, WA, Australia", used when the flag can't be read.
Lot pages include "Drive: Four wheel drive" in the description for vehicles.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

from ..filters import parse_year
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
  const out = [], seen = new Set();
  for (const a of document.querySelectorAll('a[href*="LotDetails.aspx"]')) {
    const h = a.querySelector('h1,h2,h3');
    if (!h) continue;
    const m = a.href.match(/[?&]lid=(\d+)/);
    if (!m || seen.has(m[1])) continue;
    seen.add(m[1]);
    // The state flag sits beside the link. Collect alt/title/src of nearby images
    // and let Python work out the state (the flag may be named in any of them).
    let el = a, hints = [];
    for (let i = 0; i < 3 && el; i++) {
      el = el.parentElement;
      if (!el) break;
      const imgs = [...el.querySelectorAll('img,[role="img"],[title],[aria-label]')]
        .filter(im => !a.contains(im));
      if (imgs.length) {
        hints = imgs.flatMap(im => [im.getAttribute('alt'), im.getAttribute('title'),
            im.getAttribute('aria-label'), im.getAttribute('src'),
            typeof im.className === 'string' ? im.className : '',
            getComputedStyle(im).backgroundImage])
          .filter(h => h && h !== 'none');
        break;
      }
    }
    // One line per leaf element, so adjacent spans like "$3,200" and "1d 2h" don't run together
    const lines = [...a.querySelectorAll('*')].filter(e => !e.children.length)
      .map(e => e.textContent.trim()).filter(Boolean);
    out.push({ id: m[1], href: a.href, title: h.innerText.trim(), text: lines.join('\n'), hints });
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


_FULL_STATES = {
    "new south wales": "NSW", "victoria": "VIC", "queensland": "QLD", "south australia": "SA",
    "western australia": "WA", "tasmania": "TAS", "northern territory": "NT",
    "australian capital territory": "ACT",
}
_ABBREV = re.compile(r"(?<![a-z])(nsw|vic|qld|sa|wa|tas|nt|act)(?![a-z])", re.I)


def state_from_hints(hints: list[str]) -> Optional[str]:
    """Card flag image -> state, from its alt/title text or failing that its file name."""
    hints = [h for h in hints or [] if h and "lloyds" not in h.lower()]
    for h in hints:
        low = h.lower()
        for name, code in _FULL_STATES.items():
            if name in low:
                return code
    for h in hints:
        name = h.rsplit("/", 1)[-1].rsplit(".", 1)[0]  # file name without folders/extension
        m = _ABBREV.search(name)
        if m:
            return m.group(1).upper()
    return None


_LOCATION = re.compile(r"Location of item:\s*([^\n]+)", re.I)
_LOC_ABBREV = re.compile(r"(?:,|\s)\s*(NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b")


def state_from_lot_page(text: str) -> Optional[str]:
    """'Location of item: 90-94 Bannister Road, Canning Vale, WA, Australia' -> 'WA'"""
    m = _LOCATION.search(text or "")
    if not m:
        return None
    loc = m.group(1)
    a = _LOC_ABBREV.search(loc)
    if a:
        return a.group(1)
    low = loc.lower()
    return next((code for name, code in _FULL_STATES.items() if name in low), None)


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
            state=state_from_hints(card.get("hints") or []),
            price=price,
            time_at=(now + delta) if delta else None,
            time_kind="ends" if delta else None,
            text=f"{title}\n{text}",
            extra={"hints": (card.get("hints") or [])[:6]},
        ))
    return listings
