#!/usr/bin/env python3
"""
Cube Runner 3D - un jeu de course / esquive en 3D (vue subjective).
Évitez les cubes, avancez le plus loin possible !

Commandes :
  ← / →  ou  A / D   : se déplacer à gauche / droite
  ↑ / ↓  ou  W / S   : monter / descendre
  R                  : recommencer après une collision
  Échap              : quitter
"""

import math
import random

import pyglet
from pyglet import gl
from pyglet.window import key

# ------------------------------------------------------------------ configuration
WIDTH, HEIGHT = 960, 640
FOV = math.radians(78)
FOCAL = (HEIGHT / 2) / math.tan(FOV / 2)
NEAR = 0.4
VIEW_DIST = 150.0
GROUND = -4.0
CUBE_H = 1.2
PLAYER_R = 0.55
LANE_MIN, LANE_MAX = -8.0, 8.0
Y_MIN, Y_MAX = -2.5, 2.8

PALETTE = [
    (255, 99, 132),
    (54, 162, 235),
    (255, 206, 86),
    (75, 192, 192),
    (153, 102, 255),
    (255, 159, 64),
]

# ------------------------------------------------------------------ helpers
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def norm(color):
    """RGB 0-255 -> RGBA flottants 0-1 attendus par le shader."""
    return tuple(c / 255.0 for c in color) + (1.0,)


def shade(color, factor):
    return tuple(int(clamp(c * factor, 0, 255)) for c in color)


def gpu_draw(mode, points, colors):
    """Envoie des sommets 2D avec couleurs au shader par défaut de pyglet."""
    pos = []
    for x, y in points:
        pos.extend((x, y, 0.0))
    col = []
    for c in colors:
        col.extend(norm(c) if len(c) == 3 else tuple(v / 255 for v in c[:3]) + (c[3],))
    pyglet.graphics.draw(len(points), mode,
                         position=("f", pos), colors=("f", col))


# ------------------------------------------------------------------ world state
class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.cam_z = 0.0
        self.speed = 9.0
        self.score = 0
        self.game_over = False
        self.obstacles = []
        z = 22.0
        for _ in range(12):
            self.obstacles.append(self.new_obstacle(z))
            z += random.uniform(11, 16)
        self.max_z = z

    def new_obstacle(self, z):
        return {
            "x": random.uniform(LANE_MIN, LANE_MAX),
            "y": random.uniform(Y_MIN, Y_MAX),
            "z": z,
            "color": random.choice(PALETTE),
        }

    def update(self, dt):
        if self.game_over:
            return

        self.speed = min(9.0 + self.cam_z * 0.012, 22.0)
        self.cam_z += self.speed * dt
        self.score = int(self.cam_z)

        mv = 9.0 * dt
        if key.LEFT in pressed or key.A in pressed:
            self.cam_x -= mv
        if key.RIGHT in pressed or key.D in pressed:
            self.cam_x += mv
        if key.UP in pressed or key.W in pressed:
            self.cam_y += mv * 0.8
        if key.DOWN in pressed or key.S in pressed:
            self.cam_y -= mv * 0.8
        self.cam_x = clamp(self.cam_x, LANE_MIN, LANE_MAX)
        self.cam_y = clamp(self.cam_y, Y_MIN, Y_MAX)

        # recycler les obstacles dépassés
        for o in self.obstacles:
            if o["z"] < self.cam_z - 4:
                o.update(self.new_obstacle(self.max_z))
                self.max_z += random.uniform(11, 16)

        # collision
        for o in self.obstacles:
            if abs(o["z"] - self.cam_z) < CUBE_H + 0.6:
                if abs(o["x"] - self.cam_x) < CUBE_H + PLAYER_R and \
                   abs(o["y"] - self.cam_y) < CUBE_H + PLAYER_R:
                    self.game_over = True
                    break

    # -------------------------------------------------------------- projection
    def project(self, p):
        x, y, z = p
        zc = z - self.cam_z
        s = FOCAL / zc
        return (WIDTH / 2 + (x - self.cam_x) * s,
                HEIGHT / 2 + (y - self.cam_y) * s)

    def clip(self, poly):
        """Sutherland-Hodgman : coupe un polygone derrière le plan near."""
        out = []
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            a_in = (a[2] - self.cam_z) >= NEAR
            b_in = (b[2] - self.cam_z) >= NEAR
            if a_in and b_in:
                out.append(b)
            elif a_in and not b_in:
                out.append(self.intersect(a, b))
            elif not a_in and b_in:
                out.append(self.intersect(a, b))
                out.append(b)
        return out

    def intersect(self, a, b):
        za, zb = a[2] - self.cam_z, b[2] - self.cam_z
        t = (NEAR - za) / (zb - za)
        return (a[0] + (b[0] - a[0]) * t,
                a[1] + (b[1] - a[1]) * t,
                a[2] + (b[2] - a[2]) * t)


game = Game()
pressed = set()  # touches actuellement maintenues (flèches incluses)

# ------------------------------------------------------------------ window
window = pyglet.window.Window(width=WIDTH, height=HEIGHT,
                             caption="Cube Runner 3D", resizable=False)


@window.event
def on_key_press(symbol, modifiers):
    pressed.add(symbol)
    if symbol == key.ESCAPE:
        window.close()
    if game.game_over and symbol in (key.R, key.SPACE, key.ENTER):
        game.reset()


@window.event
def on_key_release(symbol, modifiers):
    pressed.discard(symbol)


