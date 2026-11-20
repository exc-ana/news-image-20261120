#!/usr/bin/env python3
"""The World Today - Friday 20 November 2026, in one broadsheet image.

Draws a single-page newspaper front page (1024x1024) summing up the
world news of Friday 20 November 2026: 40 stories, two lead heroes
(Anthropic's market debut, Cyclone Akvan's confirmed landfall), a
dotted world map with numbered pins, a numbers strip, a UTC timeline,
a numbered index and a DATE CHECK footer.

Everything is drawn from scratch with the Python standard library
only: an RGB bytearray canvas rendered at 2x (2048x2048) and box
downsampled to 1024x1024, a hand-built vector stroke font, and a
hand-rolled PNG encoder. No network, no clock, no randomness, no
external files: the same input always produces the same bytes.

Output: $MAKEFUN_OUTPUT_DIR/entry.png, or /output/entry.png when
the variable is unset or empty.
"""

import hashlib
import os
import struct
import zlib

# ---------------------------------------------------------------- canvas
S = 2                    # supersampling factor
FW, FH = 1024, 1024      # final image size
W, H = FW * S, FH * S    # working canvas size

PAPER = (247, 243, 232)
CARD = (255, 253, 246)
INK = (26, 26, 26)
NAVY = (20, 38, 74)
NAVY2 = (30, 55, 105)
RED = (179, 32, 44)
REDDK = (140, 20, 32)
GRAY = (105, 105, 100)
LINE = (180, 174, 158)
SKY = (172, 200, 226)
SKYDK = (120, 160, 200)
SEA = (52, 102, 138)
SEADK = (32, 72, 108)
GREEN = (32, 118, 68)
GOLD = (176, 132, 32)
GOLDLT = (214, 172, 74)
WHITE = (255, 255, 255)
CREAM = (233, 228, 214)
ORANGE = (214, 110, 40)


def px(v):
    """Final-pixel coordinate -> working-pixel coordinate."""
    return int(round(v * S))


