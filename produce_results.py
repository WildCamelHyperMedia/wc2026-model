#!/usr/bin/env python3
"""Run final 50k sims in three modes (conditioned on recorded results),
price every group match (with rotation logic), project R32, write outputs."""
import json
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import wc2026_model as M

off_data = json.load(open("offsets.json"))
OFFSETS = off_data["offsets"]
TARGET = off_data["target"]
N = 50_000

MODES = {"pure": 0.0, "blend": 0.5, "market": 1.0}
runs, finals = {}, {}
r32_counter = Counter()
for mode, alpha in MODES.items():
    probs, fin = M.run(OFFSETS, alpha=alpha, n_sims=N, seed=20260611,
                       r32_counter=r32_counter if mode == "blend" else None)
    runs[mode] = probs
    finals[mode] = [{"pair": list(p), "p": c / N} for p, c in fin.most_common(8)]
    print(f"{mode:7s} done — top: " +
          ", ".join(f"{t} {probs[t]['champion']*100:.1f}%"
                    for t in sorted(M.TEAMS, key=lambda x: -probs[x]['champion'])[:4]))

# ---------- teams ----------
teams = []
for t in M.TEAMS:
    p_pure = runs["pure"][t]["champion"]
    p_blend = runs["blend"][t]["champion"]
    mp = TARGET[t]
    d = M.ODDS[t]
    teams.append({
        "team": t, "group": M.TEAMS[t][0], "elo": round(M.ELO[t]),
        "offset": round(OFFSETS[t], 1),
        "manual": M.MANUAL.get(t, 0.0),
        "calibrated": t in set(off_data["calibrated"]),
        "odds_decimal": d, "market_implied": mp,
        "modes": {m: runs[m][t] for m in MODES},
        "edge_pure": p_pure - mp, "ev_pure": p_pure * d - 1.0,
        "edge_blend": p_blend - mp, "ev_blend": p_blend * d - 1.0,
        "kelly_blend": max(0.0, (p_blend * d - 1.0) / (d - 1.0)),
    })
teams.sort(key=lambda r: -r["modes"]["blend"]["champion"])

# ---------- real standings (locked results only) ----------
locked_pts = defaultdict(Counter)        # group -> Counter pts
locked_count_r12 = Counter()             # group -> # of R1+R2 matches locked
for n, rd, g, a, b, res in M.GROUP_FIX:
    if res is None:
        continue
    ga, gb = res
    if ga > gb:   locked_pts[g][a] += 3
    elif gb > ga: locked_pts[g][b] += 3
    else:         locked_pts[g][a] += 1; locked_pts[g][b] += 1
    if rd < 3:
        locked_count_r12[g] += 1

# ---------- match board ----------
fixtures = json.load(open("fixtures.json"))
fxmeta = {fx["MatchNumber"]: fx for fx in fixtures}
matches = []
for n, rd, g, a, b, res in M.GROUP_FIX:
    fx = fxmeta[n]
    entry = {
        "n": n, "round": rd, "utc": fx["DateUtc"],
        "venue": fx["Location"].replace(" Stadium", ""),
        "group": g, "home": a, "away": b, "probs": {}, "rot": [False, False],
    }
    if res is not None:
        entry["played"] = list(res)
    # rotation flags: only computable once the group's R1+R2 are all real
    pen_a = pen_b = 0.0
    if rd == 3 and res is None and locked_count_r12[g] == 4:
        la = M.locked_top2(locked_pts[g], a, M.GROUPS[g])
        lb = M.locked_top2(locked_pts[g], b, M.GROUPS[g])
        entry["rot"] = [la, lb]
        pen_a = M.ROTATION_PENALTY * la
        pen_b = M.ROTATION_PENALTY * lb
    for mode, alpha in MODES.items():
        pw, pd, pl = M.match_probs(a, b, OFFSETS, alpha, "group", pen_a, pen_b)
        entry["probs"][mode] = [round(pw, 4), round(pd, 4), round(pl, 4)]
    bk = M.BOOK.get((a, b))
    if bk and res is None:
        entry["book"] = bk[0]
        entry["book_n"] = bk[1]
    matches.append(entry)
