#!/usr/bin/env python3
"""
Pilote d'Avion 3D - vue troisième personne.
L'avion est visible à l'écran : on le pilote avec les flèches directionnelles.

Commandes :
  ← / →  : virer à gauche / à droite (l'avion s'incline)
  ↑ / ↓  : piquer / cabrer (monter / descendre)
  R      : recommencer après un crash
  Échap  : quitter

Objectif : traverser les anneaux pour marquer des points, sans toucher le sol.
"""

import math
import random

import pyglet
from pyglet import gl
from pyglet.window import key

# ------------------------------------------------------------------ config
W, H = 960, 640
FOV = math.radians(75)
FOCAL = (H / 2) / math.tan(FOV / 2)
NEAR = 0.3
GROUND_Y = 0.0
SPEED = 34.0

# ------------------------------------------------------------------ maths
def add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def mul(a, s): return (a[0]*s, a[1]*s, a[2]*s)
def dot(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def norm(a):
    l = math.sqrt(dot(a, a))
    return mul(a, 1/l) if l else (0, 0, 0)

def clamp(v, lo, hi): return max(lo, min(hi, v))

def shade(c, f): return tuple(int(clamp(x*f, 0, 255)) for x in c)

# ------------------------------------------------------------------ rendu
LINE_PTS, LINE_COLS = [], []
FACE_BATCH = []
cam_pos = (0, 0, 0)
cam_r = (1, 0, 0)
cam_u = (0, 1, 0)
cam_f = (0, 0, 1)


def gpu_draw(mode, pts, cols):
    pos = []
    for x, y in pts:
        pos.extend((x, y, 0.0))
    col = []
    for c in cols:
        col.extend(tuple(v/255 for v in c[:3]) + ((c[3],) if len(c) > 3 else (1.0,)))
    pyglet.graphics.draw(len(pts), mode, position=("f", pos), colors=("f", col))


def world_to_cam(p):
    d = sub(p, cam_pos)
    return (dot(d, cam_r), dot(d, cam_u), dot(d, cam_f))


def project(c):
    s = FOCAL / c[2]
    return (W/2 + c[0]*s, H/2 + c[1]*s)


def clip(poly):
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i+1) % len(poly)]
        ai, bi = a[2] >= NEAR, b[2] >= NEAR
        if ai and bi:
            out.append(b)
        elif ai and not bi:
            out.append(intersect(a, b))
        elif not ai and bi:
            out.append(intersect(a, b))
            out.append(b)
    return out


def intersect(a, b):
    t = (NEAR - a[2]) / (b[2] - a[2])
    return add(a, mul(sub(b, a), t))


def add_line(p1, p2, color):
    a, b = world_to_cam(p1), world_to_cam(p2)
    if a[2] < NEAR and b[2] < NEAR:
        return
    if a[2] < NEAR or b[2] < NEAR:
        t = (NEAR - a[2]) / (b[2] - a[2])
        m = add(a, mul(sub(b, a), t))
        if a[2] < NEAR:
            a = m
        else:
            b = m
    LINE_PTS.extend((project(a), project(b)))
    LINE_COLS.extend((color, color))


def add_face(verts, color):
    c = clip([world_to_cam(v) for v in verts])
    if len(c) < 3:
        return
    pts = [project(p) for p in c]
    z = sum(p[2] for p in c) / len(c)
    FACE_BATCH.append((z, pts, color))


def flush():
    global LINE_PTS, LINE_COLS
    if LINE_PTS:
        gpu_draw(gl.GL_LINES, LINE_PTS, LINE_COLS)
    LINE_PTS, LINE_COLS = [], []

    FACE_BATCH.sort(key=lambda f: -f[0])  # loin -> proche
    tp, tc, ep, ec = [], [], [], []
    for _, pts, col in FACE_BATCH:
        for i in range(1, len(pts)-1):
            for j in (0, i, i+1):
                tp.append(pts[j]); tc.append(col)
        edge = shade(col, 0.6)
        for i in range(len(pts)):
            ep.append(pts[i]); ep.append(pts[(i+1) % len(pts)])
            ec.extend((edge, edge))
    if tp:
        gpu_draw(gl.GL_TRIANGLES, tp, tc)
    if ep:
        gpu_draw(gl.GL_LINES, ep, ec)
    FACE_BATCH.clear()