class Canvas:
    def __init__(self, w, h, color):
        self.w = w
        self.h = h
        self.buf = bytearray(color * (w * h))

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._off(x, y)
            self.buf[o:o + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.w, int(x + w))
        y1 = min(self.h, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            o = self._off(x0, yy)
            self.buf[o:o + len(row)] = row

    def vgrad(self, x, y, w, h, top, bottom):
        """Vertical gradient rectangle."""
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.w, int(x + w))
        y1 = min(self.h, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        for yy in range(y0, y1):
            t = (yy - y0) / max(1, y1 - y0 - 1)
            c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            row = bytes(c) * (x1 - x0)
            o = self._off(x0, yy)
            self.buf[o:o + len(row)] = row

    def disc(self, cx, cy, r, color):
        r = int(r)
        if r <= 0:
            return
        x0 = max(0, int(cx - r))
        x1 = min(self.w - 1, int(cx + r))
        y0 = max(0, int(cy - r))
        y1 = min(self.h - 1, int(cy + r))
        rr = r * r
        for yy in range(y0, y1 + 1):
            dy = yy - cy
            for xx in range(x0, x1 + 1):
                dx = xx - cx
                if dx * dx + dy * dy <= rr:
                    self.set(xx, yy, color)

    def ellipse(self, cx, cy, rx, ry, color):
        rx = int(rx)
        ry = int(ry)
        if rx <= 0 or ry <= 0:
            return
        x0 = max(0, int(cx - rx))
        x1 = min(self.w - 1, int(cx + rx))
        y0 = max(0, int(cy - ry))
        y1 = min(self.h - 1, int(cy + ry))
        for yy in range(y0, y1 + 1):
            ny = (yy - cy) / ry
            for xx in range(x0, x1 + 1):
                nx = (xx - cx) / rx
                if nx * nx + ny * ny <= 1.0:
                    self.set(xx, yy, color)

    def poly(self, pts, color):
        """Scanline fill of a polygon given as [(x, y), ...]."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h - 1, int(max(ys)))
        n = len(pts)
        for yy in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, y0v = pts[i]
                x1, y1v = pts[(i + 1) % n]
                if (y0v <= yy < y1v) or (y1v <= yy < y0v):
                    t = (yy - y0v) / (y1v - y0v)
                    xs.append(x0 + t * (x1 - x0))
            if len(xs) < 2:
                continue
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(0, int(xs[k]))
                xb = min(self.w - 1, int(xs[k + 1]))
                if xb >= xa:
                    row = bytes(color) * (xb - xa + 1)
                    o = self._off(xa, yy)
                    self.buf[o:o + len(row)] = row

    def seg(self, x0, y0, x1, y1, w, color):
        """Thick line segment with round caps."""
        dx = x1 - x0
        dy = y1 - y0
        ln = (dx * dx + dy * dy) ** 0.5
        r = w / 2.0
        if ln < 0.001:
            self.disc(x0, y0, r, color)
            return
        nx = -dy / ln * r
        ny = dx / ln * r
        self.poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                   (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], color)
        self.disc(x0, y0, r, color)
        self.disc(x1, y1, r, color)

    def arc(self, cx, cy, r, a0, a1, w, color):
        """Arc from angle a0 to a1 (degrees, 0 = east, clockwise down)."""
        import math
        steps = max(2, int(abs(a1 - a0) / 4))
        prev = None
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            p = (cx + r * math.cos(a), cy + r * math.sin(a))
            if prev is not None:
                self.seg(prev[0], prev[1], p[0], p[1], w, color)
            prev = p

    def spiral(self, cx, cy, r0, r1, turns, w, color):
        """Archimedean spiral, used for the cyclone scene."""
        import math
        steps = int(turns * 48)
        prev = None
        for i in range(steps + 1):
            t = i / steps
            a = t * turns * 2 * math.pi
            r = r0 + (r1 - r0) * t
            p = (cx + r * math.cos(a), cy + r * math.sin(a))
            if prev is not None:
                self.seg(prev[0], prev[1], p[0], p[1], w, color)
            prev = p


CV = Canvas(W, H, PAPER)

# ------------------------------------------------------------------ font
# Vector stroke font, drawn fresh for this entry. Each glyph is a set
# of polylines on an 11-wide, 16-tall grid: x 0..10, y 0..15, cap top
# y=1, baseline y=12, descender y=14. Encoding: strokes separated by
# "|", points separated by spaces, each point two hex digits (x, y).
# A single-point stroke is a dot.
GLYPHS = {
    "A": "1c 51 9c|39 79", "B": "11 1c|11 81 93 85 15|15 85 97 9a 8c 1c",
    "C": "93 71 31 13 1a 3c 7c 9a", "D": "11 1c|11 71 93 9a 7c 1c",
    "E": "11 1c 9c|11 91|16 76", "F": "11 1c|11 91|16 76",
    "G": "93 71 31 13 1a 3c 7c 9a 97 67", "H": "11 1c|91 9c|16 96",
    "I": "51 5c|21 81|2c 8c", "J": "31 91|91 9a 7c 3c",
    "K": "11 1c|91 16|38 9c", "L": "11 1c 9c", "M": "1c 11 58 91 9c",
    "N": "1c 11 9c 91", "O": "31 71 93 9a 7c 3c 1a 13 31",
    "P": "1c 11 81 93 86 16", "Q": "31 71 93 9a 7c 3c 1a 13 31|69 9c",
    "R": "1c 11 81 93 86 16|46 9c",
    "S": "92 71 31 13 15 36 77 99 9b 7c 3c 1a", "T": "11 91|51 5c",
    "U": "11 1a 3c 7c 9a 91", "V": "11 5c 91", "W": "11 3c 56 7c 91",
    "X": "11 9c|91 1c", "Y": "11 56 91|56 5c", "Z": "11 91 1c 9c",
    "0": "31 71 93 9a 7c 3c 1a 13 31", "1": "23 51|51 5c|2c 8c",
    "2": "13 31 71 93 96 1c 9c", "3": "12 31 71 93 75 56|56 86 98 9a 7c 3c 1a",
    "4": "18 71 7c|18 98", "5": "91 11 16 76 98 9a 7c 3c 1a",
    "6": "93 71 31 14 1a 3c 7c 9a 97 66 26", "7": "11 91 4c",
    "8": "31 71 93 95 77 37 15 13 31|37 77 99 9b 7c 3c 1a 18 37",
    "9": "1a 3c 7c 9a 93 71 31 13 16 47 87",
    "a": "36 65 86 8a 6c 3c 2a 27 36|85 8c", "b": "21 2c|27 55 86 8a 5c 2b",
    "c": "86 65 35 27 2a 3c 6c 8b", "d": "81 8c|87 55 26 2a 5c 8b",
    "e": "28 88|86 65 35 27 2a 3c 6c 8a", "f": "61 43 4c|38 78",
    "g": "36 65 86 8a 6c 3c 2a 27 36|8a 8e 5f 2e", "h": "21 2c|27 55 76 7c",
    "i": "55 5c|52 52", "j": "65 6c 5e 3e|62 62",
    "k": "21 2c|65 28|47 7c", "l": "51 5c", "m": "2c 25 45 57 5c|57 75 86 8c",
    "n": "2c 25 55 76 7c", "o": "36 65 86 8a 6c 3c 2a 27 36",
    "p": "25 2e|27 55 86 8a 5c 2b", "q": "85 8e|87 55 26 2a 5c 8b",
    "r": "2c 25 65 87 8a", "s": "86 65 35 27 28 39 7a 8b 7c 4c 2b",
    "t": "51 5c 7c|37 77", "u": "25 2a 3c 6c 8a 85", "v": "15 4c 85",
    "w": "15 2c 48 6c 85", "x": "25 8c|85 2c", "y": "15 4b 85|68 3e",
    "z": "25 85 2c 8c",
    ".": "5c 5c", ",": "5b 5c 3e", ":": "55 55|5b 5b", ";": "55 55|5b 5c 3e",
    "!": "52 59|5c 5c", "?": "23 41 71 93 95 77 57 59|5c 5c",
    "'": "51 44", '"': "31 24|71 64", "-": "27 87", "—": "17 a7",
    "•": "47 67", "(": "61 34 39 6c", ")": "41 74 79 4c", "/": "2c 81",
    "+": "53 5b|27 87", "=": "25 85|29 89",
    "%": "12 82|22 42 44 24 22|68 88 8a 6a 68",
    "$": "51 5c|83 61 31 13 15 36 77 99 9b 7c 3c 1a",
    "#": "41 3c|71 6c|15 95|19 99",
    "&": "71 41 23 26 48 78 9a 9c 7c 5a 2c", "_": "1d 9d",
    "*": "52 5b|15 99|95 19", "[": "71 31 3c 7c", "]": "31 71 7c 3c",
    "<": "81 27 8c", ">": "21 87 2c",
}

NARROW = {"i": 4, "l": 4, ".": 4, ",": 4, ":": 4, ";": 4, "!": 4,
          "'": 3, '"': 6, "(": 5, ")": 5, "/": 5, "-": 6, " ": 5,
          "[": 5, "]": 5, "|": 4, "•": 5}
WIDE = {"m": 10, "w": 10, "M": 11, "W": 11, "%": 10, "&": 9, "G": 9,
        "O": 9, "Q": 9, "0": 9, "8": 9, "D": 9, "H": 9, "U": 9}


def _adv_units(ch):
    if ch in NARROW:
        return NARROW[ch]
    if ch in WIDE:
        return WIDE[ch]
    return 8


def _glyph_strokes(ch):
    """Decode one glyph into a list of polylines of (gx, gy) points."""
    spec = GLYPHS.get(ch)
    if spec is None:
        return []
    out = []
    for stroke in spec.split("|"):
        pts = []
        for tok in stroke.split():
            pts.append((int(tok[0], 16), int(tok[1], 16)))
        if pts:
            out.append(pts)
    return out


TRACK = 0.4  # extra advance units between glyphs, for legibility


def text_width(s, size):
    """Width of string s at cap-height `size` (final px)."""
    sc = size * S / 11.0
    return sum((_adv_units(c) + TRACK) * sc for c in s) / S


def draw_text(x, y, s, size, color, bold=False, align="l"):
    """Draw text; (x, y) is the top-left of the cap height (final px).
    align "l" (left), "c" (centred on x), "r" (right edge at x)."""
    sc = size * S / 11.0
    wdt = text_width(s, size)
    if align == "c":
        x -= wdt / 2.0
    elif align == "r":
        x -= wdt
    lw = max(1.6, size * S * (0.20 if bold else 0.14))
    ox = px(x)
    oy = px(y)
    cx = ox
    for ch in s:
        for stroke in _glyph_strokes(ch):
            pts = [(cx + gx * sc, oy + gy * sc) for gx, gy in stroke]
            if len(pts) == 1:
                CV.disc(pts[0][0], pts[0][1], lw * 0.55, color)
            else:
                for a, b in zip(pts, pts[1:]):
                    CV.seg(a[0], a[1], b[0], b[1], lw, color)
                for p in pts:
                    CV.disc(p[0], p[1], lw * 0.5, color)
        cx += (_adv_units(ch) + TRACK) * sc
    return wdt


def wrap(s, size, maxw):
    """Greedy word wrap; returns list of lines fitting maxw (final px)."""
    lines = []
    cur = ""
    for word in s.split(" "):
        trial = word if not cur else cur + " " + word
        if text_width(trial, size) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def para(x, y, s, size, color, maxw, lh=None, bold=False):
    """Draw a wrapped paragraph; returns y just below the last line."""
    if lh is None:
        lh = size * 1.32
    for line in wrap(s, size, maxw):
        draw_text(x, y, line, size, color, bold=bold)
        y += lh
    return y

# -------------------------------------------------------------------- png
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(rgb, w, h):
    """Encode raw RGB bytes as a PNG (Sub filter, zlib level 9)."""
    raw = bytearray()
    for y in range(h):
        raw.append(1)  # Sub filter
        row = rgb[y * w * 3:(y + 1) * w * 3]
        prev = bytearray(3)
        for i in range(0, len(row), 3):
            for k in range(3):
                raw.append((row[i + k] - prev[k]) & 0xFF)
            prev = row[i:i + 3]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


def downsample():
    """Box-average the 2x working canvas down to 1024x1024 RGB bytes."""
    out = bytearray(FW * FH * 3)
    src = CV.buf
    for y in range(FH):
        for x in range(FW):
            for k in range(3):
                o = (y * FW + x) * 3 + k
                s = 0
                for dy in (0, 1):
                    for dx in (0, 1):
                        s += src[((y * 2 + dy) * W + (x * 2 + dx)) * 3 + k]
                out[o] = s // 4
    return bytes(out)


# ----------------------------------------------------------------- scenes
def scene_chart(x, y, w, h):
    """Anthropic debut: IPO price chart. (x, y, w, h) in final px."""
    X, Y, Wd, Ht = px(x), px(y), px(w), px(h)
    CV.vgrad(X, Y, Wd, Ht, (214, 228, 240), (247, 243, 232))
    base = Y + Ht - px(14)
    top = Y + px(8)
    # price points: priced 83, open 111.50, high 115.10, close 97.17
    vals = [83.0, 111.50, 115.10, 97.17]
    labels = ["$83", "$111.50", "$115.10", "$97.17"]
    names = ["PRICED", "OPEN", "HIGH", "CLOSE"]
    lo, hi = 75.0, 122.0

    def py(v):
        return base - (v - lo) / (hi - lo) * (base - top)

    n = len(vals)
    xs = [X + Wd * (i + 0.5) / n for i in range(n)]
    bw = px(44)
    for i, v in enumerate(vals):
        col = NAVY2 if i in (1, 2) else GREEN if i == 0 else RED
        if i == 3:
            col = NAVY
        CV.rect(xs[i] - bw / 2, py(v), bw, base - py(v), col)
        CV.rect(xs[i] - bw / 2, py(v), bw, px(2), WHITE)
    for i in range(n - 1):
        CV.seg(xs[i], py(vals[i]), xs[i + 1], py(vals[i + 1]), px(2.2),
               INK)
    for i in range(n):
        CV.disc(xs[i], py(vals[i]), px(3.2), WHITE)
        CV.disc(xs[i], py(vals[i]), px(2.0), INK)
    # value labels, staggered so none collide
    draw_text(xs[0] / S, (py(vals[0]) - px(14)) / S, "$83", 10, INK,
              bold=True, align="c")
    draw_text(xs[1] / S, (py(vals[1]) + px(10)) / S, "$111.50", 8, WHITE,
              bold=True, align="c")
    draw_text(xs[2] / S, (py(vals[2]) - px(14)) / S, "$115.10", 10, INK,
              bold=True, align="c")
    draw_text(xs[3] / S, (py(vals[3]) + px(10)) / S, "$97.17", 8, WHITE,
              bold=True, align="c")
    for i in range(n):
        nx = xs[i] - (px(24) if i == 3 else 0)
        draw_text(nx / S, (base + px(2)) / S, names[i], 8, GRAY,
                  align="c")
    # after-hours dashed marker; price sits in the name row, far right
    ahx = X + Wd - px(6)
    CV.seg(xs[3], py(vals[3]), ahx, py(92.60), px(1.6), RED)
    draw_text((ahx - px(2)) / S, (base + px(2)) / S, "AH $92.60",
              8, RED, bold=True, align="r")


def scene_cyclone(x, y, w, h):
    """Cyclone Akvan: spiral over the Bay of Bengal coast."""
    X, Y, Wd, Ht = px(x), px(y), px(w), px(h)
    CV.vgrad(X, Y, Wd, Ht, (196, 214, 232), (233, 228, 214))
    # coastline: Bay of Bengal on the right, land on the left
    coast = [(X + Wd * 0.62, Y), (X + Wd * 0.58, Y + Ht * 0.3),
             (X + Wd * 0.66, Y + Ht * 0.55), (X + Wd * 0.60, Y + Ht * 0.8),
             (X + Wd * 0.68, Y + Ht), (X, Y + Ht), (X, Y)]
    CV.poly(coast, (206, 196, 164))
    sea = [(X + Wd * 0.62, Y), (X + Wd, Y), (X + Wd, Y + Ht),
           (X + Wd * 0.68, Y + Ht), (X + Wd * 0.60, Y + Ht * 0.8),
           (X + Wd * 0.66, Y + Ht * 0.55), (X + Wd * 0.58, Y + Ht * 0.3)]
    CV.poly(sea, (96, 146, 178))
    cx = X + Wd * 0.42
    cy = Y + Ht * 0.46
    r1 = Ht * 0.42
    for i, rr in enumerate((1.0, 0.72, 0.46)):
        CV.spiral(cx, cy, r1 * rr * 0.12, r1 * rr, 2.6, px(2.4),
                  WHITE if i == 0 else (240, 244, 248))
    CV.disc(cx, cy, px(5), NAVY)
    CV.disc(cx, cy, px(2.5), WHITE)
    # landfall marker on the coast
    gx = X + Wd * 0.60
    gy = Y + Ht * 0.42
    CV.disc(gx, gy, px(6), RED)
    CV.disc(gx, gy, px(3), WHITE)
    draw_text((gx + px(12)) / S, (gy - px(5)) / S, "GOPALPUR", 9, INK,
              bold=True)
    # wind arrows
    for ax, ay, ang in ((0.16, 0.20, 40), (0.80, 0.16, 130),
                        (0.22, 0.82, -30), (0.86, 0.78, 200)):
        import math
        a = math.radians(ang)
        x0 = X + Wd * ax
        y0 = Y + Ht * ay
        x1 = x0 + px(22) * math.cos(a)
        y1 = y0 + px(22) * math.sin(a)
        CV.seg(x0, y0, x1, y1, px(2), INK)
        CV.poly([(x1, y1), (x1 - px(7) * math.cos(a - 0.5),
                  y1 - px(7) * math.sin(a - 0.5)),
                 (x1 - px(7) * math.cos(a + 0.5),
                  y1 - px(7) * math.sin(a + 0.5))], INK)
    draw_text((X + px(4)) / S, (Y + px(3)) / S, "BAY OF BENGAL", 8, WHITE,
              bold=True)


def scene_tanker(x, y, w, h):
    """Hormuz tanker: burning tanker on a strait at dusk."""
    X, Y, Wd, Ht = px(x), px(y), px(w), px(h)
    CV.vgrad(X, Y, Wd, Ht * 0.62, (232, 150, 92), (196, 96, 88))
    CV.disc(X + Wd * 0.82, Y + Ht * 0.22, px(13), (240, 200, 120))
    CV.rect(X, Y + Ht * 0.62, Wd, Ht * 0.38, (44, 66, 96))
    for i in range(3):
        wy = Y + Ht * (0.68 + i * 0.10)
        CV.seg(X + px(6), wy, X + Wd - px(6), wy, px(1.4),
               (120, 150, 180))
    # tanker hull and deck
    hx, hy, hw, hh = X + Wd * 0.10, Y + Ht * 0.42, Wd * 0.62, Ht * 0.22
    CV.poly([(hx, hy), (hx + hw, hy), (hx + hw - px(10), hy + hh),
             (hx + px(12), hy + hh)], (30, 30, 34))
    CV.rect(hx + hw * 0.08, hy - Ht * 0.16, hw * 0.30, Ht * 0.16,
            (60, 60, 66))
    CV.rect(hx + hw * 0.55, hy - Ht * 0.10, hw * 0.22, Ht * 0.10,
            (80, 80, 88))
    # fire and smoke
    fx = hx + hw * 0.72
    fy = hy - Ht * 0.02
    CV.poly([(fx - px(12), fy), (fx, fy - Ht * 0.30), (fx + px(12), fy)],
            ORANGE)
    CV.poly([(fx - px(7), fy), (fx + px(2), fy - Ht * 0.20),
             (fx + px(9), fy)], (240, 200, 60))
    CV.disc(fx - px(4), fy - Ht * 0.34, px(7), (120, 120, 118))
    CV.disc(fx + px(6), fy - Ht * 0.44, px(9), (140, 140, 138))
    CV.disc(fx - px(2), fy - Ht * 0.55, px(6), (160, 160, 158))
    draw_text((X + px(4)) / S, (Y + Ht - px(11)) / S,
              "STRAIT OF HORMUZ", 8, WHITE, bold=True)


def scene_gold(x, y, w, h):
    """Gold bars stacked, price falling."""
    X, Y, Wd, Ht = px(x), px(y), px(w), px(h)
    CV.vgrad(X, Y, Wd, Ht, (238, 226, 196), (222, 204, 164))
    bw, bh = Wd * 0.30, Ht * 0.26
    for row in range(2):
        for col in range(3 - row):
            bx = X + Wd * 0.12 + col * bw * 1.02 + row * bw * 0.5
            by = Y + Ht * 0.62 - row * bh * 0.95
            top = [(bx + bw * 0.12, by), (bx + bw * 0.88, by),
                   (bx + bw, by + bh * 0.35), (bx, by + bh * 0.35)]
            CV.poly(top, GOLDLT)
            CV.rect(bx, by + bh * 0.35, bw, bh * 0.65, GOLD)
            CV.rect(bx, by + bh * 0.35, bw, px(1.5), (120, 88, 20))
    # falling arrow
    ax0, ay0 = X + Wd * 0.84, Y + Ht * 0.14
    ax1, ay1 = X + Wd * 0.97, Y + Ht * 0.55
    CV.seg(ax0, ay0, ax1, ay1, px(3), RED)
    CV.poly([(ax1, ay1), (ax1 - px(10), ay1 - px(2)),
             (ax1 - px(2), ay1 - px(10))], RED)
    draw_text((X + px(4)) / S, (Y + px(3)) / S, "-2.3% TODAY", 9, REDDK,
              bold=True)


def scene_globe(x, y, w, h):
    """COP31: globe with meridian lines."""
    X, Y, Wd, Ht = px(x), px(y), px(w), px(h)
    CV.rect(X, Y, Wd, Ht, (222, 232, 240))
    cx, cy, r = X + Wd * 0.5, Y + Ht * 0.52, min(Wd, Ht) * 0.42
    CV.disc(cx, cy, r, SEA)
    import math
    for k in (-2, -1, 0, 1, 2):
        off = k * r * 0.32
        half = math.sqrt(max(0.0, r * r - off * off))
        CV.seg(cx + off, cy - half, cx + off, cy + half, px(1.2),
               (150, 180, 205))
    for fy in (-0.5, 0.0, 0.5):
        CV.seg(cx - r, cy + r * fy, cx + r, cy + r * fy, px(1.2),
               (150, 180, 205))
    CV.ellipse(cx - r * 0.35, cy - r * 0.15, r * 0.28, r * 0.2, GREEN)
    CV.ellipse(cx + r * 0.30, cy + r * 0.25, r * 0.22, r * 0.18, GREEN)
    draw_text((X + Wd / 2) / S, (Y + px(2)) / S, "ANTALYA", 8, NAVY,
              bold=True, align="c")


def scene_chip(x, y, w, h):
    """Nvidia probe: a chip under a magnifier."""
    X, Y, Wd, Ht = px(x), px(y), px(w), px(h)
    CV.rect(X, Y, Wd, Ht, (226, 228, 234))
    cx, cy = X + Wd * 0.5, Y + Ht * 0.52
    s = min(Wd, Ht) * 0.60
    for i in range(4):
        off = -s * 0.6 + i * s * 0.4
        CV.seg(cx + off, cy - s * 0.62, cx + off, cy - s * 0.38, px(2),
               INK)
        CV.seg(cx + off, cy + s * 0.38, cx + off, cy + s * 0.62, px(2),
               INK)
        CV.seg(cx - s * 0.62, cy + off, cx - s * 0.38, cy + off, px(2),
               INK)
        CV.seg(cx + s * 0.38, cy + off, cx + s * 0.62, cy + off, px(2),
               INK)
    CV.rect(cx - s * 0.5, cy - s * 0.5, s, s, (24, 60, 40))
    CV.rect(cx - s * 0.28, cy - s * 0.28, s * 0.56, s * 0.56, GREEN)
    draw_text(cx / S, (cy - px(5)) / S, "AI", 13, WHITE, bold=True,
              align="c")
    draw_text((X + px(4)) / S, (Y + px(2)) / S, "CHIP PROBE", 8, NAVY,
              bold=True)


def icon_scales(x, y, s):
    """Tiny scales of justice for the ICJ card."""
    X, Y, Sc = px(x), px(y), px(s)
    CV.seg(X + Sc * 0.5, Y, X + Sc * 0.5, Y + Sc * 0.8, px(2), NAVY)
    CV.seg(X + Sc * 0.1, Y + Sc * 0.22, X + Sc * 0.9, Y + Sc * 0.22,
           px(2), NAVY)
    for bx in (0.16, 0.84):
        CV.seg(X + Sc * bx, Y + Sc * 0.22, X + Sc * (bx - 0.14),
               Y + Sc * 0.55, px(1.6), NAVY)
        CV.seg(X + Sc * bx, Y + Sc * 0.22, X + Sc * (bx + 0.14),
               Y + Sc * 0.55, px(1.6), NAVY)
        CV.seg(X + Sc * (bx - 0.14), Y + Sc * 0.55,
               X + Sc * (bx + 0.14), Y + Sc * 0.55, px(1.6), NAVY)
    CV.seg(X + Sc * 0.28, Y + Sc * 0.8, X + Sc * 0.72, Y + Sc * 0.8,
           px(2), NAVY)


def icon_flags(x, y, w, h):
    """Three flags on poles for the Shenzhen summit card."""
    X, Y, Wd, Ht = px(x), px(y), px(w), px(h)
    cols = [RED, (30, 80, 160), (240, 210, 60)]
    for i, c in enumerate(cols):
        fx = X + Wd * (0.16 + i * 0.34)
        CV.seg(fx, Y + Ht * 0.1, fx, Y + Ht, px(2), INK)
        CV.rect(fx, Y + Ht * 0.12, Wd * 0.26, Ht * 0.34, c)


def icon_bridge(x, y, w, h):
    """Kerch bridge: arch span with a broken section and smoke."""
    X, Y, Wd, Ht = px(x), px(y), px(w), px(h)
    CV.rect(X, Y, Wd, Ht, (214, 222, 232))
    CV.seg(X + px(3), Y + Ht * 0.72, X + Wd - px(3), Y + Ht * 0.72,
           px(3), INK)
    CV.arc(X + Wd * 0.5, Y + Ht * 0.72, Wd * 0.34, 180, 360, px(2.4),
           NAVY)
    CV.seg(X + Wd * 0.62, Y + Ht * 0.30, X + Wd * 0.62,
           Y + Ht * 0.72, px(2), NAVY)
    CV.seg(X + Wd * 0.72, Y + Ht * 0.42, X + Wd * 0.80,
           Y + Ht * 0.72, px(2.4), RED)
    CV.disc(X + Wd * 0.70, Y + Ht * 0.30, px(6), (130, 130, 128))
    CV.disc(X + Wd * 0.76, Y + Ht * 0.20, px(8), (150, 150, 148))

# ----------------------------------------------------------------- layout
def card(x, y, w, h):
    CV.rect(px(x), px(y), px(w), px(h), CARD)
    CV.rect(px(x), px(y), px(w), px(1), LINE)
    CV.rect(px(x), px(y + h - 1), px(w), px(1), LINE)
    CV.rect(px(x), px(y), px(1), px(h), LINE)
    CV.rect(px(x + w - 1), px(y), px(1), px(h), LINE)


def tag(x, y, text):
    tw = text_width(text, 8) + 10
    CV.rect(px(x), px(y), px(tw), px(15), RED)
    draw_text(x + 5, y + 3.5, text, 8, WHITE, bold=True)
    return tw


def hero(x, y, w, h, kicker, lines, deck, scene_fn):
    card(x, y, w, h)
    draw_text(x + 10, y + 8, kicker, 10, RED, bold=True)
    tw = text_width("CONFIRMED", 8) + 10
    tag(x + w - 6 - tw, y + 6, "CONFIRMED")
    ly = y + 26
    for ln in lines:
        draw_text(x + 10, ly, ln, 20, NAVY, bold=True)
        ly += 24
    para(x + 10, y + 78, deck, 11, INK, w - 20, lh=14.5)
    scene_fn(x + 6, y + h - 118, w - 12, 112)


def row2_card(x, y, w, h, kicker, head, body, icon):
    card(x, y, w, h)
    draw_text(x + 10, y + 7, kicker, 9, RED, bold=True)
    icon(x, y)
    lines = wrap(head, 13, w - 16)
    ly = y + 21
    for ln in lines:
        draw_text(x + 10, ly, ln, 13, NAVY, bold=True)
        ly += 16
    para(x + 10, y + 21 + len(lines) * 16 + 6, body, 10, INK, w - 16,
         lh=13.2)


def mini_card(x, y, w, h, kicker, stat, head, body):
    card(x, y, w, h)
    draw_text(x + 10, y + 6, kicker, 8.5, RED, bold=True)
    draw_text(x + w - 8, y + 4, stat, 15, RED, bold=True, align="r")
    draw_text(x + 10, y + 25, head, 12, NAVY, bold=True)
    para(x + 10, y + 44, body, 9.5, INK, w - 16, lh=12.5)


def row4_card(x, y, w, h, scene_fn, kicker, head, body):
    card(x, y, w, h)
    scene_fn(x + 4, y + 4, w - 8, 52)
    draw_text(x + 10, y + 61, kicker, 9, RED, bold=True)
    draw_text(x + 10, y + 74, head, 12, NAVY, bold=True)
    para(x + 10, y + 92, body, 9.5, INK, w - 16, lh=12.5)


# Dotted world map: continents as ellipses in (lon, lat, rx, ry).
LAND = [
    (-100, 48, 32, 16), (-95, 32, 18, 10), (-150, 64, 15, 8),
    (-90, 15, 10, 5), (-42, 74, 10, 6), (-60, -12, 12, 18),
    (-62, -30, 7, 10), (12, 52, 14, 7), (18, 62, 8, 6),
    (-1, 54, 3, 4), (18, 8, 14, 14), (20, -18, 10, 10),
    (47, -19, 2, 5), (80, 55, 35, 14), (100, 35, 18, 10),
    (78, 21, 7, 9), (102, 12, 8, 7), (115, -2, 12, 4),
    (139, 37, 3, 6), (45, 24, 8, 7), (134, -25, 14, 8),
    (172, -41, 2, 4),
]
PINS = [
    (1, -122, 37), (2, 84.8, 19.1), (3, 4.3, 56), (4, 114, 22.5),
    (5, 41, 48), (6, -72, 42), (7, -80, 25.8), (8, -86, 41),
    (10, 30.7, 36.9), (12, 56.5, 26.5), (13, -2, 47),
    (21, 10, 41), (33, 174.8, -41.3),
]

INDEX = [
    "Europe ready for talks; Putin invites leaders to Moscow",
    "US envoy: Russia may accept NATO-like guarantees",
    "Putin rejects new ceasefire after Kerch strikes",
    "N. Korea expanding uranium enrichment at Yongbyon",
    "US and Venezuela sign deal to restore military ties",
    "Israeli army ends operation beyond Gaza's Yellow Line",
    "Israeli strike hits Hezbollah site in eastern Lebanon",
    "Genoa airport shut ~4 hours after mystery drones",
    "Austrian, Dutch embassies hit in Kyiv; envoy summoned",
    "Migrant boat sinks off Senegal; dozens missing",
    "Fiji declares national disaster over El Nino drought",
    "S. Korea court clears ex-PM Han over 2024 martial law",
    "Taiwan unveils five measures to steady stocks",
    "Trump warns APEC: strict AI rules would stifle growth",
    "Trump returns from China; White House briefing today",
    "Anthropic debut sparks protests in New York, S.F.",
    "IEA: data-centre power use could double by 2030",
    "PM Modi meets Prince and Princess of Wales in New Delhi",
    "Fire at Muhammad Yunus home; arson suspected",
    "Cricket: NZ 368; Nicholls 175*, Phillips 118; India 16/0",
    "Hippo Fiona dies after swallowing a hat in Cincinnati",
    "Sensex +1.21%, Nifty +1.14% on Thursday",
    "Russian prosecutors warn Wikimedia may be 'undesirable'",
    "Japan PM Takaichi dodges Taiwan question at APEC",
    "Anthropic -4.7% after hours to $92.60",
    "GTA VI: The Festival, one-day Miami event, Sat 21 Nov",
    "Anthropic Q3 revenue $17bn, ~12x YoY (SEC filing)",
]


def draw_map(x, y, w, h):
    card(x, y, w, h)
    draw_text(x + 8, y + 5, "WHERE IT HAPPENED - 13 STORIES PINNED",
              9, NAVY, bold=True)
    x0, y0, pw, ph = x + 6, y + 18, w - 12, h - 22

    def mx(lon):
        return px(x0 + (lon + 180) / 360.0 * pw)

    def my(lat):
        return px(y0 + (80 - lat) / 140.0 * ph)

    for lon in range(-180, 181, 4):
        for lat in range(80, -61, -4):
            for cl, ca, rx, ry in LAND:
                if ((lon - cl) / rx) ** 2 + ((lat - ca) / ry) ** 2 <= 1.0:
                    CV.ellipse(mx(lon), my(lat), px(2.2), px(1.1),
                               (70, 100, 140))
                    break
    for num, lon, lat in PINS:
        pxc, pyc = mx(lon), my(lat)
        CV.disc(pxc, pyc, px(5), RED)
        CV.disc(pxc, pyc, px(4.2), WHITE)
        CV.disc(pxc, pyc, px(3.9), RED)
        draw_text(pxc / S, (pyc - px(3.2)) / S, str(num), 6.5, WHITE,
                  bold=True, align="c")


def build():
    # Masthead
    CV.rect(0, 0, W, px(52), NAVY)
    draw_text(18, 10, "THE WORLD TODAY", 30, WHITE, bold=True)
    draw_text(1006, 11, "FRIDAY EDITION", 12, WHITE, bold=True,
              align="r")
    draw_text(1006, 30, "40 STORIES - ONE DAY - 20 NOV 2026", 9,
              (200, 210, 230), align="r")
    CV.rect(0, px(52), W, px(3), GOLD)

    # Date band
    draw_text(14, 58, "FRIDAY, 20 NOVEMBER 2026", 32, NAVY, bold=True)
    draw_text(14, 97, "THE WORLD IN ONE DAY - 40 STORIES FROM EVERY "
              "CONTINENT", 10, GRAY)
    CV.rect(px(884), px(56), px(126), px(54), RED)
    draw_text(947, 61, "NOV 20", 24, WHITE, bold=True, align="c")
    draw_text(947, 90, "2026", 12, WHITE, bold=True, align="c")

    # Lead heroes
    hero(14, 116, 492, 256, "MARKETS - BIGGEST IPO EVER",
         ["ANTHROPIC DEBUT", "$83 TO $115 IN A DAY"],
         "Priced $83, above the $70-78 range. Opened $111.50, hit "
         "$115.10, closed $97.17 (+17%). After hours $92.60. "
         "$81.3bn raised, the largest IPO on record.",
         scene_chart)
    hero(518, 116, 492, 256, "WEATHER - LANDFALL CONFIRMED",
         ["CYCLONE AKVAN", "LANDFALL CONFIRMED"],
         "Crossed the Andhra-Odisha coast near Gopalpur at 07:30 "
         "IST. Winds 70-80 km/h, gusts to 90. 300,000 evacuated; "
         "423 rescue teams; 69 trains cancelled.",
         scene_cyclone)

    # Row 2: three big cards
    row2_card(14, 376, 326, 124, "THE HAGUE",
              "ICJ: MYANMAR GUILTY OF GENOCIDE",
              "9-6 vote, the first time the court has found a state "
              "committed genocide. About 10,000 Rohingya killed in "
              "2017; 700,000 fled. Reparations and safe return "
              "ordered.",
              lambda x, y: icon_scales(x + 326 - 34, y + 6, 22))
    row2_card(348, 376, 327, 124, "SUMMIT",
              "TRUMP, XI AND PUTIN SIGN PEACE DECLARATION",
              "Historic trilateral summit in Shenzhen on 19 Nov "
              "issues a joint peace declaration. European allies "
              "say they are ready for talks; Putin invites envoys "
              "to Moscow.",
              lambda x, y: icon_flags(x + 327 - 56, y + 5, 48, 24))
    row2_card(683, 376, 327, 124, "UKRAINE",
              "KERCH BRIDGE HIT A THIRD TIME",
              "Third Ukrainian strike in four days hits the rail "
              "span overnight. Putin rejects further ceasefire "
              "agreements afterwards.",
              lambda x, y: icon_bridge(x + 327 - 60, y + 4, 52, 28))

    # Mini row: four cards
    mini_card(14, 504, 243, 92, "MARKETS", "-1,101", "DOW SINKS 2.19%",
              "Dow -2.19% to 49,097. S&P 500 -2.02%; Nasdaq -2.25%. "
              "Sixth straight down day for the S&P.")
    mini_card(265, 504, 243, 92, "GAMING", "24.6M",
              "GTA VI SMASHES RECORDS",
              "Estimate via Sensor Tower: $2.36bn. 7.91m peak "
              "viewers, 125.47m hours watched in 24h.")
    mini_card(516, 504, 243, 92, "SPORT", "4,256",
              "PETE ROSE PARDONED",
              "Trump grants a posthumous pardon to MLB's hits "
              "leader. Banned since 1989; died Sep 2024, aged 83.")
    mini_card(767, 504, 243, 92, "JAPAN", "+25BP",
              "BOJ HIKE IN DECEMBER",
              "Reuters poll: 86% of economists expect +25bp to "
              "1.50% at the 17-18 Dec meeting.")

    # Row 4: four scene cards
    row4_card(14, 600, 243, 126, scene_globe, "CLIMATE",
              "COP31 DROPS FOSSIL FUELS",
              "Draft cut 144 to 80 paragraphs; all fossil-fuel "
              "mentions removed. No deal yet.")
    row4_card(265, 600, 243, 126, scene_chip, "TECH",
              "CALIFORNIA PROBES NVIDIA",
              "State targets Nvidia in a China AI-chip probe as "
              "the AI sell-off spreads.")
    row4_card(516, 600, 243, 126, scene_tanker, "GULF",
              "TANKER HIT OFF HORMUZ",
              "Tanker catches fire after hitting a mine; Houthis "
              "claim four Saudi strikes.")
    row4_card(767, 600, 243, 126, scene_gold, "GOLD",
              "GOLD $3,543, 4TH DAY DOWN",
              "Spot gold falls 2.3% to $3,543.19, below $3,600. "
              "Worst week since March.")

    # Map + numbers
    draw_map(14, 730, 646, 108)
    card(668, 730, 342, 108)
    draw_text(676, 735, "THE DAY IN NUMBERS", 11, NAVY, bold=True)
    stats = [("1,101", "DOW POINTS LOST"), ("$81.3BN", "BIGGEST IPO EVER"),
             ("9-6", "ICJ GENOCIDE VOTE"), ("300,000", "EVACUATED FROM AKVAN"),
             ("7.9M", "GTA VI PEAK VIEWERS"), ("$3,543", "GOLD PER OUNCE")]
    for i, (num, lab) in enumerate(stats):
        sx = 676 + (i % 2) * 174
        sy = 752 + (i // 2) * 29
        draw_text(sx, sy, num, 14, RED, bold=True)
        draw_text(sx, sy + 17, lab, 8, GRAY)

    # UTC timeline
    draw_text(14, 843, "UTC TIMELINE", 9, RED, bold=True)
    draw_text(118, 843,
              "00:22 NZ 317-6 AT LUNCH, DAY 2  •  00:35 GOLD LOWEST "
              "SINCE SEPT  •  01:22 MISSILES HIT KYIV", 8.5, INK)
    draw_text(118, 856,
              "02:00 AKVAN MAKES LANDFALL  •  02:38 GOLD FALLS 2.3% "
              "TO $3,543  •  04:29 ANTHROPIC $92.60 AFTER HOURS",
              8.5, INK)

    # Index: 27 more stories, 3 columns
    draw_text(14, 874, "THE REST OF THE DAY - 27 MORE STORIES", 10,
              NAVY, bold=True)
    for i, item in enumerate(INDEX):
        col, row = i % 3, i // 3
        ix = 14 + col * 334
        iy = 890 + row * 12.5
        draw_text(ix, iy, "%d. %s" % (14 + i, item), 8, INK)

    # Footer: date check + sources
    draw_text(14, 1001,
              "DATE CHECK - Every story above happened, or was "
              "reported, on Friday 20 November 2026. Shenzhen met 19 "
              "Nov; only its declaration is 20 Nov news. Anthropic "
              "priced 18 Nov; only day one counts.",
              7.5, INK)
    draw_text(14, 1012,
              "SOURCES: WSJ - BARRON'S - REUTERS - BBC - NYT - CNN - "
              "IMD - UN - AP - ESPNCRICINFO - DEADLINE - FT - "
              "TRADINGVIEW", 8, GRAY)


def main():
    build()
    data = encode_png(downsample(), FW, FH)
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s %d bytes sha256=%s"
          % (path, len(data), hashlib.sha256(data).hexdigest()))


if __name__ == "__main__":
    main()
