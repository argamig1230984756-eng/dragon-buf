import json, uuid, random, base64, io, math, os
from PIL import Image, ImageDraw

random.seed(7)
OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(OUT, 'attacks'), exist_ok=True)
U = lambda: str(uuid.uuid4())

class Model:
    def __init__(self, name):
        self.name = name
        self.elements = []
        self.groups = {}
        self.anims = []
        self.gobj = {}   # v2: lookup of group dicts by name so extra parts can be appended

    def cube(self, name, fr, to, kind="body", rot=None, origin=None):
        el = {"name": name, "type": "cube", "uuid": U(), "box_uv": True, "rescale": False,
              "locked": False, "light_emission": 0, "render_order": "default",
              "allow_mirror_modeling": True, "from": list(fr), "to": list(to),
              "autouv": 0, "color": 0, "origin": [0, 0, 0], "rotation": [0, 0, 0],
              "_kind": kind}
        if rot:   # v2: optional rotation about `origin` (defaults to cube centre)
            el["rotation"] = list(rot)
            el["origin"] = list(origin) if origin else [(fr[0] + to[0]) / 2, (fr[1] + to[1]) / 2, (fr[2] + to[2]) / 2]
        self.elements.append(el)
        return el["uuid"]

    def group(self, name, origin, children):
        g = {"name": name, "origin": list(origin), "rotation": [0, 0, 0], "color": 0,
             "uuid": U(), "export": True, "isOpen": True, "locked": False,
             "visibility": True, "autouv": 0, "children": children}
        self.groups[name] = g["uuid"]
        self.gobj[name] = g
        return g

    def mirror_x(self, v):
        return [-v[0], v[1], v[2]]

    # ---- texture ----
    def build(self):
        size = 256
        while True:
            placed = self._pack(size)
            if placed:
                break
            size *= 2
        self.size = size
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        for el in self.elements:
            self._paint(img, el)
        self.img = img
        for el in self.elements:
            u, v = el["uv_offset"]
            w, h, d = el["_dims"]
            el["faces"] = {
                "north": {"uv": [u + d, v + d, u + d + w, v + d + h], "texture": 0},
                "east":  {"uv": [u, v + d, u + d, v + d + h], "texture": 0},
                "south": {"uv": [u + 2 * d + w, v + d, u + 2 * d + 2 * w, v + d + h], "texture": 0},
                "west":  {"uv": [u + d + w, v + d, u + 2 * d + w, v + d + h], "texture": 0},
                "up":    {"uv": [u + d, v, u + d + w, v + d], "texture": 0},
                "down":  {"uv": [u + d + w, v, u + d + 2 * w, v + d], "texture": 0},
            }

    def _pack(self, size):
        for el in self.elements:
            f, t = el["from"], el["to"]
            el["_dims"] = [max(1, round(t[0] - f[0])), max(1, round(t[1] - f[1])), max(1, round(t[2] - f[2]))]
        order = sorted(self.elements, key=lambda e: -(e["_dims"][1] + e["_dims"][2]))
        x = y = rowh = 0
        for el in order:
            w, h, d = el["_dims"]
            bw, bh = 2 * (w + d) + 1, d + h + 1
            if x + bw > size:
                x, y, rowh = 0, y + rowh, 0
            if y + bh > size:
                return False
            el["uv_offset"] = [x, y]
            x += bw
            rowh = max(rowh, bh)
        return True

    def _paint(self, img, el):
        px = img.load()
        u, v = el["uv_offset"]
        w, h, d = el["_dims"]
        kind = el["_kind"]
        regions = {
            "up": (u + d, v, w, d), "down": (u + d + w, v, w, d),
            "east": (u, v + d, d, h), "north": (u + d, v + d, w, h),
            "west": (u + d + w, v + d, d, h), "south": (u + 2 * d + w, v + d, w, h),
        }
        for face, (rx, ry, rw, rh) in regions.items():
            side = face in ("north", "south", "east", "west")
            for yy in range(rh):
                for xx in range(rw):
                    px[rx + xx, ry + yy] = self._color(kind, side, xx, yy, rw, rh)

    def _color(self, kind, side, xx, yy, rw, rh):
        n = random.randint(-5, 5)
        # ---- v2 texture kinds (new; old kinds below are untouched) ----
        if kind == "energy":      # purple/magenta glow
            return (170 + random.randint(0, 60), 60 + random.randint(0, 50), 255, 255)
        if kind == "lightning":   # PURPLE lightning: lilac-white core, violet edges
            if random.random() < 0.28:
                return (240, 225, 255, 255)
            return (185 + random.randint(0, 40), 100 + random.randint(0, 40), 255, 255)
        if kind == "fire":        # void-fire gradient violet -> magenta -> white-hot
            t = yy / max(rh - 1, 1)
            if random.random() < 0.08:
                return (255, 210, 255, 255)
            return (int(255 - 115 * t) + n, int(70 - 45 * t) + max(n, 0), int(230 + 25 * t), 255)
        if kind == "crystal":
            c0 = (120 + n, 60 + n, 200 + n, 255)
            return (190, 130, 255, 255) if (xx + yy) % 7 == 0 else c0
        if kind == "void":
            if random.random() < 0.04:
                return (150, 70, 220, 255)
            if (xx + yy * 2) % 11 == 0:
                return (90, 30, 150, 255)
            return (8 + n // 2, 4 + n // 2, 16 + n, 255)
        if kind == "tooth":
            return (170, 150, 190, 255) if yy % 4 == 3 else (215 + n, 205 + n, 225 + n, 255)
        if kind == "deepslate":
            if random.random() < 0.03:
                return (40, 40, 46, 255)
            if random.random() < 0.015:
                return (170, 80, 255, 255)
            return (58 + n, 58 + n, 64 + n, 255)
        if kind == "glow":
            return (255, 40 + random.randint(0, 30), 110, 255)
        if kind == "membrane":
            c = (48 + n, 18 + n // 2, 78 + n, 255)
            if yy % 6 == 0 or xx % 9 == 0:
                c = (125, 50, 175, 255)
            return c
        base = (22 + n, 17 + n, 30 + n, 255)
        if kind == "body" and side and rw >= 3:
            sw = 2 if rw >= 5 else 1
            cx = rw // 2 - sw // 2
            if cx <= xx < cx + sw and (yy % 8) < 5:
                return (200, 80, 255, 255) if xx == cx else (235, 150, 255, 255)
        if random.random() < 0.02:
            return (90, 40, 130, 255)
        return base

    # ---- animations ----
    def anim(self, name, length, tracks, loop="loop"):
        animators = {}
        for gname, chans in tracks.items():
            kfs = []
            for channel, pts in chans.items():
                for t, (x, y, z) in pts:
                    kfs.append({"channel": channel, "data_points": [{"x": str(x), "y": str(y), "z": str(z)}],
                                "uuid": U(), "time": t, "color": -1, "interpolation": "catmullrom"})
            animators[self.groups[gname]] = {"name": gname, "type": "bone", "keyframes": kfs}
        self.anims.append({"uuid": U(), "name": name, "loop": loop, "override": False, "length": length,
                           "snapping": 24, "selected": False, "anim_time_update": "", "blend_weight": "",
                           "start_delay": "", "loop_delay": "", "animators": animators})

    def save(self, outliner, path_json, path_png):
        buf = io.BytesIO()
        self.img.save(buf, "PNG")
        self.img.save(path_png)
        b64 = base64.b64encode(buf.getvalue()).decode()
        els = []
        for el in self.elements:
            e = {k: v for k, v in el.items() if not k.startswith("_")}
            els.append(e)
        data = {
            "meta": {"format_version": "4.10", "model_format": "free", "box_uv": True},
            "name": self.name, "model_identifier": "", "visible_box": [1, 1, 0],
            "variable_placeholders": "", "variable_placeholder_buttons": [],
            "timeline_setups": [],
            "unhandled_root_fields": {},
            "resolution": {"width": self.size, "height": self.size},
            "elements": els, "outliner": outliner,
            "textures": [{"path": "", "name": self.name + ".png", "folder": "", "namespace": "", "id": "0",
                          "width": self.size, "height": self.size, "uv_width": self.size, "uv_height": self.size,
                          "particle": False, "use_as_default": False, "layers_enabled": False,
                          "sync_to_project": "", "render_mode": "default", "render_sides": "auto",
                          "frame_time": 1, "frame_order_type": "loop", "frame_order": "",
                          "frame_interpolate": False, "visible": True, "internal": True, "saved": False,
                          "uuid": U(), "source": "data:image/png;base64," + b64}],
            "animations": self.anims,
        }
        with open(path_json, "w") as f:
            json.dump(data, f)

    def preview(self, path):
        S = 4
        W, H = 1100, 420
        im = Image.new("RGB", (W, H), (200, 200, 215))
        dr = ImageDraw.Draw(im)
        cols = {"body": (60, 40, 85), "glow": (255, 50, 110), "membrane": (110, 50, 160), "plain": (45, 35, 60)}
        # front view (x,y) and side view (z,y)
        for view, ox in (("front", 330), ("side", 800)):
            els = sorted(self.elements, key=lambda e: (e["from"][2] if view == "front" else e["from"][0]), reverse=(view != "front"))
            for el in els:
                f, t = el["from"], el["to"]
                if view == "front":
                    a, b = f[0], t[0]
                else:
                    a, b = f[2], t[2]
                x1, x2 = ox + a * S, ox + b * S
                y1, y2 = H - 20 - t[1] * S, H - 20 - f[1] * S
                dr.rectangle([min(x1, x2), y1, max(x1, x2), y2], fill=cols.get(el["_kind"], (60, 40, 85)), outline=(15, 10, 20))
        im.save(path)


# ============================ DRAGON ============================
D = Model("void_dragon")
c = D.cube

body = c("body", [-12, 44, -16], [12, 64, 24])
spines = [c(f"spine{i}", [-2, 64, z], [2, 70, z + 4], "plain") for i, z in enumerate([-12, -4, 4, 12, 20])]
chest = c("chest", [-10, 46, -22], [10, 62, -16])

neck1 = c("neck1", [-6, 52, -30], [6, 64, -22])
neck2 = c("neck2", [-5, 54, -42], [5, 64, -30])
head = c("head", [-7, 52, -60], [7, 66, -42])
snout = c("snout", [-4, 52, -72], [4, 58, -60])
horn_l = c("horn_l", [4, 66, -52], [6, 74, -50], "plain")
horn_r = c("horn_r", [-6, 66, -52], [-4, 74, -50], "plain")
eye_l = c("eye_l", [7, 59, -58], [8, 62, -54], "glow")
eye_r = c("eye_r", [-8, 59, -58], [-7, 62, -54], "glow")
jaw = c("jaw_cube", [-4, 49, -70], [4, 52, -54], "plain")

jaw_g = D.group("jaw", [0, 51, -54], [jaw])
head_g = D.group("head", [0, 59, -42], [head, snout, horn_l, horn_r, eye_l, eye_r, jaw_g])
neck2_g = D.group("neck2", [0, 59, -30], [neck2, head_g])
neck_g = D.group("neck", [0, 58, -22], [neck1, neck2_g])

def wing(side):
    s = 1 if side == "l" else -1
    X = lambda x: x * s
    def box(a, b):
        xs = sorted([X(a[0]), X(b[0])])
        return [xs[0], a[1], a[2]], [xs[1], b[1], b[2]]
    f, t = box([12, 58, -8], [36, 64, 0]); arm = c(f"wing_{side}_arm", f, t)
    f, t = box([36, 58, -6], [62, 63, -2]); fore = c(f"wing_{side}_fore", f, t)
    f, t = box([36, 60, -2], [64, 61, 24]); mem = c(f"wing_{side}_membrane", f, t, "membrane")
    f, t = box([14, 59, 0], [36, 60, 20]); mem2 = c(f"wing_{side}_membrane_in", f, t, "membrane")
    f, t = box([62, 58, -6], [66, 70, -2]); claw = c(f"wing_{side}_claw", f, t, "plain")
    tip = D.group(f"wing_{side}_tip", [X(36), 61, -4], [fore, mem, claw])
    return D.group(f"wing_{side}", [X(12), 62, -4], [arm, mem2, tip])

wing_l, wing_r = wing("l"), wing("r")

tail1 = c("tail1", [-8, 46, 24], [8, 60, 40])
tail2 = c("tail2", [-6, 48, 40], [6, 58, 58])
tail3 = c("tail3", [-4, 49, 58], [4, 57, 76])
tail_tip = c("tail_tip", [-2, 50, 76], [2, 56, 86], "plain")
t3_g = D.group("tail3", [0, 53, 58], [tail3, tail_tip])
t2_g = D.group("tail2", [0, 53, 40], [tail2, t3_g])
t1_g = D.group("tail1", [0, 54, 24], [tail1, t2_g])

def leg(name, x, z):
    s = 1 if x > 0 else -1
    lo, hi = sorted([x - 3, x + 3])
    thigh = c(f"{name}_thigh", [lo, 30, z - 3], [hi, 46, z + 3])
    lo, hi = sorted([x - 2, x + 2])
    shin = c(f"{name}_shin", [lo, 10, z - 2], [hi, 30, z + 2])
    lo, hi = sorted([x - 3, x + 3])
    foot = c(f"{name}_foot", [lo, 2, z - 4], [hi, 10, z + 2], "plain")
    lo, hi = sorted([x - 1, x + 1])
    claw = c(f"{name}_claw", [lo, 0, z - 9], [hi, 4, z - 4], "plain")
    claw2 = c(f"{name}_claw2", [lo, 0, z - 4], [hi, 2, z + 2], "plain")
    foot_g = D.group(f"{name}_foot", [x, 10, z], [foot, claw, claw2])
    shin_g = D.group(f"{name}_shin", [x, 30, z], [shin, foot_g])
    return D.group(f"{name}_thigh", [x, 46, z], [thigh, shin_g])

legs = [leg("leg_fl", 9, -8), leg("leg_fr", -9, -8), leg("leg_bl", 9, 14), leg("leg_br", -9, 14)]

root = D.group("root", [0, 0, 0], [body, chest] + spines + [neck_g, wing_l, wing_r, t1_g] + legs)

# ======================= v2 ADDITIONS - DRAGON (every original part above is untouched) =======================
def mir(model, name, fr, to, kind="body"):
    """cube + its x-mirror twin, returns both uuids"""
    a = model.cube(name + "_l", fr, to, kind)
    b = model.cube(name + "_r", [-to[0], fr[1], fr[2]], [-fr[0], to[1], to[2]], kind)
    return [a, b]

def pulse(a, b, L, n=1):
    """n back-and-forth cycles a->b->a inside length L"""
    return [(round(L * k / (2 * n), 4), a if k % 2 == 0 else b) for k in range(2 * n + 1)]

def spin(ax, deg, L):
    out = []
    for t, f in ((0, 0), (L / 2, .5), (L, 1)):
        v = [0, 0, 0]
        v[ax] = deg * f
        out.append((t, tuple(v)))
    return out

def hold(vec, t_in, t_out, L):
    return [(0, (0, 0, 0)), (t_in, vec), (t_out, vec), (L, (0, 0, 0))]

# head: brow ridges, cheek spikes, swept-back horns, crest, nostrils, upper fangs
head_g["children"] += (mir(D, "brow", [3, 64, -57], [7, 67, -46], "plain")
    + mir(D, "cheek_spike", [7, 53, -52], [10, 58, -47], "plain")
    + mir(D, "horn_back", [7, 60, -47], [10, 64, -43], "plain")
    + mir(D, "horn_back_tip", [8, 64, -46], [10, 72, -44], "plain")
    + mir(D, "nostril", [2, 55, -73], [3, 57, -72], "energy"))
head_g["children"] += [D.cube(f"head_crest{i}", [-1, 66, z], [1, 69 + (i % 2) * 3, z + 3], "plain") for i, z in enumerate([-50, -46, -43])]
head_g["children"] += [D.cube(f"tooth_up{i}_{sd}", [x, 50, z], [x + 1, 52, z + 1], "tooth") for i, z in enumerate([-71, -67, -63]) for sd, x in (("l", 2), ("r", -3))]
jaw_g["children"] += [D.cube(f"tooth_low{i}_{sd}", [x, 51, z], [x + 1, 54, z + 1], "tooth") for i, z in enumerate([-69, -65, -61]) for sd, x in (("l", 4), ("r", -5))]
jaw_g["children"].append(D.cube("chin_spike", [-1, 46, -66], [1, 49, -62], "plain"))

# neck spines
neck_g["children"] += [D.cube(f"neck1_spine{i}", [-1, 64, z], [1, 68, z + 3], "plain") for i, z in enumerate([-29, -25])]
neck2_g["children"] += [D.cube(f"neck2_spine{i}", [-1, 64, z], [1, 67, z + 3], "plain") for i, z in enumerate([-41, -37, -33])]

# body: void core, belly plate, armour plates, back crystals
root["children"] += [D.cube("void_core", [-3, 47, -23], [3, 52, -22], "energy"),
                     D.cube("belly_plate", [-8, 42, -14], [8, 44, 20], "plain")]
root["children"] += mir(D, "shoulder_plate", [12, 56, -16], [15, 64, -9], "plain") + mir(D, "hip_plate", [12, 54, 10], [15, 62, 18], "plain")
for i, (z, h) in enumerate([(-10, 7), (0, 9), (10, 8), (18, 6)]):
    root["children"] += mir(D, f"back_crystal{i}", [4, 64, z], [6, 64 + h, z + 2], "crystal")

# wings: bone ribs + glowing veins
def wing_extras(side):
    sg = 1 if side == "l" else -1
    def bx(a, b):
        xs = sorted([a[0] * sg, b[0] * sg])
        return [xs[0], a[1], a[2]], [xs[1], b[1], b[2]]
    tip_kids, wing_kids = [], []
    for i, x in enumerate((42, 50, 58)):
        f, t = bx([x, 59, -2], [x + 2, 62, 24]); tip_kids.append(D.cube(f"wing_{side}_rib{i}", f, t, "plain"))
    for i, z in enumerate((4, 12)):
        f, t = bx([37, 61, z], [63, 63, z + 1]); tip_kids.append(D.cube(f"wing_{side}_vein{i}", f, t, "energy"))
    for i, x in enumerate((20, 28)):
        f, t = bx([x, 58, 0], [x + 2, 61, 20]); wing_kids.append(D.cube(f"wing_{side}_inrib{i}", f, t, "plain"))
    D.gobj[f"wing_{side}_tip"]["children"] += tip_kids
    D.gobj[f"wing_{side}"]["children"] += wing_kids
wing_extras("l"); wing_extras("r")

# tail: spikes + blade
for gname, top, zs, h in (("tail1", 60, (28, 35), 5), ("tail2", 58, (44, 52), 4), ("tail3", 57, (62, 69), 3)):
    D.gobj[gname]["children"] += [D.cube(f"{gname}_spike{i}", [-1, top, z], [1, top + h, z + 3], "plain") for i, z in enumerate(zs)]
D.gobj["tail3"]["children"] += [D.cube("tail_blade", [-1, 50, 86], [1, 62, 96], "plain"),
                                D.cube("tail_blade_tip", [-1, 56, 96], [1, 66, 102], "energy")]

# legs: knee spike, heel spike, side toe claws
def leg_extras(name, x, z):
    D.gobj[f"{name}_thigh"]["children"].append(D.cube(f"{name}_knee_spike", [x - 1, 40, z - 7], [x + 1, 44, z - 3], "plain"))
    D.gobj[f"{name}_shin"]["children"].append(D.cube(f"{name}_heel_spike", [x - 1, 20, z + 2], [x + 1, 25, z + 6], "plain"))
    D.gobj[f"{name}_foot"]["children"] += [D.cube(f"{name}_toe_a", [x - 3, 0, z - 8], [x - 2, 3, z - 4], "plain"),
                                           D.cube(f"{name}_toe_b", [x + 2, 0, z - 8], [x + 3, 3, z - 4], "plain")]
for nm, lx, lz in (("leg_fl", 9, -8), ("leg_fr", -9, -8), ("leg_bl", 9, 14), ("leg_br", -9, 14)):
    leg_extras(nm, lx, lz)

# orbiting void aura above the back (spins in every animation)
_orbs = []
for i in range(4):
    a = i * math.pi / 2
    ox, oz = round(16 * math.cos(a)), round(16 * math.sin(a)) + 4
    _orbs.append(D.cube(f"aura_orb{i}", [ox - 2, 78, oz - 2], [ox + 2, 82, oz + 2], "energy"))
    _orbs.append(D.cube(f"aura_shard{i}", [ox - 1, 82, oz - 1], [ox + 1, 88, oz + 1], "crystal"))
root["children"].append(D.group("aura", [0, 80, 4], _orbs))
D.build()

def sw(a, b, *rest):   # symmetric 3-key loop
    dur = rest[-1]
    return [(0, a), (dur / 2, b), (dur, a)]

L = 2.0
tracks = {
    "root": {"position": sw((0, 0, 0), (0, -3, 0), L)},
    "wing_l": {"rotation": sw((0, 0, -20), (0, 0, 35), None, L)},
    "wing_r": {"rotation": sw((0, 0, 20), (0, 0, -35), None, L)},
    "wing_l_tip": {"rotation": sw((0, 0, 15), (0, 0, -25), None, L)},
    "wing_r_tip": {"rotation": sw((0, 0, -15), (0, 0, 25), None, L)},
    "neck": {"rotation": sw((3, 0, 0), (-3, 0, 0), None, L)},
    "head": {"rotation": sw((-2, 0, 0), (2, 0, 0), None, L)},
    "jaw": {"rotation": [(0, (0, 0, 0)), (0.5, (12, 0, 0)), (1.0, (0, 0, 0)), (1.5, (12, 0, 0)), (2.0, (0, 0, 0))]},
    "tail1": {"rotation": sw((0, -8, 0), (0, 8, 0), None, L)},
    "tail2": {"rotation": sw((0, 8, 0), (0, -8, 0), None, L)},
    "tail3": {"rotation": sw((0, -8, 0), (0, 8, 0), None, L)},
}
for n, sgn in (("leg_fl", 1), ("leg_br", 1), ("leg_fr", -1), ("leg_bl", -1)):
    tracks[f"{n}_thigh"] = {"rotation": sw((-6 * sgn, 0, 0), (6 * sgn, 0, 0), None, L)}
    tracks[f"{n}_shin"] = {"rotation": sw((10, 0, 0), (-4, 0, 0), None, L)}
tracks["aura"] = {"rotation": spin(1, 360, L), "position": sw((0, 0, 0), (0, 3, 0), L)}
D.anim("fly", L, tracks)
# ---- v2 extra dragon animations (fly is untouched) ----
D.anim("idle", 3.0, {
    "root": {"position": pulse((0, 0, 0), (0, -1.5, 0), 3.0)},
    "wing_l": {"rotation": pulse((0, 0, -8), (0, 0, 12), 3.0)}, "wing_r": {"rotation": pulse((0, 0, 8), (0, 0, -12), 3.0)},
    "neck": {"rotation": pulse((2, 0, 0), (-2, 0, 0), 3.0)},
    "tail1": {"rotation": pulse((0, -5, 0), (0, 5, 0), 3.0)}, "tail2": {"rotation": pulse((0, 5, 0), (0, -5, 0), 3.0)},
    "aura": {"rotation": spin(1, 360, 3.0)}})
D.anim("breath", 2.5, {   # void breath: head up, jaw wide, wings flared
    "neck": {"rotation": hold((-22, 0, 0), 0.4, 2.0, 2.5)}, "neck2": {"rotation": hold((-12, 0, 0), 0.4, 2.0, 2.5)},
    "head": {"rotation": hold((-18, 0, 0), 0.4, 2.0, 2.5)}, "jaw": {"rotation": hold((38, 0, 0), 0.4, 2.0, 2.5)},
    "wing_l": {"rotation": hold((0, 0, -40), 0.4, 2.0, 2.5)}, "wing_r": {"rotation": hold((0, 0, 40), 0.4, 2.0, 2.5)},
    "aura": {"rotation": spin(1, 720, 2.5)}}, "once")
D.anim("tail_whip", 1.2, {
    "tail1": {"rotation": [(0, (0, 0, 0)), (0.3, (0, -35, 0)), (0.7, (0, 35, 0)), (1.2, (0, 0, 0))]},
    "tail2": {"rotation": [(0, (0, 0, 0)), (0.3, (0, -45, 0)), (0.7, (0, 45, 0)), (1.2, (0, 0, 0))]},
    "tail3": {"rotation": [(0, (0, 0, 0)), (0.3, (0, -55, 0)), (0.7, (0, 55, 0)), (1.2, (0, 0, 0))]},
    "root": {"rotation": [(0, (0, 0, 0)), (0.3, (0, 12, 0)), (0.7, (0, -12, 0)), (1.2, (0, 0, 0))]}}, "once")
D.anim("dive", 1.6, {
    "root": {"rotation": hold((40, 0, 0), 0.5, 1.1, 1.6)}, "neck": {"rotation": hold((15, 0, 0), 0.5, 1.1, 1.6)},
    "wing_l": {"rotation": hold((0, 0, 50), 0.5, 1.1, 1.6)}, "wing_r": {"rotation": hold((0, 0, -50), 0.5, 1.1, 1.6)},
    "tail1": {"rotation": hold((-20, 0, 0), 0.5, 1.1, 1.6)}}, "once")
D.anim("roar", 2.0, {
    "neck": {"rotation": hold((-15, 0, 0), 0.3, 1.6, 2.0)}, "head": {"rotation": hold((-25, 0, 0), 0.3, 1.6, 2.0)},
    "jaw": {"rotation": hold((40, 0, 0), 0.3, 1.6, 2.0)},
    "wing_l": {"rotation": hold((0, 0, -35), 0.3, 1.6, 2.0)}, "wing_r": {"rotation": hold((0, 0, 35), 0.3, 1.6, 2.0)},
    "root": {"position": pulse((0, 0, 0), (0, 1.5, 0), 2.0, 4)}}, "once")
D.anim("heal", 3.0, {    # dragon draining a crystal: wings up, aura spinning fast, hover bob
    "root": {"position": pulse((0, 0, 0), (0, 3, 0), 3.0)},
    "wing_l": {"rotation": pulse((0, 0, -30), (0, 0, -20), 3.0, 2)}, "wing_r": {"rotation": pulse((0, 0, 30), (0, 0, 20), 3.0, 2)},
    "neck": {"rotation": hold((-10, 0, 0), 0.5, 2.5, 3.0)}, "aura": {"rotation": spin(1, 1080, 3.0)}})
D.save([root], os.path.join(OUT, "void_dragon.bbmodel"), os.path.join(OUT, "void_dragon.png"))
D.preview(os.path.join(OUT, "void_dragon_preview.png"))

# ============================ MINION ============================
M = Model("void_wraith")
c = M.cube
torso = c("torso", [-4, 8, -3], [4, 20, 3])
head = c("head", [-4, 20, -4], [4, 28, 4])
eye_l = c("eye_l", [4, 23, -3], [5, 26, 0], "glow")
eye_r = c("eye_r", [-5, 23, -3], [-4, 26, 0], "glow")
horn_l = c("horn_l", [2, 28, -1], [4, 33, 1], "plain")
horn_r = c("horn_r", [-4, 28, -1], [-2, 33, 1], "plain")
arm_l = c("arm_l", [4, 11, -1], [6, 21, 1])
arm_r = c("arm_r", [-6, 11, -1], [-4, 21, 1])
claw_l = c("claw_l", [4, 6, -2], [6, 11, 2], "plain")
claw_r = c("claw_r", [-6, 6, -2], [-4, 11, 2], "plain")
w_l = c("wing_l_cube", [4, 12, 2], [16, 26, 3], "membrane")
w_r = c("wing_r_cube", [-16, 12, 2], [-4, 26, 3], "membrane")
wisp1 = c("wisp1", [-3, 2, -2], [3, 8, 2])
wisp2 = c("wisp2", [-2, -3, -1], [2, 2, 1], "plain")

wl = M.group("wing_l", [4, 16, 2], [w_l])
wr = M.group("wing_r", [-4, 16, 2], [w_r])
al = M.group("arm_l", [5, 20, 0], [arm_l, claw_l])
ar = M.group("arm_r", [-5, 20, 0], [arm_r, claw_r])
w2 = M.group("wisp2", [0, 2, 0], [wisp2])
w1 = M.group("wisp1", [0, 8, 0], [wisp1, w2])
hd = M.group("head", [0, 20, 0], [head, eye_l, eye_r, horn_l, horn_r])
mroot = M.group("root", [0, 0, 0], [torso, hd, al, ar, wl, wr, w1])

# ======================= v2 ADDITIONS - MINION (original parts above are untouched) =======================
M.gobj["head"]["children"] += [M.cube(f"crown_spike{i}", [-1, 28, z], [1, 28 + h, z + 1], "plain") for i, (z, h) in enumerate([(-3, 3), (0, 5), (2, 3)])]
M.gobj["head"]["children"] += [M.cube(f"fang{i}", [x, 20, -5], [x + 1, 22, -4], "tooth") for i, x in enumerate((-3, 2))]
mroot["children"] += [M.cube("heart_core", [-2, 13, -4], [2, 17, -3], "energy"),
                      M.cube("back_spike0", [-1, 12, 3], [1, 18, 5], "plain"),
                      M.cube("back_spike1", [-1, 18, 3], [1, 24, 5], "plain")]
M.gobj["arm_l"]["children"].append(M.cube("shoulder_l", [4, 19, -2], [7, 22, 2], "plain"))
M.gobj["arm_r"]["children"].append(M.cube("shoulder_r", [-7, 19, -2], [-4, 22, 2], "plain"))
# void scythe held in the right claw (swings with the arm)
M.gobj["arm_r"]["children"] += [M.cube("scythe_handle", [-8, 3, -1], [-6, 30, 0], "plain"),
                                M.cube("scythe_blade", [-15, 29, -1], [-6, 32, 0], "crystal"),
                                M.cube("scythe_tip", [-17, 24, -1], [-15, 31, 0], "energy")]
M.gobj["wisp1"]["children"] += [M.cube("robe_front", [-3, 2, -3], [3, 8, -2], "membrane"),
                                M.cube("robe_l", [3, 1, -1], [4, 8, 1], "membrane"),
                                M.cube("robe_r", [-4, 1, -1], [-3, 8, 1], "membrane")]
M.gobj["wing_l"]["children"] += [M.cube("wing_l_low", [4, 5, 2], [11, 12, 3], "membrane"), M.cube("wing_l_bone", [4, 25, 3], [16, 27, 4], "plain")]
M.gobj["wing_r"]["children"] += [M.cube("wing_r_low", [-11, 5, 2], [-4, 12, 3], "membrane"), M.cube("wing_r_bone", [-16, 25, 3], [-4, 27, 4], "plain")]
mroot["children"].append(M.group("halo", [0, 36, 0], [
    M.cube("halo_n", [-5, 36, -5], [5, 37, -4], "energy"), M.cube("halo_s", [-5, 36, 4], [5, 37, 5], "energy"),
    M.cube("halo_w", [-5, 36, -4], [-4, 37, 4], "energy"), M.cube("halo_e", [4, 36, -4], [5, 37, 4], "energy")]))
M.build()
L = 0.6
M.anim("fly", L, {
    "root": {"position": sw((0, 0, 0), (0, 2, 0), None, L)},
    "wing_l": {"rotation": sw((0, -30, 0), (0, 30, 0), None, L)},
    "wing_r": {"rotation": sw((0, 30, 0), (0, -30, 0), None, L)},
    "arm_l": {"rotation": sw((-15, 0, -10), (15, 0, -10), None, L)},
    "arm_r": {"rotation": sw((15, 0, 10), (-15, 0, 10), None, L)},
    "wisp1": {"rotation": sw((10, 0, 0), (-10, 0, 0), None, L)},
    "wisp2": {"rotation": sw((-15, 0, 0), (15, 0, 0), None, L)},
    "halo": {"rotation": spin(1, 360, L)},
})
# ---- v2 extra minion animations (fly is untouched) ----
M.anim("idle", 1.4, {"root": {"position": pulse((0, 0, 0), (0, 1.5, 0), 1.4)},
                     "wing_l": {"rotation": pulse((0, -12, 0), (0, 12, 0), 1.4)}, "wing_r": {"rotation": pulse((0, 12, 0), (0, -12, 0), 1.4)},
                     "halo": {"rotation": spin(1, 360, 1.4)}})
M.anim("attack", 0.8, {"root": {"position": [(0, (0, 0, 0)), (0.25, (0, 0, 6)), (0.45, (0, 0, -8)), (0.8, (0, 0, 0))]},
                       "arm_r": {"rotation": [(0, (0, 0, 10)), (0.25, (-70, 0, 10)), (0.45, (60, 0, 10)), (0.8, (0, 0, 10))]},
                       "arm_l": {"rotation": [(0, (0, 0, -10)), (0.25, (-50, 0, -10)), (0.45, (40, 0, -10)), (0.8, (0, 0, -10))]},
                       "wing_l": {"rotation": hold((0, -40, 0), 0.25, 0.5, 0.8)}, "wing_r": {"rotation": hold((0, 40, 0), 0.25, 0.5, 0.8)}}, "once")
M.anim("spawn", 1.0, {"root": {"scale": [(0, (0, 0, 0)), (0.5, (1.25, 1.25, 1.25)), (1.0, (1, 1, 1))],
                               "rotation": [(0, (0, 0, 0)), (1.0, (0, 360, 0))]}}, "once")
M.anim("death", 1.2, {"root": {"position": [(0, (0, 0, 0)), (1.2, (0, -10, 0))],
                               "rotation": [(0, (0, 0, 0)), (1.2, (80, 0, 0))],
                               "scale": [(0, (1, 1, 1)), (0.9, (1, 1, 1)), (1.2, (0, 0, 0))]}}, "once")
M.save([mroot], os.path.join(OUT, "void_wraith.bbmodel"), os.path.join(OUT, "void_wraith.png"))
M.preview(os.path.join(OUT, "void_wraith_preview.png"))

# ======================= v2 ADDITIONS - ATTACK MODELS (new; saved in ./attacks) =======================
def AP(n):
    return os.path.join(OUT, "attacks", n)

def ringXZ(m, p, half, th, y0, h, kind, rot=None):
    o = [0, y0, 0]
    return [m.cube(p + "_n", [-half, y0, -half], [half, y0 + h, -half + th], kind, rot, o),
            m.cube(p + "_s", [-half, y0, half - th], [half, y0 + h, half], kind, rot, o),
            m.cube(p + "_w", [-half, y0, -half + th], [-half + th, y0 + h, half - th], kind, rot, o),
            m.cube(p + "_e", [half - th, y0, -half + th], [half, y0 + h, half - th], kind, rot, o)]

def ringXY(m, p, z, half, th, cy, kind):
    return [m.cube(p + "_t", [-half, cy + half - th, z], [half, cy + half, z + 1], kind),
            m.cube(p + "_b", [-half, cy - half, z], [half, cy - half + th, z + 1], kind),
            m.cube(p + "_l", [-half, cy - half + th, z], [-half + th, cy + half - th, z + 1], kind),
            m.cube(p + "_r", [half - th, cy - half + th, z], [half, cy + half - th, z + 1], kind)]

def finish(m, outliner, name):
    m.save(outliner, AP(name + ".bbmodel"), AP(name + ".png"))
    m.preview(AP(name + "_preview.png"))
    return len(m.elements)

counts = {}

# ---- 1. VOID BREATH (cone of void energy + purple lightning swirls, flies along -Z from the mouth) ----
B = Model("void_breath"); c = B.cube
cone = [c(f"breath_cone{i}", [-(4 + 3 * i) // 2, 8 - (4 + 3 * i) // 2, -(i + 1) * 8], [(4 + 3 * i) // 2, 8 + (4 + 3 * i) // 2, -i * 8], "void" if i % 2 else "energy") for i in range(8)]
swirls = []
for k in range(3):
    z0, r, kids = -10 - k * 20, 8 + k * 5, []
    for j in range(4):
        a = j * math.pi / 2 + k * 0.4
        px, py = round(r * math.cos(a)), round(r * math.sin(a))
        kids.append(c(f"swirl{k}_{j}", [px - 1, 8 + py - 1, z0 - 1], [px + 1, 8 + py + 1, z0 + 3], "lightning"))
    swirls.append(B.group(f"swirl_{k}", [0, 8, z0], kids))
B_root = B.group("root", [0, 8, 0], cone + swirls)
B.build()
B.anim("breath", 1.0, {"swirl_0": {"rotation": spin(2, 360, 1.0)}, "swirl_1": {"rotation": spin(2, -360, 1.0)}, "swirl_2": {"rotation": spin(2, 360, 1.0)},
                       "root": {"scale": pulse((1, 1, 1), (1.08, 1.08, 1), 1.0, 3)}})
counts["void_breath"] = finish(B, [B_root], "void_breath")

# ---- 2. VOID FIREBALL ----
F = Model("void_fireball"); c = F.cube
fb = [c("core_a", [-4, 4, -4], [4, 12, 4], "fire"),
      c("core_b", [-4, 4, -4], [4, 12, 4], "fire", [0, 45, 0], [0, 8, 0]),
      c("core_c", [-4, 4, -4], [4, 12, 4], "energy", [45, 0, 45], [0, 8, 0]),
      c("spike_px", [4, 7, -1], [8, 9, 1], "energy"), c("spike_nx", [-8, 7, -1], [-4, 9, 1], "energy"),
      c("spike_py", [-1, 12, -1], [1, 16, 1], "energy"), c("spike_ny", [-1, 0, -1], [1, 4, 1], "energy"),
      c("spike_nz", [-1, 7, -8], [1, 9, -4], "lightning")]
trail = [c("trail0", [-3, 5, 5], [3, 11, 10], "void"), c("trail1", [-2, 6, 10], [2, 10, 15], "fire"), c("trail2", [-1, 7, 15], [1, 9, 20], "energy")]
F_core = F.group("core", [0, 8, 0], fb); F_trail = F.group("trail", [0, 8, 5], trail)
F_root = F.group("root", [0, 8, 0], [F_core, F_trail])
F.build()
F.anim("fly", 0.8, {"core": {"rotation": [(0, (0, 0, 0)), (0.4, (180, 180, 0)), (0.8, (360, 360, 0))]},
                    "trail": {"scale": pulse((1, 1, 1), (1.25, 1.25, 1.35), 0.8, 3)}})
counts["void_fireball"] = finish(F, [F_root], "void_fireball")

# ---- 3. VOID LIGHTNING (PURPLE bolt, base on the ground, 96px tall) ----
Lg = Model("void_lightning"); c = Lg.cube
xs_ = [0, 6, -4, 5, -6, 3, -5, 2]; zs_ = [0, -3, 2, -2, 3, -3, 2, 0]
bolt = []
for i in range(8):
    y0 = i * 12
    bolt.append(c(f"bolt_seg{i}", [xs_[i] - 2, y0, zs_[i] - 2], [xs_[i] + 2, y0 + 12, zs_[i] + 2], "lightning"))
    if i < 7:
        bolt.append(c(f"bolt_link{i}", [min(xs_[i], xs_[i + 1]) - 2, y0 + 10, min(zs_[i], zs_[i + 1]) - 2],
                      [max(xs_[i], xs_[i + 1]) + 2, y0 + 14, max(zs_[i], zs_[i + 1]) + 2], "lightning"))
for j, (bx0, by0, sg) in enumerate(((xs_[3], 40, 1), (xs_[5], 62, -1))):   # side forks
    for k in range(3):
        bolt.append(c(f"fork{j}_{k}", [bx0 + sg * (2 + k * 4) - 1 + (2 if sg < 0 else 0) - (2 if sg < 0 else 0), by0 - k * 5 - 5, -1], [bx0 + sg * (2 + k * 4) + 3 * (1 if sg > 0 else -1) + (0 if sg > 0 else 0), by0 - k * 5, 1], "lightning"))
imp = [c("scorch", [-14, 0, -14], [14, 1, 14], "void"), c("flash", [-7, 1, -7], [7, 2, 7], "energy"),
       c("ground_spark0", [-10, 2, -2], [-8, 8, 0], "lightning"), c("ground_spark1", [8, 2, 2], [10, 7, 4], "lightning")]
Lg_bolt = Lg.group("bolt", [0, 0, 0], bolt); Lg_imp = Lg.group("impact", [0, 0, 0], imp)
Lg_root = Lg.group("root", [0, 0, 0], [Lg_bolt, Lg_imp])
Lg.build()
Lg.anim("strike", 0.5, {"bolt": {"scale": [(0, (1, 0, 1)), (0.06, (1, 1, 1)), (0.2, (1.6, 1, 1.6)), (0.5, (1, 1, 1))]},
                        "impact": {"scale": [(0, (0.2, 1, 0.2)), (0.1, (1.4, 1, 1.4)), (0.5, (1, 1, 1))]}}, "once")
Lg.anim("flicker", 0.3, {"bolt": {"scale": pulse((1, 1, 1), (1.5, 1, 1.5), 0.3)}, "impact": {"scale": pulse((1, 1, 1), (1.2, 1, 1.2), 0.3)}})
counts["void_lightning"] = finish(Lg, [Lg_root], "void_lightning")

# ---- 4. VOID SHOCKWAVE ----
S = Model("void_shockwave"); c = S.cube
wave = ringXZ(S, "ring_a", 20, 4, 0, 4, "energy") + ringXZ(S, "ring_b", 20, 4, 0, 4, "void", [0, 45, 0]) + ringXZ(S, "ring_c", 12, 3, 0, 7, "lightning")
for i, (x, z) in enumerate([(20, 20), (-20, 20), (20, -20), (-20, -20), (28, 0), (-28, 0), (0, 28), (0, -28)]):
    wave.append(c(f"wave_spike{i}", [x - 1, 4, z - 1], [x + 1, 12, z + 1], "crystal"))
S_wave = S.group("wave", [0, 0, 0], wave)
S.build()
S.anim("expand", 0.8, {"wave": {"scale": [(0, (0.2, 1, 0.2)), (0.8, (2.2, 0.6, 2.2))]}}, "once")
S.anim("pulse", 0.6, {"wave": {"scale": pulse((1, 1, 1), (1.15, 1, 1.15), 0.6)}})
counts["void_shockwave"] = finish(S, [S_wave], "void_shockwave")

# ---- 5. VOID METEOR ----
Mt = Model("void_meteor"); c = Mt.cube
rock = [c("rock1", [-7, 2, -7], [7, 16, 7], "void"), c("rock2", [-9, 5, -5], [9, 13, 5], "void"), c("rock3", [-5, 0, -5], [5, 18, 5], "void"),
        c("vein0", [-8, 9, -3], [-6, 11, 3], "fire"), c("vein1", [6, 6, -2], [10, 8, 2], "fire"),
        c("shard0", [6, 10, -3], [10, 14, 0], "crystal"), c("shard1", [-10, 8, 0], [-6, 12, 3], "crystal")]
tail = [c(f"tail{i}", [-(14 - 2 * i) // 2, 18 + 8 * i, -(14 - 2 * i) // 2], [(14 - 2 * i) // 2, 26 + 8 * i, (14 - 2 * i) // 2], "fire" if i % 2 == 0 else "energy") for i in range(6)]
Mt_rock = Mt.group("rock", [0, 9, 0], rock); Mt_tail = Mt.group("tail", [0, 16, 0], tail)
Mt_root = Mt.group("root", [0, 0, 0], [Mt_rock, Mt_tail])
Mt.build()
Mt.anim("fall", 1.2, {"rock": {"rotation": spin(1, 360, 1.2)}, "tail": {"scale": pulse((1, 1, 1), (0.85, 1.15, 0.85), 1.2, 4)}})
counts["void_meteor"] = finish(Mt, [Mt_root], "void_meteor")

# ---- 6. CRYSTAL HEAL BEAM (crystal -> dragon, runs along +Z, 64px) ----
H = Model("void_heal_beam"); c = H.cube
core = [c(f"beam{i}", [-1, 7, i * 8], [1, 9, i * 8 + 8], "energy") if i % 2 else c(f"beam{i}", [-2, 6, i * 8], [2, 10, i * 8 + 8], "lightning") for i in range(8)]
rings = [H.group(f"ring{i}", [0, 8, 8 + i * 16], ringXY(H, f"ring{i}", 8 + i * 16, 5, 1, 8, "energy")) for i in range(4)]
helix = [c(f"helix{j}", [round(4 * math.cos(j * math.pi / 2)) - 1, 8 + round(4 * math.sin(j * math.pi / 2)) - 1, 4 + 8 * j], [round(4 * math.cos(j * math.pi / 2)) + 1, 8 + round(4 * math.sin(j * math.pi / 2)) + 1, 8 + 8 * j], "crystal") for j in range(8)]
H_core = H.group("core", [0, 8, 32], core); H_helix = H.group("helix", [0, 8, 32], helix)
H_root = H.group("root", [0, 8, 0], [H_core, H_helix] + rings)
H.build()
htr = {"helix": {"rotation": spin(2, 360, 1.0)}, "core": {"scale": pulse((1, 1, 1), (1.4, 1.4, 1), 1.0, 2)}}
for i in range(4):
    htr[f"ring{i}"] = {"scale": [(0, (1, 1, 1)), (0.25 * i + 0.01, (1, 1, 1)), (0.25 * i + 0.12 + 0.01, (1.7, 1.7, 1)), (1.0, (1, 1, 1))]}
H.anim("beam", 1.0, htr)
counts["void_heal_beam"] = finish(H, [H_root], "void_heal_beam")

# ---- 7. VOID SPIKES (ground eruption) ----
Sp = Model("void_spikes"); c = Sp.cube
def spike(m, name, cx, cz, h, base, tilt=None):
    ids = []
    for i in range(3):
        w = max(2, round(base * (1 - i / 3)))
        y0, y1 = round(h * i / 3), round(h * (i + 1) / 3)
        ids.append(m.cube(f"{name}_{i}", [cx - w // 2, y0, cz - w // 2], [cx - w // 2 + w, y1, cz - w // 2 + w], "crystal" if i else "void",
                          list(tilt) if tilt else None, [cx, 0, cz]))
    return ids
base_plate = [c("crack_a", [-18, 0, -8], [18, 1, 8], "void"), c("crack_b", [-8, 0, -18], [8, 1, 18], "void")]
sp_groups = [Sp.group("spike_0", [0, 0, 0], spike(Sp, "s0", 0, 0, 44, 8))]
for k in range(6):
    a = k * math.pi / 3
    cx, cz = round(14 * math.cos(a)), round(14 * math.sin(a))
    sp_groups.append(Sp.group(f"spike_{k + 1}", [cx, 0, cz], spike(Sp, f"s{k + 1}", cx, cz, 22 + (k % 3) * 6, 6, (round(14 * math.sin(a)), 0, -round(14 * math.cos(a))))))
Sp_root = Sp.group("root", [0, 0, 0], base_plate + sp_groups)
Sp.build()
sptr = {}
for k in range(7):
    t1 = round(0.05 + 0.05 * k, 3); t2 = round(t1 + 0.2, 3)
    sptr[f"spike_{k}"] = {"scale": [(0, (1, 0, 1)), (t1, (1, 0, 1)), (t2, (1, 1.15, 1)), (0.9, (1, 1, 1)), (1.2, (1, 1, 1))]}
Sp.anim("erupt", 1.2, sptr, "once")
counts["void_spikes"] = finish(Sp, [Sp_root], "void_spikes")

# ---- 8. VOID VORTEX / black hole ----
V = Model("void_vortex"); c = V.cube
vcore = [c("hole_a", [-6, 4, -4], [6, 12, 4], "void"), c("hole_b", [-4, 4, -6], [4, 12, 6], "void"), c("hole_c", [-4, 2, -4], [4, 14, 4], "void")]
disc_a = ringXZ(V, "disc_a", 12, 3, 7, 2, "energy") + ringXZ(V, "disc_a45", 12, 3, 7, 2, "energy", [0, 45, 0])
disc_b = ringXZ(V, "disc_b", 18, 2, 8, 1, "lightning") + ringXZ(V, "disc_b45", 18, 2, 8, 1, "lightning", [0, 45, 0])
arms = []
for arm in range(3):
    for j in range(5):
        a = arm * 2 * math.pi / 3 + j * 0.5; r = 8 + j * 4
        px, pz = round(r * math.cos(a)), round(r * math.sin(a))
        arms.append(c(f"arm{arm}_{j}", [px - 1, 7, pz - 1], [px + 2, 9, pz + 2], ("energy", "void", "lightning")[j % 3]))
V_core = V.group("core", [0, 8, 0], vcore); V_a = V.group("disc_a", [0, 8, 0], disc_a); V_b = V.group("disc_b", [0, 8, 0], disc_b); V_arms = V.group("arms", [0, 8, 0], arms)
V_root = V.group("root", [0, 8, 0], [V_core, V_a, V_b, V_arms])
V.build()
V.anim("spin", 2.0, {"core": {"rotation": spin(1, 360, 2.0)}, "disc_a": {"rotation": spin(1, 360, 2.0)}, "disc_b": {"rotation": spin(1, -360, 2.0)},
                     "arms": {"rotation": spin(1, 720, 2.0)}, "root": {"scale": pulse((1, 1, 1), (1.1, 1, 1.1), 2.0, 2)}})
counts["void_vortex"] = finish(V, [V_root], "void_vortex")

# ---- 9. SHADOW BOLT (minion projectile) ----
Sb = Model("shadow_bolt"); c = Sb.cube
sb_core = [c("bolt_core", [-2, 6, -4], [2, 10, 4], "energy"), c("bolt_cross", [-4, 7, -2], [4, 9, 2], "lightning"),
           c("shard_u", [-1, 10, -1], [1, 13, 1], "crystal"), c("shard_d", [-1, 3, -1], [1, 6, 1], "crystal")]
sb_tail = [c("bolt_tail0", [-1, 7, 4], [1, 9, 9], "void"), c("bolt_tail1", [-1, 7, 9], [1, 9, 13], "energy")]
Sb_core = Sb.group("core", [0, 8, 0], sb_core); Sb_tail = Sb.group("tail", [0, 8, 4], sb_tail)
Sb_root = Sb.group("root", [0, 8, 0], [Sb_core, Sb_tail])
Sb.build()
Sb.anim("fly", 0.5, {"core": {"rotation": spin(2, 360, 0.5)}, "tail": {"scale": pulse((1, 1, 1), (1.3, 1.3, 1.4), 0.5, 2)}})
counts["shadow_bolt"] = finish(Sb, [Sb_root], "shadow_bolt")

# ---- 10. VOID SLASH (claw / tail sweep crescent) ----
Sl = Model("void_slash"); c = Sl.cube
arc = []
thick = [2, 3, 4, 5, 6, 5, 4, 3, 2]
for k in range(9):
    a = -80 + 20 * k; ar = math.radians(a)
    for rad, kind, tk in ((26, "energy", thick[k]), (22, "lightning", max(1, thick[k] - 3))):
        px, pz = rad * math.sin(ar), -rad * math.cos(ar)
        cx, cz = round(px), round(pz)
        arc.append(c(f"slash{k}_{rad}", [cx - 5, 7, cz - tk // 2], [cx + 5, 9 if rad == 26 else 8, cz - tk // 2 + tk], kind, [0, -a, 0], [cx, 8, cz]))
Sl_arc = Sl.group("arc", [0, 8, 0], arc)
Sl.build()
Sl.anim("swipe", 0.4, {"arc": {"rotation": [(0, (0, -70, 0)), (0.2, (0, 0, 0)), (0.4, (0, 70, 0))],
                               "scale": [(0, (0.6, 1, 0.6)), (0.2, (1.1, 1, 1.1)), (0.4, (0.8, 1, 0.8))]}}, "once")
counts["void_slash"] = finish(Sl, [Sl_arc], "void_slash")

# ---- 11. CRYSTAL SHIELD (deepslate cage + rune ring; shown while the crystal is protected) ----
Cs = Model("crystal_shield"); c = Cs.cube
cage = []
for i, (x, z) in enumerate([(-20, -20), (17, -20), (-20, 17), (17, 17)]):
    cage.append(c(f"post{i}", [x, 3, z], [x + 3, 37, z + 3], "deepslate"))
    cage.append(c(f"cap{i}", [x, 40, z], [x + 3, 46, z + 3], "crystal"))
cage += ringXZ(Cs, "base", 20, 3, 0, 3, "deepslate") + ringXZ(Cs, "top", 20, 3, 37, 3, "deepslate")
runes = ringXZ(Cs, "rune_ring", 24, 2, 19, 2, "energy") + [c(f"rune_orb{i}", [x - 2, 18, z - 2], [x + 2, 22, z + 2], "lightning") for i, (x, z) in enumerate([(24, 0), (-24, 0), (0, 24), (0, -24)])]
Cs_cage = Cs.group("cage", [0, 0, 0], cage); Cs_runes = Cs.group("runes", [0, 20, 0], runes)
Cs_root = Cs.group("root", [0, 0, 0], [Cs_cage, Cs_runes])
Cs.build()
Cs.anim("idle", 4.0, {"runes": {"rotation": spin(1, 360, 4.0)}, "cage": {"scale": pulse((1, 1, 1), (1.02, 1.02, 1.02), 4.0, 2)}})
Cs.anim("break", 0.8, {"cage": {"scale": [(0, (1, 1, 1)), (0.8, (1.5, 0, 1.5))]}, "runes": {"scale": [(0, (1, 1, 1)), (0.8, (2, 0, 2))]}}, "once")
counts["crystal_shield"] = finish(Cs, [Cs_root], "crystal_shield")
print("attack models:", counts)

print("dragon tex", D.size, "elements", len(D.elements), "| minion tex", M.size, "elements", len(M.elements))
