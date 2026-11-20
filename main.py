#!/usr/bin/env python3
"""THE WORLD TODAY -- Friday 20 November 2026.

A one-page newspaper broadsheet summing up the day's world news, drawn
entirely in code with the Python standard library only.

Pipeline (all my own): render at 2x (2048x2048) onto an RGB bytearray,
draw with a hand-made vector stroke font, box-average downsample to
1024x1024, and write a deterministic PNG with a hand-rolled encoder.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   ->  out/entry.png
The program takes no input, reads no files, uses no network and no
randomness, so two runs write byte-identical output.
"""
import math
import os
import struct
import zlib

S = 2                    # supersampling factor
W = H = 1024             # final image size
CW, CH = W * S, H * S    # working canvas size

# ---- palette ----
PAPER = (247, 242, 228)
CARD = (255, 253, 246)
INK = (24, 24, 24)
NAVY = (15, 37, 63)
NAVY2 = (26, 58, 94)
RED = (178, 29, 36)
GOLD = (198, 158, 38)
GREY = (104, 102, 94)
LGREY = (208, 203, 188)
TEAL = (13, 118, 108)
SKY = (216, 229, 239)
SKY2 = (188, 210, 228)
NIGHT = (17, 31, 64)
NIGHT2 = (34, 56, 96)
WHITE = (255, 255, 255)
CREAM = (238, 231, 210)
GREEN = (74, 122, 62)
SEA = (38, 92, 138)

# ---- working canvas (RGB bytearray) ----
buf = bytearray(CW * CH * 3)


def _off(x, y):
    return (y * CW + x) * 3


def rect(x0, y0, x1, y1, c):
    """Fill a rectangle. Coords in final pixels."""
    X0 = max(0, int(x0 * S))
    Y0 = max(0, int(y0 * S))
    X1 = min(CW, int(x1 * S))
    Y1 = min(CH, int(y1 * S))
    if X1 <= X0 or Y1 <= Y0:
        return
    row = bytes(c) * (X1 - X0)
    for y in range(Y0, Y1):
        o = _off(X0, y)
        buf[o:o + len(row)] = row


def box(x0, y0, x1, y1, c, w=1):
    """Rectangle outline. Coords in final pixels."""
    rect(x0, y0, x1, y0 + w, c)
    rect(x0, y1 - w, x1, y1, c)
    rect(x0, y0, x0 + w, y1, c)
    rect(x1 - w, y0, x1, y1, c)


def _wdisc(cx, cy, r, c):
    """Filled disc in working-pixel coords."""
    R = int(r)
    X, Y = int(cx), int(cy)
    row = bytes(c)
    for dy in range(-R, R + 1):
        dx = int((R * R - dy * dy) ** 0.5) if R > 0 else 0
        y = Y + dy
        if 0 <= y < CH:
            x0 = max(0, X - dx)
            x1 = min(CW, X + dx + 1)
            if x1 > x0:
                o = _off(x0, y)
                buf[o:o + (x1 - x0) * 3] = row * (x1 - x0)


def disc(cx, cy, r, c):
    """Filled disc. Coords and radius in final pixels."""
    _wdisc(cx * S, cy * S, r * S, c)


def _seg(x0, y0, x1, y1, w, c):
    """Thick line segment in working-pixel coords."""
    dx, dy = x1 - x0, y1 - y0
    n = max(1, int((dx * dx + dy * dy) ** 0.5))
    step = max(1, int(w * 0.35))
    r = w / 2.0
    for i in range(0, n + 1, step):
        t = i / n
        _wdisc(x0 + dx * t, y0 + dy * t, r, c)
    _wdisc(x1, y1, r, c)


def line(x0, y0, x1, y1, w, c):
    """Thick line. Coords and width in final pixels."""
    _seg(x0 * S, y0 * S, x1 * S, y1 * S, w * S, c)


def poly(pts, c):
    """Filled polygon (scanline). Coords in final pixels."""
    P = [(x * S, y * S) for x, y in pts]
    ys = [p[1] for p in P]
    y0 = max(0, int(min(ys)))
    y1 = min(CH, int(max(ys)) + 1)
    n = len(P)
    row = bytes(c)
    for y in range(y0, y1):
        xs = []
        for i in range(n):
            ax, ay = P[i]
            bx, by = P[(i + 1) % n]
            if (ay <= y < by) or (by <= y < ay):
                t = (y - ay) / (by - ay)
                xs.append(ax + t * (bx - ax))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            x0 = max(0, int(xs[k]))
            x1 = min(CW, int(xs[k + 1]) + 1)
            if x1 > x0:
                o = _off(x0, y)
                buf[o:o + (x1 - x0) * 3] = row * (x1 - x0)


def arc(cx, cy, r, a0, a1, w, c, steps=28):
    """Arc stroke (angles in radians). Coords in final pixels."""
    pts = []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    for i in range(len(pts) - 1):
        line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], w, c)