# ------------------------------------------------------------------ drawing
def draw_segment(a, b, color):
    """Ligne 3D coupée au plan near."""
    za, zb = a[2] - game.cam_z, b[2] - game.cam_z
    if za < NEAR and zb < NEAR:
        return
    if za < NEAR or zb < NEAR:
        t = (NEAR - za) / (zb - za)
        mid = (a[0] + (b[0] - a[0]) * t,
               a[1] + (b[1] - a[1]) * t,
               a[2] + (b[2] - a[2]) * t)
        if za < NEAR:
            a = mid
        else:
            b = mid
    gpu_draw(gl.GL_LINES, [game.project(a), game.project(b)], [color, color])


def draw_floor():
    z0 = game.cam_z + NEAR + 0.2
    z1 = game.cam_z + VIEW_DIST
    for x in range(-12, 13, 3):
        draw_segment((x, GROUND, z0), (x, GROUND, z1), (40, 90, 120))
    step = 5.0
    for k in range(int(z0 / step) + 1, int(z1 / step) + 1):
        z = k * step
        c = (60, 140, 180) if k % 2 == 0 else (35, 75, 105)
        draw_segment((-12, GROUND, z), (12, GROUND, z), c)
    for x in (-12, 12):
        k0, k1 = int(z0 / step) + 1, int(z1 / step)
        for k in range(k0, k1 + 1, 2):
            z = k * step
            draw_segment((x, GROUND, z), (x, GROUND + 7, z), (90, 60, 150))
        draw_segment((x, GROUND + 7, z0), (x, GROUND + 7, z1), (90, 60, 150))


def cube_vertices(o):
    x, y, z, h = o["x"], o["y"], o["z"], CUBE_H
    return [
        (x-h, y-h, z-h), (x+h, y-h, z-h), (x+h, y+h, z-h), (x-h, y+h, z-h),
        (x-h, y-h, z+h), (x+h, y-h, z+h), (x+h, y+h, z+h), (x-h, y+h, z+h),
    ]


def draw_cubes():
    drawable = []
    for o in game.obstacles:
        dz = o["z"] - game.cam_z
        if dz < -CUBE_H or dz > VIEW_DIST:
            continue
        v = cube_vertices(o)
        dx, dy = o["x"] - game.cam_x, o["y"] - game.cam_y

        faces = [([v[0], v[1], v[2], v[3]], 1.0)]  # face avant
        if dx > 0:
            faces.append(([v[0], v[4], v[7], v[3]], 0.72))
        else:
            faces.append(([v[1], v[5], v[6], v[2]], 0.72))
        if dy > 0:
            faces.append(([v[0], v[4], v[5], v[1]], 0.82))
        else:
            faces.append(([v[3], v[7], v[6], v[2]], 0.9))

        for quad, f in faces:
            clipped = game.clip(quad)
            if len(clipped) < 3:
                continue
            pts = [game.project(p) for p in clipped]
            avg_z = sum(p[2] - game.cam_z for p in clipped) / len(clipped)
            drawable.append((avg_z, pts, shade(o["color"], f)))

    drawable.sort(key=lambda d: -d[0])  # du plus loin au plus proche
    for _, pts, col in drawable:
        # triangulation en éventail
        p, c = [], []
        for i in range(1, len(pts) - 1):
            for idx in (0, i, i + 1):
                p.append(pts[idx])
                c.append(col)
        gpu_draw(gl.GL_TRIANGLES, p, c)
        # contour
        p, c = [], []
        edge = shade(col, 0.55)
        for i in range(len(pts)):
            p.append(pts[i])
            p.append(pts[(i + 1) % len(pts)])
            c.extend((edge, edge))
        gpu_draw(gl.GL_LINES, p, c)


# ------------------------------------------------------------------ HUD
score_label = pyglet.text.Label("", font_size=22, weight="bold",
                                x=20, y=HEIGHT - 24,
                                anchor_x="left", anchor_y="top")
speed_label = pyglet.text.Label("", font_size=15,
                                x=20, y=HEIGHT - 56,
                                anchor_x="left", anchor_y="top",
                                color=(150, 220, 255, 255))
help_label = pyglet.text.Label(
    "← → / A D : gauche-droite    ↑ ↓ / W S : haut-bas    Échap : quitter",
    font_size=13, x=WIDTH // 2, y=16,
    anchor_x="center", anchor_y="bottom", color=(200, 200, 210, 255))

over_label = pyglet.text.Label("COLLISION !", font_size=56, weight="bold",
                               x=WIDTH // 2, y=HEIGHT // 2 + 30,
                               anchor_x="center", anchor_y="center",
                               color=(255, 90, 90, 255))
restart_label = pyglet.text.Label("Appuyez sur R pour recommencer", font_size=22,
                                  x=WIDTH // 2, y=HEIGHT // 2 - 35,
                                  anchor_x="center", anchor_y="center")


@window.event
def on_draw():
    gl.glClearColor(0.05, 0.06, 0.12, 1.0)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
    gl.glDisable(gl.GL_DEPTH_TEST)

    draw_floor()
    draw_cubes()

    score_label.text = f"Score : {game.score} m"
    speed_label.text = f"Vitesse : {game.speed:.1f}"
    score_label.draw()
    speed_label.draw()
    help_label.draw()

    if game.game_over:
        over_label.draw()
        restart_label.draw()


pyglet.clock.schedule_interval(game.update, 1 / 60)
pyglet.app.run()
