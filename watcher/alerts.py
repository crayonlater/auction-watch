"""Decides which notifications are due, given current matches and stored state."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from .models import Listing
from .notify import Notifier, fmt_time

SITE_NAMES = {"lloyds": "Lloyds", "pickles": "Pickles"}
PRUNE_AFTER = timedelta(days=14)


def _parse(dt: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(dt) if dt else None


def _when(kind: Optional[str], at: Optional[datetime]) -> str:
    verb = "Live auction starts" if kind == "starts" else "Ends"
    return f"{verb} {fmt_time(at)}"


def _summary(l: Listing) -> str:
    bits = [SITE_NAMES.get(l.site, l.site)]
    if l.location:
        bits.append(l.location)
    if l.price:
        bits.append(l.price)
    return " · ".join(bits)


def process(matches: list[Listing], state: dict, notifier: Notifier, now: datetime,
            reminder_hours: list[int], run_interval_minutes: int, digest_threshold: int) -> None:
    store = state.setdefault("listings", {})
    hours = sorted(set(reminder_hours), reverse=True)
    grace = timedelta(minutes=run_interval_minutes)

    new = []
    for l in matches:
        rec = store.get(l.key)
        if rec is None:
            rec = store[l.key] = {"first_seen": now.isoformat(), "reminded": []}
            new.append(l)
            # Don't send reminders for thresholds already passed when first seen;
            # the "new listing" alert already shows the time.
            if l.time_at:
                left = l.time_at - now
                rec["reminded"] = [h for h in hours if left <= timedelta(hours=h) + grace]
        rec.update({
            "title": l.title, "url": l.url, "site": l.site, "location": l.location,
            "price": l.price, "time_kind": l.time_kind, "last_seen": now.isoformat(),
            "time_at": l.time_at.isoformat() if l.time_at else rec.get("time_at"),
        })

    # New-listing alerts
    if len(new) > digest_threshold:
        lines = [f"• {l.title} — {_summary(l)} — {_when(l.time_kind, l.time_at)}\n  {l.url}" for l in new]
        notifier.send(f"{len(new)} new 4x4s at auction", "\n".join(lines), priority="high")
    else:
        for l in new:
            notifier.send(f"New: {l.title}", f"{_summary(l)}\n{_when(l.time_kind, l.time_at)}",
                          url=l.url, priority="high")

    # Reminders for anything seen in the last three days (so a failed scrape
    # doesn't swallow a reminder)
    for key, rec in store.items():
        last = _parse(rec.get("last_seen"))
        if not last or now - last > timedelta(days=3):
            continue
        at = _parse(rec.get("time_at"))
        if not at:
            continue
        left = at - now
        if left < -timedelta(hours=1):
            continue
        due = [h for h in hours if h not in rec["reminded"] and left <= timedelta(hours=h) + grace]
        if not due:
            continue
        h = min(due)  # most urgent only; mark the rest done
        rec["reminded"] = sorted(set(rec["reminded"]) | set(due), reverse=True)
        label = f"{h} hour" + ("s" if h != 1 else "")
        verb = "starts" if rec.get("time_kind") == "starts" else "ends"
        notifier.send(
            f"{label} left: {rec['title']}" if verb == "ends" else f"Starts in ~{label}: {rec['title']}",
            f"{SITE_NAMES.get(rec['site'], rec['site'])} · {rec.get('location') or ''}\n"
            f"{_when(rec.get('time_kind'), at)}",
            url=rec["url"], priority="urgent" if h <= 1 else "high", tags="alarm_clock",
        )

    # Forget listings that haven't appeared for a while
    for key in list(store):
        last = _parse(store[key].get("last_seen"))
        if last and now - last > PRUNE_AFTER:
            del store[key]
