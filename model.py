"""Quant engine for 2026 World Cup bolao entry.

Scoring rules being optimized:
- Group match: 3 pts correct result class + 1 pt per exact team goal count.
- Knockout advancement per team per stage (path-independent):
  R32=3, R16=6, QF=10, SF=15, F=20, Champion=+30.
- Knockout scorelines: same 5-pt kernel, only if matchup exactly right.
"""

import numpy as np
from scipy.stats import poisson

NMAX = 9  # goal grid 0..NMAX
LAMBDA_SHOCK = 0.10  # common-shock term of bivariate Poisson (draw inflation)


def biv_poisson_grid(mu_h, mu_a, lam3=LAMBDA_SHOCK):
    """Joint pmf P(H=h, A=a) on [0..NMAX]^2 via common-shock bivariate Poisson.

    H = X1 + X3, A = X2 + X3 with X1~Po(mu_h-lam3), X2~Po(mu_a-lam3), X3~Po(lam3).
    """
    l3 = min(lam3, 0.8 * min(mu_h, mu_a))
    l1, l2 = mu_h - l3, mu_a - l3
    p1 = poisson.pmf(np.arange(NMAX + 1), l1)
    p2 = poisson.pmf(np.arange(NMAX + 1), l2)
    p3 = poisson.pmf(np.arange(NMAX + 1), l3)
    grid = np.zeros((NMAX + 1, NMAX + 1))
    for k in range(NMAX + 1):
        if p3[k] < 1e-12:
            break
        gh = np.zeros(NMAX + 1)
        ga = np.zeros(NMAX + 1)
        gh[k:] = p1[: NMAX + 1 - k]
        ga[k:] = p2[: NMAX + 1 - k]
        grid += p3[k] * np.outer(gh, ga)
    return grid / grid.sum()


def outcome_probs(grid):
    h = np.tril(grid, -1).sum()  # home win (row index = home goals > col)
    d = np.trace(grid)
    a = np.triu(grid, 1).sum()
    return h, d, a


def strip_vig(odds):
    """Proportional vig strip: odds list -> prob list."""
    raw = np.array([1.0 / o for o in odds])
    return raw / raw.sum()


def mus_from_1x2(ph, pd, pa, total_hint=None):
    """Fit (mu_h, mu_a) so the bivariate Poisson matches market 1X2 probs."""
    from scipy.optimize import minimize

    def loss(x):
        mh, ma = np.exp(x)
        gh, gd, ga = outcome_probs(biv_poisson_grid(mh, ma))
        return (
            (np.log(gh / ph)) ** 2 + (np.log(gd / pd)) ** 2 + (np.log(ga / pa)) ** 2
        )

    t = total_hint or 2.5
    # init from win prob skew
    d0 = np.log(max(ph, 1e-3) / max(pa, 1e-3)) * 0.35
    x0 = np.log([max(0.2, (t + d0) / 2), max(0.2, (t - d0) / 2)])
    res = minimize(loss, x0, method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-8})
    return tuple(np.exp(res.x))


def mus_from_elo(elo_h, elo_a, hfa=0.0, base_total=2.35):
    """Map an Elo difference to (mu_h, mu_a).

    p_dnb = 1/(1+10^(-d/400)); choose goal-expectation difference D so the
    Poisson model reproduces p_dnb, with total goals rising with mismatch.
    """
    d = elo_h + hfa - elo_a
    p_dnb = 1.0 / (1.0 + 10 ** (-d / 400.0))

    def solve_D(total):
        lo, hi = -4.0, 4.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            mh, ma = (total + mid) / 2.0, (total - mid) / 2.0
            mh, ma = max(mh, 0.05), max(ma, 0.05)
            gh, _, ga = outcome_probs(biv_poisson_grid(mh, ma))
            if gh / (gh + ga) < p_dnb:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    D = solve_D(base_total)
    total = min(base_total + 0.45 * abs(D), 4.4)
    D = solve_D(total)
    mh, ma = (total + D) / 2.0, (total - D) / 2.0
    return max(mh, 0.08), max(ma, 0.08)


def best_group_pick(grid):
    """Argmax over (h,a) of 3*P(result class) + P(H=h) + P(A=a)."""
    ph, pd, pa = outcome_probs(grid)
    mh = grid.sum(axis=1)  # marginal home goals
    ma = grid.sum(axis=0)
    best, best_ev = None, -1
    for h in range(NMAX + 1):
        for a in range(NMAX + 1):
            cls = ph if h > a else pd if h == a else pa
            ev = 3 * cls + mh[h] + ma[a]
            if ev > best_ev:
                best_ev, best = ev, (h, a)
    ph_, pd_, pa_ = ph, pd, pa
    return best, best_ev, (ph_, pd_, pa_), mh, ma


def ko_120_grid(mu_h, mu_a):
    """Distribution of the 120-minute score: 90' score if decisive, else +ET goals.

    ET goal means scaled to 30 min with a tempo haircut (~0.85).
    """
    g90 = biv_poisson_grid(mu_h, mu_a)
    et_h, et_a = mu_h / 3.0 * 0.85, mu_a / 3.0 * 0.85
    get = biv_poisson_grid(et_h, et_a, lam3=min(0.05, 0.5 * min(et_h, et_a)))
    out = np.zeros_like(g90)
    for h in range(NMAX + 1):
        for a in range(NMAX + 1):
            if h != a:
                out[h, a] += g90[h, a]
    for k in range(NMAX + 1):
        p = g90[k, k]
        if p < 1e-12:
            continue
        lim = NMAX + 1 - k
        out[k:, k:] += p * get[:lim, :lim]
    return out / out.sum()


def best_ko_pick(mu_h, mu_a):
    """Best (h,a) for a knockout match on the 120' distribution + win prob incl pens."""
    grid = ko_120_grid(mu_h, mu_a)
    (h, a), ev, cls, _, _ = best_group_pick(grid)
    ph, pd, pa = cls
    # pens: split draws by relative strength (slight favorite edge)
    fav_edge = 0.5 + 0.08 * np.sign(mu_h - mu_a)
    p_h_through = ph + pd * fav_edge
    return (h, a), ev, (ph, pd, pa), p_h_through


# ---------------- group tables ----------------

def group_table(teams, results, elo):
    """results: list of (home, away, gh, ga). Returns ordered team list.

    Tiebreak: pts, GD, GF, then Elo (proxy for drawing of lots / fair play).
    """
    st = {t: [0, 0, 0] for t in teams}  # pts, gd, gf
    for h, a, gh, ga in results:
        st[h][1] += gh - ga
        st[h][2] += gh
        st[a][1] += ga - gh
        st[a][2] += ga
        if gh > ga:
            st[h][0] += 3
        elif gh < ga:
            st[a][0] += 3
        else:
            st[h][0] += 1
            st[a][0] += 1
    order = sorted(teams, key=lambda t: (-st[t][0], -st[t][1], -st[t][2], -elo[t]))
    return order, st
