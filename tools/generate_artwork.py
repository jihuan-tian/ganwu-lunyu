#!/usr/bin/env python3
"""Ink-wash plates for the volume title pages.

Each mark is a brush tip dragged along a path: soft at the lift of the
brush, darker where it is pressed, with a few hairs missing so the stroke
is not a filled shape. The ground is transparent; the book paper is the paper.
"""

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artwork"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 900, 1200
TIP_W, TIP_H = 72, 18

# Pine-soot ink, plus the mineral colors of a lightly tinted wash.
BARK = (58, 36, 24)
INK = (36, 28, 22)
NEEDLE = (24, 118, 52)
NEEDLE_DEEP = (16, 86, 38)
CULM = (32, 96, 58)
CULM_NODE = (18, 62, 36)
LEAF = (30, 148, 64)
PLUM_PINK = (186, 48, 78)
PLUM_HEART = (214, 168, 42)
PEACH_PINK = (214, 78, 108)
TANGDI_GOLD = (214, 156, 36)
TANGDI_HEART = (168, 96, 18)
FRUIT = (206, 164, 42)
FRUIT_SHADE = (168, 112, 28)
WATER = (64, 118, 156)


def make_tip():
    """A soft brush footprint. The long axis is the width of the stroke.

    The edge is uneven, and a few hairs at the side are missing. There is no
    regular stripe: a stripe reads as a hatch, not as ink.
    """
    tip = Image.new("L", (TIP_W, TIP_H), 0)
    px = tip.load()
    rng = random.Random(2)
    for y in range(TIP_H):
        for x in range(TIP_W):
            nx = (x + 0.5) / TIP_W * 2 - 1
            ny = (y + 0.5) / TIP_H * 2 - 1
            d = nx * nx * 0.92 + ny * ny
            if d > 1:
                continue
            edge = (1 - d) ** 0.28
            grain = 0.9 + 0.1 * rng.random()
            if abs(nx) > 0.72 and rng.random() > 0.82:
                grain *= 0.35
            px[x, y] = int(255 * edge * grain)
    return tip.filter(ImageFilter.GaussianBlur(0.8))