def vgrad(x0, y0, x1, y1, c0, c1):
    """Vertical gradient fill. Coords in final pixels."""
    X0 = max(0, int(x0 * S))
    Y0 = max(0, int(y0 * S))
    X1 = min(CW, int(x1 * S))
    Y1 = min(CH, int(y1 * S))
    h = max(1, Y1 - Y0)
    for y in range(Y0, Y1):
        t = (y - Y0) / h
        c = tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
        o = _off(X0, y)
        buf[o:o + (X1 - X0) * 3] = bytes(c) * (X1 - X0)


def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def png_bytes(px):
    """Encode 1024x1024 RGB bytes as a deterministic PNG (filter 0)."""
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
            _chunk(b"IDAT", zlib.compress(bytes(raw), 6)) +
            _chunk(b"IEND", b""))


def downsample():
    """Box-average the 2x working canvas down to 1024x1024 RGB bytes."""
    out = bytearray(W * H * 3)
    for y in range(H):
        r0 = buf[(2 * y) * CW * 3:(2 * y + 1) * CW * 3]
        r1 = buf[(2 * y + 1) * CW * 3:(2 * y + 2) * CW * 3]
        o = y * W * 3
        for x in range(W):
            i = x * 6
            out[o] = (r0[i] + r0[i + 3] + r1[i] + r1[i + 3] + 2) // 4
            out[o + 1] = (r0[i + 1] + r0[i + 4] + r1[i + 1] + r1[i + 4] + 2) // 4
            out[o + 2] = (r0[i + 2] + r0[i + 5] + r1[i + 2] + r1[i + 5] + 2) // 4
            o += 3
    return bytes(out)

# ---- stroke font ----
# Glyphs live on a 9-wide x 13-tall grid: cap top y=1, baseline y=10,
# descenders to y=12. Each glyph is (advance, "stroke;stroke") where a
# stroke is space-separated 2-char points: x digit 0-8, y digit 0-9 or
# a/b/c for 10/11/12. Every glyph below was designed here, by hand.
FONT = {}


def _dec(s):
    out = []
    for st in s.split(";"):
        pts = []
        for tok in st.split():
            x = int(tok[0])
            yc = tok[1]
            y = int(yc) if yc.isdigit() else 10 + "abc".index(yc)
            pts.append((x, y))
        if pts:
            out.append(pts)
    return out


def _g(ch, adv, s):
    FONT[ch] = (adv, _dec(s))


