"""Year, state and 4x4 checks. Pure functions so they're easy to test."""
from __future__ import annotations

import re
from typing import Iterable, Optional

STATE_NAMES = {
    "new south wales": "NSW", "nsw": "NSW",
    "victoria": "VIC", "vic": "VIC",
    "queensland": "QLD", "qld": "QLD",
    "south australia": "SA", "sa": "SA",
    "western australia": "WA", "wa": "WA",
    "tasmania": "TAS", "tas": "TAS",
    "northern territory": "NT", "nt": "NT",
    "australian capital territory": "ACT", "act": "ACT",
}

_YEAR_START = re.compile(r"^\s*((?:19|20)\d{2})\b")
_YEAR_ANY = re.compile(r"\b((?:19[6-9]|20[0-3])\d)\b")

_FOUR_WD = re.compile(
    r"\b(4x4|4wd|4\s?wd|four[\s-]wheel[\s-]drive|4xd|dual range|part[\s-]time 4|full[\s-]time 4)\b",
    re.I,
)
_TWO_WD = re.compile(r"\b(4x2|2wd|two[\s-]wheel[\s-]drive|rear[\s-]wheel[\s-]drive|rwd)\b", re.I)


def normalise_state(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return STATE_NAMES.get(value.strip().lower())


def state_from_location(location: Optional[str]) -> Optional[str]:
    """'Tullamarine, VIC' -> 'VIC'"""
    if not location:
        return None
    m = re.search(r",\s*([A-Za-z]{2,3})\s*$", location.strip())
    return normalise_state(m.group(1)) if m else None


def parse_year(title: str) -> Optional[int]:
    m = _YEAR_START.search(title or "")
    if m:
        return int(m.group(1))
    m = _YEAR_ANY.search(title or "")
    return int(m.group(1)) if m else None


def _has_model(text: str, models: Iterable[str]) -> bool:
    t = text.lower()
    for model in models:
        if re.search(r"(?<![a-z0-9])" + re.escape(str(model).lower()) + r"(?![a-z0-9])", t):
            return True
    return False


def four_wd_status(text: str, always_models: Iterable[str]) -> Optional[bool]:
    """True = 4x4, False = not, None = can't tell from this text (open the lot page)."""
    text = text or ""
    if _TWO_WD.search(text) and not _FOUR_WD.search(text):
        return False
    if _FOUR_WD.search(text):
        return True
    if _has_model(text, always_models):
        return True
    return None


def in_year_range(year: Optional[int], years: list[int]) -> bool:
    return year is not None and years[0] <= year <= years[1]
