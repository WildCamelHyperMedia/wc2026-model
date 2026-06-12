#!/usr/bin/env python3
"""
Live bookmaker odds via The Odds API (the-odds-api.com) with CLOSING-LINE CAPTURE.

Key resolution: env ODDS_API_KEY, else file odds_api_key.txt (gitignored).

Cadence (quota-aware, 500 req/month free):
  - normal: refresh match odds if cache older than 6 h
  - closing window: if any match kicks off within the next 150 min,
    refresh if cache older than 30 min  -> captures lines near kickoff
  - quota guard: if fewer than 60 requests remain, force 6 h cadence
  - outrights: every 12 h (they move slowly)

Outputs:
  match_odds.json     latest de-vigged consensus 1X2 per fixture
  closing_lines.json  per match: LAST snapshot taken before kickoff
                      (frozen forever once the match starts — the closing line)
  odds.json           outright winner odds -> market calibration input
"""
import json
import os
import statistics
import urllib.request
from datetime import datetime, timezone, timedelta

API = "https://api.the-odds-api.com/v4/sports"
NORMAL_H = float(os.environ.get("ODDS_REFRESH_H", 6))
CLOSING_MIN = 30          # refresh every 30 min inside the closing window
WINDOW_MIN = 150          # closing window: kickoff within next 150 min
QUOTA_FLOOR = 60

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

def _now_dt():
    return datetime.now(timezone.utc)

def _now():
    return _now_dt().strftime("%Y-%m-%d %H:%M UTC")

def _parse_ts(s):
    s = s.replace("T", " ").replace("Z", "").strip()
    return datetime.strptime(s[:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

def _age_min(fname):
    if not os.path.exists(fname):
        return 1e9
    try:
        as_of = json.load(open(fname)).get("as_of", "")
        return (_now_dt() - _parse_ts(as_of)).total_seconds() / 60.0
    except Exception:
        return 1e9

def _quota_left():
    try:
        return float(json.load(open("match_odds.json")).get("quota_left", 1e9))
    except Exception:
        return 1e9

def _in_closing_window():
    """True if any unplayed fixture kicks off within the next WINDOW_MIN minutes."""
    try:
        fixtures = json.load(open("fixtures.json"))
    except Exception:
        return False
    now = _now_dt()
    for fx in fixtures:
        if fx.get("HomeTeamScore") is not None:
            continue
        try:
            ko = _parse_ts(fx["DateUtc"])
        except Exception:
            continue
        delta = (ko - now).total_seconds() / 60.0
        if 0 <= delta <= WINDOW_MIN:
            return True
    return False

def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        remaining = r.headers.get("x-requests-remaining")
        return json.loads(r.read().decode()), remaining

def fetch_match_odds(force=False):
    """De-vigged consensus 1X2 + closing-line ledger maintenance."""
    closing = _in_closing_window()
    limit_min = CLOSING_MIN if closing else NORMAL_H * 60
    if _quota_left() < QUOTA_FLOOR:
        limit_min = NORMAL_H * 60
    age = _age_min("match_odds.json")
    if not force and age < limit_min:
        return f"cached ({age:.0f} min old{'; closing window' if closing else ''})"
    key = _key()
    if not key:
        return "no key"
    try:
        data, remaining = _get(f"{API}/soccer_fifa_world_cup/odds/"
                               f"?apiKey={key}&regions=us&markets=h2h&oddsFormat=decimal")
    except Exception as e:
        return f"fetch failed: {e}"

    now_s = _now()
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
                per_book.append([x / s for x in q])
        if not per_book:
            continue
        cons = [statistics.median(b[i] for b in per_book) for i in range(3)]
        s = sum(cons)
        events[f"{home}|{away}"] = {
            "probs": [round(c / s, 4) for c in cons],
            "n_books": len(per_book),
            "commence": ev["commence_time"],
        }
    json.dump({"as_of": now_s, "source": "The Odds API consensus",
               "quota_left": float(remaining or 0), "events": events},
              open("match_odds.json", "w"), indent=1)

    # ---- closing-line ledger: last snapshot before each kickoff, frozen after ----
    cl = json.load(open("closing_lines.json")) if os.path.exists("closing_lines.json") else {}
    now = _now_dt()
    for k, v in events.items():
        try:
            ko = _parse_ts(v["commence"])
        except Exception:
            continue
        if now < ko:  # still pre-kickoff: this becomes the provisional closing line
            mins_to_ko = (ko - now).total_seconds() / 60.0
            cl[k] = {"probs": v["probs"], "n_books": v["n_books"],
                     "captured_at": now_s, "kickoff": v["commence"],
                     "mins_before_ko": round(mins_to_ko)}
        # if kickoff has passed: never touch — the last pre-kickoff snapshot stands
    json.dump(cl, open("closing_lines.json", "w"), indent=1)

    return (f"{len(events)} fixtures priced "
            f"({'closing window, ' if closing else ''}{remaining} requests left)")

def fetch_outrights(force=False):
    """Median outright winner odds across books -> odds.json (every 12 h)."""
    if not force and _age_min("odds.json") < 12 * 60 and \
       json.load(open("odds.json")).get("source", "").startswith("The Odds API"):
        return "cached"
    key = _key()
    if not key:
        return "no key"
    if _quota_left() < QUOTA_FLOOR:
        return "skipped (quota guard)"
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
    return f"{len(odds)} teams ({remaining} requests left)"

if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    print("match odds:", fetch_match_odds(force))
    print("outrights: ", fetch_outrights(force))
