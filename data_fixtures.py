"""2026 World Cup groups, fixtures, and official knockout slotting (FIFA)."""

GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# (home, away) in matchday order 1,1,2,2,3,3
FIXTURES = {
    "A": [("Mexico", "South Africa"), ("South Korea", "Czechia"),
          ("Czechia", "South Africa"), ("Mexico", "South Korea"),
          ("Czechia", "Mexico"), ("South Africa", "South Korea")],
    "B": [("Canada", "Bosnia"), ("Qatar", "Switzerland"),
          ("Switzerland", "Bosnia"), ("Canada", "Qatar"),
          ("Switzerland", "Canada"), ("Bosnia", "Qatar")],
    "C": [("Brazil", "Morocco"), ("Haiti", "Scotland"),
          ("Scotland", "Morocco"), ("Brazil", "Haiti"),
          ("Scotland", "Brazil"), ("Morocco", "Haiti")],
    "D": [("USA", "Paraguay"), ("Australia", "Turkey"),
          ("USA", "Australia"), ("Turkey", "Paraguay"),
          ("Turkey", "USA"), ("Paraguay", "Australia")],
    "E": [("Germany", "Curacao"), ("Ivory Coast", "Ecuador"),
          ("Germany", "Ivory Coast"), ("Ecuador", "Curacao"),
          ("Curacao", "Ivory Coast"), ("Ecuador", "Germany")],
    "F": [("Netherlands", "Japan"), ("Sweden", "Tunisia"),
          ("Netherlands", "Sweden"), ("Tunisia", "Japan"),
          ("Japan", "Sweden"), ("Tunisia", "Netherlands")],
    "G": [("Belgium", "Egypt"), ("Iran", "New Zealand"),
          ("Belgium", "Iran"), ("New Zealand", "Egypt"),
          ("Egypt", "Iran"), ("New Zealand", "Belgium")],
    "H": [("Spain", "Cape Verde"), ("Saudi Arabia", "Uruguay"),
          ("Spain", "Saudi Arabia"), ("Uruguay", "Cape Verde"),
          ("Cape Verde", "Saudi Arabia"), ("Uruguay", "Spain")],
    "I": [("France", "Senegal"), ("Iraq", "Norway"),
          ("France", "Iraq"), ("Norway", "Senegal"),
          ("Norway", "France"), ("Senegal", "Iraq")],
    "J": [("Argentina", "Algeria"), ("Austria", "Jordan"),
          ("Argentina", "Austria"), ("Jordan", "Algeria"),
          ("Jordan", "Argentina"), ("Algeria", "Austria")],
    "K": [("Portugal", "DR Congo"), ("Uzbekistan", "Colombia"),
          ("Portugal", "Uzbekistan"), ("Colombia", "DR Congo"),
          ("Colombia", "Portugal"), ("DR Congo", "Uzbekistan")],
    "L": [("England", "Croatia"), ("Ghana", "Panama"),
          ("England", "Ghana"), ("Panama", "Croatia"),
          ("Panama", "England"), ("Croatia", "Ghana")],
}

# Round of 32: match number -> (slot1, slot2); "X1"/"X2" = group X winner/runner-up,
# "T74" = third-placed team assigned to that match.
R32 = {
    73: ("A2", "B2"), 74: ("E1", "T74"), 75: ("F1", "C2"), 76: ("C1", "F2"),
    77: ("I1", "T77"), 78: ("E2", "I2"), 79: ("A1", "T79"), 80: ("L1", "T80"),
    81: ("D1", "T81"), 82: ("G1", "T82"), 83: ("K2", "L2"), 84: ("H1", "J2"),
    85: ("B1", "T85"), 86: ("J1", "H2"), 87: ("K1", "T87"), 88: ("D2", "G2"),
}

# Eligible source groups for each third-place slot (FIFA schedule)
THIRD_ELIG = {
    74: "ABCDF", 77: "CDFGH", 79: "CEFHI", 80: "EHIJK",
    81: "BEFIJ", 82: "AEHIJ", 85: "EFGIJ", 87: "DEIJL",
}

R16 = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
       93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87)}
QF = {97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96)}
SF = {101: (97, 98), 102: (99, 100)}
FINAL = {104: (101, 102)}
