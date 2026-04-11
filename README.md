# NOAA Rainfall Tracker — Palo Alto

Fetches daily precipitation data from the **NOAA NCEI public API** (no API key needed) for the current rain season (Oct 1 – present) and generates a report.

## Quick start

Run from inside the repo directory:

```bash
# No dependencies beyond Python 3.10+ standard library
python3 noaa_rainfall.py
```

## Output formats

```bash
python3 noaa_rainfall.py           # Pretty-printed console report
python3 noaa_rainfall.py --json    # Raw JSON
python3 noaa_rainfall.py --csv     # CSV (pipeable)
```

## Pick a station

By default the script tries Redwood City → San Jose Airport → SFO, using the first one that returns data. Use `--station` to force a specific GHCND station:

```bash
python3 noaa_rainfall.py --station USW00023293   # San Jose Airport
python3 noaa_rainfall.py --station USC00047339   # Redwood City
python3 noaa_rainfall.py --station USW00023234   # SFO Airport
```

## Email updates

Credentials are stored in your **macOS Keychain** — nothing is saved in plaintext.

```bash
# 1. One-time setup (interactive, saves to Keychain)
python3 noaa_rainfall.py --setup-email

# 2. Send a report
python3 noaa_rainfall.py --email you@gmail.com
```

For Gmail, use an [App Password](https://myaccount.google.com/apppasswords) (not your main password).

Credentials are stored under the Keychain service `noaa-rainfall-tracker`. You can view/delete them in Keychain Access.app or via `security delete-generic-password -s noaa-rainfall-tracker -a smtp_pass`.

**Non-macOS fallback**: set `SMTP_USER` and `SMTP_PASS` environment variables.

## Automate with cron

Send yourself a weekly update every Monday at 8 AM:

```cron
0 8 * * 1  cd /path/to/weather && python3 noaa_rainfall.py --email you@gmail.com
```

## Custom date ranges

```bash
python3 noaa_rainfall.py --start 2024-10-01 --end 2025-03-15
```

## Web dashboard

A mobile-first dashboard lives at `site/` after running `build_site.py`. It fetches all three nearby stations, computes a weighted Palo Alto estimate using `(2 × San Jose + Redwood City) / 3`, and renders a self-contained HTML page with a station selector, monthly bars, and a 14-day strip. The eight rain visualizations in `sketches/` are mirrored into `site/sketches/` so they ship with the deploy.

```bash
python3 build_site.py
python3 -m http.server 8765 --bind 0.0.0.0 --directory site   # preview locally
```

The deployed copy lives at **https://design-in-product.github.io/weather/** and is rebuilt daily by a GitHub Action (`.github/workflows/update.yml`). When the daily run sees newly observed records with rain (set-diffed against the previously deployed `state.json`), it emails the report to the configured recipient.

### One-time deploy setup

1. **Repository secrets** (Settings → Secrets and variables → Actions):
   - `SMTP_USER` — Gmail address used to send the report
   - `SMTP_PASS` — Gmail [App Password](https://myaccount.google.com/apppasswords)
   - `SMTP_FROM` — *(optional)* From-address; defaults to `SMTP_USER`
   - `REPORT_TO` — recipient address for fresh-rain notifications
2. **GitHub Pages source** (Settings → Pages): set Source to **GitHub Actions**.
3. **First run**: trigger the workflow manually from the Actions tab (`Update rainfall site` → Run workflow). The first run will see no previous state and will skip the email; subsequent runs will set-diff and notify only on truly new rain.

## Data source

- **API**: `https://www.ncei.noaa.gov/access/services/data/v1` (public, no auth)
- **Dataset**: GHCN-Daily (`daily-summaries`)
- **Station**: USC00046646 (Palo Alto, CA)
- **Variable**: PRCP (daily precipitation in inches)
