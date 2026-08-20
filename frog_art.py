"""
The frog's pixel art, and nothing else.

Kept in its own module with no imports so that both the app and the icon
generator can share it. frog.py used to read the art out of generate_icon.py,
which imports Pillow, and that pulled the whole imaging library into the
shipped .exe and added six megabytes to it for no reason.

Public interface:
    ART, ART_W, ART_H, PALETTE
"""

PALETTE = {
    "K": (26, 26, 26, 255),        # outline
    "L": (124, 207, 86, 255),      # body, lit
    "D": (74, 143, 54, 255),       # body, shaded
    "E": (32, 78, 30, 255),        # eyes and mouth
    "C": (247, 220, 150, 255),     # belly
    ".": (0, 0, 0, 0),             # transparent
}

# 16 wide, 14 tall. A squat dome with the eyes on top, which keeps the
# silhouette readable even when the whole frog is 16 pixels across. Widening
# the grid would allow more detail but would stop fitting a 16 pixel icon at
# one pixel per cell, which is the thing that keeps it sharp.
ART = [
    "....KK....KK....",
    "...KLLK..KLLK...",
    "..KLEELKKLEELK..",
    "..KLLLLLLLLLLK..",
    ".KLLLLLLLLLLLLK.",
    ".KLLLLEELLLLLLK.",
    "KLLLLLLLLLLLLLLK",
    "KLLLLLLCCLLLLLLK",
    "KLLDLLLCCLLLLLLK",
    "KLDDLLLCCLLLLLLK",
    "KLLDLLLCCLLLLDLK",
    "KLLLLLLCCLLLLLLK",
    "KDDDDDDDDDDDDDDK",
    ".KKKKKKKKKKKKKK.",
]

ART_W = len(ART[0])
ART_H = len(ART)

# A row of the wrong length would silently shift the whole drawing.
assert all(len(row) == ART_W for row in ART), "every ART row must be the same width"
