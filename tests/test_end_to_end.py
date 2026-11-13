"""Full run against a local web server serving sample pages: scrape -> filter -> alerts -> state."""
import json
import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from watcher import run
from watcher.sites import lloyds, pickles
from tests.fixtures import LLOYDS_CARDS, PICKLES_CARDS, lloyds_page, pickles_page

LOT_PAGES = {
    "6140002": "<html><body><h1>1994 Toyota Hilux Dual Cab</h1><p>Drive: Four wheel drive</p></body></html>",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/used/search/cars"):
            body = pickles_page(PICKLES_CARDS) if "page=1" in self.path else "<html><body></body></html>"
        elif self.path.startswith("/AuctionLots.aspx"):
            body = lloyds_page(LLOYDS_CARDS)
        elif self.path.startswith("/LotDetails.aspx"):
            lid = self.path.split("lid=")[-1]
            body = LOT_PAGES.get(lid, "<html><body>No drive info</body></html>")
        else:
            body = "<html><body></body></html>"
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def server(monkeypatch):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    monkeypatch.setattr(lloyds, "BASE", base)
    monkeypatch.setattr(pickles, "BASE", base)
    monkeypatch.setattr(run, "pause", lambda: None)
    yield base
    srv.shutdown()


def test_full_run(server, tmp_path, monkeypatch):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)  # notifier falls back to dry-run (log only)
    state_file = tmp_path / "state.json"
    args = ["--state", str(state_file), "--keywords", "landcruiser"]

    n = run.main(args)
    titles = sorted(m["title"] for m in n.sent)
    # Pickles: 1991 HDJ80 QLD, 1997 FZJ80 VIC, 1989 Patrol NSW. Not: 1998 (year), SA, 4x2 Hilux.
    # Lloyds: 1987 Patrol NSW, 1994 Hilux QLD (lot page says 4WD). Not: WA lot, 2012 lot.
    assert titles == sorted([
        "New: 1991 Toyota Landcruiser HDJ80R GXL Wagon 8st 5dr Man 5sp 4x4 4.2DT",
        "New: 1997 Toyota Landcruiser FZJ80R RV Wagon 8st 5dr Man 5sp 4WD 4.5i",
        "New: 1989 Nissan Patrol GQ Wagon",
        "New: 1987 Nissan Patrol MQ Wagon - White...",
        "New: 1994 Toyota Hilux Dual Cab Ute...",
    ])
    saved = json.loads(state_file.read_text())
    assert saved["drive_checks"] == {"lloyds:6140002": True}

    # Second run: nothing new. The Hilux ends in 45 min, so its 1h reminder was
    # already marked done when first seen (the "new" alert showed the time).
    n2 = run.main(args)
    assert [m["title"] for m in n2.sent] == []