class Brush:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.tip = make_tip()
        self.ink = INK

    def use(self, rgb):
        self.ink = rgb

    def blit(self, sprite, cx, cy):
        ox = int(round(cx - sprite.size[0] / 2))
        oy = int(round(cy - sprite.size[1] / 2))
        sx0 = max(0, -ox)
        sy0 = max(0, -oy)
        sx1 = min(sprite.size[0], W - ox)
        sy1 = min(sprite.size[1], H - oy)
        if sx1 <= sx0 or sy1 <= sy0:
            return
        crop = sprite.crop((sx0, sy0, sx1, sy1))
        dx, dy = ox + sx0, oy + sy0
        base = self.img.crop((dx, dy, dx + crop.size[0], dy + crop.size[1]))
        self.img.paste(Image.alpha_composite(base, crop), (dx, dy))

    def stamp(self, x, y, ang, width, alpha):
        if width < 0.8 or alpha < 6:
            return
        scale = width / TIP_W
        tw = max(1, int(TIP_W * scale))
        th = max(1, int(TIP_H * scale))
        tip = self.tip.resize((tw, th), Image.Resampling.BILINEAR)
        # The tip's long axis is its width, so turn that axis across the stroke.
        tip = tip.rotate(math.degrees(ang) + 90, resample=Image.Resampling.BICUBIC, expand=True)
        shade = tip.point(lambda v, a=alpha: 0 if v < 12 else int(v * a / 255))
        sprite = Image.new("RGBA", tip.size, self.ink + (0,))
        sprite.putalpha(shade)
        self.blit(sprite, x + self.rng.uniform(-0.3, 0.3), y + self.rng.uniform(-0.3, 0.3))

    def follow(self, samples, width, alpha=210, dry=0.0):
        """samples: (x, y, pressure). pressure is 0 where the brush lifts."""
        if len(samples) < 2:
            return
        acc = 0.0
        step = max(1.1, width * 0.07)
        prev = samples[0]
        for x, y, p in samples[1:]:
            dx, dy = x - prev[0], y - prev[1]
            seg = math.hypot(dx, dy)
            if seg < 0.2:
                prev = (x, y, p)
                continue
            ang = math.atan2(dy, dx)
            n = max(1, int(math.ceil(seg / step)))
            for i in range(n):
                t = i / n
                pr = prev[2] * (1 - t) + p * t
                if pr < 0.04:
                    continue
                if dry and self.rng.random() < dry * (1.1 - pr):
                    continue
                self.stamp(
                    prev[0] + dx * t,
                    prev[1] + dy * t,
                    ang,
                    width * (0.35 + 0.65 * pr),
                    alpha * (0.45 + 0.55 * pr),
                )
            prev = (x, y, p)

    def cubic(self, p0, p1, p2, p3, n=36, pressure=1.0, fade=0.12):
        pts = []
        for i in range(n + 1):
            t = i / n
            u = 1 - t
            x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
            y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
            pr = pressure
            if t < fade:
                pr *= t / fade
            if t > 1 - fade:
                pr *= (1 - t) / fade
            pts.append((x, y, pr))
        return pts

    def stroke(self, p0, p1, p2, p3, width, alpha=210, dry=0.0, fade=0.1, pressure=1.0):
        self.follow(self.cubic(p0, p1, p2, p3, pressure=pressure, fade=fade), width, alpha, dry)

    def leaf(self, x, y, angle_deg, length, width, alpha=200):
        ang = math.radians(angle_deg)
        bend = self.rng.uniform(-0.12, 0.12)
        pts = []
        n = 28
        for i in range(n + 1):
            t = i / n
            curve = math.sin(t * math.pi) * length * bend
            px = x + math.cos(ang) * t * length - math.sin(ang) * curve
            py = y + math.sin(ang) * t * length + math.cos(ang) * curve
            if t < 0.2:
                pr = (t / 0.2) ** 0.8
            else:
                pr = ((1 - t) / 0.8) ** 0.85
            pts.append((px, py, pr))
        self.follow(pts, width, alpha, dry=0.04)

    def _lay_color(self, shade):
        layer = Image.new("RGBA", (W, H), self.ink + (0,))
        layer.putalpha(shade)
        self.img = Image.alpha_composite(self.img, layer)

    def soft_fill(self, cx, cy, rx, ry, alpha, blur=6):
        """A boneless wash: one pressed pool of color, not a stack of strokes."""
        layer = Image.new("L", (W, H), 0)
        ImageDraw.Draw(layer).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
        self._lay_color(layer.point(lambda v, a=alpha: int(v * a / 255)))

    def soft_fill_rotated(self, cx, cy, rx, ry, rot_deg, alpha, blur=5):
        pad = int(max(rx, ry) * 2 + blur * 8 + 16)
        layer = Image.new("L", (pad, pad), 0)
        ImageDraw.Draw(layer).ellipse(
            (pad / 2 - rx, pad / 2 - ry, pad / 2 + rx, pad / 2 + ry), fill=255
        )
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
        layer = layer.rotate(rot_deg, resample=Image.Resampling.BICUBIC, center=(pad / 2, pad / 2))
        shade = layer.point(lambda v, a=alpha: int(v * a / 255))
        full = Image.new("L", (W, H), 0)
        full.paste(shade, (int(cx - pad / 2), int(cy - pad / 2)))
        self._lay_color(full)

    def petal(self, x, y, angle_deg, length, width, alpha=200):
        ang = math.radians(angle_deg)
        x0 = x + math.cos(ang) * length * 0.06
        y0 = y + math.sin(ang) * length * 0.06
        pts = []
        n = 16
        for i in range(n + 1):
            t = i / n
            px = x0 + math.cos(ang) * t * length
            py = y0 + math.sin(ang) * t * length
            pts.append((px, py, math.sin(t * math.pi) ** 0.9))
        self.follow(pts, width, alpha, dry=0.02)

    def blossom(self, x, y, radius, alpha=210, petals=5, spread=1.0, gap=0.36, heart=None):
        """Five boneless petals. A wider gap keeps the petals from fusing."""
        petal = self.ink
        turn = self.rng.uniform(0, math.tau)
        for k in range(petals):
            a = turn + k * math.tau / petals + self.rng.uniform(-0.05, 0.05)
            px = x + math.cos(a) * radius * gap
            py = y + math.sin(a) * radius * gap
            self.ink = petal
            self.soft_fill_rotated(
                px,
                py,
                radius * 0.55,
                radius * 0.34 * spread,
                math.degrees(a) + 90,
                alpha=alpha + self.rng.randint(-12, 6),
                blur=2.4,
            )
        if heart is not None:
            self.ink = heart
            self.soft_fill(x, y, radius * 0.16, radius * 0.16, min(255, alpha + 15), blur=1.3)
        self.ink = petal

    def sheaf(self, x, y, aim, length, count=16, spread=42, width=6.5):
        """A bundle of long needles, the mass that makes a pine read as a pine."""
        for n in range(count):
            a = math.radians(aim + (n - (count - 1) / 2) * (spread / max(1, count - 1)))
            reach = length * self.rng.uniform(0.82, 1.08)
            x2 = x + math.cos(a) * reach
            y2 = y + math.sin(a) * reach
            self.follow(
                [(x, y, 0.85), ((x + x2) / 2, (y + y2) / 2, 1.0), (x2, y2, 0.2)],
                width,
                alpha=230,
            )

    def culm(self, x, y0, y1, width, alpha, lean=0.0):
        y = y0
        n = 0
        while y < y1 - 40:
            h = 168 + (n % 2) * 24
            y2 = min(y + h, y1)
            if y2 - y < 70:
                break
            x1 = x + lean * (y - y0) / 120
            x2 = x + lean * (y2 - y0) / 120
            body = self.ink
            self.stroke(
                (x1, y + 3),
                (x1, y + (y2 - y) * 0.35),
                (x2, y + (y2 - y) * 0.65),
                (x2, y2 - 4),
                width,
                alpha=alpha,
                dry=0.05,
                fade=0.04,
            )
            # The node is a short press of the brush, darker than the culm.
            self.ink = CULM_NODE
            self.stroke(
                (x2 - width * 0.72, y2),
                (x2 - width * 0.2, y2 + 0.6),
                (x2 + width * 0.25, y2 - 0.4),
                (x2 + width * 0.72, y2 + 0.2),
                width * 0.22,
                alpha=min(255, alpha + 40),
                fade=0.2,
            )
            self.ink = body
            y = y2 + 8
            n += 1

    def save(self, name):
        # A hair of blur joins the stamps into one stroke.
        soft = self.img.filter(ImageFilter.GaussianBlur(0.45))
        soft.save(OUT / name, "PNG")


