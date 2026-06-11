"""Market odds snapshot, June 10-11 2026 (BetMGM/FanDuel/Bet365 via ESPN/FOX/CBS/etc).

American odds unless noted. Collected by research agent; see PR/commit notes.
"""

# Outright champion (FanDuel June 10 primary, BetMGM cross-check)
OUTRIGHT = {
    "Spain": 462, "France": 500, "England": 675, "Brazil": 850,
    "Portugal": 825, "Argentina": 950, "Germany": 1350, "Netherlands": 1800,
    "Belgium": 2200, "Colombia": 3300, "Norway": 3300, "Morocco": 5000,
    "Japan": 5000, "USA": 5250, "Uruguay": 5500, "Mexico": 6000,
    "Ecuador": 6600, "Switzerland": 6500, "Croatia": 7500, "Turkey": 7500,
    "Canada": 15000, "Senegal": 17500,
}

# To reach the final (FanDuel June 10)
REACH_FINAL = {
    "Spain": 240, "France": 280, "England": 340, "Portugal": 410,
    "Brazil": 440, "Argentina": 500, "Germany": 650, "Netherlands": 750,
}

# Group winner odds (best available quotes; fractional converted)
GROUP_WINNER = {
    "A": {"Mexico": -150, "South Korea": 400, "Czechia": 400, "South Africa": 1200},
    "B": {"Switzerland": -125, "Canada": 130},  # Canada ~co-fav, est
    "C": {"Brazil": -330},
    "D": {"USA": 138, "Turkey": 175, "Paraguay": 400, "Australia": 800},
    "E": {"Germany": -270, "Ecuador": 350, "Ivory Coast": 625, "Curacao": 18900},
    "F": {"Netherlands": -125},
    "G": {"Belgium": -225, "Egypt": 333, "Iran": 550},
    "H": {"Spain": -425},
    "I": {"France": -210},
    "J": {"Argentina": -300, "Austria": 450},
    "K": {"Portugal": -250, "Colombia": 250},
    "L": {"England": -275, "Croatia": 350, "Ghana": 1000, "Panama": 4000},
}

# Matchday-1 1X2 odds (home, draw, away) American
MATCH_1X2 = {
    ("Mexico", "South Africa"): (-260, 360, 800),
    ("South Korea", "Czechia"): (163, 210, 185),
    ("Canada", "Bosnia"): (-125, 280, 320),
    ("USA", "Paraguay"): (-103, 255, 295),
    ("Qatar", "Switzerland"): (1000, 500, -360),
    ("Brazil", "Morocco"): (-175, 300, 425),
    ("Haiti", "Scotland"): (650, 300, -195),
    ("Netherlands", "Japan"): (105, 250, 260),
}


def american_to_decimal(a):
    return 1 + (a / 100.0 if a > 0 else 100.0 / -a)
