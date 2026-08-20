"""
One-time generator for app_icon.ico. A pixel-art frog.

The frog is a deliberate answer to a real constraint. A taskbar icon is 24
physical pixels wide, and smoothly drawn artwork at that size smears into an
unreadable blob no matter how carefully it is composed. Pixel art is authored
on the pixel grid instead of fighting it, scaled up by whole numbers with
nearest-neighbour so every pixel stays a hard square. It reads perfectly at 16
pixels and still looks intentional at 256.

It is deliberately generic art rather than any organisation's logo, so a
fork of this tool carries no branding it has no right to.

Run once, or whenever you want to tweak it:
    .venv/Scripts/python.exe generate_icon.py

Requires Pillow, which is build-only. The shipped app never imports it, since
PyInstaller and tkinter both just read the resulting .ico file.
"""

from PIL import Image

from frog_art import ART, ART_H, ART_W, PALETTE

ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]


def _base() -> Image.Image:
    """The frog at exactly one pixel per art cell."""
    img = Image.new("RGBA", (ART_W, ART_H), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(ART):
        for x, ch in enumerate(row):
            px[x, y] = PALETTE[ch]
    return img


def build_icon(size: int = 256) -> Image.Image:
    """Render the icon at one size, scaled by a whole number of pixels.

    Scaling by a whole number with NEAREST is the entire point: it keeps every
    art pixel a crisp square. Any leftover space becomes padding rather than a
    fractional scale, which would blur the edges straight back.
    """
    cell = max(1, min(size // ART_W, size // ART_H))
    art = _base().resize((ART_W * cell, ART_H * cell), Image.NEAREST)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
    return canvas


def main() -> None:
    images = [build_icon(n) for n in ICO_SIZES]
    images[-1].save("app_icon.ico", format="ICO", append_images=images[:-1])
    print(f"Wrote app_icon.ico with sizes {ICO_SIZES}")


if __name__ == "__main__":
    main()


# ART, drawn out, so a change to the grid above can be checked by eye.
# Regenerate with:  python -c "from generate_icon import ART; \
#   print('\n'.join(''.join({'K':'##','L':'..','D':'::','E':'\"\"','C':'oo','.':'  '}[c] \
#   for c in r) for r in ART))"
#
#         ####        ####
#       ##....##    ##....##
#     ##..""""..####..""""..##
#     ##....................##
#   ##........................##
#   ##........""""............##
# ##............................##
# ##............oooo............##
# ##....::......oooo............##
# ##..::::......oooo............##
# ##....::......oooo........::..##
# ##............oooo............##
# ##::::::::::::::::::::::::::::##
#   ############################