def pine():
    b = Brush(11)
    b.use(BARK)
    b.stroke((140, 1040), (240, 820), (340, 620), (420, 460), 36, alpha=235, dry=0.06, fade=0.05)
    b.stroke((420, 460), (500, 340), (620, 250), (780, 200), 16, alpha=210, dry=0.08)
    twigs = [
        ((430, 560), (360, 470), (310, 400), (270, 340), -145),
        ((460, 480), (490, 370), (500, 280), (470, 210), -95),
        ((540, 420), (610, 330), (660, 260), (640, 200), -65),
        ((620, 400), (680, 330), (730, 280), (710, 230), -25),
        ((390, 680), (330, 660), (280, 720), (250, 820), 155),
    ]
    for p0, p1, p2, p3, aim in twigs:
        b.use(BARK)
        b.stroke(p0, p1, p2, p3, 8, alpha=200, dry=0.1, fade=0.12)
        # Needles along the outer half of the twig, not only at one tip.
        pts = b.cubic(p0, p1, p2, p3, n=8, fade=0)
        b.use(NEEDLE if b.rng.random() < 0.5 else NEEDLE_DEEP)
        for i, (x, y, _pr) in enumerate(pts):
            if i < 4:
                continue
            b.sheaf(x, y, aim + b.rng.uniform(-8, 8), 170 + (i - 4) * 8, count=16, spread=56, width=6.4)
    b.save("pine.png")


