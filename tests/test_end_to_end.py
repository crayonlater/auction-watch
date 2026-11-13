"""Full run against a local web server serving sample pages: scrape -> filter -> alerts -> state."""
import json
import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from watcher import run
from watcher.sites import carbids, grays, lloyds, pickles
from tests.fixtures import (CARBIDS_CARDS, GRAYS_CARDS, GRAYS_LOT_PAGES, LLOYDS_CARDS, PICKLES_CARDS,
                            carbids_home, carbids_results, grays_page, lloyds_page, pickles_page)

LOT_PAGES = {
    "6140002": "<html><body><h1>1994 Toyota Hilux Dual Cab</h1><p>Drive: Four wheel drive</p></body></html>",
    "6140003": "<html><body><h1>1981 Nissan Patrol</h1><p><strong>Location of item:</strong> "
               "1 Example Rd, Wetherill Park, NSW, Australia</p></body></html>",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/used/search/cars"):
            body = pickles_page(PICKLES_CARDS) if "page=1" in self.path else "<html><body></body></html>"
        elif self.path.startswith("/AuctionLots.aspx"):
            body = lloyds_page(LLOYDS_CARDS)
        elif self.path.startswith("/search?"):
            body = grays_page(GRAYS_CARDS)  # every page number repeats page 1, like past-the-end pages
        elif self.path.startswith("/lot/"):
            lot = self.path.split("/")[2]
            body = GRAYS_LOT_PAGES.get(lot, "<html><body>No drive info</body></html>")
        elif self.path == "/":
            body = carbids_home({"landcruiser": carbids_results(CARBIDS_CARDS)})
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
    monkeypatch.setattr(grays, "BASE", base)
    monkeypatch.setattr(carbids, "BASE", base)
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
    # Lloyds: 1987 Patrol NSW, 1994 Hilux QLD (lot page says 4WD), 1981 Patrol (no flag;
    # lot page says NSW). Not: WA lot, 2012 lot.
    assert titles == sorted([
        "New: 1991 Toyota Landcruiser HDJ80R GXL Wagon 8st 5dr Man 5sp 4x4 4.2DT",
        "New: 1997 Toyota Landcruiser FZJ80R RV Wagon 8st 5dr Man 5sp 4WD 4.5i",
        "New: 1989 Nissan Patrol GQ Wagon",
        "New: 1987 Nissan Patrol MQ Wagon - White...",
        "New: 1994 Toyota Hilux Dual Cab Ute...",
        "New: 1981 Nissan Patrol Single Cab Utility - Yellow...",
        # Grays: Patrol VIC; Hilux NSW (lot page says 4x4). Not: Rodeo 4x2, 2010 Slattery Prado.
        "New: 1994 Nissan Patrol GQ ST Wagon Man 4WD Diesel",
        "New: 1991 Toyota Hilux Single Cab Ute",
        # Carbids: FJ62 NSW. Not: 2006 Prado (year), 1985 Patrol (ACT).
        "New: 03/1989 Toyota Landcruiser GXL (4x4) FJ62RG 4d Wagon White 4.0L",
    ])
    saved = json.loads(state_file.read_text())
    assert saved["drive_checks"] == {"lloyds:6140002": True, "grays:0006-23502964": True}
    assert saved["state_checks"] == {"lloyds:6140003": "NSW"}

    # Second run: nothing new. The Hilux ends in 45 min, so its 1h reminder was
    # already marked done when first seen (the "new" alert showed the time).
    n2 = run.main(args)
    assert [m["title"] for m in n2.sent] == []


def test_keyword_rotation():
    cfg = {"keywords": ["a", "b", "c", "d"], "site_keywords": {"grays": ["x", "y"]}}
    state = {"keyword_offset": {"pickles": 3}}
    assert run.plan_keywords(cfg, "pickles", None, state) == (["d", "a", "b", "c"], 3)
    assert run.plan_keywords(cfg, "grays", None, state) == (["x", "y"], 0)
    assert run.plan_keywords(cfg, "lloyds", ["only"], state) == (["only"], 0)


def test_time_budget_stops_early_and_resumes(server, tmp_path, monkeypatch):
    """With no time left, each site does one search, saves where it stopped, and alerts still go out."""
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load((Path(run.ROOT) / "config.yaml").read_text())
    cfg["time_budget_minutes"] = {s: 0 for s in cfg["sites"]}
    cfg["site_keywords"] = {s: ["landcruiser", "nothing1", "nothing2"] for s in cfg["sites"]}
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.safe_dump(cfg))
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    state_file = tmp_path / "state.json"

    n = run.main(["--config", str(cfg_file), "--state", str(state_file)])
    saved = json.loads(state_file.read_text())
    assert saved["keyword_offset"] == {"lloyds": 1, "pickles": 1, "grays": 1, "carbids": 1}
    assert any("Patrol" in m["title"] for m in n.sent)  # first search still produced alerts

    run.main(["--config", str(cfg_file), "--state", str(state_file)])
    saved = json.loads(state_file.read_text())
    assert saved["keyword_offset"] == {"lloyds": 2, "pickles": 2, "grays": 2, "carbids": 2}
