#!/usr/bin/env python3
"""
2026 World Cup model core v3 — live-updating, result-conditioned simulator.

Effective rating = Elo(live) + manual_adjustment + alpha * market_offset
  alpha=0 pure | alpha=0.5 blend | alpha=1 market-anchored

Data files (all optional except fixtures.json):
  elo_live.json      {"as_of":..., "elo":{team:rating}}    written by update.py
  odds.json          {"as_of":..., "source":..., "odds":{team:decimal}}
  adjustments.json   {"adjustments":{team:elo_delta}}      manual news lever
  market_live.json   {"as_of":..., "probs":{team:p}}       e.g. Polymarket
  fixtures.json      fixturedownload.com feed (dates, venues, RESULTS)

Conditioning: any group match with a recorded score is replayed exactly;
knockout slots/winners recorded in the feed are honored. Matchday-3
"dead rubber" rotation: a team mathematically locked into the top two
gets a -60 Elo rotation penalty in that match.
"""

import json
import math
import os
import random
from collections import Counter, defaultdict

HOSTS = {"United States", "Mexico", "Canada"}
HOME_BONUS = 100
ROTATION_PENALTY = 60

# Launch-day snapshot fallbacks (overridden by elo_live.json / odds.json)
TEAMS = {
    "Czechia":            ("A", 1740, 251.0),
    "Mexico":             ("A", 1875, 67.0),
    "South Africa":       ("A", 1517, 1001.0),
    "South Korea":        ("A", 1758, 251.0),
    "Bosnia-Herzegovina": ("B", 1595, 251.0),
    "Canada":             ("B", 1788, 151.0),
    "Qatar":              ("B", 1421, 1001.0),
    "Switzerland":        ("B", 1891, 67.0),
    "Brazil":             ("C", 1991, 10.0),
    "Haiti":              ("C", 1548, 2501.0),
    "Morocco":            ("C", 1827, 41.0),
    "Scotland":           ("C", 1782, 251.0),
    "Australia":          ("D", 1777, 501.0),
    "Paraguay":           ("D", 1834, 251.0),
    "Turkey":             ("D", 1911, 67.0),
    "United States":      ("D", 1726, 51.0),
    "Curacao":            ("E", 1434, 2501.0),
    "Ecuador":            ("E", 1938, 81.0),
    "Germany":            ("E", 1932, 15.0),
    "Ivory Coast":        ("E", 1695, 201.0),
    "Japan":              ("F", 1906, 51.0),
    "Netherlands":        ("F", 1948, 21.0),
    "Sweden":             ("F", 1712, 101.0),
    "Tunisia":            ("F", 1628, 501.0),
    "Belgium":            ("G", 1894, 34.0),
    "Egypt":              ("G", 1696, 251.0),
    "Iran":               ("G", 1772, 501.0),
    "New Zealand":        ("G", 1562, 1001.0),
    "Cape Verde":         ("H", 1578, 1001.0),
    "Saudi Arabia":       ("H", 1576, 1001.0),
    "Spain":              ("H", 2157, 5.5),
    "Uruguay":            ("H", 1892, 67.0),
    "France":             ("I", 2063, 6.0),
    "Iraq":               ("I", 1607, 1001.0),
    "Norway":             ("I", 1914, 34.0),
    "Senegal":            ("I", 1860, 67.0),
    "Algeria":            ("J", 1772, 251.0),
    "Argentina":          ("J", 2115, 10.0),
    "Austria":            ("J", 1830, 151.0),
    "Jordan":             ("J", 1680, 1001.0),
    "Colombia":           ("K", 1982, 41.0),
    "DR Congo":           ("K", 1652, 751.0),
    "Portugal":           ("K", 1989, 9.0),
    "Uzbekistan":         ("K", 1714, 1001.0),
    "Croatia":            ("L", 1912, 81.0),
    "England":            ("L", 2024, 8.0),
    "Ghana":              ("L", 1510, 501.0),
    "Panama":             ("L", 1730, 1001.0),
}

NAME_MAP = {
    "Korea Republic": "South Korea", "USA": "United States",
    "Türkiye": "Turkey", "Côte d'Ivoire": "Ivory Coast",
    "Cabo Verde": "Cape Verde", "Congo DR": "DR Congo",
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Curaçao": "Curacao", "IR Iran": "Iran",
}
norm = lambda n: NAME_MAP.get(n, n)