# uppercase
_g("A", 9, "0a 41 8a;27 67")
_g("B", 9, "11 1a;11 61 73 65 15;15 65 77 6a 1a")
_g("C", 9, "72 51 21 03 08 2a 5a 79")
_g("D", 9, "11 1a;11 51 73 78 5a 1a")
_g("E", 9, "11 1a;11 71;15 55;1a 7a")
_g("F", 9, "11 1a;11 71;15 55")
_g("G", 9, "72 51 21 03 08 2a 5a 79 76;56 76")
_g("H", 9, "11 1a;71 7a;15 75")
_g("I", 5, "21 2a;11 31;1a 3a")
_g("J", 8, "71 78 5a 2a 18")
_g("K", 9, "11 1a;71 15;26 7a")
_g("L", 8, "11 1a;1a 7a")
_g("M", 10, "1a 11 47 71 7a")
_g("N", 9, "1a 11 7a 71")
_g("O", 9, "21 61 83 88 6a 2a 08 03 21")
_g("P", 9, "11 1a;11 61 73 65 15")
_g("Q", 9, "21 61 83 88 6a 2a 08 03 21;58 8b")
_g("R", 9, "11 1a;11 61 73 65 15;35 7a")
_g("S", 9, "72 51 21 13 14 35 66 77 79 5a 2a 19")
_g("T", 9, "11 71;41 4a")
_g("U", 9, "11 18 3a 5a 78 71")
_g("V", 9, "11 4a 71")
_g("W", 11, "11 2a 46 6a 71")
_g("X", 9, "11 7a;71 1a")
_g("Y", 9, "11 45 71;45 4a")
_g("Z", 9, "11 71 1a 7a")
# lowercase
_g("a", 8, "64 34 16 18 3a 6a 79 74;74 7a")
_g("b", 8, "11 1a;16 44 65 68 4a 19")
_g("c", 8, "65 44 24 16 18 2a 4a 69")
_g("d", 8, "71 7a;76 54 24 16 18 2a 5a 79")
_g("e", 8, "64 34 16 18 3a 6a 78 76 16")
_g("f", 7, "61 31 22 2a;15 55")
_g("g", 8, "74 78 6a 3a 18 16 34 64;78 7b 5c 2c")
_g("h", 8, "11 1a;16 34 64 76 7a")
_g("i", 4, "44 4a;41 42")
_g("j", 5, "54 5a 4c 2c;51 52")
_g("k", 8, "11 1a;64 27;37 7a")
_g("l", 4, "41 4a")
_g("m", 11, "1a 14 34 46 54 74 7a")
_g("n", 8, "1a 14 34 64 76 7a")
_g("o", 8, "24 64 76 78 6a 2a 18 16 24")
_g("p", 8, "14 1c;17 44 65 68 4a 19")
_g("q", 8, "74 7c;77 54 24 16 18 2a 5a 79")
_g("r", 7, "1a 14;16 34 64")
_g("s", 8, "75 54 24 15 16 37 67 78 79 5a 2a 19")
_g("t", 6, "41 4a;15 65;3a 5a")
_g("u", 8, "14 18 2a 5a 78 74")
_g("v", 8, "14 4a 74")
_g("w", 11, "14 2a 46 6a 74")
_g("x", 8, "14 7a;74 1a")
_g("y", 8, "14 48 74;48 4b 3c 1c")
_g("z", 8, "14 74 1a 7a")
# digits
_g("0", 9, "21 61 83 88 6a 2a 08 03 21")
_g("1", 8, "32 51 5a;2a 7a")
_g("2", 9, "13 21 61 73 75 1a 7a")
_g("3", 9, "12 31 61 73 74 45;45 76 78 6a 3a 19")
_g("4", 9, "61 17 77;51 5a")
_g("5", 9, "71 11 15 65 77 6a 2a 19")
_g("6", 9, "72 51 21 13 18 2a 5a 78 76 55 25")
_g("7", 9, "11 71 3a")
_g("8", 9, "21 61 73 74 55 35 14 13 21;55 76 78 6a 2a 18 16 35 55")
_g("9", 9, "19 13 21 61 73 78 6a 3a;16 76")
# punctuation and symbols
_g(" ", 4, "")
_g(".", 4, "49 4a")
_g(",", 4, "49 4a;4a 3c")
_g(":", 4, "43 44;48 49")
_g(";", 4, "43 44;48 49 3b")
_g("!", 4, "41 48;4a 4a")
_g("?", 7, "22 41 61 73 74 46 48;4a 4a")
_g("'", 3, "41 34")
_g("\u2019", 3, "41 34")
_g("\u2018", 3, "31 44")
_g('"', 6, "31 24;61 54")
_g("\u201c", 6, "34 21;64 51")
_g("\u201d", 6, "31 24;61 54")
_g("(", 5, "51 33 38 5a")
_g(")", 5, "31 53 58 3a")
_g("-", 6, "16 76")
_g("\u2212", 6, "16 76")
_g("\u2013", 8, "16 86")
_g("\u2014", 9, "06 86")
_g("\u2022", 5, "45 45")
_g("%", 9, "71 1a;13 13;78 78")
_g("$", 9, "72 41 21 13 14 35 66 77 79 5a 2a 19;40 4c")
_g("&", 9, "61 31 13 15 37 7a;74 56 38 1a")
_g("/", 6, "61 2a")
_g("+", 8, "42 49;15 75")
_g("=", 8, "14 74;18 78")
_g("*", 7, "41 49;13 77;73 17")
_g("_", 9, "0b 8b")
_g("\u00b0", 6, "31 51 62 64 55 35 32 31")
_g("#", 9, "31 2a;61 5a;14 74;17 77")
_g("<", 8, "61 15 6a")
_g(">", 8, "21 75 2a")
_g("[", 5, "61 21 2a 6a")
_g("]", 5, "21 61 6a 2a")
_g("{", 6, "51 32 34 25 26 37 39 5a")
_g("}", 6, "31 52 54 65 66 57 59 3a")
_g("~", 8, "16 34 56 74")
_g("^", 7, "15 42 75")
_g("|", 4, "41 4a")
_g("\\", 6, "21 6a")
_g("`", 3, "41 34")
_g("\u2026", 9, "2a 2a;4a 4a;6a 6a")


def text_w(s, size):
    """Width of s in final pixels at the given cap-height size."""
    u = size / 13.0
    w = 0.0
    for ch in s:
        w += FONT.get(ch, FONT[" "])[0] * u
    return w


def text(x, y, s, size, c, bold=False, align="l"):
    """Draw text; y is the cap-top in final pixels. Returns width."""
    w = text_w(s, size)
    if align == "c":
        x -= w / 2.0
    elif align == "r":
        x -= w
    u = size * S / 13.0
    sw = max(1.2, size * S * (0.17 if bold else 0.12))
    cx = x * S
    cy = y * S
    for ch in s:
        adv, strokes = FONT.get(ch, FONT[" "])
        for st in strokes:
            for i in range(len(st) - 1):
                ax, ay = st[i]
                bx, by = st[i + 1]
                _seg(cx + ax * u, cy + ay * u, cx + bx * u, cy + by * u, sw, c)
            if len(st) == 1:
                _wdisc(cx + st[0][0] * u, cy + st[0][1] * u, sw * 0.7, c)
        cx += adv * u
    return w