# ------------------------------------------------------------------ modèle avion
PARTS = [
    ((0, 0, 0.3),  (0.45, 0.45, 2.6), (225, 70, 60)),    # fuselage
    ((0, 0, 0),    (4.3, 0.12, 0.65), (235, 235, 235)),  # ailes
    ((0, 0, -2.0), (1.7, 0.1, 0.45),  (235, 235, 235)),  # empennage
    ((0, 0.9, -2.0), (0.12, 0.9, 0.5), (225, 70, 60)),   # dérive
    ((0, 0.48, 0.9), (0.36, 0.28, 0.8), (50, 110, 170)), # cockpit
]

BOX_FACES = [
    ([4, 5, 6, 7], 1.0),   # avant
    ([0, 3, 2, 1], 0.55),  # arrière
    ([1, 5, 6, 2], 0.8),   # droite
    ([0, 3, 7, 4], 0.7),   # gauche
    ([3, 2, 6, 7], 1.12),  # dessus
    ([0, 1, 5, 4], 0.6),   # dessous
]


# ------------------------------------------------------------------ état
class Plane:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x, self.y, self.z = 0.0, 30.0, 0.0
        self.yaw, self.pitch, self.roll = 0.0, 0.0, 0.0
        self.prop = 0.0
        self.prev_z = self.z
        self.crashed = False

    def basis(self, rolled=True):
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        f = (math.sin(self.yaw)*cp, sp, math.cos(self.yaw)*cp)
        r = norm((f[2], 0.0, -f[0]))
        u = norm(cross(f, r))
        if rolled:
            cr, sr = math.cos(self.roll), math.sin(self.roll)
            r2 = add(mul(r, cr), mul(u, sr))
            u2 = add(mul(u, cr), mul(r, -sr))
            return r2, u2, f
        return r, u, f

    def update(self, dt):
        if self.crashed:
            return
        turn = 1.6 * dt
        pitch = 1.2 * dt
        if key.LEFT in pressed:
            self.yaw -= turn
        if key.RIGHT in pressed:
            self.yaw += turn
        if key.UP in pressed:
            self.pitch += pitch
        if key.DOWN in pressed:
            self.pitch -= pitch
        self.yaw = clamp(self.yaw, -1.0, 1.0)
        self.pitch = clamp(self.pitch, -0.8, 0.8)

        # inclinaison visualisée lors des virages
        target_roll = 0.0
        if key.LEFT in pressed:
            target_roll = 0.5
        if key.RIGHT in pressed:
            target_roll = -0.5
        self.roll += (target_roll - self.roll) * min(1, 4*dt)

        r, u, f = self.basis(rolled=False)
        self.prev_z = self.z
        self.x += f[0]*SPEED*dt
        self.y += f[1]*SPEED*dt
        self.z += f[2]*SPEED*dt
        self.prop += 22*dt

        if self.y < GROUND_Y + 1.5:
            self.crashed = True

    def to_world(self, v, r, u, f):
        return (self.x + v[0]*r[0] + v[1]*u[0] + v[2]*f[0],
                self.y + v[0]*r[1] + v[1]*u[1] + v[2]*f[1],
                self.z + v[0]*r[2] + v[1]*u[2] + v[2]*f[2])

    def draw(self):
        r, u, f = self.basis(rolled=True)
        for center, h, color in PARTS:
            cx, cy, cz = center
            hx, hy, hz = h
            v = [
                (cx-hx, cy-hy, cz-hz), (cx+hx, cy-hy, cz-hz),
                (cx+hx, cy+hy, cz-hz), (cx-hx, cy+hy, cz-hz),
                (cx-hx, cy-hy, cz+hz), (cx+hx, cy-hy, cz+hz),
                (cx+hx, cy+hy, cz+hz), (cx-hx, cy+hy, cz+hz),
            ]
            wv = [self.to_world(p, r, u, f) for p in v]
            for idxs, sf in BOX_FACES:
                add_face([wv[i] for i in idxs], shade(color, sf))
        # hélice
        ca, sa = math.cos(self.prop), math.sin(self.prop)
        p1 = self.to_world((-1.25*ca, -1.25*sa, 3.05), r, u, f)
        p2 = self.to_world(( 1.25*ca,  1.25*sa, 3.05), r, u, f)
        p3 = self.to_world((-1.25*sa,  1.25*ca, 3.05), r, u, f)
        p4 = self.to_world(( 1.25*sa, -1.25*ca, 3.05), r, u, f)
        add_line(p1, p2, (40, 40, 45))
        add_line(p3, p4, (40, 40, 45))


