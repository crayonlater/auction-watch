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

    assert [l.state for l in listings] == ["WA", "NSW", "QLD", "VIC"]
    patrol = listings[1]
    assert patrol.year == 1987 and patrol.price == "$3,200"
    assert patrol.url == "https://www.lloydsonline.com.au/LotDetails.aspx?lid=6140001"
    assert patrol.time_at == now + timedelta(days=1, hours=2, minutes=5)
    assert listings[2].time_at == now + timedelta(minutes=45)


def test_lloyds_countdown():
    assert lloyds.parse_countdown("$5,800\n3d 6h 58m") == timedelta(days=3, hours=6, minutes=58)
    assert lloyds.parse_countdown("$1 45m") == timedelta(minutes=45)
    assert lloyds.parse_countdown("Closed") is None
