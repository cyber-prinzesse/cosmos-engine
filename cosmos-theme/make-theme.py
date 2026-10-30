#!/usr/bin/env python3
"""Turns Wine's light visual style (dlls/light.msstyles) into the Cosmos one: Cosmopolitan's black, its greys and its
off-white (Sources/UI/CosmoTheme.swift), selection drawn as off-white with dark text like the app does.

Usage: make-theme.py <wine source tree> [--no-bitmaps]

Recolours every SVG and the colour tables in light.rc in place, names the style "Cosmos", then rebuilds each committed
.bmp from its SVG with Wine's own tools/buildimage (needs rsvg-convert and ImageMagick). The module keeps its file name
(light.msstyles), so Wine's build and wine.inf need no change: every new bottle starts with it, as with the light style.
Run after the patch series, before configure. Same input, same output: it only maps colours.
"""
import os, re, subprocess, sys

# Cosmopolitan's tokens
BLACK, SURFACE, RAISED, HAIRLINE, RULE = 0x000000, 0x0D0D0D, 0x161616, 0x2A2A2A, 0x5E5E5B
TEXT, TEXT2 = 0xEDEDEA, 0x9A9A96

# The light style's palette, by role (counted over all 480 SVGs).
EXPLICIT = {
    0xFFFFFF: SURFACE, 0xFEFEFE: SURFACE, 0xFFFFFE: SURFACE, 0xFFFFF9: SURFACE, 0xFDFFFF: SURFACE,  # control fills
    0xF5F5F5: RAISED,                       # pressed / disabled fills
    0xAEAEAE: RULE,                         # control borders
    0x3096FA: TEXT2,                        # hover / focus accent
    0x2979FF: TEXT, 0x0091EA: TEXT,         # selected / pressed / checked: off-white, its glyph turns dark
    0x000000: TEXT,                         # glyphs and text
    0xE3F2FD: RAISED, 0xE1F5FE: RAISED,     # hot list and tree items
    0xBBDEFB: HAIRLINE, 0xB3E5FC: HAIRLINE, # selected list and tree items
    0xFF1744: 0xFF1744, 0xD50000: 0xD50000, # close-button red stays
}
# light.rc's system colours with a role of their own
SYSCOLORS = {
    "Background": BLACK, "AppWorkSpace": BLACK, "Highlight": TEXT, "HighlightText": SURFACE, "HotTrackingColor": TEXT,
    "MenuHilight": TEXT, "MenuBar": SURFACE, "Menu": RAISED, "InfoWindow": RAISED, "InfoText": TEXT,
    "GrayText": RULE, "BtnFace": SURFACE, "Window": SURFACE, "WindowFrame": HAIRLINE, "ActiveBorder": HAIRLINE,
    "InactiveBorder": HAIRLINE, "ActiveCaption": RAISED, "InactiveCaption": SURFACE, "GradientActiveCaption": RAISED,
    "GradientInactiveCaption": SURFACE, "CaptionText": TEXT, "InactiveCaptionText": TEXT2,
}


def generic(c):
    """Anything not listed: greys turn around on Cosmopolitan's range (white -> surface, black -> text); colours go by lightness."""
    r, g, b = c >> 16, (c >> 8) & 0xFF, c & 0xFF
    if max(r, g, b) - min(r, g, b) < 24:
        v = round(0xED - (r + g + b) / 3 / 255 * (0xED - 0x0D))
        return v << 16 | v << 8 | v
    if r > 180 and g < 90 and b < 90:
        return c  # reds (errors, close) stay
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return RAISED if lum > 190 else TEXT2 if lum > 100 else BLACK


def mapped(c):
    return EXPLICIT.get(c, generic(c))


HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F])")


def recolour_svg(text):
    def sub(m):
        h = m.group(1)
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return "#%06x" % mapped(int(h, 16))
    return HEX.sub(sub, text)


TRIPLET = re.compile(r'"(\w+) = (\d{1,3}) (\d{1,3}) (\d{1,3})\\r\\n"')
SECTION = re.compile(r'"(?:\\r\\n)?\[([^\]]+)\]\\r\\n"')
# Progress bars draw like Cosmopolitan's: off-white fill on a raised track (the generic rule would make the fill grey).
SECTION_COLORS = {("Progress", "FillColor"): TEXT, ("Progress.Chunk", "FillColor"): TEXT, ("Progress.ChunkVert", "FillColor"): TEXT,
                  ("Progress.Bar", "FillColor"): RAISED, ("Progress.BarVert", "FillColor"): RAISED}


def recolour_rc(text):
    section = ""

    def sub(m):
        name, c = m.group(1), int(m.group(2)) << 16 | int(m.group(3)) << 8 | int(m.group(4))
        n = SECTION_COLORS.get((section, name), SYSCOLORS.get(name, mapped(c)))
        return '"%s = %d %d %d\\r\\n"' % (name, n >> 16, (n >> 8) & 0xFF, n & 0xFF)
    out = []
    for line in text.split("\n"):
        s = SECTION.search(line)
        if s:
            section = s.group(1)
        out.append(TRIPLET.sub(sub, line))
    text = "\n".join(out)
    text = text.replace('"DisplayName = Light\\r\\n"', '"DisplayName = Cosmos\\r\\n"')
    text = text.replace('"ToolTip = Light Visual Style\\r\\n"', '"ToolTip = Cosmos Visual Style\\r\\n"')
    return text


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    wine = os.path.abspath(sys.argv[1])
    d = os.path.join(wine, "dlls", "light.msstyles")
    svgs = sorted(f for f in os.listdir(d) if f.endswith(".svg"))
    for f in svgs:
        p = os.path.join(d, f)
        with open(p, encoding="utf-8") as fh:
            t = fh.read()
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(recolour_svg(t))
    rc = os.path.join(d, "light.rc")
    with open(rc, encoding="utf-8") as fh:
        t = fh.read()
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(recolour_rc(t))
    print("cosmos theme: %d SVGs and light.rc recoloured" % len(svgs))
    if "--no-bitmaps" in sys.argv:
        return
    env = dict(os.environ)
    env.setdefault("CONVERT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "convert"))
    built = 0
    for f in svgs:
        bmp = os.path.join(d, f[:-4] + ".bmp")
        if not os.path.exists(bmp):
            continue  # only the bitmaps Wine commits; others are built from SVG by the build itself
        subprocess.run(["perl", os.path.join(wine, "tools", "buildimage"), os.path.join(d, f), bmp], check=True, env=env)
        built += 1
    print("cosmos theme: %d bitmaps rebuilt" % built)


if __name__ == "__main__":
    main()