class Game:
    def __init__(self):
        self.plane = Plane()
        self.reset()

    def reset(self):
        self.plane.reset()
        self.score = 0
        self.distance = 0.0
        self.rings = []
        z = 70.0
        for _ in range(5):
            self.rings.append(self.new_ring(z))
            z += 70.0
        self.max_z = z

    def new_ring(self, z):
        return {"x": random.uniform(-35, 35),
                "y": random.uniform(12, 65),
                "z": z, "r": 9.0, "flash": 0.0}

    def update(self, dt):
        self.plane.update(dt)
        if self.plane.crashed:
            return
        self.distance += SPEED*dt
        p = self.plane
        for ring in self.rings:
            if p.prev_z < ring["z"] <= p.z:
                if math.hypot(p.x-ring["x"], p.y-ring["y"]) < ring["r"]:
                    self.score += 100
                    ring["flash"] = 1.0
                    ring.update(self.new_ring(self.max_z))
                    self.max_z += 70.0
            if ring["z"] < p.z - 20:
                ring.update(self.new_ring(self.max_z))
                self.max_z += 70.0
            ring["flash"] = max(0, ring["flash"] - dt*2)


plane_game = Game()
pressed = set()

window = pyglet.window.Window(width=W, height=H, caption="Pilote d'Avion 3D", resizable=False)


@window.event
def on_key_press(symbol, modifiers):
    pressed.add(symbol)
    if symbol == key.ESCAPE:
        window.close()
    if plane_game.plane.crashed and symbol in (key.R, key.SPACE, key.ENTER):
        plane_game.reset()


@window.event
def on_key_release(symbol, modifiers):
    pressed.discard(symbol)


def update_camera():
    global cam_pos, cam_r, cam_u, cam_f
    p = plane_game.plane
    r, u, f = p.basis(rolled=False)
    cam_pos = add(sub((p.x, p.y, p.z), mul(f, 19)), mul(u, 6.5))
    cam_f = f
    cam_r = r
    cam_u = norm(cross(f, r))


def draw_ground():
    p = plane_game.plane
    x0 = (int(p.x)//20 - 10) * 20
    z0 = (int(p.z)//20 - 5) * 20
    for x in range(x0, x0 + 401, 20):
        add_line((x, 0, z0-20), (x, 0, z0+420), (45, 95, 75))
    for z in range(z0, z0 + 421, 20):
        c = (60, 130, 100) if (z//20) % 2 == 0 else (40, 90, 70)
        add_line((x0-20, 0, z), (x0+400, 0, z), c)


def draw_rings():
    for ring in plane_game.rings:
        color = (120, 255, 140) if ring["flash"] > 0 else (255, 200, 60)
        pts = []
        n = 28
        for i in range(n):
            a = i * 2*math.pi/n
            pts.append((ring["x"] + ring["r"]*math.cos(a),
                        ring["y"] + ring["r"]*math.sin(a), ring["z"]))
        for i in range(n):
            add_line(pts[i], pts[(i+1) % n], color)


# ------------------------------------------------------------------ HUD
hud_score = pyglet.text.Label("", font_size=22, weight="bold",
                              x=20, y=H-24, anchor_x="left", anchor_y="top",
                              color=(255, 220, 100, 255))
hud_info = pyglet.text.Label("", font_size=14,
                             x=20, y=H-56, anchor_x="left", anchor_y="top",
                             color=(180, 230, 255, 255))
hud_help = pyglet.text.Label(
    "← → : virer    ↑ ↓ : monter/descendre    R : recommencer    Échap : quitter",
    font_size=13, x=W//2, y=16, anchor_x="center", anchor_y="bottom",
    color=(210, 210, 220, 255))
hud_crash = pyglet.text.Label("CRASH !", font_size=56, weight="bold",
                              x=W//2, y=H//2+30, anchor_x="center", anchor_y="center",
                              color=(255, 90, 90, 255))
hud_retry = pyglet.text.Label("Appuyez sur R pour redécoller", font_size=22,
                              x=W//2, y=H//2-35, anchor_x="center", anchor_y="center")


@window.event
def on_draw():
    gl.glClearColor(0.35, 0.62, 0.88, 1.0)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
    gl.glDisable(gl.GL_DEPTH_TEST)

    update_camera()
    draw_ground()
    draw_rings()
    plane_game.plane.draw()
    flush()

    p = plane_game.plane
    hud_score.text = f"Score : {plane_game.score}"
    hud_info.text = (f"Altitude : {p.y:.0f} m    Vitesse : {SPEED}    "
                     f"Distance : {int(plane_game.distance)} m")
    hud_score.draw()
    hud_info.draw()
    hud_help.draw()
    if p.crashed:
        hud_crash.draw()
        hud_retry.draw()


pyglet.clock.schedule_interval(plane_game.update, 1/60)
pyglet.app.run()
