"""Full bolao optimization pipeline. Produces REPORT.md."""

import numpy as np

from model import (
    biv_poisson_grid, outcome_probs, strip_vig, mus_from_1x2, mus_from_elo,
    best_group_pick, ko_120_grid, NMAX, group_table,
)
from data_elo import ELO
from data_odds import MATCH_1X2, american_to_decimal
from data_fixtures import GROUPS, FIXTURES, R32, THIRD_ELIG, R16, QF, SF

rng = np.random.default_rng(7)
N = 240_000

# Host bonus reconciles Elo to June-2026 market quotes (1X2 + group winner odds)
HOST_BONUS = {"Mexico": 100, "USA": 195, "Canada": 80}
# Targeted reconciliation where Elo ordering contradicts quoted group-winner
# markets (Germany -270 vs Ecuador +350; Egypt +333 vs Iran +550)
MARKET_ADJ = {"Germany": 45, "Ecuador": -65, "Egypt": 55, "Iran": -25}
RATING = {t: ELO[t] + HOST_BONUS.get(t, 0) + MARKET_ADJ.get(t, 0)
          for g in GROUPS for t in GROUPS[g]}

TEAMS = [t for g in "ABCDEFGHIJKL" for t in GROUPS[g]]
TIDX = {t: i for i, t in enumerate(TEAMS)}
ARG = TIDX["Argentina"]

# ---------- match goal expectations ----------
_elo_memo = {}


def elo_mus(rh, ra, base_total=2.35):
    key = (int(round((rh - ra) / 5.0)), base_total)
    if key not in _elo_memo:
        _elo_memo[key] = mus_from_elo(key[0] * 5.0, 0.0, base_total=base_total)
    return _elo_memo[key]


MARKET_MUS = {}
for (h, a), (oh, od, oa) in MATCH_1X2.items():
    probs = strip_vig([american_to_decimal(o) for o in (oh, od, oa)])
    MARKET_MUS[(h, a)] = mus_from_1x2(*probs, total_hint=2.4)


def group_match_mus(h, a):
    if (h, a) in MARKET_MUS:
        return MARKET_MUS[(h, a)]
    return elo_mus(RATING[h], RATING[a])


# ---------- group picks ----------
group_picks = {}   # (h,a) -> (gh,ga)
pick_detail = {}   # (h,a) -> (ev, (pH,pD,pA))
grids = {}
for g in "ABCDEFGHIJKL":
    for h, a in FIXTURES[g]:
        grid = biv_poisson_grid(*group_match_mus(h, a))
        grids[(h, a)] = grid
        (gh, ga), ev, cls, _, _ = best_group_pick(grid)
        group_picks[(h, a)] = (gh, ga)
        pick_detail[(h, a)] = (ev, cls)

# ---------- my predicted tables ----------
my_tables = {}
for g in "ABCDEFGHIJKL":
    results = [(h, a, *group_picks[(h, a)]) for h, a in FIXTURES[g]]
    order, st = group_table(GROUPS[g], results, RATING)
    my_tables[g] = (order, st)

my_thirds = {g: my_tables[g][0][2] for g in "ABCDEFGHIJKL"}


def third_sort_key(g):
    t = my_thirds[g]
    st = my_tables[g][1][t]
    return (-st[0], -st[1], -st[2], -RATING[t])


third_rank = sorted("ABCDEFGHIJKL", key=third_sort_key)
my_adv_groups = third_rank[:8]


def assign_thirds(groups8):
    """Feasible perfect matching of 8 advancing third-place groups to slots."""
    groups8 = set(groups8)
    slots = sorted(THIRD_ELIG, key=lambda s: sum(g in THIRD_ELIG[s] for g in groups8))

    def bt(i, used, acc):
        if i == len(slots):
            return acc
        s = slots[i]
        for g in sorted(groups8 - used):
            if g in THIRD_ELIG[s]:
                r = bt(i + 1, used | {g}, {**acc, s: g})
                if r:
                    return r
        return None

    return bt(0, frozenset(), {})


my_assign = assign_thirds(my_adv_groups)
assert my_assign, "no feasible third-place assignment"


def resolve_slot(slot, tables, thirds_assign):
    if slot.startswith("T"):
        g = thirds_assign[int(slot[1:])]
        return tables[g][0][2]
    g, pos = slot[0], int(slot[1])
    return tables[g][0][pos - 1]