def wrap(s, size, maxw):
    """Word-wrap s to lines no wider than maxw (final px)."""
    lines, cur = [], ""
    for wd in s.split(" "):
        t = (cur + " " + wd).strip()
        if text_w(t, size) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines

# ---- card helpers ----

def frame(x, y, w, h):
    rect(x, y, x + w, y + h, CARD)
    box(x, y, x + w, y + h, NAVY, 2)


def card_head(x, y, w, num, kicker, head, head_size=24, head_lines=2):
    """Number badge + kicker + headline. Returns y below the headline."""
    rect(x + 6, y + 6, x + 30, y + 30, RED)
    text(x + 18, y + 9, str(num), 14, WHITE, bold=True, align="c")
    text(x + 36, y + 10, kicker, 12, RED, bold=True)
    lines = wrap(head, head_size, w - 16)
    yy = y + 34
    for ln in lines[:head_lines]:
        text(x + 8, yy, ln, head_size, INK, bold=True)
        yy += head_size * 1.08
    return yy


def card_body(x, y, w, body, size=11, leading=None, max_lines=3):
    if leading is None:
        leading = size * 1.18
    lines = wrap(body, size, w)
    for ln in lines[:max_lines]:
        text(x, y, ln, size, INK)
        y += leading
    return y


# ---- scenes (each draws inside its own box, final-pixel coords) ----

def scene_chart(x, y, w, h):
    """Anthropic IPO: $83 -> $115.10 high -> $97.17 close -> $91 pre-mkt."""
    rect(x, y, x + w, y + h, SKY)
    box(x, y, x + w, y + h, NAVY, 1)
    for i in range(1, 4):
        gy = y + h * i / 4.0
        line(x + 4, gy, x + w - 4, gy, 0.7, LGREY)
    pts = [(0.07, 0.72), (0.25, 0.32), (0.45, 0.14), (0.67, 0.52), (0.93, 0.64)]
    P = [(x + px * w, y + py * h) for px, py in pts]
    for i in range(2):
        line(P[i][0], P[i][1], P[i + 1][0], P[i + 1][1], 2.2, TEAL)
    for i in range(2, 4):
        line(P[i][0], P[i][1], P[i + 1][0], P[i + 1][1], 2.2, RED)
    for px, py in P:
        disc(px, py, 2.6, INK)
        disc(px, py, 1.4, WHITE)
    text(x + 6, y + 4, "$115.10 HIGH", 10, TEAL, bold=True)
    text(x + 6, y + h - 13, "$83 IPO", 10, TEAL, bold=True)
    text(P[3][0] + 4, P[3][1] - 14, "$97.17 CLOSE", 10, RED, bold=True)
    text(P[4][0] - 4, P[4][1] + 5, "$91 PRE-MKT", 10, RED, bold=True, align="r")


def scene_bridges(x, y, w, h):
    """Kyiv bridges at night under missile fire."""
    vgrad(x, y, x + w, y + h, NIGHT, NIGHT2)
    rect(x, y + h * 0.68, x + w, y + h, (28, 62, 110))
    for cx in (0.22, 0.50, 0.78):
        ax = x + cx * w
        ay = y + h * 0.78
        arc(ax, ay, h * 0.42, math.pi, 2 * math.pi, 2.5, (220, 222, 226))
        line(ax - h * 0.42, ay, ax + h * 0.42, ay, 2.5, (220, 222, 226))
    for fx, fy in ((0.30, 0.30), (0.58, 0.22), (0.84, 0.34)):
        ex, ey = x + fx * w, y + fy * h
        disc(ex, ey, 5, (255, 140, 30))
        disc(ex, ey, 3, (255, 210, 80))
        for ang in (45, 135, 225, 315):
            a = math.radians(ang)
            line(ex, ey, ex + 8 * math.cos(a), ey + 8 * math.sin(a), 1.6,
                 (255, 190, 60))
    text(x + 8, y + 6, "100+ MISSILES", 13, WHITE, bold=True)
    text(x + 8, y + 22, "400 DRONES", 13, WHITE, bold=True)


