"""Push notifications via ntfy (https://ntfy.sh). Free, no account needed."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import requests

log = logging.getLogger(__name__)
SYD = ZoneInfo("Australia/Sydney")


def fmt_time(dt: Optional[datetime]) -> str:
    if not dt:
        return "time not listed"
    local = dt.astimezone(SYD)
    return local.strftime("%a %-d %b, %-I:%M%p").replace("AM", "am").replace("PM", "pm")


class Notifier:
    def __init__(self, topic: Optional[str] = None, server: Optional[str] = None, dry_run: bool = False):
        self.topic = topic or os.environ.get("NTFY_TOPIC", "")
        self.server = (server or os.environ.get("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
        self.token = os.environ.get("NTFY_TOKEN")
        self.dry_run = dry_run or not self.topic
        self.sent: list[dict] = []

    def send(self, title: str, message: str, url: Optional[str] = None,
             priority: str = "default", tags: str = "pickup_truck") -> None:
        msg = {"title": title, "message": message, "url": url, "priority": priority, "tags": tags}
        self.sent.append(msg)
        if self.dry_run:
            log.info("[dry run] %s | %s | %s", title, message.replace("\n", " / "), url or "")
            return
        headers = {"Title": title, "Priority": priority, "Tags": tags}
        if url:
            headers["Click"] = url
            headers["Actions"] = f"view, Open listing, {url}"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        r = requests.post(f"{self.server}/{self.topic}", data=message.encode("utf-8"),
                          headers={k: v.encode("utf-8").decode("latin-1", "ignore") for k, v in headers.items()},
                          timeout=20)
        r.raise_for_status()