matches.sort(key=lambda m: m["utc"])
assert len(matches) == 72

# ---------- knockout schedule + projections ----------
SLOT_LABELS = {73:"2A v 2B",74:"1E v 3rd",75:"1F v 2C",76:"1C v 2F",77:"1I v 3rd",
               78:"2E v 2I",79:"1A v 3rd",80:"1L v 3rd",81:"1D v 3rd",82:"1G v 3rd",
               83:"2K v 2L",84:"1H v 2J",85:"1B v 3rd",86:"1J v 2H",87:"1K v 3rd",
               88:"2D v 2G",89:"W74 v W77",90:"W73 v W75",91:"W76 v W78",92:"W79 v W80",
               93:"W83 v W84",94:"W81 v W82",95:"W86 v W88",96:"W85 v W87",
               97:"QF: W89 v W90",98:"QF: W93 v W94",99:"QF: W91 v W92",100:"QF: W95 v W96",
               101:"SF: W97 v W98",102:"SF: W99 v W100",103:"3rd place",104:"FINAL"}
ko = []
for fx in fixtures:
    n = fx["MatchNumber"]
    if fx["Group"] or n not in SLOT_LABELS:
        continue
    label = SLOT_LABELS[n]
    known = n in M.KO_SLOTS
    if known:
        label = f"{M.KO_SLOTS[n][0]} v {M.KO_SLOTS[n][1]}"
    item = {"n": n, "utc": fx["DateUtc"],
            "venue": fx["Location"].replace(" Stadium", ""),
            "label": label, "known": known,
            "winner": M.KO_WINNERS.get(n), "proj": []}
    if 73 <= n <= 88 and not known:
        pairs = [(p, c) for (mid, p), c in r32_counter.items() if mid == n]
        pairs.sort(key=lambda x: -x[1])
        item["proj"] = [{"pair": list(p), "p": c / N} for p, c in pairs[:3]]
    ko.append(item)
ko.sort(key=lambda m: (m["utc"], m["n"]))

out = {
    "meta": {
        "n_sims": N,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "overround_pct": round((off_data["overround"] - 1) * 100, 1),
        "freshness": M.freshness(),
        "modes": {
            "pure": "Raw Elo (live) — no injury/news information",
            "blend": "Half-weight market adjustment — recommended estimate",
            "market": "Calibrated to de-vigged outright market — injuries/news as priced",
        },
    },
    "teams": teams, "finals": finals, "matches": matches, "ko": ko,
}
with open("wc2026_results_v2.json", "w") as f:
    json.dump(out, f, indent=1)

# ---------- CSVs ----------
cols = ["team", "group", "elo", "offset", "manual", "odds_decimal", "market_implied",
        "edge_pure", "ev_pure", "edge_blend", "ev_blend", "kelly_blend"]
stage_keys = ["group_win", "r32", "r16", "qf", "sf", "final", "champion"]
with open("wc2026_results.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(cols + [f"{m}_{s}" for m in MODES for s in stage_keys])
    for r in teams:
        w.writerow([r[c] for c in cols] +
                   [r["modes"][m][s] for m in MODES for s in stage_keys])

with open("wc2026_matches.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["match", "date_utc", "venue", "group", "round", "home", "away",
                "played", "rot_home", "rot_away"] +
               [f"{m}_{o}" for m in MODES for o in ("home_win", "draw", "away_win")] +
               ["blend_fair_1", "blend_fair_X", "blend_fair_2"])
    for mt in matches:
        bl = mt["probs"]["blend"]
        w.writerow([mt["n"], mt["utc"], mt["venue"], mt["group"], mt["round"],
                    mt["home"], mt["away"],
                    "-".join(map(str, mt.get("played", []))) or "",
                    int(mt["rot"][0]), int(mt["rot"][1])] +
                   [p for m in MODES for p in mt["probs"][m]] +
                   [round(1/p, 2) for p in bl])

fr = M.freshness()
print(f"wrote outputs · {len(matches)} matches · results locked: {fr['results_locked']}"
      f" · KO known: {fr['ko_slots_known']} · manual adj: {len(fr['manual_adjustments'])}")
