"""
The frog, for the window.

Shares its artwork with generate_icon.py so the app and its icon are the same
character. Frames are built with tkinter's own PhotoImage.put rather than
Pillow, which keeps Pillow a build-only dependency and the shipped .exe smaller.

Every frame is the same canvas size, with the frog drawn higher or lower inside
it. Swapping frames then reads as the frog leaving the ground rather than the
label itself resizing, which would shove the rest of the header around.

Public interface:
    FRAMES                      -- frame names
    frame_size(scale)           -> (width, height) in pixels
    build_frame(scale, frame)   -> tk.PhotoImage
"""

import tkinter as tk

from frog_art import ART, ART_H, ART_W, PALETTE

FRAMES = ("idle", "hop", "happy")

LIFT = 3                                  # art pixels of air at the top of a hop

_BLINK_ROW = "..KLDDLKKLDDLK.."           # eyes squeezed shut mid-jump
_SMILE_ROW = ".KLLLLDDLLLLLLK."           # mouth widened into a grin


def _rows(frame: str) -> list[str]:
    rows = list(ART)
    if frame == "hop":
        rows[2] = _BLINK_ROW
    elif frame == "happy":
        rows[5] = _SMILE_ROW
    return rows


def _hex(rgba: tuple[int, int, int, int]) -> str:
    return "#%02x%02x%02x" % rgba[:3]


def frame_size(scale: int) -> tuple[int, int]:
    return ART_W * scale, (ART_H + LIFT) * scale


def build_frame(scale: int, frame: str = "idle", background: str = "#ffffff") -> tk.PhotoImage:
    """Return one frame as a PhotoImage, scaled by a whole number of pixels.

    tkinter's PhotoImage has no usable alpha, so transparent art pixels are
    painted in the widget's own background colour. Whole-number scaling keeps
    every art pixel a hard square, which is the point of drawing pixel art.
    """
    width, height = frame_size(scale)
    img = tk.PhotoImage(width=width, height=height)

    # Fill the whole canvas first, so the air above or below the frog matches
    # the header rather than showing through as grey.
    img.put(background, to=(0, 0, width, height))

    # Mid-hop the frog sits at the top of the canvas; otherwise it rests at the
    # bottom, so the two frames differ by LIFT pixels of height.
    top = 0 if frame == "hop" else LIFT * scale

    # One put() per art row. Painting pixel by pixel is visibly slow in tkinter,
    # while a row of colour runs is a single cheap call.
    for y, row in enumerate(_rows(frame)):
        line = []
        for ch in row:
            rgba = PALETTE[ch]
            colour = background if rgba[3] == 0 else _hex(rgba)
            line.extend([colour] * scale)
        block = "{" + " ".join(line) + "}"
        img.put(" ".join([block] * scale), to=(0, top + y * scale))

    return img
