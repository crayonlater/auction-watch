"""Small helpers shared by the Grays and Carbids parsers."""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Optional

STATE_CODES = ("NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT")
_STATE_ALT = "|".join(STATE_CODES)

# JS: one line per text node inside `el`, so adjacent spans don't run together and
# text sitting beside a child element (e.g. "4d left <span>(Tue)</span>") isn't lost
LEAF_LINES_JS = r"""
const leafLines = el => {
  const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), out = [];
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const p = n.parentElement;
    if (p && (p.tagName === 'SCRIPT' || p.tagName === 'STYLE')) continue;
    const t = n.textContent.replace(/\s+/g, ' ').trim();
    if (t) out.push(t);
  }
  return out;
};
"""

_TIME_PART = re.compile(r"(\d+)\s*([dhms])\b", re.I)


def parse_relative(text: Optional[str]) -> Optional[timedelta]:
    """'2d: 01h: 16m' or '4d 1h left (Tuesday 7:35 AM)' -> timedelta. Only reads up to 'left' or '('."""
    if not text:
        return None
    head = re.split(r"left|\(", text, maxsplit=1, flags=re.I)[0]
    parts = {u.lower(): int(n) for n, u in _TIME_PART.findall(head)}
    if not parts:
        return None
    return timedelta(days=parts.get("d", 0), hours=parts.get("h", 0),
                     minutes=parts.get("m", 0), seconds=parts.get("s", 0))


_SUBURB_STATE = re.compile(rf"^([A-Za-z][A-Za-z .'\-]*),\s*({_STATE_ALT})$")
_STATE_ONLY = re.compile(rf"^({_STATE_ALT})$")


def location_from_lines(lines: list[str]) -> tuple[Optional[str], Optional[str]]:
    """Finds 'Hexham, NSW' on one line, or 'Moorebank' then 'NSW' on the next. -> (location, state)"""
    for i, line in enumerate(lines):
        line = line.strip()
        m = _SUBURB_STATE.match(line)
        if m:
            return line, m.group(2)
        if _STATE_ONLY.match(line):
            suburb = lines[i - 1].strip() if i > 0 else ""
            loc = f"{suburb}, {line}" if suburb and not suburb.startswith("$") else line
            return loc, line
    return None, None


_PRICE = re.compile(r"^\$[\d,]+(?:\.\d{2})?$")


def price_from_lines(lines: list[str]) -> Optional[str]:
    return next((l.strip() for l in lines if _PRICE.match(l.strip())), None)


_ADDRESS_STATE = re.compile(rf"(?m)^\s*Location\s*:?\s*(?:\n\s*)?([^\n]*?\b({_STATE_ALT})\b[^\n]*)")


def state_from_address_page(text: str) -> Optional[str]:
    """Lot page with a line like 'Location 3 Maxwell Rd Pooraka SA 5095' -> 'SA'."""
    m = _ADDRESS_STATE.search(text or "")
    return m.group(2) if m else None
