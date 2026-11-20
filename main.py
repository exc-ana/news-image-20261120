#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - Friday 20 November 2026.
One-page broadsheet summing up the world's news of 20 Nov 2026.

Pure Python standard library only (no PIL, no network). The image is
drawn on a 2048x2048 canvas with a hand-built vector stroke font and then
box-downscaled to 1024x1024, which gives crisp anti-aliased text.

Writes $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).
Deterministic: two runs produce byte-identical output.
"""
import os
import struct
import zlib

S = 2            # supersample factor (draw at 2048, deliver at 1024)
W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER   = (246, 241, 231)
INK     = (26, 26, 26)
NAVY    = (14, 42, 82)
NAVY2   = (22, 56, 107)
RED     = (200, 16, 46)
GOLD    = (201, 162, 39)
TEAL    = (14, 124, 123)
SKY     = (196, 222, 235)
CREAM   = (255, 252, 244)
MUTED   = (107, 107, 107)
RULE    = (216, 208, 188)
WHITE   = (255, 255, 255)
BLACK   = (0, 0, 0)
DUSK    = (232, 122, 54)
SEA     = (18, 92, 122)
SAND    = (233, 214, 170)

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w=W, h=H, s=S):
        self.s = s
        self.W = w * s
        self.H = h * s
        self.buf = bytearray(self.W * self.H * 3)
        self._discs = {}

    def _disc(self, r):
        """Cached list of (dx, dy) offsets for a filled disc of radius r (internal px)."""
        r = int(round(r))
        if r < 1:
            return [(0, 0)]
        if r in self._discs:
            return self._discs[r]
        out = []
        rr = r * r
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= rr:
                    out.append((dx, dy))
        self._discs[r] = out
        return out

    def px(self, x, y, c):
        if 0 <= x < self.W and 0 <= y < self.H:
            i = (y * self.W + x) * 3
            self.buf[i] = c[0]
            self.buf[i + 1] = c[1]
            self.buf[i + 2] = c[2]

    def stamp(self, cx, cy, r, c):
        """Stamp a filled disc centred at internal coords (cx, cy)."""
        for dx, dy in self._disc(r):
            self.px(cx + dx, cy + dy, c)

    def rect(self, x, y, w, h, c):
        s = self.s
        x0 = max(0, int(x * s)); y0 = max(0, int(y * s))
        x1 = min(self.W, int((x + w) * s)); y1 = min(self.H, int((y + h) * s))
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = c
        W3 = self.W * 3
        for yy in range(y0, y1):
            i = yy * W3 + x0 * 3
            for xx in range(x0, x1):
                self.buf[i] = r; self.buf[i + 1] = g; self.buf[i + 2] = b
                i += 3

    def vgrad(self, x, y, w, h, c1, c2):
        """Vertical gradient, coords in final px."""
        s = self.s
        x0 = max(0, int(x * s)); y0 = max(0, int(y * s))
        x1 = min(self.W, int((x + w) * s)); y1 = min(self.H, int((y + h) * s))
        n = max(1, y1 - y0)
        W3 = self.W * 3
        for j, yy in enumerate(range(y0, y1)):
            t = j / n
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            i = yy * W3 + x0 * 3
            for _ in range(x0, x1):
                self.buf[i] = r; self.buf[i + 1] = g; self.buf[i + 2] = b
                i += 3

    def hline(self, x0, x1, y, w, c):
        self.line(x0, y, x1, y, w, c)

    def vline(self, x, y0, y1, w, c):
        self.line(x, y0, x, y1, w, c)

    def line(self, x0, y0, x1, y1, w, c):
        """Thick line, coords in final px, width w in final px."""
        s = self.s
        ax, ay = int(x0 * s), int(y0 * s)
        bx, by = int(x1 * s), int(y1 * s)
        r = max(0.6, w * s / 2.0)
        steps = max(abs(bx - ax), abs(by - ay), 1)
        for k in range(steps + 1):
            t = k / steps
            self.stamp(int(ax + (bx - ax) * t), int(ay + (by - ay) * t), r, c)

    def polyline(self, pts, w, c, closed=False):
        seq = list(pts) + ([pts[0]] if closed and len(pts) > 1 else [])
        for a, b in zip(seq, seq[1:]):
            self.line(a[0], a[1], b[0], b[1], w, c)

    def polyfill(self, pts, c):
        """Scanline fill of a polygon, coords in final px."""
        s = self.s
        P = [(int(x * s), int(y * s)) for x, y in pts]
        if len(P) < 3:
            return
        ys = [p[1] for p in P]
        y0, y1 = max(0, min(ys)), min(self.H - 1, max(ys))
        n = len(P)
        W3 = self.W * 3
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, yy1 = P[i]
                x2, yy2 = P[(i + 1) % n]
                if (yy1 <= y < yy2) or (yy2 <= y < yy1):
                    xs.append(x1 + (y - yy1) * (x2 - x1) / (yy2 - yy1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(0, int(xs[k])); xb = min(self.W - 1, int(xs[k + 1]))
                i = y * W3 + xa * 3
                for _ in range(xa, xb + 1):
                    self.buf[i] = c[0]; self.buf[i + 1] = c[1]; self.buf[i + 2] = c[2]
                    i += 3

    def circle(self, cx, cy, r, c):
        self.stamp(int(cx * self.s), int(cy * self.s), r * self.s, c)

    def ellipse(self, cx, cy, rx, ry, c):
        n = 48
        pts = []
        for k in range(n):
            import math
            a = 2 * math.pi * k / n
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        self.polyfill(pts, c)

    def downscale(self):
        """Box-average 2x2 -> 1024x1024 RGB bytes."""
        s = self.s
        out = bytearray(W * H * 3)
        buf = self.buf
        W3 = self.W * 3
        for oy in range(H):
            b0 = (oy * s) * W3
            b1 = b0 + W3
            ob = oy * W * 3
            for ox in range(W):
                x = ox * s * 3
                i0 = b0 + x; i1 = b1 + x
                o = ob + ox * 3
                out[o]     = (buf[i0] + buf[i0 + 3] + buf[i1] + buf[i1 + 3]) >> 2
                out[o + 1] = (buf[i0 + 1] + buf[i0 + 4] + buf[i1 + 1] + buf[i1 + 4]) >> 2
                out[o + 2] = (buf[i0 + 2] + buf[i0 + 5] + buf[i1 + 2] + buf[i1 + 5]) >> 2
        return bytes(out)


def write_png(rgb, path):
    """Deterministic PNG: filter 0, fixed zlib level."""
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 6)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---------------------------------------------------------------- stroke font
# Hand-built single-stroke geometric sans. Each glyph: list of strokes;
# each stroke: "x,y x,y ..." on a 0..10 grid, y=0 baseline, y=10 cap top.
# Advance widths are in the same units. All-caps design, like a newspaper
# display face; hierarchy comes from size, weight and colour, not case.
_FONT_RAW = {
    "A": (11, ["0,0 5,10 10,0", "2.5,4 7.5,4"]),
    "B": (11, ["0,0 0,10 7,10 9.5,8 9.5,6 7,5 0,5", "7,5 9.5,3 9.5,2 7,0 0,0"]),
    "C": (10, ["9,8 7,10 3,10 0,7 0,3 3,0 7,0 9,2"]),
    "D": (11, ["0,0 0,10 6,10 10,7 10,3 6,0 0,0"]),
    "E": (10, ["9,10 0,10 0,0 9,0", "0,5 6,5"]),
    "F": (10, ["0,0 0,10 9,10", "0,5 6,5"]),
    "G": (11, ["9,8 7,10 3,10 0,7 0,3 3,0 7,0 10,3 10,5 6,5"]),
    "H": (11, ["0,0 0,10", "10,0 10,10", "0,5 10,5"]),
    "I": (6,  ["5,0 5,10", "2,10 8,10", "2,0 8,0"]),
    "J": (10, ["9,10 9,2 7,0 4,0 2,2"]),
    "K": (11, ["0,0 0,10", "9,10 1,5 9,0"]),
    "L": (10, ["0,10 0,0 9,0"]),
    "M": (12, ["0,0 0,10 5,4 10,10 10,0"]),
    "N": (11, ["0,0 0,10 10,0 10,10"]),
    "O": (11, ["2,10 7,10 10,7 10,3 7,0 2,0 0,3 0,7 2,10"]),
    "P": (11, ["0,0 0,10 7,10 9.5,7.5 7,5 0,5"]),
    "Q": (11, ["2,10 7,10 10,7 10,3 7,0 2,0 0,3 0,7 2,10", "6,4 10,0"]),
    "R": (11, ["0,0 0,10 7,10 9.5,7.5 7,5 0,5", "7,5 10,0"]),
    "S": (10, ["9,8 7,10 3,10 1,8 1,6 3,5 7,5 9,4 9,2 7,0 3,0 1,2"]),
    "T": (11, ["0,10 10,10", "5,10 5,0"]),
    "U": (11, ["0,10 0,3 2,0 8,0 10,3 10,10"]),
    "V": (11, ["0,10 5,0 10,10"]),
    "W": (13, ["0,10 2.5,0 5,5 7.5,0 10,10"]),
    "X": (11, ["0,10 10,0", "10,10 0,0"]),
    "Y": (11, ["0,10 5,5 10,10", "5,5 5,0"]),
    "Z": (10, ["0,10 10,10 0,0 10,0"]),
    "0": (11, ["2,10 7,10 10,7 10,3 7,0 2,0 0,3 0,7 2,10", "3,8 7,2"]),
    "1": (8,  ["3,8 5,10 5,0", "2,0 8,0"]),
    "2": (10, ["1,8 3,10 7,10 9,8 9,6 1,0 9,0"]),
    "3": (10, ["1,9 3,10 7,10 9,8 9,6 7,5 4,5", "7,5 9,4 9,2 7,0 3,0 1,2"]),
    "4": (10, ["7,10 2,4 8,4", "7,10 7,0"]),
    "5": (10, ["9,10 1,10 1,5 7,5 9,3 9,2 7,0 3,0 1,2"]),
    "6": (10, ["8,10 4,10 1,8 0,5 0,3 2,0 7,0 9,2 9,4 7,6 3,6"]),
    "7": (10, ["0,10 10,10 5,0"]),
    "8": (10, ["3,10 7,10 9,8 9,6 7,5 3,5 1,6 1,8 3,10",
                "3,5 7,5 9,4 9,2 7,0 3,0 1,2 1,4 3,5"]),
    "9": (10, ["2,0 6,0 9,2 10,5 10,7 8,10 3,10 1,8 1,6 3,4 6,4 8,5"]),
    ".": (5,  ["5,0 5,0"]),
    ",": (5,  ["5,1 4,-2"]),
    ":": (5,  ["5,7 5,7", "5,3 5,3"]),
    ";": (5,  ["5,7 5,7", "5,1 4,-2"]),
    "'": (5,  ["5,10 4,7"]),
    '"': (7,  ["3,10 2,7", "7,10 6,7"]),
    "-": (10, ["1,5 9,5"]),
    "–": (10, ["1,5 9,5"]),
    "—": (11, ["0,5 10,5"]),
    "/": (10, ["2,0 8,10"]),
    "(": (7,  ["7,10 4,7 4,3 7,0"]),
    ")": (7,  ["3,10 6,7 6,3 3,0"]),
    "%": (11, ["2,0 8,10", "2.5,8 2.5,8", "7.5,2 7.5,2"]),
    "$": (10, ["8,8 6,10 3,10 2,8 2,6 4,5 7,5 8,4 8,2 6,0 3,0 2,2",
                "5,11 5,-1"]),
    "+": (10, ["5,2 5,8", "2,5 8,5"]),
    "=": (10, ["1,6.5 9,6.5", "1,3.5 9,3.5"]),
    "?": (10, ["2,8 4,10 7,10 8,8 8,6 5,4 5,2.5", "5,0 5,0"]),
    "!": (6,  ["5,10 5,3", "5,0 5,0"]),
    "•": (6,  ["5,5 5,5"]),
    "·": (5,  ["5,5 5,5"]),
    "→": (11, ["1,5 9,5", "6,2 9,5 6,8"]),
    " ": (5,  []),
}
_FONT = {}
for _ch, (_adv, _strokes) in _FONT_RAW.items():
    _parsed = []
    for _st in _strokes:
        _pts = []
        for _tok in _st.split():
            _x, _y = _tok.split(",")
            _pts.append((float(_x), float(_y)))
        _parsed.append(_pts)
    _FONT[_ch] = (_adv, _parsed)


class Text:
    """Vector text renderer with a per-glyph mask cache (internal 2x px)."""

    def __init__(self, cv):
        self.cv = cv
        self.cache = {}

    def _glyph(self, ch, size, weight):
        """Return (offsets, advance_px, height_px) for a glyph at given
        size (final px cap height) and weight (stroke-width factor)."""
        key = (ch, size, weight)
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        adv, strokes = _FONT.get(ch, _FONT["?"])
        s = self.cv.s
        scale = size * s / 10.0
        wdt = max(0.7, size * s * 0.13 * weight)
        r = wdt / 2.0
        # mask bounds in internal px, with margin for stroke radius
        m = int(r) + 2
        gw = int(adv * scale) + 2 * m
        gh = int(13 * scale) + 2 * m   # y from -3 to 10
        # render strokes into a small boolean mask via disc stamps
        mask = bytearray(gw * gh)
        disc = self.cv._disc(r)
        for stroke in strokes:
            for (ax, ay), (bx, by) in zip(stroke, stroke[1:]):
                px0 = m + ax * scale
                py0 = m + (10 - ay) * scale
                px1 = m + bx * scale
                py1 = m + (10 - by) * scale
                steps = max(abs(px1 - px0), abs(py1 - py0), 1)
                steps = int(steps) + 1
                for k in range(steps + 1):
                    t = k / steps
                    cx = int(px0 + (px1 - px0) * t)
                    cy = int(py0 + (py1 - py0) * t)
                    for dx, dy in disc:
                        xx, yy = cx + dx, cy + dy
                        if 0 <= xx < gw and 0 <= yy < gh:
                            mask[yy * gw + xx] = 1
        offs = []
        for yy in range(gh):
            row = yy * gw
            for xx in range(gw):
                if mask[row + xx]:
                    offs.append((xx - m, yy - m))
        res = (offs, adv * scale, gh)
        self.cache[key] = res
        return res

    def width(self, text, size, weight=1.0, track=0.0):
        w = 0.0
        for ch in text:
            adv, _ = _FONT.get(ch, _FONT["?"])
            w += adv * size / 10.0 + track
        return w - track if text else 0.0

    def draw(self, x, y_base, text, size, color, weight=1.0, align="l",
             track=0.0, shear=0.0):
        """Draw text; (x, y_base) is the baseline origin in final px.
        align: 'l' left, 'c' centre, 'r' right. shear: italic slant."""
        if not text:
            return
        total = self.width(text, size, weight, track)
        if align == "c":
            x -= total / 2.0
        elif align == "r":
            x -= total
        s = self.cv.s
        buf = self.cv.buf
        W3 = self.cv.W * 3
        cx = x
        for ch in text:
            offs, advpx, _gh = self._glyph(ch, size, weight)
            ix = int(round(cx * s))
            iy = int(round((y_base - size) * s))
            sh = int(round(shear * size * s))
            for dx, dy in offs:
                # shear shifts x in proportion to distance below cap top
                xx = ix + dx + (sh * dy // max(1, int(size * s)) if shear else 0)
                yy = iy + dy
                if 0 <= xx < self.cv.W and 0 <= yy < self.cv.H:
                    i = yy * W3 + xx * 3
                    buf[i] = color[0]; buf[i + 1] = color[1]; buf[i + 2] = color[2]
            cx += advpx / s + track

    def wrap(self, text, size, maxw, weight=1.0, track=0.0):
        """Greedy word wrap; returns list of lines (final-px widths)."""
        words = text.split(" ")
        lines = []
        cur = ""
        for wd in words:
            trial = (cur + " " + wd) if cur else wd
            if self.width(trial, size, weight, track) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines

    def block(self, x, y, w, text, size, color, weight=1.0, leading=None,
              track=0.0, align="l"):
        """Draw a wrapped paragraph; y is the top of the first cap.
        Returns the y just below the last line."""
        if leading is None:
            leading = size * 1.28
        lines = self.wrap(text, size, w, weight, track)
        yy = y
        for ln in lines:
            self.draw(x, yy + size, ln, size, color, weight, align, track)
            yy += leading
        return yy

# ---------------------------------------------------------------- world map
import math

# Rough continent outlines as (lon, lat) polygons.
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 80), (-85, 80),
     (-80, 73), (-75, 72), (-65, 60), (-55, 52), (-60, 47), (-70, 44),
     (-75, 38), (-80, 32), (-81, 26), (-84, 30), (-90, 21), (-97, 26),
     (-105, 20), (-110, 23), (-115, 30), (-120, 34), (-125, 40),
     (-125, 49), (-135, 58), (-150, 60), (-165, 60)],
    # Greenland
    [(-58, 64), (-45, 60), (-40, 64), (-30, 68), (-25, 70), (-20, 74),
     (-30, 76), (-45, 76), (-58, 74), (-60, 70)],
    # South America
    [(-80, 9), (-75, 11), (-72, 12), (-62, 10), (-52, 5), (-50, 0),
     (-44, -3), (-35, -8), (-40, -20), (-48, -28), (-58, -35), (-65, -41),
     (-70, -50), (-74, -54), (-72, -40), (-72, -25), (-70, -18),
     (-80, -5), (-81, 0), (-80, 5)],
    # Africa
    [(-17, 15), (-10, 30), (-5, 35), (10, 37), (20, 32), (32, 31),
     (35, 28), (37, 22), (43, 12), (48, 11), (51, 10), (44, 0),
     (40, -10), (35, -18), (32, -26), (26, -34), (19, -35), (15, -27),
     (12, -18), (13, -10), (9, 4), (4, 6), (-8, 5), (-13, 8), (-17, 12)],
    # Eurasia
    [(-10, 36), (-9, 43), (-2, 48), (-5, 50), (0, 51), (5, 53), (8, 57),
     (10, 59), (5, 60), (5, 62), (12, 64), (18, 69), (25, 71), (32, 70),
     (40, 68), (50, 69), (60, 69), (70, 72), (80, 73), (90, 75),
     (100, 77), (110, 76), (120, 73), (130, 72), (140, 72), (150, 70),
     (160, 70), (170, 67), (178, 65), (178, 62), (170, 60), (162, 56),
     (158, 52), (150, 59), (142, 59), (140, 53), (138, 46), (135, 43),
     (130, 42), (127, 40), (126, 38), (122, 38), (120, 32), (118, 25),
     (110, 20), (108, 18), (105, 10), (100, 8), (98, 10), (95, 16),
     (92, 21), (88, 22), (85, 19), (80, 15), (77, 8), (75, 10),
     (72, 20), (68, 23), (65, 25), (60, 25), (57, 26), (55, 26),
     (52, 26), (50, 29), (48, 30), (44, 29), (40, 28), (39, 21),
     (35, 28), (36, 36), (30, 36), (27, 37), (23, 36), (19, 40),
     (15, 44), (12, 44), (8, 44), (3, 43), (0, 40), (-2, 37), (-6, 36)],
    # Indonesia / SE Asia islands
    [(95, 5), (98, 3), (100, 0), (103, -2), (106, -6), (110, -7),
     (114, -8), (119, -9), (122, -10), (120, -8), (117, -4), (113, 0),
     (110, 2), (105, 3), (100, 5)],
    [(109, -1), (113, -2), (117, -3), (119, -1), (117, 1), (112, 2),
     (109, 0)],
    [(131, -1), (136, -2), (141, -3), (141, -8), (136, -8), (132, -4)],
    # Australia
    [(113, -22), (114, -30), (115, -35), (120, -34), (125, -32),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (145, -38), (150, -37), (153, -32), (153, -27), (150, -22),
     (146, -19), (142, -15), (142, -11), (137, -12), (135, -15),
     (132, -12), (130, -13), (126, -14), (122, -17), (118, -20)],
    # Britain
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51)],
    # Japan
    [(130, 31), (132, 33), (135, 34), (137, 35), (139, 36), (140, 38),
     (141, 40), (141, 42), (143, 44), (145, 44), (142, 42), (140, 39),
     (139, 37), (137, 34), (134, 34), (132, 32)],
    # New Zealand
    [(167, -45), (170, -43), (173, -41), (175, -38), (177, -37),
     (174, -35), (173, -35), (171, -37), (168, -44)],
]


def _in_poly(lon, lat, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            xin = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < xin:
                inside = not inside
    return inside


def on_land(lon, lat):
    return any(_in_poly(lon, lat, p) for p in CONTINENTS)


def draw_map(cv, x, y, w, h, pins, tx):
    """Dotted world map with numbered pins. pins: list of (num, lon, lat)."""
    cv.rect(x, y, w, h, (232, 240, 244))
    cv.rect(x, y, w, 1.2, NAVY)
    cv.rect(x, y + h - 1.2, w, 1.2, NAVY)
    step = 7.0
    lon0, lon1 = -180.0, 180.0
    lat0, lat1 = 84.0, -58.0
    yy = y + 5
    row = 0
    while yy < y + h - 4:
        lat = lat0 + (yy - y) / h * (lat1 - lat0)
        xx = x + 5 + (row % 2) * step / 2
        while xx < x + w - 4:
            lon = lon0 + (xx - x) / w * (lon1 - lon0)
            if on_land(lon, lat):
                cv.circle(xx, yy, 0.85, NAVY2)
            xx += step
        yy += step
        row += 1
    for num, lon, lat, dx, dy in pins:
        px = x + (lon - lon0) / (lon1 - lon0) * w + dx
        py = y + (lat - lat0) / (lat1 - lat0) * h + dy
        cv.circle(px, py, 9, WHITE)
        cv.circle(px, py, 7.5, RED)
        tx.draw(px, py + 3, str(num), 8, WHITE, weight=1.6, align="c")


# ---------------------------------------------------------------- illustrations
def hero_anthropic(cv, x, y, w, h):
    """Dusk skyline with a chart that spikes to $111.50 then fades to $97.17."""
    cv.vgrad(x, y, w, h, (38, 62, 110), (232, 122, 54))
    cv.circle(x + w * 0.78, y + h * 0.30, 13, (255, 214, 140))
    # buildings
    bx = x + 4
    heights = [0.42, 0.62, 0.35, 0.72, 0.5, 0.8, 0.58, 0.44]
    bw = (w - 8) / len(heights)
    for i, hh in enumerate(heights):
        bh = h * hh
        cv.rect(bx + i * bw + 1, y + h - bh, bw - 2, bh, (16, 28, 52))
        for wy in range(3):
            cv.rect(bx + i * bw + 3, y + h - bh + 6 + wy * 12, 2.5, 4,
                    (255, 214, 140))
    # chart line: $83 -> $111.50 -> $97.17
    pts = [(x + 8, y + h * 0.62), (x + w * 0.30, y + h * 0.52),
           (x + w * 0.52, y + h * 0.18), (x + w * 0.72, y + h * 0.30),
           (x + w - 8, y + h * 0.42)]
    cv.polyline(pts, 3.2, (120, 220, 120))
    cv.polyline([(x + w * 0.52, y + h * 0.18), (x + w * 0.72, y + h * 0.30),
                 (x + w - 8, y + h * 0.42)], 3.2, (255, 90, 90))
    for px, py in pts:
        cv.circle(px, py, 3.2, WHITE)


def hero_cyclone(cv, x, y, w, h):
    """Spiral cyclone over the Bay of Bengal coast."""
    cv.vgrad(x, y, w, h, (10, 60, 90), (120, 190, 205))
    # sea + coastline
    cv.polyfill([(x, y + h), (x, y + h * 0.62), (x + w * 0.35, y + h * 0.55),
                 (x + w * 0.62, y + h * 0.72), (x + w, y + h * 0.66),
                 (x + w, y + h)], (16, 110, 105))
    cv.polyfill([(x, y + h * 0.62), (x + w * 0.35, y + h * 0.55),
                 (x + w * 0.62, y + h * 0.72), (x + w, y + h * 0.66),
                 (x + w, y + h * 0.60), (x + w * 0.6, y + h * 0.55),
                 (x + w * 0.3, y + h * 0.48), (x, y + h * 0.55)],
                (233, 214, 170))
    # spiral arms
    cx, cy = x + w * 0.42, y + h * 0.42
    for arm in range(3):
        pts = []
        for k in range(26):
            t = k / 25.0
            ang = arm * 2.094 + t * 4.6
            r = 4 + t * 34
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang) * 0.82))
        cv.polyline(pts, 3.4, WHITE)
    cv.circle(cx, cy, 7, (200, 16, 46))
    cv.circle(cx, cy, 3.5, WHITE)
    # rain streaks
    for i in range(9):
        rx = x + 12 + i * (w - 24) / 8
        cv.line(rx, y + 8, rx - 5, y + 22, 1.4, (220, 235, 240))


def hero_icj(cv, x, y, w, h):
    """Courthouse columns and the scales of justice."""
    cv.vgrad(x, y, w, h, (28, 58, 102), (120, 160, 200))
    # pediment + columns
    cv.polyfill([(x + 8, y + h * 0.34), (x + w / 2, y + h * 0.10),
                 (x + w - 8, y + h * 0.34)], (233, 214, 170))
    cv.rect(x + 8, y + h * 0.34, w - 16, 5, (233, 214, 170))
    for i in range(4):
        colx = x + w * (0.14 + i * 0.24)
        cv.rect(colx, y + h * 0.38, 11, h * 0.56, (240, 236, 224))
        cv.rect(colx - 2, y + h * 0.36, 15, 4, (240, 236, 224))
        cv.rect(colx - 2, y + h * 0.92, 15, 4, (240, 236, 224))
    cv.rect(x + 8, y + h * 0.94, w - 16, 5, (233, 214, 170))
    # scales: beam + two pans
    sx, sy = x + w * 0.5, y + h * 0.62
    cv.line(sx - 26, sy - 16, sx + 26, sy - 16, 2.4, GOLD)
    cv.line(sx, sy - 16, sx, sy + 2, 2.4, GOLD)
    cv.line(sx - 26, sy - 16, sx - 26, sy + 2, 1.8, GOLD)
    cv.line(sx + 26, sy - 16, sx + 26, sy + 2, 1.8, GOLD)
    cv.ellipse(sx - 26, sy + 4, 9, 3, GOLD)
    cv.ellipse(sx + 26, sy + 4, 9, 3, GOLD)
    cv.circle(sx, sy - 18, 3, GOLD)


def thumb(cv, x, y, w, h, kind):
    """Small flat pictogram for a story card."""
    bg = {"chart": (16, 110, 105), "fire": (200, 16, 46), "missile": NAVY,
          "game": (90, 40, 130), "globe": SEA, "gold": (176, 132, 20),
          "bank": (22, 56, 107), "court": (60, 60, 60), "ball": (14, 124, 123),
          "ship": (18, 92, 122), "leaf": (46, 125, 50), "flag": RED}.get(
              kind, NAVY)
    cv.rect(x, y, w, h, bg)
    cx, cy = x + w / 2, y + h / 2
    if kind == "chart":
        cv.polyline([(x + 5, y + h - 8), (x + w * 0.35, y + h * 0.55),
                     (x + w * 0.6, y + h * 0.68), (x + w - 5, y + 7)],
                    2.6, (120, 220, 120))
        cv.polyline([(x + 5, y + h - 8), (x + w * 0.35, y + h * 0.55),
                     (x + w * 0.6, y + h * 0.68)], 2.6, WHITE)
    elif kind == "fire":
        cv.polyfill([(cx, y + 6), (cx + 9, y + h * 0.5), (cx + 5, y + h - 6),
                     (cx - 5, y + h - 6), (cx - 9, y + h * 0.5)],
                    (255, 170, 40))
        cv.polyfill([(cx, y + h * 0.45), (cx + 5, y + h * 0.68),
                     (cx, y + h - 6), (cx - 5, y + h * 0.68)],
                    (255, 220, 120))
    elif kind == "missile":
        cv.line(cx - 12, cy + 10, cx + 12, cy - 10, 3, WHITE)
        cv.polyfill([(cx + 12, cy - 10), (cx + 16, cy - 2), (cx + 6, cy - 4)],
                    (255, 170, 40))
        cv.circle(cx - 12, cy + 10, 3, (255, 170, 40))
    elif kind == "game":
        cv.rect(x + 6, y + h * 0.32, w - 12, h * 0.36, WHITE)
        cv.line(cx, y + h * 0.32, cx, y + h * 0.68, 2, bg)
        cv.circle(cx - 7, cy, 2.5, bg)
        cv.circle(cx + 7, cy, 2.5, bg)
    elif kind == "globe":
        cv.circle(cx, cy, 13, WHITE)
        cv.circle(cx, cy, 13, bg)
        cv.ellipse(cx, cy, 13, 5.5, WHITE)
        cv.line(cx, cy - 13, cx, cy + 13, 1.6, WHITE)
    elif kind == "gold":
        cv.circle(cx, cy, 11, (255, 214, 140))
        cv.circle(cx, cy, 11, bg)
        cv.circle(cx, cy, 7.5, (255, 214, 140))
        cv.line(cx - 3, cy - 3, cx + 3, cy + 3, 2, bg)
    elif kind == "bank":
        cv.polyfill([(x + 5, y + h * 0.42), (cx, y + 8), (x + w - 5, y + h * 0.42)],
                    WHITE)
        for i in range(3):
            cv.rect(x + 7 + i * (w - 14) / 3, y + h * 0.46, 4, h * 0.4, WHITE)
        cv.rect(x + 5, y + h * 0.86, w - 10, 3, WHITE)
    elif kind == "court":
        cv.line(cx - 10, cy - 8, cx + 10, cy - 8, 2.2, WHITE)
        cv.line(cx, cy - 8, cx, cy + 4, 2.2, WHITE)
        cv.ellipse(cx - 10, cy + 6, 5, 2, WHITE)
        cv.ellipse(cx + 10, cy + 6, 5, 2, WHITE)
    elif kind == "ball":
        cv.circle(cx, cy, 12, WHITE)
        cv.polyfill([(cx - 5, cy - 10), (cx + 5, cy - 10), (cx, cy - 2)],
                    bg)
        cv.line(cx, cy - 2, cx, cy + 12, 1.6, bg)
    elif kind == "ship":
        cv.polyfill([(x + 5, cy + 2), (x + w - 5, cy + 2), (x + w - 10, cy + 9),
                     (x + 10, cy + 9)], WHITE)
        cv.rect(cx - 2, cy - 10, 3, 12, WHITE)
        cv.polyfill([(cx + 1, cy - 10), (cx + 12, cy - 4), (cx + 1, cy - 4)],
                    (255, 170, 40))
    elif kind == "leaf":
        cv.ellipse(cx, cy, 12, 6, WHITE)
        cv.line(cx - 12, cy, cx + 12, cy, 1.6, bg)
    elif kind == "flag":
        cv.line(x + 8, y + 5, x + 8, y + h - 5, 2.2, WHITE)
        cv.polyfill([(x + 8, y + 5), (x + w - 6, y + 10), (x + 8, y + 16)],
                    WHITE)
    else:
        cv.circle(cx, cy, 4, WHITE)

# ---------------------------------------------------------------- story data
# All facts verified by web search on 20 Nov 2026 (see BUILD-NOTES.md).
# Regions: NA / EU / ME / APAC / AF / GL
HEROES = [
    dict(num=1, kind="anthropic", kicker="MARKETS • NEW YORK",
         head="ANTHROPIC'S $2 TRILLION DAY FADES FAST",
         body="PRICED $83, OPENED $111.50, CLOSED $97.17 — UP 17%. BIGGEST "
              "IPO EVER: $81.3BN.",
         pin=(-74.0, 40.7)),
    dict(num=2, kind="cyclone", kicker="WEATHER • ODISHA, INDIA",
         head="AKVAN BEARS DOWN ON ODISHA",
         body="LANDFALL DUE AT NOON NEAR GOPALPUR, WINDS 90–100 KM/H. "
              "100,000+ EVACUATED.",
         pin=(84.9, 19.3)),
    dict(num=3, kind="icj", kicker="JUSTICE • THE HAGUE",
         head="MYANMAR GUILTY OF GENOCIDE",
         body="WORLD COURT RULES 9–6, A FIRST FOR A STATE. 10,000 KILLED; "
              "REPARATIONS ORDERED.",
         pin=(4.3, 52.1)),
]

CARDS = [
    dict(num=4, kind="chart", region="NA", kicker="MARKETS",
         head="WALL ST'S WORST DAY SINCE SPRING",
         body="DOW -1,101 (-2.2%) TO 49,097. S&P -2.0%, NASDAQ -2.3%: SIXTH "
              "STRAIGHT DOWN DAY.",
         pin=(-74.0, 40.7, 18, -10)),
    dict(num=5, kind="flag", region="APAC", kicker="DIPLOMACY",
         head="A 'PEACE DECLARATION' FROM SHENZHEN",
         body="TRUMP, XI AND PUTIN ISSUE JOINT TEXT. EUROPE NOW READY TO "
              "TALK TO MOSCOW.",
         pin=(114.1, 22.5)),
    dict(num=6, kind="missile", region="EU", kicker="UKRAINE",
         head="MISSILES RAIN ON KYIV",
         body="RUSSIA FIRES BALLISTIC MISSILES AT THE CAPITAL; ENERGY "
              "SITES TARGETED.",
         pin=(30.5, 50.4)),
    dict(num=7, kind="ship", region="ME", kicker="GULF",
         head="TANKER BURNS EAST OF HORMUZ",
         body="TANKER CATCHES FIRE AFTER HITTING A MINE. HOUTHIS CLAIM "
              "FOUR SAUDI STRIKES.",
         pin=(56.5, 26.5)),
    dict(num=8, kind="game", region="NA", kicker="CULTURE",
         head="GTA VI: $2.36BN IN A DAY",
         body="EST. 24.6M COPIES SOLD. 7.9M PEAK VIEWERS, 125.5M HOURS "
              "WATCHED — A RECORD.",
         pin=(-80.2, 25.8)),
    dict(num=9, kind="leaf", region="EU", kicker="CLIMATE",
         head="FOSSIL FUELS VANISH FROM COP31 TEXT",
         body="DRAFT CUT 144 TO 80 PARAGRAPHS. NO OIL, GAS OR COAL. TALKS "
              "CLOSE TODAY.",
         pin=(30.7, 36.9)),
    dict(num=10, kind="ball", region="NA", kicker="SPORT",
         head="TRUMP PARDONS PETE ROSE",
         body="POSTHUMOUS PARDON FOR THE 4,256-HIT KING, BANNED IN 1989. "
              "HALL VOTE DUE 2028.",
         pin=(-84.5, 39.1)),
    dict(num=11, kind="gold", region="GL", kicker="MARKETS",
         head="GOLD SLIDES TO $3,610",
         body="DOWN ABOUT 12% IN A MONTH AS THE AI SELL-OFF SPREADS.",
         pin=(-0.1, 51.5, -18, 12)),
    dict(num=12, kind="bank", region="APAC", kicker="JAPAN",
         head="BOJ HIKE ALL BUT CERTAIN",
         body="86% OF ECONOMISTS IN A REUTERS POLL SEE +25BP TO 1.50% ON "
              "17–18 DEC.",
         pin=(139.7, 35.7)),
    dict(num=13, kind="chart", region="APAC", kicker="TRADE",
         head="KOREA'S EXPORTS TOP $1 TRILLION",
         body="ANNUAL EXPORTS PASS $1TN FOR THE FIRST TIME, LED BY CHIPS "
              "AND SHIPS.",
         pin=(127.0, 37.5)),
]

INDEX = [
    (14, "EUROPE READY FOR TALKS WITH RUSSIA"),
    (15, "RUSSIA OPEN TO NATO-LIKE GUARANTEES"),
    (16, "CRIMEAN BRIDGE HIT A THIRD TIME"),
    (17, "N. KOREA EXPANDING YONGBYON SITE"),
    (18, "US–VENEZUELA RESTORE MILITARY TIES"),
    (19, "ISRAEL ENDS GAZA GROUND OPERATION"),
    (20, "ISRAELI STRIKE ON HEZBOLLAH SITE"),
    (21, "GENOA AIRPORT SHUT BY DRONES"),
    (22, "BLAST NEAR DUTCH EMBASSY, KYIV"),
    (23, "MIGRANT BOAT SINKS OFF SENEGAL"),
    (24, "FIJI DECLARES DROUGHT DISASTER"),
    (25, "S. KOREA COURT CLEARS EX-PM HAN"),
    (26, "TAIWAN MOVES TO STEADY STOCKS"),
    (27, "TRUMP WARNS APEC ON AI RULES"),
    (28, "TRUMP WHITE HOUSE NEWS CONFERENCE"),
    (29, "CALIFORNIA PROBES NVIDIA CHIP SALES"),
    (30, "IEA: DATA-CENTRE POWER MAY DOUBLE"),
    (31, "MODI MEETS WILLIAM AND KATE"),
    (32, "FIRE AT YUNUS FAMILY HOME"),
    (33, "NZ 243/5, NICHOLLS CENTURY"),
    (34, "HIPPO FIONA DIES AT CINCINNATI ZOO"),
    (35, "SENSEX +1.21%, NIFTY +1.14%"),
    (36, "SAUDI: REBEL ATTACK HIT LANDMARK"),
    (37, "TAKAICHI DUCKS TAIWAN QUESTION"),
    (38, "ANTHROPIC -4% AFTER HOURS (SEE 1)"),
    (39, "GTA VI FESTIVAL IN MIAMI SATURDAY"),
    (40, "ANTHROPIC Q3 REVENUE $17BN"),
]

NUMBERS = [
    ("1,101", "DOW POINTS LOST"),
    ("$81.3BN", "BIGGEST IPO EVER"),
    ("9–6", "ICJ GENOCIDE VOTE"),
    ("100,000+", "EVACUATED: AKVAN"),
    ("7.9M", "GTA VI PEAK VIEWERS"),
    ("$3,610", "GOLD PER OUNCE"),
]

REGIONS = [
    ("N. AMERICA", 11, NAVY2), ("EUROPE", 8, RED), ("MIDDLE EAST", 4, TEAL),
    ("ASIA-PACIFIC", 14, (176, 132, 20)), ("AFRICA", 1, (46, 125, 50)),
    ("GLOBAL", 2, MUTED),
]

DATE_CHECK = ("DATE CHECK — LEFT OUT ON PURPOSE: THE SHENZHEN SUMMIT ITSELF "
              "(19 NOV) — ONLY ITS PEACE DECLARATION AND REACTIONS ARE 20 NOV "
              "NEWS. ANTHROPIC'S $83 PRICING WAS SET 18 NOV. AKVAN'S LANDFALL "
              "IS FORECAST FOR NOON TODAY, NOT YET CONFIRMED. NOTHING FROM "
              "17–19 NOV IS PRESENTED AS TODAY'S NEWS.")

SOURCES = ("SOURCES: REUTERS, AP, BBC, CNN, WSJ, AL JAZEERA, IMD, ICJ, SENSOR "
           "TOWER (EST.), STREAMS CHARTS, DE-CIX. ALL FIGURES AS REPORTED "
           "20 NOV 2026.")


# ---------------------------------------------------------------- layout
def build():
    cv = Canvas()
    tx = Text(cv)
    cv.rect(0, 0, W, H, PAPER)

    # ---- masthead
    cv.rect(14, 14, 996, 54, NAVY)
    cv.rect(14, 68, 996, 2, GOLD)
    tx.draw(26, 52, "THE WORLD IN ONE DAY", 30, WHITE, weight=1.7)
    tx.draw(998, 52, "40 STORIES • ONE PAGE", 13, (200, 214, 235),
            weight=1.2, align="r")

    # ---- giant date headline + red NOV 20 box
    tx.draw(14, 128, "FRIDAY 20 NOVEMBER 2026", 34, NAVY, weight=1.9)
    cv.rect(862, 76, 148, 66, RED)
    tx.draw(936, 106, "NOV", 20, WHITE, weight=1.7, align="c")
    tx.draw(936, 136, "20", 30, WHITE, weight=1.9, align="c")
    tx.draw(14, 160, "ANTHROPIC FADES, WALL STREET SLIDES — AND THE WORLD "
                      "COURT MAKES HISTORY", 12.5, INK, weight=1.1, shear=0.12)

    # ---- region bar
    parts = []
    total = 0.0
    for name, n, col in REGIONS:
        wdt = tx.width(name + " " + str(n), 9.5, weight=1.3) + 14
        parts.append((name, n, col, wdt))
        total += wdt + 22
    total -= 22
    xx = (W - total) / 2
    for name, n, col, wdt in parts:
        cv.rect(xx, 168, 9, 9, col)
        tx.draw(xx + 13, 177, name + " " + str(n), 9.5, INK, weight=1.3)
        xx += wdt + 22

    # ---- hero row
    hero_y, hero_h = 186, 186
    hero_w = 324
    for i, hs in enumerate(HEROES):
        hx = 14 + i * (hero_w + 12)
        cv.rect(hx, hero_y, hero_w, hero_h, CREAM)
        cv.rect(hx, hero_y, hero_w, 1.4, NAVY)
        cv.rect(hx, hero_y + hero_h - 1.4, hero_w, 1.4, NAVY)
        if hs["kind"] == "anthropic":
            hero_anthropic(cv, hx + 1, hero_y + 1, hero_w - 2, 88)
        elif hs["kind"] == "cyclone":
            hero_cyclone(cv, hx + 1, hero_y + 1, hero_w - 2, 88)
        else:
            hero_icj(cv, hx + 1, hero_y + 1, hero_w - 2, 88)
        cv.circle(hx + 16, hero_y + 16, 11, RED)
        tx.draw(hx + 16, hero_y + 20.5, str(hs["num"]), 13, WHITE,
                weight=1.8, align="c")
        tx.draw(hx + 10, hero_y + 106, hs["kicker"], 8.5, RED, weight=1.5)
        y = tx.block(hx + 10, hero_y + 110, hero_w - 20, hs["head"], 14,
                     INK, weight=1.5, leading=18)
        tx.block(hx + 10, y + 1, hero_w - 20, hs["body"], 10, (60, 60, 60),
                 weight=1.0, leading=12.5)

    # ---- card grid (10 cards, 2 rows x 5)
    card_w, card_h = 191, 122
    for r in range(2):
        for c in range(5):
            cd = CARDS[r * 5 + c]
            cx = 14 + c * (card_w + 10)
            cy = 378 + r * (card_h + 6)
            cv.rect(cx, cy, card_w, card_h, CREAM)
            cv.rect(cx, cy, card_w, 1.2, NAVY)
            cv.rect(cx, cy + card_h - 1.2, card_w, 1.2, NAVY)
            cv.circle(cx + 11, cy + 11, 8.5, RED)
            tx.draw(cx + 11, cy + 14.5, str(cd["num"]), 10, WHITE,
                    weight=1.8, align="c")
            tx.draw(cx + 24, cy + 15, cd["kicker"], 8, RED, weight=1.5)
            thumb(cv, cx + card_w - 36, cy + 5, 30, 30, cd["kind"])
            y = tx.block(cx + 8, cy + 24, card_w - 54, cd["head"], 10.5, INK,
                         weight=1.6, leading=13.5)
            tx.block(cx + 8, y + 1, card_w - 16, cd["body"], 8.5,
                     (60, 60, 60), weight=1.0, leading=10.5)

    # ---- the day in numbers
    ny = 634
    cv.rect(14, ny, 996, 60, NAVY)
    tx.draw(24, ny + 15, "THE DAY IN NUMBERS", 11, GOLD, weight=1.6)
    cell_w = 996 / 6
    for i, (num, lab) in enumerate(NUMBERS):
        cx = 14 + i * cell_w
        size = 20
        if tx.width(num, size, weight=1.8) > cell_w - 16:
            size = 17
        tx.draw(cx + cell_w / 2, ny + 38, num, size, WHITE, weight=1.8,
                align="c")
        tx.draw(cx + cell_w / 2, ny + 52, lab, 8, (200, 214, 235),
                weight=1.2, align="c")
        if i:
            cv.vline(cx, ny + 10, ny + 50, 1, (70, 95, 135))

    # ---- map
    tx.draw(14, 712, "WHERE IT HAPPENED", 12, NAVY, weight=1.7)
    tx.draw(1010, 712, "NUMBERED PINS = THE 13 LEAD STORIES", 9, MUTED,
            weight=1.1, align="r")
    pins = []
    for hs in HEROES:
        pins.append((hs["num"], hs["pin"][0], hs["pin"][1], 0, 0))
    for cd in CARDS:
        p = cd["pin"]
        pins.append((cd["num"], p[0], p[1], p[2] if len(p) > 2 else 0,
                     p[3] if len(p) > 3 else 0))
    draw_map(cv, 14, 718, 996, 122, pins, tx)

    # ---- index
    tx.draw(14, 858, "ALSO ON FRIDAY 20 NOVEMBER", 11, NAVY, weight=1.7)
    cv.rect(14, 862, 996, 1.4, RED)
    col_w = 322
    for i, (num, item) in enumerate(INDEX):
        col = i // 9
        row = i % 9
        ix = 14 + col * (col_w + 15)
        iy = 872 + row * 10.5
        tx.draw(ix, iy + 7, str(num) + ".", 8, RED, weight=1.6)
        tx.draw(ix + 17, iy + 7, item, 8, INK, weight=1.0)

    # ---- date check + sources
    cv.rect(14, 970, 996, 36, RED)
    y = tx.block(24, 975, 976, DATE_CHECK, 8.5, WHITE, weight=1.1,
                 leading=10)
    tx.draw(512, 1016, SOURCES, 8, MUTED, weight=1.0, align="c")
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    cv = build()
    rgb = cv.downscale()
    path = os.path.join(out_dir, "entry.png")
    n = write_png(rgb, path)
    print("wrote %s (%d bytes)" % (path, n))


if __name__ == "__main__":
    main()