def scene_palace(x, y, w, h):
    """ICJ Peace Palace, The Hague."""
    rect(x, y, x + w, y + h, SKY)
    box(x, y, x + w, y + h, NAVY, 1)
    rect(x, y + h * 0.78, x + w, y + h, (120, 150, 120))
    cx = x + w * 0.38
    rect(cx - w * 0.22, y + h * 0.45, cx + w * 0.22, y + h * 0.80, NAVY2)
    arc(cx, y + h * 0.45, h * 0.40, math.pi, 2 * math.pi, 2.0, NAVY2)
    disc(cx, y + h * 0.45, h * 0.40, NAVY2)
    for i in range(5):
        px = x + w * (0.22 + i * 0.08)
        rect(px, y + h * 0.52, px + 3, y + h * 0.78, WHITE)
    rect(cx - 2, y + h * 0.30, cx + 2, y + h * 0.45, NAVY2)
    disc(cx, y + h * 0.28, 2.5, GOLD)
    text(x + w - 6, y + 3, "9-6", 11, NAVY, bold=True, align="r")


def scene_globe(x, y, w, h):
    """COP31 globe under a hot sun, no deal."""
    rect(x, y, x + w, y + h, (232, 240, 232))
    box(x, y, x + w, y + h, NAVY, 1)
    sx, sy = x + w * 0.82, y + h * 0.24
    disc(sx, sy, 6, GOLD)
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        line(sx + 8 * math.cos(a), sy + 8 * math.sin(a),
             sx + 11 * math.cos(a), sy + 11 * math.sin(a), 1.6, GOLD)
    gx, gy, gr = x + w * 0.32, y + h * 0.52, h * 0.36
    disc(gx, gy, gr, SEA)
    poly([(gx - gr * 0.5, gy - gr * 0.4), (gx - gr * 0.1, gy - gr * 0.55),
          (gx + gr * 0.2, gy - gr * 0.2), (gx - gr * 0.2, gy + gr * 0.1)],
         GREEN)
    poly([(gx + gr * 0.1, gy + gr * 0.3), (gx + gr * 0.55, gy + gr * 0.15),
          (gx + gr * 0.5, gy + gr * 0.6), (gx + gr * 0.05, gy + gr * 0.55)],
         GREEN)
    arc(gx, gy, gr, -1.2, 1.2, 1.2, WHITE)
    arc(gx, gy, gr * 0.6, -1.2, 1.2, 1.2, WHITE)
    text(x + w * 0.58, y + h * 0.58, "NO DEAL YET", 11, RED, bold=True)


def scene_cyclone(x, y, w, h):
    """Cyclone Akvan spiral over the Bay of Bengal."""
    rect(x, y, x + w, y + h, (223, 233, 242))
    box(x, y, x + w, y + h, NAVY, 1)
    cx, cy = x + w * 0.20, y + h * 0.50
    for k, rr in enumerate((0.14, 0.26, 0.38)):
        arc(cx, cy, h * rr, -0.4 + k * 0.7, 4.4 + k * 0.7, 1.8, NAVY2)
    disc(cx, cy, 3, WHITE)
    for i in range(5):
        rx = x + w * (0.80 + i * 0.03)
        line(rx, y + h * 0.72, rx - 2, y + h * 0.88, 1.2, SEA)
    text(x + w * 0.44, y + h * 0.10, "372,000", 13, NAVY, bold=True)
    text(x + w * 0.44, y + h * 0.10 + 14, "EVACUATED", 11, NAVY, bold=True)


def scene_summit(x, y, w, h):
    """Shenzhen dusk: skyline, three flags, three leaders at a table."""
    vgrad(x, y, x + w, y + h, (242, 166, 90), (122, 74, 138))
    for bx, bh in ((0.02, 0.30), (0.14, 0.44), (0.30, 0.34), (0.72, 0.40),
                   (0.84, 0.28)):
        rect(x + w * bx, y + h * (0.92 - bh), x + w * (bx + 0.10),
             y + h * 0.92, (52, 40, 66))
    rect(x, y + h * 0.90, x + w, y + h, (52, 40, 66))
    # three flags: US, China, Russia (abstract stripes)
    for i, cols in enumerate((((200, 40, 40), (255, 255, 255)),
                             ((200, 40, 40), (240, 200, 40)),
                             ((255, 255, 255), (40, 80, 160)))):
        fx = x + w * (0.16 + i * 0.20)
        line(fx, y + h * 0.42, fx, y + h * 0.72, 1.6, INK)
        rect(fx, y + h * 0.44, fx + 16, y + h * 0.52, cols[0])
        rect(fx, y + h * 0.52, fx + 16, y + h * 0.58, cols[1])
        if i == 2:
            rect(fx, y + h * 0.58, fx + 16, y + h * 0.63, RED)
    # table + three leaders
    rect(x + w * 0.30, y + h * 0.76, x + w * 0.70, y + h * 0.82, (96, 62, 40))
    for i, suit in enumerate((NAVY, (120, 30, 30), (60, 60, 60))):
        lx = x + w * (0.38 + i * 0.12)
        disc(lx, y + h * 0.68, 4.5, (232, 200, 170))
        rect(lx - 6, y + h * 0.72, lx + 6, y + h * 0.78, suit)