def bamboo():
    b = Brush(7)
    b.use(CULM)
    b.culm(400, 70, 1120, 34, 200, lean=6)
    b.culm(560, 30, 1140, 46, 225, lean=-4)
    b.use(LEAF)
    sprays = [
        (575, 150, [(-130, 230, 28), (-85, 260, 32), (-40, 200, 24)]),
        (568, 330, [(-160, 180, 24), (-110, 210, 28), (10, 160, 22)]),
        (412, 230, [(-120, 200, 26), (-65, 230, 30), (-20, 160, 22)]),
        (418, 470, [(130, 170, 24), (85, 200, 26), (40, 140, 20)]),
    ]
    for x, y, leaves in sprays:
        for ang, length, width in leaves:
            b.leaf(x, y, ang, length, width, alpha=215)
    b.save("bamboo.png")


def plum():
    b = Brush(19)
    b.use(BARK)
    b.stroke((80, 1040), (150, 860), (210, 680), (300, 520), 28, alpha=235, dry=0.07, fade=0.05)
    b.stroke((300, 520), (390, 420), (520, 350), (740, 300), 12, alpha=200, dry=0.1)
    b.stroke((280, 600), (230, 500), (210, 380), (250, 270), 7, alpha=180, dry=0.14)
    b.stroke((620, 330), (680, 410), (700, 530), (650, 650), 6, alpha=170, dry=0.14)
    # Round, overlapping rose petals. Smaller than tangdi, and pink rather than gold.
    b.use(PLUM_PINK)
    for x, y, r in [
        (250, 250, 58),
        (390, 340, 52),
        (520, 270, 64),
        (680, 250, 50),
        (760, 340, 56),
        (220, 430, 40),
        (640, 500, 44),
    ]:
        b.blossom(x, y, r, alpha=225, spread=1.15, gap=0.30, heart=PLUM_HEART)
    b.save("plum.png")


def peach():
    b = Brush(23)
    b.use(BARK)
    b.stroke((100, 980), (200, 780), (340, 580), (500, 430), 24, alpha=220, dry=0.06, fade=0.05)
    b.stroke((500, 430), (620, 350), (740, 320), (860, 370), 10, alpha=185, dry=0.1)
    b.stroke((360, 600), (300, 500), (280, 390), (340, 280), 7, alpha=170, dry=0.12)
    b.use(LEAF)
    b.leaf(470, 460, 125, 170, 28, alpha=190)
    b.leaf(560, 420, 45, 150, 24, alpha=175)
    b.leaf(310, 540, 165, 130, 22, alpha=170)
    b.use(PEACH_PINK)
    for x, y, r in [
        (420, 280, 62),
        (580, 320, 56),
        (730, 290, 60),
        (340, 430, 46),
        (810, 410, 42),
        (250, 540, 40),
    ]:
        b.blossom(x, y, r, alpha=215, spread=1.25, gap=0.28, heart=PLUM_HEART)
    b.save("peach.png")


