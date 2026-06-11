#!/usr/bin/env python3
"""
Calibrate per-team Elo offsets so simulated title probabilities match the
de-vigged market — for teams where the market actually carries signal.

The offsets quantify, in Elo points, what the market prices but raw Elo
can't see: injuries, squad selection, manager situations, current form.

Longshots (market implied < 0.4%, odds ~200-1+) are NOT calibrated: outright
quotes at that level are floored marketing prices, not information. Their
offsets stay 0 (pure Elo).
"""
import json
import math
import wc2026_model as M

target, overround = M.market_probs()
CAL_SET = {t for t in M.TEAMS if target[t] >= 0.004}  # ~150-1 or shorter
print(f"calibrating {len(CAL_SET)} teams: "
      f"{', '.join(sorted(CAL_SET, key=lambda x: -target[x]))}\n")

offsets = {t: 0.0 for t in M.TEAMS}
N_CAL = 15_000
GAINS = [80, 80, 60, 50, 40, 30, 25, 20, 15, 15, 12, 12]
SEED = 777  # common random numbers across iterations -> smooth convergence
FLOOR = 1.0 / (2 * N_CAL)
history = []

for it, gain in enumerate(GAINS):
    probs, _ = M.run(offsets, alpha=1.0, n_sims=N_CAL, seed=SEED)
    max_err = 0.0
    for t in CAL_SET:
        model_p = max(probs[t]["champion"], FLOOR)
        err = math.log(target[t] / model_p)
        max_err = max(max_err, abs(err))
        step = max(-50, min(50, gain * err))
        offsets[t] = max(-200, min(200, offsets[t] + step))
    history.append(dict(offsets))
    print(f"iter {it+1:2d} (gain {gain:2d}): max |log err| = {max_err:.3f}")
    if max_err < 0.10 and it >= 4:
        break

# average last 3 iterations to kill residual noise
last = history[-3:]
offsets = {t: sum(h[t] for h in last) / len(last) for t in M.TEAMS}

# out-of-sample check at higher N, different seed
probs, _ = M.run(offsets, alpha=1.0, n_sims=30_000, seed=424242)
print("\nvalidation (30k sims, fresh seed):")
print(f"{'Team':<16}{'target%':>9}{'model%':>9}{'ratio':>7}")
worst = 0.0
for t in sorted(CAL_SET, key=lambda x: -target[x]):
    mp = max(probs[t]["champion"], FLOOR)
    ratio = mp / target[t]
    worst = max(worst, abs(math.log(ratio)))
    print(f"{t:<16}{target[t]*100:>8.2f}%{mp*100:>8.2f}%{ratio:>7.2f}")
print(f"worst |log ratio|: {worst:.3f}")

with open("offsets.json", "w") as f:
    json.dump({"offsets": offsets, "target": target, "overround": overround,
               "calibrated": sorted(CAL_SET)}, f, indent=1)

print(f"\nMarket-implied adjustments (what Elo can't see):")
print(f"{'Team':<16}{'Elo':>6}{'Adj':>7}{'EffElo':>8}")
for t in sorted(CAL_SET, key=lambda x: -abs(offsets[x])):
    print(f"{t:<16}{M.ELO[t]:>6}{offsets[t]:>+7.0f}{M.ELO[t]+offsets[t]:>8.0f}")