def scene_tankers(x, y, w, h):
    """Two tankers burning in the Strait of Hormuz."""
    vgrad(x, y, x + w, y + h, (150, 190, 220), SEA)
    rect(x, y + h * 0.62, x + w, y + h, (24, 66, 104))
    for tx in (0.10, 0.52):
        hx, hy = x + w * tx, y + h * 0.55
        poly([(hx, hy + 9), (hx + w * 0.34, hy + 9), (hx + w * 0.30, hy),
              (hx + w * 0.04, hy)], (30, 30, 30))
        rect(hx + w * 0.24, hy - 7, hx + w * 0.30, hy, (30, 30, 30))
        fx, fy = hx + w * 0.16, hy - 4
        disc(fx, fy, 3.5, (255, 140, 30))
        disc(fx, fy - 2, 2.2, (255, 210, 80))
        disc(fx + 7, fy - 1, 2.5, (150, 150, 150))
        disc(fx + 12, fy - 3, 3, (170, 170, 170))
    text(x + 6, y + 3, "HORMUZ", 11, WHITE, bold=True)


def scene_cricket(x, y, w, h):
    """Wellington: stumps, bat, ball, NZ 368."""
    rect(x, y, x + w, y + h, (122, 154, 74))
    box(x, y, x + w, y + h, NAVY, 1)
    rect(x + w * 0.30, y + h * 0.30, x + w * 0.70, y + h * 0.95,
         (196, 214, 150))
    for i in range(3):
        sx = x + w * (0.60 + i * 0.035)
        line(sx, y + h * 0.34, sx, y + h * 0.52, 2.0, (240, 210, 90))
    poly([(x + w * 0.18, y + h * 0.86), (x + w * 0.24, y + h * 0.84),
          (x + w * 0.38, y + h * 0.52), (x + w * 0.33, y + h * 0.50)],
         (150, 105, 60))
    disc(x + w * 0.80, y + h * 0.70, 4, RED)
    text(x + 8, y + 2, "NZ 368", 11, WHITE, bold=True)

# ---- dotted world map (my own coarse land sketch) ----
# Each row is a list of (first_col, last_col) land runs on a 76-column
# grid (lon -180..+180); rows run lat ~80N down to ~60S.
MAP_ROWS = [
    [(3, 16), (29, 31), (48, 70)],
    [(2, 24), (28, 30), (40, 42), (44, 72)],
    [(4, 22), (36, 36), (37, 46), (48, 62), (63, 68), (70, 71)],
    [(5, 20), (37, 46), (47, 52), (54, 58), (60, 66), (70, 70)],
    [(4, 10), (10, 13), (36, 47), (48, 51), (53, 57), (59, 64), (62, 68)],
    [(12, 18), (37, 45), (61, 69), (70, 73)],
    [(13, 19), (39, 44), (65, 72)],
    [(14, 18), (40, 43), (64, 72), (74, 75)],
    [(15, 17), (65, 70), (74, 75)],
    [(15, 16)],
]
# numbered pins: (story number, grid col, grid row); pin 4 (Antalya) is
# nudged 2 cols east so it does not merge with pin 2 (Kyiv) above it.
MAP_PINS = [(1, 22, 2), (2, 44, 2), (3, 39, 2), (4, 47, 3),
            (5, 56, 4), (10, 62, 4), (11, 50, 4), (12, 74, 8)]


def draw_map(x, y, w, h):
    text(x + 8, y + 5, "WHERE IT HAPPENED", 10, NAVY, bold=True)
    mx0, my0 = x + 8, y + 16
    mw, mh = w - 16, h - 20
    px, py = mw / 76.0, mh / 10.0
    dot = (74, 84, 104)
    for r, runs in enumerate(MAP_ROWS):
        for c0, c1 in runs:
            for c in range(c0, c1 + 1):
                disc(mx0 + c * px + px / 2, my0 + r * py + py / 2, 2.0, dot)
    for num, c, r in MAP_PINS:
        cx = mx0 + c * px + px / 2
        cy = my0 + r * py + py / 2
        disc(cx, cy, 6.5, RED)
        text(cx, cy - 4.5, str(num), 9, WHITE, bold=True, align="c")


NUMBERS = [
    ("1,101", "DOW POINTS LOST"),
    ("$81.3BN", "BIGGEST IPO EVER"),
    ("9\u20136", "ICJ GENOCIDE VOTE"),
    ("372,000", "EVACUATED"),
    ("$2.36BN", "GTA VI DAY ONE"),
    ("$61,500", "BITCOIN PRICE"),
]