def xingcai():
    b = Brush(29)
    b.use(WATER)
    for y, x0, x1 in [
        (230, 60, 390),
        (248, 540, 860),
        (420, 40, 280),
        (450, 500, 820),
        (690, 80, 340),
        (710, 580, 870),
        (950, 120, 460),
        (970, 640, 840),
    ]:
        b.stroke((x0, y), ((x0 + x1) / 2, y - 5), ((x0 + x1) / 2, y + 4), (x1, y), 4, alpha=80, dry=0.35, fade=0.18)
    pads = [
        (400, 520, 90, 36, -18),
        (560, 470, 74, 30, 20),
        (320, 650, 64, 26, 8),
        (660, 620, 84, 32, -26),
        (480, 760, 52, 22, 4),
    ]
    for cx, cy, rx, ry, rot in pads:
        ang = math.radians(rot)

        def place(lx, ly):
            return (
                cx + math.cos(ang) * lx - math.sin(ang) * ly,
                cy + math.sin(ang) * lx + math.cos(ang) * ly,
            )

        b.use(LEAF)
        b.soft_fill_rotated(cx, cy, rx, ry, rot, alpha=185, blur=3)
        b.use(NEEDLE_DEEP)
        b.soft_fill_rotated(cx, cy, rx * 0.45, ry * 0.32, rot, alpha=90, blur=2)
        b.use(NEEDLE_DEEP)
        sx, sy = place(0, ry * 0.3)
        ex, ey = place(-8, ry + 70)
        b.stroke((sx, sy), (sx - 6, sy + 24), (ex + 4, ey - 20), (ex, ey), 3.5, alpha=140, dry=0.1)
    b.save("xingcai.png")


def tangdi():
    b = Brush(31)
    b.use(BARK)
    b.stroke((130, 1080), (190, 880), (280, 700), (420, 540), 22, alpha=225, dry=0.07, fade=0.05)
    b.stroke((420, 540), (560, 400), (650, 250), (530, 150), 9, alpha=190, dry=0.1)
    b.stroke((530, 150), (430, 130), (320, 190), (280, 320), 5, alpha=165, dry=0.14)
    b.stroke((450, 400), (540, 460), (590, 570), (530, 680), 5, alpha=160, dry=0.14)
    b.use(LEAF)
    b.leaf(430, 560, 145, 150, 26, alpha=180)
    b.leaf(500, 480, 35, 130, 22, alpha=165)
    # Broad gold petals, held apart, so the flower is not another plum.
    b.use(TANGDI_GOLD)
    for x, y, r in [(500, 150, 96), (340, 210, 78), (270, 340, 84), (620, 300, 72), (560, 620, 70)]:
        b.blossom(x, y, r, alpha=220, spread=0.85, gap=0.62, heart=TANGDI_HEART)
    b.save("tangdi.png")


def mugua():
    b = Brush(37)
    b.use(BARK)
    b.stroke((120, 220), (260, 280), (420, 340), (560, 300), 11, alpha=210, dry=0.07)
    b.stroke((400, 330), (370, 460), (355, 560), (360, 600), 5.5, alpha=185, dry=0.08)
    b.stroke((560, 300), (650, 400), (720, 500), (710, 570), 5.5, alpha=180, dry=0.08)
    b.stroke((500, 310), (515, 430), (528, 520), (530, 640), 5, alpha=175, dry=0.08)
    fruits = [
        (360, 700, 72, 96),
        (530, 760, 88, 114),
        (710, 660, 64, 86),
        (500, 560, 48, 64),
    ]
    for cx, cy, rx, ry in fruits:
        b.use(FRUIT)
        b.soft_fill(cx, cy, rx, ry, alpha=210, blur=3.5)
        b.use(FRUIT_SHADE)
        b.soft_fill(cx - rx * 0.22, cy + 6, rx * 0.38, ry * 0.62, alpha=120, blur=2.5)
        b.use(LEAF)
        b.leaf(cx - 6, cy - ry + 10, -150, 90, 22, alpha=185)
        b.leaf(cx + 10, cy - ry + 14, -30, 80, 18, alpha=170)
    b.save("mugua.png")


def main():
    pine()
    bamboo()
    plum()
    peach()
    xingcai()
    tangdi()
    mugua()


if __name__ == "__main__":
    main()
