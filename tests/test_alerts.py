from datetime import datetime, timedelta, timezone

from watcher import alerts
from watcher.models import Listing
from watcher.notify import Notifier

T0 = datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)


def lst(id_, ends_in, kind="ends"):
    return Listing("lloyds", id_, f"1987 Nissan Patrol #{id_}", f"https://x/{id_}", year=1987,
                   state="NSW", location="New South Wales", price="$3,000",
                   time_at=T0 + ends_in, time_kind=kind)


def run(matches, state, now):
    n = Notifier(dry_run=True)
    alerts.process(matches, state, n, now, [24, 1], 30, 5)
    return [m["title"] for m in n.sent]


def test_new_then_24h_then_1h_then_nothing():
    state = {}
    l = lst("a", timedelta(days=3))
    assert run([l], state, T0) == ["New: 1987 Nissan Patrol #a"]
    assert run([l], state, T0 + timedelta(hours=1)) == []                       # nothing new
    assert run([l], state, T0 + timedelta(days=2, minutes=1)) == ["24 hours left: 1987 Nissan Patrol #a"]
    assert run([l], state, T0 + timedelta(days=2, hours=2)) == []
    assert run([l], state, T0 + timedelta(days=2, hours=22, minutes=40)) == ["1 hour left: 1987 Nissan Patrol #a"]
    assert run([l], state, T0 + timedelta(days=2, hours=23, minutes=20)) == []


def test_first_seen_close_to_end_skips_passed_reminders():
    state = {}
    l = lst("b", timedelta(hours=5))
    assert run([l], state, T0) == ["New: 1987 Nissan Patrol #b"]                # no 24h reminder
    assert run([l], state, T0 + timedelta(hours=4, minutes=10)) == ["1 hour left: 1987 Nissan Patrol #b"]


def test_missed_runs_send_only_most_urgent():
    state = {}
    l = lst("c", timedelta(days=3))
    run([l], state, T0)
    assert run([l], state, T0 + timedelta(days=2, hours=23, minutes=30)) == ["1 hour left: 1987 Nissan Patrol #c"]


def test_live_auction_wording():
    state = {}
    l = lst("d", timedelta(days=2), kind="starts")
    run([l], state, T0)
    assert run([l], state, T0 + timedelta(days=1)) == ["Starts in ~24 hours: 1987 Nissan Patrol #d"]


def test_digest_when_many_new():
    state = {}
    titles = run([lst(str(i), timedelta(days=5)) for i in range(8)], state, T0)  # threshold 5 in this test
    assert titles == ["8 new 4x4s at auction"]


def test_reminder_still_sent_if_scrape_misses_it_once():
    state = {}
    l = lst("e", timedelta(days=3))
    run([l], state, T0)
    assert run([], state, T0 + timedelta(days=2, minutes=5)) == ["24 hours left: 1987 Nissan Patrol #e"]


def test_extended_end_time_is_tracked():
    state = {}
    l = lst("f", timedelta(hours=30))
    run([l], state, T0)
    l.time_at = T0 + timedelta(hours=40)  # soft close pushed it out
    run([l], state, T0 + timedelta(hours=1))
    assert state["listings"]["lloyds:f"]["time_at"] == (T0 + timedelta(hours=40)).isoformat()


def test_old_listings_pruned():
    state = {}
    run([lst("g", timedelta(days=1))], state, T0)
    run([], state, T0 + timedelta(days=15))
    assert "lloyds:g" not in state["listings"]