my_r32 = {m: (resolve_slot(s1, my_tables, my_assign), resolve_slot(s2, my_tables, my_assign))
          for m, (s1, s2) in R32.items()}

# ---------- KO win-prob matrix (incl ET + pens) ----------
_ko_memo = {}


def ko_through_prob(r1, r2):
    """P(team1 advances) over 120' + penalties."""
    key = int(round((r1 - r2) / 5.0))
    if key not in _ko_memo:
        mh, ma = elo_mus(key * 5.0, 0.0, base_total=2.2)
        grid = ko_120_grid(mh, ma)
        ph, pd, pa = outcome_probs(grid)
        _ko_memo[key] = (ph, pd)
    ph, pd = _ko_memo[key]
    pens = 0.5 + np.clip((r1 - r2) * 0.0004, -0.08, 0.08)
    return ph + pd * pens


W = np.zeros((48, 48))
for i, ti in enumerate(TEAMS):
    for j, tj in enumerate(TEAMS):
        if i != j:
            W[i, j] = ko_through_prob(RATING[ti], RATING[tj])

# ---------- Monte Carlo, conditioned on Argentina champion ----------
print("simulating...")
ELO_RANK = {t: r for r, t in enumerate(sorted(TEAMS, key=lambda t: -RATING[t]))}

