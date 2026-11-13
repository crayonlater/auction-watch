from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Listing:
    site: str                      # "lloyds" | "pickles"
    id: str                        # site-specific lot / stock id
    title: str
    url: str
    year: Optional[int] = None
    state: Optional[str] = None    # NSW, VIC, QLD...
    location: Optional[str] = None
    price: Optional[str] = None    # current bid or buy-now, as shown
    time_at: Optional[datetime] = None   # timezone-aware
    time_kind: Optional[str] = None      # "ends" | "starts"
    text: str = ""                 # all card text, used for 4x4 detection
    four_wd: Optional[bool] = None # None = not yet known
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.site}:{self.id}"
