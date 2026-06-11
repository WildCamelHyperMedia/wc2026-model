# ⚽ World Cup 2026 — Live Predictive Model

A self-updating Monte Carlo forecast of the 2026 FIFA World Cup, built for
analysis and betting research. Zero dependencies — pure Python 3.9+ stdlib.

**[→ Live dashboard](https://YOUR-USERNAME.github.io/YOUR-REPO/)** *(after enabling GitHub Pages, see below)*

## What it does

- **Elo + Monte Carlo** — 50,000 full-tournament simulations of the exact
  48-team FIFA bracket (including third-place slot rules and host advantage)
- **Three projection types** — Pure Elo · Blended ★ (recommended) ·
  Market-anchored (per-team rating offsets calibrated so simulated title odds
  reproduce the de-vigged bookmaker market — this is how injuries, squad news
  and form enter the model)
- **Match-by-match board** — every group game by day with 1X2 probabilities,
  consensus picks across all three projections, and fair (no-vig) odds
- **Live conditioning** — played results are locked in exactly; group tables
  update; confirmed knockout pairings and winners are honored; matchday-3
  dead-rubber rotation risk is detected and priced (−60 Elo)
- **Value analysis** — model vs market edge, EV per $1, quarter-Kelly stakes

## Quick start

```bash
python3 update.py            # fetch live Elo + results + market → rebuild everything (~2 min)
python3 update.py --watch    # keep running; auto-rebuild whenever a match finishes
open wc2026_dashboard.html   # the dashboard (also written to docs/index.html)
```

## Auto-updating public dashboard (GitHub Pages)

1. Push this repo to GitHub (public repo = free unlimited Actions minutes)
2. **Settings → Pages** → Source: *Deploy from a branch* → Branch: `main`, folder `/docs`
3. **Actions** tab → enable workflows

Done. `.github/workflows/update.yml` re-runs the full pipeline every 30
minutes and commits the refreshed dashboard — your Pages URL stays current
with every match, no computer needed.

## Run on Replit

Import the GitHub repo into Replit and hit Run — `serve.py` starts the
watcher (rebuilds on every new result) and serves the dashboard on port 8080.

## Manual levers

| File | Purpose |
|---|---|
| `odds.json` | Current bettable outright odds — refresh after big line moves |
| `adjustments.json` | Instant news tweaks, e.g. `{"France": -25}` for an injury |

## Pipeline

```
update.py ─ fetch: eloratings.net (live Elo) · fixturedownload.com (results/bracket) · market
   └─ calibrate.py        market-implied Elo offsets (injury/news signal)
   └─ produce_results.py  3 × 50k conditioned simulations + match pricing
   └─ build_dashboard.py  self-contained HTML → wc2026_dashboard.html + docs/index.html
```

## Data sources

[eloratings.net](https://www.eloratings.net) · [fixturedownload.com](https://fixturedownload.com) · BetMGM outrights (manual, `odds.json`) · FIFA match schedule & regulations

## Disclaimer

Model estimates, not guarantees. A positive-EV flag means the model disagrees
with the market — the market is right more often than any public model.
Single-tournament variance is enormous. Quarter-Kelly or less; never stake
what you can't afford to lose. Analysis, not financial advice.