# eloratings.net team codes for our 48
ELO_CODES = {
    "ES": "Spain", "AR": "Argentina", "FR": "France", "EN": "England",
    "BR": "Brazil", "PT": "Portugal", "CO": "Colombia", "NL": "Netherlands",
    "EC": "Ecuador", "DE": "Germany", "NO": "Norway", "HR": "Croatia",
    "TR": "Turkey", "JP": "Japan", "BE": "Belgium", "UY": "Uruguay",
    "CH": "Switzerland", "MX": "Mexico", "SN": "Senegal", "PY": "Paraguay",
    "AT": "Austria", "MA": "Morocco", "CA": "Canada", "AU": "Australia",
    "DZ": "Algeria", "IR": "Iran", "KR": "South Korea", "CZ": "Czechia",
    "US": "United States", "UZ": "Uzbekistan", "SE": "Sweden", "EG": "Egypt",
    "CI": "Ivory Coast", "JO": "Jordan", "SQ": "Scotland", "QA": "Qatar",
    "BA": "Bosnia-Herzegovina", "HT": "Haiti", "CW": "Curacao",
    "TN": "Tunisia", "NZ": "New Zealand", "SA": "Saudi Arabia",
    "CV": "Cape Verde", "IQ": "Iraq", "CD": "DR Congo", "GH": "Ghana",
    "PA": "Panama", "ZA": "South Africa",
}
assert len(ELO_CODES) == 48

GROUPS = defaultdict(list)
for t, (g, _, _) in TEAMS.items():
    GROUPS[g].append(t)
GROUP_IDS = sorted(GROUPS.keys())

def _load(fname, default=None):
    if os.path.exists(fname):
        with open(fname) as f:
            return json.load(f)
    return default

# ---- live-overridable inputs ----
_elo_live = _load("elo_live.json", {})
ELO = {t: float(_elo_live.get("elo", {}).get(t, TEAMS[t][1])) for t in TEAMS}
ELO_AS_OF = _elo_live.get("as_of", "2026-06-11 (snapshot)")

_odds = _load("odds.json", {})
ODDS = {t: float(_odds.get("odds", {}).get(t, TEAMS[t][2])) for t in TEAMS}
ODDS_AS_OF = _odds.get("as_of", "2026-06-10")
ODDS_SOURCE = _odds.get("source", "BetMGM")

MANUAL = {t: float(v) for t, v in
          _load("adjustments.json", {}).get("adjustments", {}).items()
          if t in TEAMS}

# ---- fixtures & recorded results ----
_fixtures = _load("fixtures.json", [])
GROUP_FIX = []   # (match_n, round, group, home, away, result_or_None)
KO_SLOTS = {}    # match_n -> (home, away) when real teams known
KO_WINNERS = {}  # match_n -> winner
for fx in _fixtures:
    n = fx["MatchNumber"]
    h, a = norm(fx["HomeTeam"]), norm(fx["AwayTeam"])
    if fx.get("Group"):
        res = None
        if fx.get("HomeTeamScore") is not None and fx.get("AwayTeamScore") is not None:
            res = (int(fx["HomeTeamScore"]), int(fx["AwayTeamScore"]))
        GROUP_FIX.append((n, fx["RoundNumber"], fx["Group"][-1], h, a, res))
    else:
        if h in TEAMS and a in TEAMS:
            KO_SLOTS[n] = (h, a)
        wn = norm(fx.get("Winner") or "")
        if wn in TEAMS:
            KO_WINNERS[n] = wn
GROUP_FIX.sort(key=lambda x: (x[2], x[1], x[0]))
RESULTS_LOCKED = sum(1 for *_, r in GROUP_FIX if r is not None)

# ---- bracket ----
R32 = [
    (73, "RA", "RB"), (74, "WE", "T74"), (75, "WF", "RC"), (76, "WC", "RF"),
    (77, "WI", "T77"), (78, "RE", "RI"), (79, "WA", "T79"), (80, "WL", "T80"),
    (81, "WD", "T81"), (82, "WG", "T82"), (83, "RK", "RL"), (84, "WH", "RJ"),
    (85, "WB", "T85"), (86, "WJ", "RH"), (87, "WK", "T87"), (88, "RD", "RG"),
]
THIRD_SLOTS = {
    "T74": set("ABCDF"), "T77": set("CDFGH"), "T79": set("CEFHI"),
    "T80": set("EHIJK"), "T81": set("BEFIJ"), "T82": set("AEHIJ"),
    "T85": set("EFGIJ"), "T87": set("DEIJL"),
}
R16 = [(89, 74, 77), (90, 73, 75), (91, 76, 78), (92, 79, 80),
       (93, 83, 84), (94, 81, 82), (95, 86, 88), (96, 85, 87)]
QF  = [(97, 89, 90), (98, 93, 94), (99, 91, 92), (100, 95, 96)]
SF  = [(101, 97, 98), (102, 99, 100)]

_assign_cache = {}

