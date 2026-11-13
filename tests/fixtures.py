"""Sample pages shaped like the real sites (structure taken from live pages, Nov 2026)."""

PICKLES_CARD = """
<main>
  <figure><a href="/used/details/cars/{slug}/{stock}">View more photos</a></figure>
  <div><button><time>{time}</time></button></div>
  <a href="/used/details/cars/{slug}/{stock}">
    <div><h2>{h1}</h2><h2>{h2}</h2></div>
    <div><p>{location}</p></div>
    <div><p>{km}</p><p>Stock {stock}</p></div>
    {buy}
  </a>
</main>
"""


def pickles_page(cards):
    body = "".join(PICKLES_CARD.format(buy=c.get("buy", ""), km=c.get("km", ""), **{k: v for k, v in c.items() if k not in ("buy", "km")}) for c in cards)
    return f"<html><body><header><a href='/'>Pickles</a></header><section>{body}</section></body></html>"


PICKLES_CARDS = [
    dict(slug="1991-toyota-landcruiser", stock="62438371", time="Starts Thu 19/11/2026 01:00PM",
         h1="1991 Toyota Landcruiser", h2="HDJ80R GXL Wagon 8st 5dr Man 5sp 4x4 4.2DT",
         location="Acacia Ridge, QLD"),
    dict(slug="1997-toyota-landcruiser", stock="62435957", time="Starts Tue 17/11/2026 09:30AM",
         h1="1997 Toyota Landcruiser", h2="FZJ80R RV Wagon 8st 5dr Man 5sp 4WD 4.5i",
         location="Tullamarine, VIC", km="390,403 km"),
    dict(slug="1998-toyota-landcruiser", stock="62458971", time="Starts Fri 20/11/2026 09:00AM",
         h1="1998 Toyota Landcruiser", h2="HZJ75RP Cab Chassis Single Cab 2dr Man 5sp 4x4 1000kg 4.2D",
         location="Salisbury Plain, SA"),
    dict(slug="1992-toyota-hilux", stock="62400001", time="End Mon 30/11/2026 05:00PM",
         h1="1992 Toyota Hilux", h2="RN85R Cab Chassis 2dr Man 5sp 4x2 2.4i",
         location="Milperra, NSW", buy="<button><p>Buy $4,500</p></button>"),
    dict(slug="1989-nissan-patrol", stock="62400002", time="Sale In Progress",
         h1="1989 Nissan Patrol", h2="GQ Wagon", location="Belmore, NSW"),
]

LLOYDS_CARD = """
<div class="lot">
  <a href="LotDetails.aspx?stype=0&stypeid=0&kw=x&cid=0&smode=0&lid={lid}">
    <div><span>Lot: {lot}</span><img src="t.jpg"></div>
    <div><h1>{title}</h1><div><span>{price}</span><span>{countdown}</span></div></div>
  </a>
  <div>
    <div><img alt="{state}" src="flag.png"><img alt="Lloyds Auctioneers and Valuers" src="l.png"></div>
    <button disabled>You Need To Sign In</button>
  </div>
</div>
"""


def lloyds_page(cards, page=1, pages=1):
    body = "".join(LLOYDS_CARD.format(**c) for c in cards)
    return (f"<html><body><div>Go to page <span>|&lt; &lt; {page} of {pages} &gt; &gt;|</span></div>"
            f"{body}</body></html>")


LLOYDS_CARDS = [
    dict(lid="6148634", lot="565", title="1984 Toyota Landcruiser Wagon - Blue - 364,636...",
         price="$1", countdown="14d 23h 47m", state="Western Australia"),
    dict(lid="6140001", lot="12", title="1987 Nissan Patrol MQ Wagon - White...",
         price="$3,200", countdown="1d 2h 5m", state="New South Wales"),
    dict(lid="6140002", lot="13", title="1994 Toyota Hilux Dual Cab Ute...",
         price="$900", countdown="45m", state="Queensland"),
    dict(lid="6140489", lot="703", title="2012 Toyota LandCruiser 70 Workmate Single Cab...",
         price="$5,800", countdown="3d 6h 58m", state="Victoria"),
]
