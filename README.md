# Auction watch: 1980–1997 4x4s in NSW, VIC and QLD

Checks **Pickles**, **Lloyds**, **Grays** (including Slattery lots shown on Grays) and **Carbids** (the car side of Allbids) every 30 minutes and sends push notifications to your phone:

- **New listing:** a 4x4 from 1980–1997 in NSW, VIC or QLD. Includes location, current bid or buy price, and end time.
- **24 hours left:** the auction ends (or a Pickles Live sale starts) in about a day.
- **1 hour left:** last call.

It runs free on GitHub Actions, so nothing needs to stay on at home.

## Setup (about 10 minutes)

### 1. Phone notifications (ntfy)
1. Install **ntfy** from the App Store or Google Play. It's free and needs no account.
2. Tap **+** and subscribe to a topic. Pick a name nobody would guess, because anyone who knows it can read your alerts. For example: `4x4-watch-320a2698`

### 2. GitHub
1. Create a free account at github.com if you don't have one.
2. **New repository**, named e.g. `auction-watch`. Make it **Public**: public repos get unlimited free Actions minutes, and each run takes a few minutes. Only the car listings you're tracking are visible. Your ntfy topic stays secret (next step).
3. Click **uploading an existing file** and drag in everything from this folder, including the hidden `.github` folder. On a Mac, press Cmd+Shift+. to show hidden files.
4. **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `NTFY_TOPIC`
   - Value: your topic, e.g. `4x4-watch-320a2698`
5. **Settings → Actions → General → Workflow permissions:** choose **Read and write permissions**, then Save.

### 3. First run
**Actions** tab → **Auction watch** → **Run workflow**.

The first run sends alerts for everything that currently matches. More than 5 at once arrive as a single digest. After that you only hear about new listings and upcoming endings.

Each run's log lists every match, which is handy for checking it's working.

## Changing what it looks for
Edit `config.yaml` on GitHub (pencil icon):
- `years`, `states`: the basics
- `keywords`: search terms sent to each site
- `always_4wd_models`: models counted as 4x4 without the listing saying so
- `reminder_hours`: e.g. `[48, 24, 1]`

## How it decides something is a 4x4
1. The listing says 2WD or 4x2: **no**.
2. It says 4x4, 4WD, "four wheel drive" or "dual range": **yes**.
3. It's an always-4WD model (LandCruiser, Patrol, Pajero, Range Rover…): **yes**.
4. Otherwise (Hilux, Courier, Rodeo…), it opens the lot page once to check. It remembers the answer, and when unsure it alerts you anyway.

## If something breaks
If a site returns nothing or keeps erroring, you get a low-priority "needs a look" notification, at most once a day. That usually means the site changed its layout. The parsing for each site lives in `watcher/sites/`.

## Running it on your own computer
```
pip install -r requirements.txt
python -m playwright install chromium
python -m watcher.run --dry-run                  # print matches, send nothing
python -m watcher.run --dry-run --only pickles --keywords landcruiser
python -m pytest                                 # tests
```

## Adding more sites
Manheim blocks automated browsers, so it can't be included.

Each site is one file in `watcher/sites/` providing `search_url()`, `EXTRACT_JS` (pulls the result cards off the page) and `parse_cards()`. Add a scrape function in `watcher/run.py` and a line under `sites:` in `config.yaml`.