def assign_thirds(qualified_groups):
    key = frozenset(qualified_groups)
    if key in _assign_cache:
        return _assign_cache[key]
    slots = sorted(THIRD_SLOTS.keys(), key=lambda s: len(THIRD_SLOTS[s] & key))
    assignment, used = {}, set()

    def bt(idx):
        if idx == len(slots):
            return True
        slot = slots[idx]
        for grp in sorted(THIRD_SLOTS[slot] & key):
            if grp not in used:
                assignment[slot] = grp; used.add(grp)
                if bt(idx + 1):
                    return True
                used.discard(grp); del assignment[slot]
        return False

    if not bt(0):
        raise RuntimeError(f"no assignment for {sorted(key)}")
    _assign_cache[key] = dict(assignment)
    return _assign_cache[key]

# ---- match math ----
def poisson(lam, rnd):
    L = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        p *= rnd.random()
        if p <= L:
            return k
        k += 1

def host_bonus(team, stage):
    if team not in HOSTS:
        return 0
    if team == "United States":
        return HOME_BONUS
    return HOME_BONUS if stage in ("group", "r32", "r16") else 0

def win_expectancy(ra, rb):
    return 1.0 / (1.0 + 10 ** (-(ra - rb) / 400.0))

def effective(team, offsets, alpha):
    return ELO[team] + MANUAL.get(team, 0.0) + alpha * (offsets or {}).get(team, 0.0)

def _wdl(ra, rb):
    dr = ra - rb
    we = win_expectancy(ra, rb)
    pd = 0.27 * math.exp(-(dr / 500.0) ** 2)
    pa = max(0.005, we - pd / 2)
    pb = max(0.005, 1.0 - pa - pd)
    s = pa + pd + pb
    return pa / s, pd / s, pb / s, dr

def match_probs(a, b, offsets=None, alpha=0.0, stage="group", pen_a=0.0, pen_b=0.0):
    """1X2 probabilities, optionally with rotation penalties."""
    ra = effective(a, offsets, alpha) + host_bonus(a, stage) - pen_a
    rb = effective(b, offsets, alpha) + host_bonus(b, stage) - pen_b
    pw, pd, pl, _ = _wdl(ra, rb)
    return pw, pd, pl

def locked_top2(pts, team, group_teams):
    """True if team is guaranteed top-2 of its group regardless of round 3."""
    others = sorted((pts[x] for x in group_teams if x != team), reverse=True)
    return pts[team] == 6 and others[1] <= 2  # third-best opponent can reach max 5

