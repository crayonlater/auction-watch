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
    <div>{flag}<img alt="Lloyds Auctioneers and Valuers" src="/images/lloyds.png"></div>
    <button disabled>You Need To Sign In</button>
  </div>
</div>
"""


def lloyds_page(cards, page=1, pages=1):
    body = "".join(LLOYDS_CARD.format(**c) for c in cards)
    return (f"<html><body><div>Go to page <span>|&lt; &lt; {page} of {pages} &gt; &gt;|</span></div>"
            f"{body}</body></html>")


# The flag is marked up a few different ways, to cover what Lloyds might use
LLOYDS_CARDS = [
    dict(lid="6148634", lot="565", title="1984 Toyota Landcruiser Wagon - Blue - 364,636...",
         price="$1", countdown="14d 23h 47m", flag='<img alt="Western Australia" src="/f/1.png">'),
    dict(lid="6140001", lot="12", title="1987 Nissan Patrol MQ Wagon - White...",
         price="$3,200", countdown="1d 2h 5m", flag='<img title="New South Wales" src="/f/2.png">'),
    dict(lid="6140002", lot="13", title="1994 Toyota Hilux Dual Cab Ute...",
         price="$900", countdown="45m", flag='<img src="/images/states/flag_qld.png">'),
    dict(lid="6140489", lot="703", title="2012 Toyota LandCruiser 70 Workmate Single Cab...",
         price="$5,800", countdown="3d 6h 58m", flag='<span role="img" aria-label="Victoria"></span>'),
    dict(lid="6140003", lot="14", title="1981 Nissan Patrol Single Cab Utility - Yellow...",
         price="$2,000", countdown="2d 1h 0m", flag=""),  # no flag: state comes from the lot page
]


# ---- Grays: each result is one <li><a> card; Slattery lots link via interimPage ----
GRAYS_CARD = """
<li><a href="{href}">
  <div role="group" aria-label="Lot images"><img alt="{title}" src="x.jpg"></div>
  <p>Ends in <img src="clock.svg"><time>{time}</time></p>
  <div>
    {loc}
    <div><h3>{title}</h3><span>Used</span></div>
    <div><p>Current bid:</p><p><strong>{price}</strong></p></div>
  </div>
</a></li>
"""


def grays_page(cards):
    body = "".join(GRAYS_CARD.format(
        loc=(f'<div><dl><dd>{c["location"]}</dd></dl><span>No Reserve</span></div>' if c.get("location") else ""),
        **{k: v for k, v in c.items() if k != "location"}) for c in cards)
    return f"<html><body><h1>Search results</h1><div role='region'><ul>{body}</ul></div></body></html>"


SLATTERY_HREF = ("/redirection/interimPage?url=https%3A%2F%2Fwww.slatteryauctions.com.au%2Fassets%2F"
                 "02iOa00000FdfFZIAZ%3FauctionId%3Da0lOa00000Ppt0rIAB%26utm_source%3Dgrays&imageUrl=x&title=y")

GRAYS_CARDS = [
    dict(href="/lot/0042-23502981/motor-vehicles-motor-cycles/1994-nissan-patrol-gq-4wd",
         title="1994 Nissan Patrol GQ ST Wagon Man 4WD Diesel", time="4d: 01h: 16m",
         location="Dandenong South, VIC", price="$1,055"),
    dict(href="/lot/0006-23502964/commercial-vehicles/1991-toyota-hilux-ute",
         title="1991 Toyota Hilux Single Cab Ute", time="5d: 01h: 16m",
         location="Hexham, NSW", price="$9"),
    dict(href="/lot/0007-23502964/commercial-vehicles/1996-isuzu-rodeo-4x2",
         title="1996 Holden Rodeo LX 4x2 Ute", time="5d: 02h: 00m",
         location="Yennora, NSW", price="$500"),
    dict(href=SLATTERY_HREF, title="2010 Toyota Landcruiser Prado GXL Diesel 4x4 SUV", time="2d: 23h: 50m",
         price="$1,000"),
]

GRAYS_LOT_PAGES = {
    "0006-23502964": "<html><body><h1>1991 Toyota Hilux</h1><p>Drive Type: 4x4</p></body></html>",
}

SLATTERY_PAGE_TEXT = ("All Locations\nCollection location\n2010 Toyota Landcruiser Prado\n"
                      "Consignment No. 1-5-1-006186\nLot No. 4\nLocation 3 Maxwell Rd Pooraka SA 5095\n"
                      "Similar lots\nLocation 12 Other St Perth WA 6000")


# ---- Carbids: Angular search; results appear after typing in the search box ----
CARBIDS_CARD = """
<div class="item">
  <div>
    <a href="{href}"><img alt="{title}" src="x.jpg"></a>
    <a href="{href}"><h2>{title}</h2></a>
  </div>
  <div><span>{suburb}</span><span>{state}</span></div>
  <a href="{href}"><div><h3>{blurb}</h3><mark>61510-1</mark></div></a>
  <div><span>408,592ks</span><span>4 Sp Automatic</span></div>
  <a href="{href}"><div><span>{price}</span><span>{left} <small>({when})</small></span></div></a>
</div>
"""


def carbids_results(cards):
    return "".join(CARBIDS_CARD.format(**c) for c in cards)


def carbids_home(results_by_keyword):
    import json
    return f"""<html><body>
<input placeholder="Show me results for..." id="q">
<div id="results"></div>
<script>
const R = {json.dumps(results_by_keyword)};
document.getElementById('q').addEventListener('keydown', e => {{
  if (e.key !== 'Enter') return;
  setTimeout(() => {{ document.getElementById('results').innerHTML = R[e.target.value.toLowerCase()] || ''; }}, 300);
}});
</script></body></html>"""


CARBIDS_CARDS = [
    dict(href="https://www.carbids.com.au/c/allbids-car-auctions/commercial-4wd-vehicles/03-1989-toyota-landcruiser-fj62-1681001",
         title="03/1989 Toyota Landcruiser GXL (4x4) FJ62RG 4d Wagon White 4.0L", suburb="Moorebank", state="NSW",
         blurb="Rare FJ62 with 2 keys, left hand mirror missing", price="$4,200", left="4d 1h left", when="Tuesday 7:35 AM"),
    dict(href="https://www.carbids.com.au/c/allbids-car-auctions/commercial-4wd-vehicles/02-2006-toyota-landcruiser-prado-1681082",
         title="02/2006 Toyota Landcruiser Prado GXL (4x4) KZJ120R 4d Wagon Black 3.0L", suburb="Moorebank", state="NSW",
         blurb="Practical Prado", price="$5,000", left="4d left", when="Tuesday 7:35 AM"),
    dict(href="https://www.carbids.com.au/c/allbids-car-auctions/commercial-4wd-vehicles/07-1985-nissan-patrol-mq-1681002",
         title="07/1985 Nissan Patrol MQ 4d Wagon Beige 4.2L", suburb="Fyshwick", state="ACT",
         blurb="Canberra Patrol", price="Start bidding", left="45m left", when="Today 7:45 AM"),
]
