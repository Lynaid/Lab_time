# Symbols:
# R = Rock (solid)
# C = Crate (breakable)
# S = Spikes (trap)
# . = empty

# Design notes:
# - All layouts are 10x9.
# - Center area is kept more open to avoid soft-locks.
# - Layouts assume Room already blocks spawns in door corridors.

LAYOUTS_NORMAL = [
    # "Four pillars + center"
    [
        "..R....R..",
        "..........",
        "...C..C...",
        "..........",
        "....RR....",
        "..........",
        "...C..C...",
        "..........",
        "..R....R..",
    ],
    # "Rift" — two peninsulas and a narrow diagonal
    [
        "RRR....RRR",
        "R........R",
        "R..RRRR..R",
        "...R..R...",
        "....SS....",
        "...R..R...",
        "R..RRRR..R",
        "R........R",
        "RRR....RRR",
    ],
    # "Rings" — outer stone + inner spikes
    [
        ".RR....RR.",
        "R........R",
        "R..SSSS..R",
        "....C.C...",
        "....C.C...",
        "....C.C...",
        "R..SSSS..R",
        "R........R",
        ".RR....RR.",
    ],
    # "Arcs" — two half-rings
    [
        "..RRRRRR..",
        ".R......R.",
        "R..C..C..R",
        "R........R",
        "....SS....",
        "R........R",
        "R..C..C..R",
        ".R......R.",
        "..RRRRRR..",
    ],
    # "Cross with traps"
    [
        "....R.....",
        "....R.....",
        "..C.R.C...",
        "RRR.R.RRRR",
        "....S.....",
        "RRR.R.RRRR",
        "..C.R.C...",
        "....R.....",
        "....R.....",
    ],
    # "Snake 2" — softer, more varied paths
    [
        "RRRRRRRRR.",
        ".........R",
        "RRRRRRR..R",
        "R.........",
        "R..RRRRRRR",
        "R.........",
        "RRRRRRR..R",
        ".........R",
        ".RRRRRRRRR",
    ],
    # "Checkerboard with gaps"
    [
        "..........",
        ".R.R.R.R..",
        "..R.R.R.R.",
        ".R.R...R..",
        "..R...R.R.",
        ".R.R...R..",
        "..R.R.R.R.",
        ".R.R.R.R..",
        "..........",
    ],
    # "Two courtyards" — two safe circles, danger between them
    [
        "RR......RR",
        "R........R",
        "R..C..C..R",
        "...SSSS...",
        "...S..S...",
        "...SSSS...",
        "R..C..C..R",
        "R........R",
        "RR......RR",
    ],
    # "Pressure lines" — 3 obstacle rows, center stays open
    [
        "..........",
        "RRR....RRR",
        "...C..C...",
        "..........",
        "..SS..SS..",
        "..........",
        "...C..C...",
        "RRR....RRR",
        "..........",
    ],
    # "Broken arena" — many crates for player to clear paths
    [
        "..C..C..C.",
        "..........",
        ".C..RR..C.",
        "....SS....",
        ".C..RR..C.",
        "....SS....",
        ".C......C.",
        "..........",
        ".C..C..C..",
    ],
    # "Pockets" — safe corners, dangerous middle
    [
        "RR......RR",
        "R..C..C..R",
        "..........",
        "...SSSS...",
        "...S..S...",
        "...SSSS...",
        "..........",
        "R..C..C..R",
        "RR......RR",
    ],
    # "Honeycomb" — dense rocks but many routes
    [
        "..........",
        "..R.R.R...",
        ".R...R..R.",
        "..R.R.R...",
        ".R...R..R.",
        "..R.R.R...",
        ".R..R...R.",
        "...R.R.R..",
        "..........",
    ],
]