# ---- tournament simulation ----
def run(offsets=None, alpha=0.0, n_sims=50_000, seed=20260611, r32_counter=None):
    rnd = random.Random(seed)
    R = {t: effective(t, offsets, alpha) for t in TEAMS}

    # precompute group match variants
    # rounds 1-2: single variant; round 3: 4 variants keyed (lockA, lockB)
    pre = {}
    for n, rd, g, a, b, res in GROUP_FIX:
        ra = R[a] + host_bonus(a, "group")
        rb = R[b] + host_bonus(b, "group")
        if rd < 3:
            pre[n] = {(False, False): _wdl(ra, rb)}
        else:
            pre[n] = {(la, lb): _wdl(ra - ROTATION_PENALTY * la,
                                     rb - ROTATION_PENALTY * lb)
                      for la in (False, True) for lb in (False, True)}

    by_group = defaultdict(list)
    for fx in GROUP_FIX:
        by_group[fx[2]].append(fx)

    ko_cache = {}
    def ko_p(a, b, stage):
        k = (a, b, stage)
        if k not in ko_cache:
            ko_cache[k] = win_expectancy(R[a] + host_bonus(a, stage),
                                         R[b] + host_bonus(b, stage))
        return ko_cache[k]

    counts = {t: Counter() for t in TEAMS}
    group_wins = Counter()
    finals = Counter()

    def sample_score(pa, pd, dr):
        r = rnd.random()
        if r < pa:
            gl = poisson(0.75, rnd)
            return gl + 1 + min(poisson(0.45 + max(dr, 0) / 800.0, rnd), 5), gl
        if r < pa + pd:
            g = min(poisson(1.0, rnd), 4)
            return g, g
        gl = poisson(0.75, rnd)
        return gl, gl + 1 + min(poisson(0.45 + max(-dr, 0) / 800.0, rnd), 5)

    for _ in range(n_sims):
        winners, runners, thirds, tstats = {}, {}, {}, {}
        for g in GROUP_IDS:
            pts, gd, gf = Counter(), Counter(), Counter()
            for n, rd, _, a, b, res in by_group[g]:
                if res is not None:                      # real result locked
                    ga, gb = res
                else:
                    if rd < 3:
                        pa, pd, _, dr = pre[n][(False, False)]
                    else:
                        la = locked_top2(pts, a, GROUPS[g])
                        lb = locked_top2(pts, b, GROUPS[g])
                        pa, pd, _, dr = pre[n][(la, lb)]
                    ga, gb = sample_score(pa, pd, dr)
                gf[a] += ga; gf[b] += gb
                gd[a] += ga - gb; gd[b] += gb - ga
                if ga > gb:   pts[a] += 3
                elif gb > ga: pts[b] += 3
                else:         pts[a] += 1; pts[b] += 1
            ranked = sorted(GROUPS[g],
                            key=lambda t: (pts[t], gd[t], gf[t], rnd.random()),
                            reverse=True)
            winners[g], runners[g], thirds[g] = ranked[0], ranked[1], ranked[2]
            t3 = ranked[2]
            tstats[g] = (pts[t3], gd[t3], gf[t3], rnd.random())
            group_wins[ranked[0]] += 1

        best8 = sorted(GROUP_IDS, key=lambda g: tstats[g], reverse=True)[:8]
        slot_map = assign_thirds(best8)
        ent = {}
        for g in GROUP_IDS:
            ent["W" + g] = winners[g]; ent["R" + g] = runners[g]
        for slot, g in slot_map.items():
            ent[slot] = thirds[g]

        for t in set(winners.values()) | set(runners.values()) | {thirds[g] for g in best8}:
            counts[t]["r32"] += 1

        mw = {}
        for mid, hs, as_ in R32:
            a, b = KO_SLOTS.get(mid, (ent[hs], ent[as_]))
            if r32_counter is not None:
                r32_counter[(mid, tuple(sorted((a, b))))] += 1
            if mid in KO_WINNERS:
                mw[mid] = KO_WINNERS[mid]
            else:
                mw[mid] = a if rnd.random() < ko_p(a, b, "r32") else b
        for t in mw.values():
            counts[t]["r16"] += 1
        for stage, matches_, nxt in (("r16", R16, "qf"), ("qf", QF, "sf")):
            for mid, m1, m2 in matches_:
                a, b = mw[m1], mw[m2]
                if mid in KO_WINNERS:
                    mw[mid] = KO_WINNERS[mid]
                else:
                    mw[mid] = a if rnd.random() < ko_p(a, b, stage) else b
                counts[mw[mid]][nxt] += 1
        for mid, m1, m2 in SF:
            a, b = mw[m1], mw[m2]
            if mid in KO_WINNERS:
                mw[mid] = KO_WINNERS[mid]
            else:
                mw[mid] = a if rnd.random() < ko_p(a, b, "sf") else b
        f1, f2 = mw[101], mw[102]
        counts[f1]["final"] += 1; counts[f2]["final"] += 1
        finals[tuple(sorted((f1, f2)))] += 1
        if 104 in KO_WINNERS:
            champ = KO_WINNERS[104]
        else:
            champ = f1 if rnd.random() < ko_p(f1, f2, "final") else f2
        counts[champ]["champion"] += 1

    probs = {}
    for t in TEAMS:
        probs[t] = {
            "group_win": group_wins[t] / n_sims,
            "r32": counts[t]["r32"] / n_sims, "r16": counts[t]["r16"] / n_sims,
            "qf": counts[t]["qf"] / n_sims, "sf": counts[t]["sf"] / n_sims,
            "final": counts[t]["final"] / n_sims,
            "champion": counts[t]["champion"] / n_sims,
        }
    return probs, finals

# ---- market ----
def market_probs():
    """De-vigged market title probabilities.
    Prefers market_live.json (prediction market) where available,
    falls back to power-method de-vig of odds.json quotes."""
    inv = {t: 1.0 / ODDS[t] for t in TEAMS}
    lo, hi = 1.0, 3.0
    for _ in range(80):
        k = (lo + hi) / 2
        if sum(q ** k for q in inv.values()) > 1.0:
            lo = k
        else:
            hi = k
    p = {t: q ** k for t, q in inv.items()}

    live = _load("market_live.json", {})
    for t, lp in live.get("probs", {}).items():
        t = norm(t)
        if t in p and lp > 0:
            p[t] = float(lp)

    s = sum(p.values())
    return {t: v / s for t, v in p.items()}, sum(inv.values())

def freshness():
    return {
        "elo_as_of": ELO_AS_OF,
        "odds_as_of": ODDS_AS_OF, "odds_source": ODDS_SOURCE,
        "results_locked": RESULTS_LOCKED,
        "manual_adjustments": dict(MANUAL),
        "ko_slots_known": len(KO_SLOTS), "ko_winners_known": len(KO_WINNERS),
    }