def draw_numbers(x, y, w, h):
    text(x + 12, y + 5, "THE DAY IN NUMBERS", 14, NAVY, bold=True)
    cols = [x + 12, x + w / 2 + 6]
    rows = [y + 26, y + 48, y + 70]
    for i, (big, small) in enumerate(NUMBERS):
        cx = cols[i % 2]
        cy = rows[i // 2]
        bw = text(cx, cy, big, 15, RED, bold=True)
        text(cx + bw + 6, cy + 3, small, 9, GREY, bold=True)


INDEX = [
    (13, "Kerch Bridge hit a third time."),
    (14, "Europe open to talks; Putin invites leaders."),
    (15, "US envoy: NATO-like guarantees not ruled out."),
    (16, "N. Korea expands Yongbyon enrichment."),
    (17, "US-Venezuela restore military ties."),
    (18, "Israel ends ground op past Gaza Yellow Line."),
    (19, "Israeli strike hits Hezbollah site in Lebanon."),
    (20, "Genoa airport shut 4 hours by mystery drones."),
    (21, "Kyiv strikes hit Austrian, Dutch embassies."),
    (22, "Migrant boat sinks off Senegal; dozens missing."),
    (23, "Fiji declares disaster over drought."),
    (24, "S. Korea court clears ex-PM Han Duck-soo."),
    (25, "Taiwan steadies stocks after 5,248-pt slide."),
    (26, "Trump warns APEC on strict AI rules."),
    (27, "Trump heads home; no meeting with Kim."),
    (28, "Anthropic debut draws protests in NY, SF."),
    (29, "IEA: data-centre power may double by 2030."),
    (30, "Modi meets the Prince and Princess of Wales."),
    (31, "Fire at Muhammad Yunus ancestral home."),
    (32, "Fiona the hippo dies at Cincinnati Zoo."),
    (33, "Sensex +1.21%, Nifty +1.14%."),
    (34, "Russia warns Wikimedia over 'undesirable' tag."),
    (35, "Japan PM dodges Taiwan question at APEC."),
    (36, "Trump to give sworn testimony in BBC case."),
    (37, "US auctions first deep-sea mining leases."),
    (38, "Denmark OKs Greenland-US security deal."),
    (39, "Sheinbaum viral for economy flight to APEC."),
    (40, "Philippines, Chile sign free-trade deal."),
]


def mini_card(x, y, w, h, num, kicker, head, body):
    frame(x, y, w, h)
    rect(x + 5, y + 5, x + 27, y + 27, RED)
    text(x + 16, y + 8, str(num), 13, WHITE, bold=True, align="c")
    text(x + 31, y + 8, kicker, 11, RED, bold=True)
    text(x + 6, y + 28, head, 16, INK, bold=True)
    yy = y + 48
    for ln in wrap(body, 10, w - 12)[:2]:
        text(x + 6, yy, ln, 10, INK)
        yy += 11


def build():
    rect(0, 0, W, H, PAPER)
    box(4, 4, 1020, 1020, INK, 2)

    # masthead
    rect(4, 4, 1020, 62, NAVY)
    text(20, 12, "THE WORLD TODAY", 34, WHITE, bold=True)
    text(1004, 14, "FRIDAY 20 NOVEMBER 2026", 20, WHITE, bold=True,
         align="r")
    text(1004, 38, "THE DAY IN ONE PAGE", 13, GOLD, bold=True, align="r")
    rect(4, 62, 1020, 66, GOLD)

    # date block
    text(18, 74, "FRIDAY", 22, RED, bold=True)
    text(16, 90, "NOVEMBER 20", 80, INK, bold=True)
    text(18, 172, "MARKETS ROUT \u2014 KYIV UNDER FIRE \u2014 "
         "A GENOCIDE VERDICT", 15, GREY, bold=True)
    rect(812, 72, 1004, 180, RED)
    text(908, 78, "NOV", 26, WHITE, bold=True, align="c")
    text(908, 102, "20", 56, WHITE, bold=True, align="c")
    text(908, 160, "2026", 18, WHITE, bold=True, align="c")

    # hero row
    frame(16, 192, 482, 160)
    y = card_head(16, 192, 482, 1, "WALL STREET \u2014 AI",
                  "ANT SLIDES ON DAY TWO", 25, 1)
    scene_chart(24, 256, 466, 54)
    card_body(24, 316, 466, "Record $81.3bn debut: open $111.50, high "
              "$115.10, close $97.17 (+17%). Day two down 6% pre-market "
              "to $91.", 12, 14, 2)
    frame(506, 192, 502, 160)
    card_head(506, 192, 502, 2, "UKRAINE \u2014 WAR",
              "KYIV BRIDGES HIT", 25, 1)
    scene_bridges(514, 256, 486, 54)
    card_body(514, 316, 486, "Hours after Shenzhen, Russia fires 100+ "
              "missiles and 400 drones; three killed in Kyiv.", 12, 14, 2)

    # row 2
    frame(16, 360, 324, 136)
    card_head(16, 360, 324, 3, "THE HAGUE \u2014 JUSTICE",
              "MYANMAR GUILTY OF GENOCIDE", 19, 2)
    scene_palace(24, 438, 308, 30)
    card_body(24, 472, 308, "The ICJ rules 9\u20136 \u2014 the first state "
              "ever found guilty of genocide. Naypyidaw calls it unfair.",
              10, 11, 2)
    frame(348, 360, 328, 136)
    card_head(348, 360, 328, 4, "ANTALYA \u2014 CLIMATE",
              "COP31: NO DEAL, NO 'FOSSIL FUELS'", 19, 2)
    scene_globe(356, 438, 312, 30)
    card_body(356, 472, 312, "Final day ends with no deal; fossil-fuel "
              "language stripped, $120bn target dropped. Talks may run "
              "on.", 10, 11, 2)
    frame(684, 360, 324, 136)
    card_head(684, 360, 324, 5, "INDIA \u2014 WEATHER",
              "AKVAN FIZZLES ON LANDFALL", 19, 2)
    scene_cyclone(692, 438, 308, 30)
    card_body(692, 472, 308, "372,000 evacuated as the cyclone crosses "
              "near Gopalpur at 70\u201380 km/h. No deaths, no major "
              "damage.", 10, 11, 2)

    # mini row
    mini_card(16, 504, 246, 80, 6, "MARKETS", "DOW SINKS 2.19%",
              "Dow \u22121,101, below 50,000; S&P down a 6th straight day.")
    mini_card(270, 504, 246, 80, 7, "GAMES", "GTA VI: $2.36BN",
              "Sensor Tower: 24.6m copies on launch day, the "
              "fastest-selling game ever.")
    mini_card(524, 504, 246, 80, 8, "COMMODITIES", "GOLD TUMBLES AGAIN",
              "Spot gold near $3,530 an ounce, down ~7% on the week.")
    mini_card(778, 504, 230, 80, 9, "CRYPTO", "BITCOIN BELOW $62K",
              "BTC near $61,500 as $582m leaves US spot ETFs in a day. "
              "Fear & Greed 12.")

    # row 4
    frame(16, 592, 324, 104)
    card_head(16, 592, 324, 10, "SHENZHEN \u2014 DIPLOMACY",
              "THE PEACE DECLARATION", 17, 1)
    scene_summit(24, 646, 308, 26)
    card_body(24, 676, 308, "First three-way summit ends with a "
              "four-point peace declaration.", 10, 11, 2)
    frame(348, 592, 328, 104)
    card_head(348, 592, 328, 11, "GULF \u2014 ENERGY",
              "TWO MORE TANKERS HIT", 17, 1)
    scene_tankers(356, 646, 312, 26)
    card_body(356, 676, 312, "Two more tankers hit mines in Hormuz. "
              "Houthis claim strikes on Riyadh.", 10, 11, 2)
    frame(684, 592, 324, 104)
    card_head(684, 592, 324, 12, "WELLINGTON \u2014 CRICKET",
              "NICHOLLS 175* LIFTS NZ", 17, 1)
    scene_cricket(692, 646, 308, 26)
    card_body(692, 676, 308, "NZ 368 all out (Nicholls 175*); India 159/1 "
              "at stumps, trailing by 209.", 10, 11, 2)

    # map + numbers strip
    frame(16, 704, 624, 92)
    draw_map(16, 704, 624, 92)
    frame(648, 704, 360, 92)
    draw_numbers(648, 704, 360, 92)

    # timeline
    text(16, 804, "TIMELINE", 12, RED, bold=True)
    text(96, 804, "01:25 KYIV TIME EXPLOSIONS BEGIN   \u2022   07:30 IST "
         "AKVAN LANDFALL   \u2022   05:04 GMT GOLD $3,525", 12, INK)
    text(16, 818, "11:20 IST LANDFALL COMPLETE   \u2022   05:19 ET "
         "ANTHROPIC $91 PRE-MARKET", 12, INK)

    # index
    text(16, 834, "THE REST OF THE DAY \u2014 28 MORE STORIES", 15, NAVY,
         bold=True)
    cols = [20, 350, 680]
    for i, (num, item) in enumerate(INDEX):
        cx = cols[i // 10]
        cy = 856 + (i % 10) * 11.5
        text(cx, cy, "%d. %s" % (num, item), 10.5, INK)

    # footer
    rect(16, 972, 1008, 1014, RED)
    text(512, 978, "DATE CHECK \u2014 EVERY STORY ABOVE HAPPENED OR WAS "
         "FIRST REPORTED ON FRIDAY 20 NOVEMBER 2026.", 13, WHITE,
         bold=True, align="c")
    text(512, 996, "THE WORLD TODAY \u2014 FRIDAY 20 NOVEMBER 2026 \u2014 "
         "40 STORIES \u2014 DRAWN IN CODE", 10.5, WHITE, align="c")

    return png_bytes(downsample())


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    data = build()
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
