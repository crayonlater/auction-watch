"""Runs each site's page-extraction JS in real Chromium against sample pages."""
from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import sync_playwright

from watcher.sites import lloyds, pickles
from tests.fixtures import LLOYDS_CARDS, PICKLES_CARDS, lloyds_page, pickles_page


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        yield pg
        b.close()


def test_pickles_extract_and_parse(page):
    page.set_content(pickles_page(PICKLES_CARDS))
    listings = pickles.parse_cards(page.evaluate(pickles.EXTRACT_JS))
    assert [l.id for l in listings] == ["62438371", "62435957", "62458971", "62400001", "62400002"]

    first = listings[0]
    assert first.title == "1991 Toyota Landcruiser HDJ80R GXL Wagon 8st 5dr Man 5sp 4x4 4.2DT"
    assert first.year == 1991 and first.state == "QLD" and first.location == "Acacia Ridge, QLD"
    assert first.time_kind == "starts"
    assert first.time_at.isoformat() == "2026-11-19T13:00:00+11:00"

    hilux = listings[3]
    assert hilux.time_kind == "ends" and hilux.price == "$4,500" and hilux.state == "NSW"
    assert listings[4].time_at is None  # "Sale In Progress"


def test_pickles_time_card_matches_its_own_listing(page):
    # Each card's time must come from its own card, not the first one on the page
    page.set_content(pickles_page(PICKLES_CARDS))
    raw = page.evaluate(pickles.EXTRACT_JS)
    assert [r["time"] for r in raw] == [c["time"] for c in PICKLES_CARDS]


def test_pickles_paging_stops_past_year_range():
    from watcher.models import Listing
    page_of = lambda y: [Listing("pickles", str(i), f"{y} X", "u", year=y) for i in range(pickles.PAGE_SIZE)]
    assert pickles.keep_paging(page_of(1995), 1997)
    assert not pickles.keep_paging(page_of(2001), 1997)
    assert not pickles.keep_paging(page_of(1995)[:10], 1997)  # short page = last page


def test_lloyds_extract_and_parse(page):
    page.set_content(lloyds_page(LLOYDS_CARDS, 1, 2))
    res = page.evaluate(lloyds.EXTRACT_JS)
    assert (res["page"], res["pages"]) == (1, 2)
    now = datetime(2026, 11, 13, 3, 0, tzinfo=timezone.utc)
    listings = lloyds.parse_cards(res["cards"], now)

    assert [l.state for l in listings] == ["WA", "NSW", "QLD", "VIC", None]
    patrol = listings[1]
    assert patrol.year == 1987 and patrol.price == "$3,200"
    assert patrol.url == "https://www.lloydsonline.com.au/LotDetails.aspx?lid=6140001"
    assert patrol.time_at == now + timedelta(days=1, hours=2, minutes=5)
    assert listings[2].time_at == now + timedelta(minutes=45)


def test_lloyds_countdown():
    assert lloyds.parse_countdown("$5,800\n3d 6h 58m") == timedelta(days=3, hours=6, minutes=58)
    assert lloyds.parse_countdown("$1 45m") == timedelta(minutes=45)
    assert lloyds.parse_countdown("Closed") is None


def test_lloyds_state_from_hints():
    assert lloyds.state_from_hints(["Victoria", "/f/x.png"]) == "VIC"
    assert lloyds.state_from_hints(["", "/images/states/NSW.gif"]) == "NSW"
    assert lloyds.state_from_hints(['url("https://x/img/flags/qld.png")']) == "QLD"
    assert lloyds.state_from_hints(["Lloyds Auctioneers and Valuers", "/images/lloyds-act.png"]) is None
    assert lloyds.state_from_hints(["/content/photo123.jpg"]) is None


def test_lloyds_state_from_lot_page():
    assert lloyds.state_from_lot_page(
        "Location of item: 90-94 Bannister Road, Canning Vale, WA, Australia\nAs Standard...") == "WA"
    assert lloyds.state_from_lot_page("Location of item: 12 Smith St, Yatala QLD 4207") == "QLD"
    assert lloyds.state_from_lot_page("Location of item: Somewhere, Victoria") == "VIC"
    assert lloyds.state_from_lot_page("No location here") is None


# ---- Grays ----
from watcher.sites import carbids, grays
from watcher.sites.common import location_from_lines, parse_relative, state_from_address_page
from tests.fixtures import (CARBIDS_CARDS, GRAYS_CARDS, SLATTERY_PAGE_TEXT, carbids_results,
                            grays_page)


def test_common_helpers():
    assert parse_relative("2d: 01h: 16m") == timedelta(days=2, hours=1, minutes=16)
    assert parse_relative("4d 1h left (Tuesday 7:35 AM)") == timedelta(days=4, hours=1)
    assert parse_relative("45m left") == timedelta(minutes=45)
    assert parse_relative("Closed") is None
    assert location_from_lines(["Lot images", "Hexham, NSW", "No Reserve"]) == ("Hexham, NSW", "NSW")
    assert location_from_lines(["03/1989 Toyota", "Moorebank", "NSW", "blurb"]) == ("Moorebank, NSW", "NSW")
    assert location_from_lines(["no location"]) == (None, None)
    assert state_from_address_page(SLATTERY_PAGE_TEXT) == "SA"  # the lot's own, not the similar lot's


def test_grays_extract_and_parse(page):
    page.set_content(grays_page(GRAYS_CARDS))
    now = datetime(2026, 11, 13, 3, 0, tzinfo=timezone.utc)
    listings = grays.parse_cards(page.evaluate(grays.EXTRACT_JS), now)
    assert len(listings) == 4
    patrol = listings[0]
    assert patrol.id == "0042-23502981" and patrol.year == 1994
    assert patrol.state == "VIC" and patrol.location == "Dandenong South, VIC" and patrol.price == "$1,055"
    assert patrol.time_at == now + timedelta(days=4, hours=1, minutes=16)
    assert patrol.url.endswith("/lot/0042-23502981/motor-vehicles-motor-cycles/1994-nissan-patrol-gq-4wd")
    slat = listings[3]
    assert slat.id == "slattery-02iOa00000FdfFZIAZ" and slat.state is None
    assert slat.url == "https://www.slatteryauctions.com.au/assets/02iOa00000FdfFZIAZ?auctionId=a0lOa00000Ppt0rIAB"
    assert slat.extra["source"] == "Slattery"


# ---- Carbids ----
def test_carbids_extract_and_parse(page):
    page.set_content(f"<html><body>{carbids_results(CARBIDS_CARDS)}</body></html>")
    now = datetime(2026, 11, 13, 3, 0, tzinfo=timezone.utc)
    listings = carbids.parse_cards(page.evaluate(carbids.EXTRACT_JS), now)
    assert [l.id for l in listings] == ["1681001", "1681082", "1681002"]
    fj62 = listings[0]
    assert fj62.year == 1989 and fj62.state == "NSW" and fj62.location == "Moorebank, NSW"
    assert fj62.price == "$4,200"
    # "left hand mirror" in the blurb must not be read as the time left
    assert fj62.time_at == now + timedelta(days=4, hours=1)
    assert listings[1].year == 2006
    assert listings[2].state == "ACT" and listings[2].price is None
    assert listings[2].time_at == now + timedelta(minutes=45)


def test_carbids_year_from_title():
    assert carbids.year_from_title("03/1989 Toyota Landcruiser") == 1989
    assert carbids.year_from_title("1989 Toyota Landcruiser") == 1989
    assert carbids.year_from_title("Toyota Landcruiser") is None
