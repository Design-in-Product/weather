# NOAA Rainfall Tracker for B — Palo Alto

Fetches daily precipitation data from the **NOAA NCEI public API** (no API key needed) for the current rain season (Oct 1 – present) and generates a report.

## Quick start

```bash
# No dependencies beyond Python 3.10+ standard library
python weather/noaa_rainfall.py
```

## Output formats

```bash
python weather/noaa_rainfall.py           # Pretty-printed console report
python weather/noaa_rainfall.py --json    # Raw JSON
python weather/noaa_rainfall.py --csv     # CSV (pipeable)
```

## Email updates

Credentials are stored in your **macOS Keychain** — nothing is saved in plaintext.

```bash
# 1. One-time setup (interactive, saves to Keychain)
python weather/noaa_rainfall.py --setup-email

# 2. Send a report
python weather/noaa_rainfall.py --email you@gmail.com
```

For Gmail, use an [App Password](https://myaccount.google.com/apppasswords) (not your main password).

Credentials are stored under the Keychain service `noaa-rainfall-tracker`. You can view/delete them in Keychain Access.app or via `security delete-generic-password -s noaa-rainfall-tracker -a smtp_pass`.

**Non-macOS fallback**: set `SMTP_USER` and `SMTP_PASS` environment variables.

## Automate with cron

Send yourself a weekly update every Monday at 8 AM:

```cron
0 8 * * 1  cd /path/to/atlas && python weather/noaa_rainfall.py --email you@gmail.com
```

## Custom date ranges

```bash
python weather/noaa_rainfall.py --start 2024-10-01 --end 2025-03-15
```

## Data source

- **API**: `https://www.ncei.noaa.gov/access/services/data/v1` (public, no auth)
- **Dataset**: GHCN-Daily (`daily-summaries`)
- **Station**: USC00046646 (Palo Alto, CA)
- **Variable**: PRCP (daily precipitation in inches)
