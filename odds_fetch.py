#!/usr/bin/env python3
"""
Live bookmaker odds via The Odds API (the-odds-api.com).

Key resolution: env ODDS_API_KEY, else file odds_api_key.txt (gitignored).
Quota care (500 req/month free): fetches are skipped if the cached file is
younger than REFRESH_H hours (default 6) — ~4 pulls/day during the tournament.

Outputs:
  match_odds.json   de-vigged consensus 1X2 per fixture (median across books)
  odds.json         outright winner odds (median across books) -> drives the
                    market calibration automatically
"""
import json
import os
import statistics
import urllib.request
from datetime import datetime, timezone, timedelta

API = "https://api.the-odds-api.com/v4/sports"
REFRESH_H = float(os.environ.get("ODDS_REFRESH_H", 6))

NAME_MAP = {
    "Bosnia & Herzegovina": "Bosnia-Herzegovina", "Czech Republic": "Czechia",
    "USA": "United States", "Curaçao": "Curacao",
    "Korea Republic": "South Korea", "Türkiye": "Turkey",
    "Côte d'Ivoire": "Ivory Coast", "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo", "IR Iran": "Iran",
}
norm = lambda n: NAME_MAP.get(n, n)

def _key():
    k = os.environ.get("ODDS_API_KEY", "").strip()
    if not k and os.path.exists("odds_api_key.txt"):
        k = open("odds_api_key.txt").read().strip()
    return k

def _fresh(fname):
    if not os.path.exists(fname):
        return False
    try:
        as_of = json.load(open(fname)).get("as_of", "")
        t = datetime.strptime(as_of, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - t < timedelta(hours=REFRESH_H)
    except Exception:
        return False

def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        remaining = r.headers.get("x-requests-remaining")
        return json.loads(r.read().decode()), remaining

def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def fetch_match_odds(force=False):
    """De-vigged consensus 1X2 for every fixture with posted lines."""
    if not force and _fresh("match_odds.json"):
        return "cached"
    key = _key()
    if not key:
        return "no key"
    try:
        data, remaining = _get(f"{API}/soccer_fifa_world_cup/odds/"
                               f"?apiKey={key}&regions=us&markets=h2h&oddsFormat=decimal")
    except Exception as e:
        return f"fetch failed: {e}"
    events = {}
    for ev in data:
        home, away = norm(ev["home_team"]), norm(ev["away_team"])
        per_book = []
        for bm in ev.get("bookmakers", []):
            for mk in bm.get("markets", []):
                if mk["key"] != "h2h":
                    continue
                px = {o["name"]: float(o["price"]) for o in mk["outcomes"]}
                ph, pd_, pa = (px.get(ev["home_team"]), px.get("Draw"),
                               px.get(ev["away_team"]))
                if not (ph and pd_ and pa):
                    continue
                q = [1/ph, 1/pd_, 1/pa]
                s = sum(q)
                per_book.append([x / s for x in q])  # proportional de-vig
        if not per_book:
            continue
        cons = [statistics.median(b[i] for b in per_book) for i in range(3)]
        s = sum(cons)
        events[f"{home}|{away}"] = {
            "probs": [round(c / s, 4) for c in cons],
            "n_books": len(per_book),
            "commence": ev["commence_time"],
        }
    json.dump({"as_of": _now(), "source": f"The Odds API consensus",
               "events": events}, open("match_odds.json", "w"), indent=1)
    return f"{len(events)} fixtures priced ({remaining} API requests left)"

def fetch_outrights(force=False):
    """Median outright winner odds across books -> odds.json (calibration input)."""
    if not force and _fresh("odds.json") and \
       json.load(open("odds.json")).get("source", "").startswith("The Odds API"):
        return "cached"
    key = _key()
    if not key:
        return "no key"
    try:
        data, remaining = _get(f"{API}/soccer_fifa_world_cup_winner/odds/"
                               f"?apiKey={key}&regions=us,eu&markets=outrights&oddsFormat=decimal")
    except Exception as e:
        return f"fetch failed: {e}"
    quotes = {}
    for ev in data:
        for bm in ev.get("bookmakers", []):
            for mk in bm.get("markets", []):
                if mk["key"] != "outrights":
                    continue
                for o in mk["outcomes"]:
                    quotes.setdefault(norm(o["name"]), []).append(float(o["price"]))
    if len(quotes) < 30:
        return f"only {len(quotes)} teams quoted — kept existing odds.json"
    n_books = max(len(v) for v in quotes.values())
    odds = {t: round(statistics.median(v), 2) for t, v in quotes.items()}
    json.dump({"as_of": _now(),
               "source": f"The Odds API consensus ({n_books} books)",
               "odds": odds}, open("odds.json", "w"), indent=1)
    return f"{len(odds)} teams ({remaining} API requests left)"

if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    print("match odds:", fetch_match_odds(force))
    print("outrights: ", fetch_outrights(force))