LAYOUTS_BOSS = [
    # "Arena — 4 pillars + side traps"
    [
        "..R....R..",
        "..........",
        ".S......S.",
        "....CC....",
        "..R....R..",
        "....CC....",
        ".S......S.",
        "..........",
        "..R....R..",
    ],
    # "Ring with gaps" — circle with passages
    [
        "..RRRRRR..",
        ".R......R.",
        "R..SSSS..R",
        "R..S..S..R",
        "....CC....",
        "R..S..S..R",
        "R..SSSS..R",
        ".R......R.",
        "..RRRRRR..",
    ],
    # "Four quadrants — reinforced"
    [
        "RRR....RRR",
        "R.S....S.R",
        "R..C..C..R",
        "..........",
        "...RRRR...",
        "..........",
        "R..C..C..R",
        "R.S....S.R",
        "RRR....RRR",
    ],
    # "Diagonal gates" — forces position changes
    [
        "R........R",
        ".R......R.",
        "..R....R..",
        "...SSSS...",
        "....CC....",
        "...SSSS...",
        "..R....R..",
        ".R......R.",
        "R........R",
    ],
    # "Islands" — obstacle clusters for cover
    [
        "..........",
        "..RR..RR..",
        "..RR..RR..",
        "....SS....",
        "..........",
        "....SS....",
        "..RR..RR..",
        "..RR..RR..",
        "..........",
    ],
]

LAYOUTS_SECRET = [
    # "Trap room" — checkerboard spikes + crates
    [
        "S.S.S.S.S.",
        ".C......C.",
        "S.S.S.S.S.",
        "..........",
        "..C....C..",
        "..........",
        "S.S.S.S.S.",
        ".C......C.",
        "S.S.S.S.S.",
    ],
    # "Minefield — walkable paths"
    [
        "S.S.S.S.S.",
        "..........",
        ".S.S.S.S..",
        "..........",
        "S.S.S.S.S.",
        "..........",
        "..S.S.S.S.",
        "..........",
        "S.S.S.S.S.",
    ],
    # "False safety" — safe center, dangerous bottom
    [
        "..RRRRRR..",
        ".R......R.",
        "R........R",
        "R..C..C..R",
        "R........R",
        ".R......R.",
        "..RRRRRR..",
        "..........",
        "S.S.S.S.S.",
    ],
    # "Vice" — narrow passage, spikes on sides
    [
        "SS......SS",
        "SS......SS",
        "..C....C..",
        "..R....R..",
        "..........",
        "..R....R..",
        "..C....C..",
        "SS......SS",
        "SS......SS",
    ],
]

LAYOUTS_SHOP = [
    # "Counters — improved"
    [
        "..........",
        "...R..R...",
        "..C....C..",
        "...R..R...",
        "..........",
        "...R..R...",
        "..C....C..",
        "...R..R...",
        "..........",
    ],
    # "Islands — tidier"
    [
        "..........",
        "..RR....RR",
        "..RR....RR",
        "..........",
        "...C..C...",
        "..........",
        "RR....RR..",
        "RR....RR..",
        "..........",
    ],
    # "Showcase — wider aisles"
    [
        "RRR....RRR",
        "R........R",
        "R..C..C..R",
        "R........R",
        "R..C..C..R",
        "R........R",
        "R..C..C..R",
        "R........R",
        "RRR....RRR",
    ],
    # "Checkout" — central counter + side displays
    [
        "..........",
        "..RR..RR..",
        "..C....C..",
        "..........",
        "...RRRR...",
        "..........",
        "..C....C..",
        "..RR..RR..",
        "..........",
    ],
]

LAYOUTS_TREASURE = [
    # "Breather" — empty
    [
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
        "..........",
    ],
    # "Symmetry — 4 pillars"
    [
        "..........",
        "...R..R...",
        "..........",
        "..R....R..",
        "..........",
        "..R....R..",
        "..........",
        "...R..R...",
        "..........",
    ],
    # "Key" — soft composition around center
    [
        "..........",
        "..RRRR....",
        "..R..R....",
        "..R..R....",
        "..RRRR....",
        "....C.....",
        "..........",
        ".....C....",
        "..........",
    ],
    # "Altar" — clean center + decorative corners
    [
        "R........R",
        "..........",
        "..C....C..",
        "..........",
        "..........",
        "..........",
        "..C....C..",
        "..........",
        "R........R",
    ],
]