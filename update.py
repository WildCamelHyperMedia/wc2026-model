#!/usr/bin/env python3
"""
One-command refresh: live Elo + live results + market → recalibrate →
re-simulate (conditioned on everything played so far) → rebuild dashboard.

    python3 update.py              # full refresh once
    python3 update.py --no-fetch   # re-run pipeline on cached data only
    python3 update.py --watch      # keep running: poll every 15 min and
                                   # rebuild ONLY when a new result / KO
                                   # change lands (per-match updating)
    python3 update.py --watch 5    # poll every 5 minutes

Manual levers (take effect on next run):
    odds.json         current bettable outright odds (update after news/moves)
    adjustments.json  {"adjustments": {"France": -25}}  instant news tweaks
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def fetch_elo():
    import wc2026_model as M
    try:
        tsv = get("https://www.eloratings.net/World.tsv")
    except Exception as e:
        print(f"⚠ Elo fetch failed ({e}) — keeping cached ratings")
        return
    elo = {}
    for line in tsv.splitlines():
        c = line.split("\t")
        if len(c) > 3 and c[2] in M.ELO_CODES:
            elo[M.ELO_CODES[c[2]]] = int(c[3])
    if len(elo) < 48:
        print(f"⚠ Elo parse incomplete ({len(elo)}/48) — keeping cached ratings")
        return
    old = dict(M.ELO)
    json.dump({"as_of": NOW, "elo": elo}, open("elo_live.json", "w"), indent=1)
    try:
        moves = sorted(((t, float(elo[t]) - float(old.get(t, elo[t])))
                        for t in elo if abs(elo[t] - old.get(t, elo[t])) >= 1),
                       key=lambda x: -abs(x[1]))
        detail = (": " + ", ".join(f"{t} {d:+.0f}" for t, d in moves[:8])
                  if moves else " — no changes")
    except Exception:
        detail = ""
    print(f"✓ Elo refreshed ({NOW}){detail}")

def fetch_results():
    try:
        raw = get("https://fixturedownload.com/feed/json/fifa-world-cup-2026")
        data = json.loads(raw)
        assert len(data) >= 100
    except Exception as e:
        print(f"⚠ Fixtures fetch failed ({e}) — keeping cached fixtures")
        return
    old_done = set()
    if os.path.exists("fixtures.json"):
        for fx in json.load(open("fixtures.json")):
            if fx.get("HomeTeamScore") is not None:
                old_done.add(fx["MatchNumber"])
    json.dump(data, open("fixtures.json", "w"))
    new = [fx for fx in data if fx.get("HomeTeamScore") is not None
           and fx["MatchNumber"] not in old_done]
    done = sum(1 for fx in data if fx.get("HomeTeamScore") is not None)
    print(f"✓ Fixtures refreshed — {done} results recorded" +
          ("; new: " + "; ".join(
              f"{fx['HomeTeam']} {fx['HomeTeamScore']}-{fx['AwayTeamScore']} {fx['AwayTeam']}"
              for fx in new[:10]) if new else ""))

def fetch_market():
    """Best-effort prediction-market probabilities (Polymarket)."""
    try:
        raw = get("https://gamma-api.polymarket.com/events?search=fifa%20world%20cup%202026&limit=20", 10)
        events = json.loads(raw)
        probs = {}
        for ev in events:
            title = (ev.get("title") or "").lower()
            if "winner" not in title and "champion" not in title:
                continue
            for m in ev.get("markets", []):
                name = m.get("groupItemTitle") or m.get("question") or ""
                price = m.get("lastTradePrice")
                if price is None:
                    op = m.get("outcomePrices")
                    if isinstance(op, str):
                        op = json.loads(op)
                    price = float(op[0]) if op else None
                if name and price and 0 < float(price) < 1:
                    probs[name.strip()] = float(price)
        if len(probs) >= 10:
            json.dump({"as_of": NOW, "source": "Polymarket", "probs": probs},
                      open("market_live.json", "w"), indent=1)
            print(f"✓ Live market probabilities: {len(probs)} teams (Polymarket)")
            return
        raise ValueError("insufficient market data")
    except Exception:
        if os.path.exists("market_live.json"):
            os.remove("market_live.json")
        odds_age = json.load(open("odds.json")).get("as_of", "?") \
            if os.path.exists("odds.json") else "?"
        print(f"ℹ No live prediction market reachable — using odds.json "
              f"(as of {odds_age}). Edit odds.json after big news/line moves.")

def feed_signature():
    """Compact signature of tournament state: results + KO slots + winners."""
    try:
        data = json.loads(get("https://fixturedownload.com/feed/json/fifa-world-cup-2026"))
        sig = []
        for fx in sorted(data, key=lambda x: x["MatchNumber"]):
            sig.append((fx["MatchNumber"], fx.get("HomeTeamScore"),
                        fx.get("AwayTeamScore"), fx.get("Winner") or "",
                        fx.get("HomeTeam"), fx.get("AwayTeam")))
        return tuple(sig), data
    except Exception as e:
        return None, None

def cached_signature():
    if not os.path.exists("fixtures.json"):
        return None
    data = json.load(open("fixtures.json"))
    return tuple((fx["MatchNumber"], fx.get("HomeTeamScore"),
                  fx.get("AwayTeamScore"), fx.get("Winner") or "",
                  fx.get("HomeTeam"), fx.get("AwayTeam"))
                 for fx in sorted(data, key=lambda x: x["MatchNumber"]))

def watch(interval_min):
    import time
    print(f"👁  Watch mode: polling every {interval_min} min. "
          f"Pipeline reruns only when a result or bracket change lands. Ctrl-C to stop.")
    while True:
        sig, _ = feed_signature()
        if sig is None:
            print(f"[{datetime.now().strftime('%H:%M')}] feed unreachable — retrying later")
        elif sig != cached_signature():
            print(f"\n[{datetime.now().strftime('%H:%M')}] ⚽ Tournament state changed — refreshing everything")
            run_once()
            print(f"\n👁  back to watching (every {interval_min} min)")
        else:
            print(f"[{datetime.now().strftime('%H:%M')}] no new results")
        time.sleep(interval_min * 60)

def run_once(fetch=True):
    if fetch:
        fetch_elo()
        fetch_results()
        fetch_market()
        try:
            import odds_fetch
            print(f"✓ Book match odds: {odds_fetch.fetch_match_odds()}")
            print(f"✓ Book outrights:  {odds_fetch.fetch_outrights()}")
        except Exception as e:
            print(f"⚠ Book odds fetch skipped ({e})")

    prev = {}
    if os.path.exists("wc2026_results_v2.json"):
        for t in json.load(open("wc2026_results_v2.json"))["teams"]:
            prev[t["team"]] = t["modes"]["blend"]["champion"]

    for script in ("calibrate.py", "produce_results.py", "build_dashboard.py"):
        print(f"\n— running {script} —")
        subprocess.run([sys.executable, script], check=True)

    cur = {t["team"]: t["modes"]["blend"]["champion"]
           for t in json.load(open("wc2026_results_v2.json"))["teams"]}
    if prev:
        moves = sorted(((t, cur[t] - prev.get(t, 0)) for t in cur),
                       key=lambda x: -abs(x[1]))[:6]
        print("\nBiggest title-probability moves (blend): " +
              ", ".join(f"{t} {d*100:+.1f}pp" for t, d in moves if abs(d) > 1e-4))
    top = sorted(cur.items(), key=lambda x: -x[1])[:5]
    print("Current top 5 (blend): " +
          ", ".join(f"{t} {p*100:.1f}%" for t, p in top))
    print("\n✓ Dashboard rebuilt: wc2026_dashboard.html")

def main():
    if "--watch" in sys.argv:
        i = sys.argv.index("--watch")
        mins = 15
        if i + 1 < len(sys.argv):
            try:
                mins = max(2, int(sys.argv[i + 1]))
            except ValueError:
                pass
        run_once()          # always start with a fresh build
        watch(mins)
    else:
        run_once(fetch="--no-fetch" not in sys.argv)

if __name__ == "__main__":
    main()
