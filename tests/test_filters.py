import yaml
from pathlib import Path

from watcher import filters

CFG = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text())
ALWAYS = CFG["always_4wd_models"]


def status(text):
    return filters.four_wd_status(text, ALWAYS)


def test_explicit_4x4_and_2wd():
    assert status("1997 Toyota Landcruiser FZJ80R RV Wagon 5sp 4WD 4.5i") is True
    assert status("1992 Toyota Hilux RN85R Cab Chassis 4x2 2.4i") is False
    assert status("Drive: Four wheel drive") is True
    assert status("4XD : 4X4 Dual Range") is True


def test_always_4wd_models():
    assert status("1987 Nissan Patrol MQ Wagon - White...") is True
    assert status("1984 Toyota Landcruiser Wagon - Blue") is True
    assert status("1990 Suzuki Sierra soft top") is True
    assert status("1995 Range Rover Classic") is True


def test_mixed_models_need_checking():
    assert status("1994 Toyota Hilux Dual Cab Ute...") is None
    assert status("1988 Ford Courier") is None


def test_hilux_surf_is_4wd_but_plain_hilux_is_not_assumed():
    assert status("1993 Toyota Hilux Surf SSR") is True


def test_year():
    assert filters.parse_year("1984 Toyota Landcruiser") == 1984
    assert filters.parse_year("Toyota Landcruiser 1991 HDJ80") == 1991
    assert filters.parse_year("Toyota Landcruiser") is None
    assert filters.in_year_range(1980, [1980, 1997])
    assert filters.in_year_range(1997, [1980, 1997])
    assert not filters.in_year_range(1998, [1980, 1997])
    assert not filters.in_year_range(None, [1980, 1997])


def test_state():
    assert filters.normalise_state("New South Wales") == "NSW"
    assert filters.normalise_state("Victoria") == "VIC"
    assert filters.state_from_location("Acacia Ridge, QLD") == "QLD"
    assert filters.state_from_location("Bibra Lake, WA") == "WA"
    assert filters.state_from_location(None) is None
