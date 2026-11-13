"""Pickles (pickles.com.au). JS-rendered search; cards link to /used/details/cars/<slug>/<stock>.

Card time labels seen: "Starts Sun 22/11/2026 10:30PM" (Pickles Live start),
"End Mon 30/11/2026 05:00AM" (timed online auction), "Sale In Progress".
Times are shown in the browser's time zone, so the browser runs as Australia/Sydney.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from ..filters import parse_year, state_from_location
from ..models import Listing

NAME = "pickles"
SYD = ZoneInfo("Australia/Sydney")
PAGE_SIZE = 120
BASE = "https://www.pickles.com.au"
MAX_PAGES = 3


def search_url(keyword: str, page: int = 1) -> str:
    return (
        f"{BASE}/used/search/cars"
        f"?search={quote_plus(keyword)}&sort=year+asc%2C+titleSort+asc&page={page}&limit={PAGE_SIZE}"
    )


WAIT_SELECTOR = 'a[href*="/used/details/"] h2'

# Returns one object per result card. Climbs from each details link to the
# largest ancestor that still holds only that one card, so we pick up its time label.
EXTRACT_JS = r"""
() => {
  const links = [...document.querySelectorAll('a[href*="/used/details/"]')]
    .filter(a => a.querySelector('h2'));
  const out = [], seen = new Set();
  const cardCount = el => new Set([...el.querySelectorAll('a[href*="/used/details/"]')]
    .filter(a => a.querySelector('h2')).map(a => a.href)).size;
  for (const a of links) {
    if (seen.has(a.href)) continue;
    seen.add(a.href);
    let card = a;
    while (card.parentElement && cardCount(card.parentElement) <= 1) card = card.parentElement;
    const t = card.querySelector('time');
    const lines = [...a.querySelectorAll('*')].filter(e => !e.children.length)
      .map(e => e.textContent.trim()).filter(Boolean);
    out.push({
      href: a.href,
      headings: [...a.querySelectorAll('h2')].map(h => h.innerText.trim()),
      text: lines.join('\n'),
      time: t ? t.innerText.trim() : null,
    });
  }
  return out;
}
"""

_TIME = re.compile(
    r"\b(Starts?|Ends?|Closes?|Closing)\s+(?:[A-Za-z]{3}\s+)?(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}\s*[AP]M)",
    re.I,
)
_LOCATION = re.compile(r"([A-Za-z][A-Za-z .'\-]+,\s*(?:NSW|VIC|QLD|SA|WA|TAS|NT|ACT))\b")
_STOCK = re.compile(r"/(\d{5,})/?(?:[?#]|$)")
_PRICE = re.compile(r"\bBuy\s+(\$[\d,]+)")


def parse_time(label: Optional[str]) -> tuple[Optional[datetime], Optional[str]]:
    if not label:
        return None, None
    m = _TIME.search(label)
    if not m:
        return None, None
    word, date_s, time_s = m.groups()
    dt = datetime.strptime(f"{date_s} {time_s.replace(' ', '').upper()}", "%d/%m/%Y %I:%M%p")
    kind = "starts" if word.lower().startswith("start") else "ends"
    return dt.replace(tzinfo=SYD), kind


def parse_cards(raw: list[dict]) -> list[Listing]:
    listings = []
    for card in raw:
        href = card.get("href") or ""
        m = _STOCK.search(href)
        if not m:
            continue
        headings = card.get("headings") or []
        title = " ".join(h for h in headings if h).strip()
        text = card.get("text") or ""
        loc_m = _LOCATION.search(text)
        location = loc_m.group(1).strip() if loc_m else None
        time_at, kind = parse_time(card.get("time"))
        price_m = _PRICE.search(text)
        listings.append(Listing(
            site=NAME,
            id=m.group(1),
            title=title,
            url=href,
            year=parse_year(title),
            location=location,
            state=state_from_location(location),
            price=price_m.group(1) if price_m else None,
            time_at=time_at,
            time_kind=kind,
            text=f"{title}\n{text}",
            extra={"time_label": card.get("time")},
        ))
    return listings


def keep_paging(listings: list[Listing], max_year: int) -> bool:
    """Results are sorted oldest first, so stop once a page goes past the year range."""
    years = [l.year for l in listings if l.year]
    return bool(listings) and len(listings) >= PAGE_SIZE and (not years or max(years) <= max_year)
