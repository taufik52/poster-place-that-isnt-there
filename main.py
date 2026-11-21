#!/usr/bin/env python3
"""AURELIA — travel poster generator for a place that does not exist.

Writes one travel poster to /output/entry.png (1024x1024 PNG, pure
standard library, no network): a sunset over the floating isles of
Aurelia, with the place name set large into the picture.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024
OUT = os.environ.get("POSTER_OUTPUT", "/output/entry.png")

# ---------------------------------------------------------------- pixels
buf = bytearray(W * H * 3)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rgb(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


def set_px(x, y, rgb):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = rgb


def blend_px(x, y, rgb, a):
    """Alpha-blend rgb over the pixel at (x, y); a in 0..1."""
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = int(buf[i] + (rgb[0] - buf[i]) * a)
        buf[i + 1] = int(buf[i + 1] + (rgb[1] - buf[i + 1]) * a)
        buf[i + 2] = int(buf[i + 2] + (rgb[2] - buf[i + 2]) * a)


def fill_row(y, rgb):
    i = (y * W) * 3
    buf[i:i + W * 3] = bytes(rgb) * W


def fill_ellipse(cx, cy, rx, ry, rgb, alpha=1.0):
    for y in range(max(0, cy - ry), min(H, cy + ry + 1)):
        dy = (y - cy) / ry
        dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
        x0, x1 = int(cx - dx), int(cx + dx)
        for x in range(max(0, x0), min(W, x1 + 1)):
            if alpha >= 1.0:
                set_px(x, y, rgb)
            else:
                blend_px(x, y, rgb, alpha)


# ---------------------------------------------------------------- sky
SKY_TOP = (26, 32, 92)       # deep indigo
SKY_MID = (122, 62, 140)     # violet
SKY_LOW = (232, 116, 76)     # burnt orange
SKY_HOR = (250, 190, 110)    # golden horizon
HORIZON = 640

for y in range(HORIZON):
    t = y / HORIZON
    if t < 0.45:
        c = lerp_rgb(SKY_TOP, SKY_MID, t / 0.45)
    elif t < 0.8:
        c = lerp_rgb(SKY_MID, SKY_LOW, (t - 0.45) / 0.35)
    else:
        c = lerp_rgb(SKY_LOW, SKY_HOR, (t - 0.8) / 0.2)
    fill_row(y, c)

# ---------------------------------------------------------------- sun + glow
SUN_X, SUN_Y, SUN_R = 712, 400, 92
SUN_CORE = (255, 244, 214)
SUN_GLOW = (255, 176, 92)
GLOW_R = 260
for y in range(max(0, SUN_Y - GLOW_R), min(HORIZON, SUN_Y + GLOW_R + 1)):
    for x in range(max(0, SUN_X - GLOW_R), min(W, SUN_X + GLOW_R + 1)):
        d = math.hypot(x - SUN_X, y - SUN_Y)
        if d < SUN_R:
            set_px(x, y, SUN_CORE)
        elif d < GLOW_R:
            blend_px(x, y, SUN_GLOW, 0.55 * (1 - d / GLOW_R))

# ---------------------------------------------------------------- clouds
for (cx, cy, rx, ry, a) in [
        (200, 210, 150, 26, 0.30), (330, 235, 110, 20, 0.25),
        (820, 180, 170, 24, 0.28), (620, 130, 120, 18, 0.22),
        (120, 470, 130, 20, 0.20), (900, 500, 150, 22, 0.18)]:
    fill_ellipse(cx, cy, rx, ry, (255, 214, 178), a)

# ---------------------------------------------------------------- far mountains
# Ridge height as a function of x: interpolate the peak points, then fill
# from the ridge line down to the horizon (one clean silhouette).
MT = (58, 36, 96)
RIDGE_X = [0, 120, 260, 400, 540, 680, 820, 940, 1024]
RIDGE_Y = [640, 560, 610, 545, 615, 560, 620, 575, 630]


def ridge_y(x):
    for i in range(len(RIDGE_X) - 1):
        if RIDGE_X[i] <= x <= RIDGE_X[i + 1]:
            t = (x - RIDGE_X[i]) / (RIDGE_X[i + 1] - RIDGE_X[i])
            return RIDGE_Y[i] + (RIDGE_Y[i + 1] - RIDGE_Y[i]) * t
    return RIDGE_Y[-1]


for x in range(W):
    ry = int(ridge_y(x))
    for y in range(ry, HORIZON):
        set_px(x, y, MT)

# ---------------------------------------------------------------- sea
SEA_TOP = (64, 84, 138)
SEA_BOT = (16, 30, 74)
for y in range(HORIZON, H):
    t = (y - HORIZON) / (H - HORIZON)
    fill_row(y, lerp_rgb(SEA_TOP, SEA_BOT, t))

# sun reflection: long golden dashes on the water under the sun
for y in range(HORIZON + 6, H - 8, 4):
    t = (y - HORIZON) / (H - HORIZON)
    half = int(30 + 190 * (1 - t) + 40 * math.sin(y * 0.11))
    for x in range(SUN_X - half, SUN_X + half + 1):
        if ((x + y * 7) // 16) % 7 < 4:
            blend_px(x, y, (255, 196, 120), 0.5 * (1 - t * 0.6))

# ---------------------------------------------------------------- floating isles
def island(cx, cy, s, rock, leaf, fall_len):
    """One floating isle: green top, rocky inverted cone, waterfall."""
    # grassy top (flattened ellipse)
    fill_ellipse(cx, cy, int(150 * s), int(34 * s), leaf)
    fill_ellipse(cx, cy - int(10 * s), int(120 * s), int(22 * s),
                 lerp_rgb(leaf, (255, 255, 255), 0.25))
    # rocky underside: triangle narrowing to a point
    top_w = int(140 * s)
    tip_y = cy + int(150 * s)
    for y in range(cy, tip_y + 1):
        t = (y - cy) / max(1, tip_y - cy)
        hw = int(top_w * (1 - t))
        for x in range(cx - hw, cx + hw + 1):
            shade = 0.85 + 0.3 * ((x * 5 + y * 11) % 7) / 7.0
            set_px(x, y, (int(rock[0] * shade), int(rock[1] * shade),
                          int(rock[2] * shade)))
    # waterfall: pale streaks falling from the isle's edge
    for k in range(3):
        wx = cx - int(60 * s) + k * int(55 * s)
        for y in range(cy + int(20 * s), cy + int(20 * s) + fall_len):
            wob = int(3 * math.sin((y - cy) * 0.12 + k))
            set_px(wx + wob, y, (214, 238, 250))
            set_px(wx + wob + 1, y, (240, 248, 252))
    # tiny trees on top
    for tx in (cx - int(80 * s), cx + int(30 * s), cx + int(95 * s)):
        for dy in range(0, int(16 * s)):
            hw = max(1, int((16 * s - dy) * 0.45))
            for x in range(tx - hw, tx + hw + 1):
                set_px(x, cy - int(30 * s) - dy, (24, 92, 58))


island(360, 430, 1.0, (94, 68, 92), (46, 138, 84), 120)
island(800, 330, 0.62, (88, 62, 96), (52, 148, 88), 80)

# ---------------------------------------------------------------- birds
def bird(cx, cy, s):
    for dx in range(-s, s + 1):
        set_px(cx + dx, cy + abs(dx) // 2, (40, 30, 60))
        set_px(cx + dx, cy + abs(dx) // 2 + 1, (40, 30, 60))


bird(250, 300, 12)
bird(310, 270, 9)
bird(880, 240, 10)

# ---------------------------------------------------------------- place name
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
}


def draw_text(text, x0, y0, scale, rgb):
    for ci, ch in enumerate(text):
        glyph = FONT[ch]
        ox = x0 + ci * 6 * scale
        for r, row in enumerate(glyph):
            for c, bit in enumerate(row):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            set_px(ox + c * scale + dx,
                                   y0 + r * scale + dy, rgb)


NAME = "AURELIA"
SCALE = 13
TEXT_W = len(NAME) * 6 * SCALE - SCALE
TEXT_X = (W - TEXT_W) // 2
TEXT_Y = 108
# dark outline, then cream face
for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2)]:
    draw_text(NAME, TEXT_X + ox, TEXT_Y + oy, SCALE, (38, 24, 66))
draw_text(NAME, TEXT_X, TEXT_Y, SCALE, (255, 243, 214))
# thin gold rule under the name
for x in range(TEXT_X, TEXT_X + TEXT_W):
    for dy in range(4):
        set_px(x, TEXT_Y + 7 * SCALE + 14 + dy, (255, 205, 130))

# ---------------------------------------------------------------- write PNG
def chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = b"".join(b"\x00" + bytes(buf[y * W * 3:(y + 1) * W * 3])
                   for y in range(H))
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
           chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


size = write_png(OUT)
print(f"wrote {OUT} ({W}x{H}, {size} bytes)")