# sample all 72 group matches
samples = {}
for (h, a), grid in grids.items():
    flat = grid.ravel()
    cdf = np.cumsum(flat)
    idx = np.searchsorted(cdf, rng.random(N))
    samples[(h, a)] = (idx // (NMAX + 1), idx % (NMAX + 1))

winners, runners, thirds_t, thirds_key = {}, {}, {}, {}
for g in "ABCDEFGHIJKL":
    teams = GROUPS[g]
    loc = {t: k for k, t in enumerate(teams)}
    pts = np.zeros((N, 4), np.int64)
    gd = np.zeros((N, 4), np.int64)
    gf = np.zeros((N, 4), np.int64)
    for h, a in FIXTURES[g]:
        hs, as_ = samples[(h, a)]
        i, j = loc[h], loc[a]
        hw = hs > as_
        dr = hs == as_
        pts[:, i] += 3 * hw + dr
        pts[:, j] += 3 * (~hw & ~dr) + dr
        gd[:, i] += hs - as_
        gd[:, j] += as_ - hs
        gf[:, i] += hs
        gf[:, j] += as_
    tie = np.array([63 - ELO_RANK[t] for t in teams])
    key = ((pts * 64 + gd + 32) * 64 + gf) * 64 + tie
    order = np.argsort(-key, axis=1, kind="stable")
    gidx = np.array([TIDX[t] for t in teams])
    winners[g] = gidx[order[:, 0]]
    runners[g] = gidx[order[:, 1]]
    thirds_t[g] = gidx[order[:, 2]]
    thirds_key[g] = np.take_along_axis(key, order[:, 2:3], axis=1)[:, 0]

letters = list("ABCDEFGHIJKL")
tk = np.stack([thirds_key[g] for g in letters], axis=1)
ord12 = np.argsort(-tk, axis=1, kind="stable")
adv = np.zeros((N, 12), bool)
np.put_along_axis(adv, ord12[:, :8], True, axis=1)
mask_id = adv @ (1 << np.arange(12))

slot_team = {s: np.zeros(N, np.int64) for s in THIRD_ELIG}
_assign_memo = {}
for m in np.unique(mask_id):
    gs = frozenset(letters[b] for b in range(12) if m & (1 << b))
    if gs not in _assign_memo:
        _assign_memo[gs] = assign_thirds(gs)
    asg = _assign_memo[gs]
    sel = mask_id == m
    for s, g in asg.items():
        slot_team[s][sel] = thirds_t[g][sel]


def sim_slot(slot):
    if slot.startswith("T"):
        return slot_team[int(slot[1:])]
    g, pos = slot[0], int(slot[1])
    return winners[g] if pos == 1 else runners[g]


def play(t1, t2):
    p = W[t1, t2]
    return np.where(rng.random(N) < p, t1, t2)


w32 = {m: play(sim_slot(s1), sim_slot(s2)) for m, (s1, s2) in R32.items()}
w16 = {m: play(w32[a], w32[b]) for m, (a, b) in R16.items()}
wqf = {m: play(w16[a], w16[b]) for m, (a, b) in QF.items()}
wsf = {m: play(wqf[a], wqf[b]) for m, (a, b) in SF.items()}
champ = play(wsf[101], wsf[102])

cond = champ == ARG
nc = cond.sum()
print(f"P(Argentina champion) = {cond.mean():.3%}  ({nc} conditional sims)")


def stage_probs(arrs):
    cnt = np.zeros(48)
    for a in arrs:
        cnt += np.bincount(a[cond], minlength=48)
    return cnt / nc


P = {
    "R32": stage_probs([sim_slot(s) for m in R32 for s in R32[m]]),
    "R16": stage_probs(list(w32.values())),
    "QF": stage_probs(list(w16.values())),
    "SF": stage_probs(list(wqf.values())),
    "F": stage_probs(list(wsf.values())),
    "C": stage_probs([champ]),
}

# ---------- bracket DP on my predicted bracket ----------
VNEXT = {"R32": ("R16", 6), "R16": ("QF", 10), "QF": ("SF", 15), "SF": ("F", 20)}


def g_r32(m):
    a, b = my_r32[m]
    return {t: 6 * P["R16"][TIDX[t]] for t in (a, b)}


def combine(gl, gr, stage_val, stage_key):
    out = {}
    ml, mr = max(gl.values()), max(gr.values())
    for t, v in gl.items():
        out[t] = v + mr + stage_val * P[stage_key][TIDX[t]]
    for t, v in gr.items():
        out[t] = max(out.get(t, -1), v + ml + stage_val * P[stage_key][TIDX[t]])
    return out


g32 = {m: g_r32(m) for m in R32}
g16 = {m: combine(g32[a], g32[b], 10, "QF") for m, (a, b) in R16.items()}
gqf = {m: combine(g16[a], g16[b], 15, "SF") for m, (a, b) in QF.items()}
gsf = {m: combine(gqf[a], gqf[b], 20, "F") for m, (a, b) in SF.items()}

assert "Argentina" in gsf[102], "Argentina not available in its bracket half"
other_fin = max(gsf[101], key=gsf[101].get)
total_ko_ev = gsf[101][other_fin] + gsf[102]["Argentina"] + 30 * P["C"][ARG]


def choose(m, forced):
    """Return winner of match m (forced if given), recording picks."""
    if m in R32:
        a, b = my_r32[m]
        if forced:
            w = forced
        else:
            w = max(g32[m], key=g32[m].get)
        bracket_pick[m] = (a, b, w)
        return w
    rnd = R16 if m in R16 else QF if m in QF else SF
    ca, cb = rnd[m]
    gl = g32 if m in R16 else g16 if m in QF else gqf
    if forced:
        w = forced
        side = ca if forced in gl[ca] else cb
        wa = choose(ca, forced if side == ca else None)
        wb = choose(cb, forced if side == cb else None)
    else:
        gthis = (g16 if m in R16 else gqf if m in QF else gsf)[m]
        w = max(gthis, key=gthis.get)
        side = ca if w in gl[ca] else cb
        wa = choose(ca, w if side == ca else None)
        wb = choose(cb, w if side == cb else None)
    bracket_pick[m] = (wa, wb, w)
    return w


bracket_pick = {}
fin_a = choose(101, None)          # best half without Argentina
fin_b = choose(102, "Argentina")   # Argentina forced through its half
bracket_pick[104] = (fin_a, fin_b, "Argentina")

# ---------- KO scoreline picks ----------

def ko_score_pick(t1, t2, winner):
    """Best (h,a) on 120' distribution s.t. `winner` wins or draws (pens)."""
    mh, ma = elo_mus(RATING[t1], RATING[t2], base_total=2.2)
    grid = ko_120_grid(mh, ma)
    ph, pd, pa = outcome_probs(grid)
    mhg = grid.sum(axis=1)
    mag = grid.sum(axis=0)
    best, best_ev = None, -1
    for h in range(NMAX + 1):
        for a in range(NMAX + 1):
            if winner == t1 and h < a:
                continue
            if winner == t2 and h > a:
                continue
            cls = ph if h > a else pd if h == a else pa
            ev = 3 * cls + mhg[h] + mag[a]
            if ev > best_ev:
                best_ev, best = ev, (h, a)
    return best, best_ev


ko_scores = {}
for m, (t1, t2, w) in sorted(bracket_pick.items()):
    ko_scores[m] = ko_score_pick(t1, t2, w)

# third-place match: losers of my two semifinals
sl1 = [t for t in bracket_pick[101][:2] if t != bracket_pick[101][2]][0]
sl2 = [t for t in bracket_pick[102][:2] if t != bracket_pick[102][2]][0]
w3 = sl1 if W[TIDX[sl1], TIDX[sl2]] >= 0.5 else sl2
third_place = (sl1, sl2, w3, ko_score_pick(sl1, sl2, w3))

# ---------- report ----------
out = []
out.append("# 2026 World Cup Bolao Entry (Argentina champion)\n")
out.append(f"Model: bivariate Poisson calibrated to June 10-11 2026 market odds; "
           f"Elo (eloratings.net 2026-06-11) + host adj for unquoted matches. "
           f"{N} sims; P(ARG champ)={cond.mean():.1%}; conditional probs below.\n")

out.append("\n## Group match picks\n")
for g in "ABCDEFGHIJKL":
    out.append(f"\n### Group {g}\n")
    for k, (h, a) in enumerate(FIXTURES[g]):
        gh, ga = group_picks[(h, a)]
        ev, (ph, pd, pa) = pick_detail[(h, a)]
        out.append(f"- MD{k // 2 + 1}: **{h} {gh}-{ga} {a}**  "
                   f"(EV {ev:.2f} | 1X2 {ph:.0%}/{pd:.0%}/{pa:.0%})\n")
    order, st = my_tables[g]
    out.append(f"\n  Table: " + " | ".join(
        f"{i+1}. {t} {st[t][0]}pts GD{st[t][1]:+d}" for i, t in enumerate(order)) + "\n")

out.append("\n## Third-place ranking (best 8 advance)\n")
for r, g in enumerate(third_rank):
    t = my_thirds[g]
    st = my_tables[g][1][t]
    tag = "ADV" if g in my_adv_groups else "out"
    out.append(f"{r+1}. {t} ({g}) {st[0]}pts GD{st[1]:+d} GF{st[2]} [{tag}]\n")
out.append("\nSlot assignment: " + ", ".join(
    f"M{s}<-{my_assign[s]}3 {my_thirds[my_assign[s]]}" for s in sorted(my_assign)) + "\n")

STAGE_OF = {}
for m in R32:
    STAGE_OF[m] = "R16"
for m in R16:
    STAGE_OF[m] = "QF"
for m in QF:
    STAGE_OF[m] = "SF"
for m in SF:
    STAGE_OF[m] = "F"
STAGE_OF[104] = "C"

NAME = {**{m: "R32" for m in R32}, **{m: "R16" for m in R16},
        **{m: "QF" for m in QF}, **{m: "SF" for m in SF}, 104: "FINAL"}

out.append("\n## Knockout bracket\n")
for m in sorted(bracket_pick):
    t1, t2, w = bracket_pick[m]
    (h, a), ev = ko_scores[m]
    pen = "" if h != a else f" ({w} on pens)"
    stage = STAGE_OF[m]
    pw = P[stage][TIDX[w]]
    out.append(f"- M{m} [{NAME[m]}]: **{t1} {h}-{a} {t2}**{pen} -> {w} "
               f"(P reach {stage}|ARGC = {pw:.1%}, score EV {ev:.2f})\n")
sl1, sl2, w3, ((h3, a3), ev3) = third_place
pen3 = "" if h3 != a3 else f" ({w3} on pens)"
out.append(f"- M103 [3rd place]: **{sl1} {h3}-{a3} {sl2}**{pen3} -> {w3} (EV {ev3:.2f})\n")

out.append(f"\nKnockout advancement EV (conditional): {total_ko_ev:.1f} pts\n")

out.append("\n## Conditional reach probabilities of picked teams\n")
my_32 = sorted({t for m in my_r32 for t in my_r32[m]}, key=lambda t: -P['R16'][TIDX[t]])
for t in my_32:
    i = TIDX[t]
    out.append(f"- {t}: R32 {P['R32'][i]:.0%}, R16 {P['R16'][i]:.0%}, QF {P['QF'][i]:.0%}, "
               f"SF {P['SF'][i]:.0%}, F {P['F'][i]:.0%}, C {P['C'][i]:.0%}\n")

with open("REPORT.md", "w") as f:
    f.write("".join(out))
print("wrote REPORT.md")

ev_groups = sum(pick_detail[k][0] for k in pick_detail)
print(f"Group-stage scoreline EV: {ev_groups:.1f} pts over 72 matches")
print(f"KO advancement EV (cond): {total_ko_ev:.1f}")
