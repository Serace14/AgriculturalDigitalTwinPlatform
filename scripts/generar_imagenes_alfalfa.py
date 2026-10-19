"""Genera una vista aérea ilustrada de parcelas de alfalfa en distintos estados de
crecimiento (izq -> dcha: recién cortada, rebrote, vegetativo, floración, reposo).
Mismo planteamiento que la imagen de árboles original: cuadrícula de parcelas
con distinto estado fenológico, vista cenital con sombras.

Uso: python3 alfalfa_img.py <salida.jpg> [tamaño=1024] [semilla=7]
"""
import os, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

out = sys.argv[1]
SIZE = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 7
SS = 2                       # supersampling
ASPECT = float(os.environ.get('ASPECT', '1'))
W = SIZE * SS
H = int(W * ASPECT)
rng = random.Random(SEED)
nrng = np.random.default_rng(SEED)

# ---------------------------------------------------------------- paleta
SOIL = (150, 124, 92)
SOIL_DARK = (96, 78, 58)
SHADOW = (18, 38, 22)

def jitter(c, a=12):
    return tuple(max(0, min(255, int(v + rng.uniform(-a, a)))) for v in c)

def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

# ---------------------------------------------------------------- lienzo base
img = Image.new('RGB', (W, H), SOIL)
d = ImageDraw.Draw(img)

# ruido de suelo
noise = nrng.normal(0, 9, (H, W, 1))
base = np.asarray(img).astype(np.float32) + noise
img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)

# ---------------------------------------------------------------- geometría
NCOL = int(os.environ.get('NCOL', '5'))
ORDER = [int(v) for v in os.environ.get('ORDER', '0,1,2,3,4').split(',')]
RSCALE = float(os.environ.get('RSCALE', '1'))
PATH = int(float(os.environ.get('PATHW', '0.020')) * W)        # caminos entre parcelas
MARGIN = int(0.012 * W)
colw = (W - 2 * MARGIN - (NCOL - 1) * PATH) / NCOL
NROW = int(os.environ.get('NROW', '4'))
rowh = (H - 2 * MARGIN - (NROW - 1) * PATH) / NROW

ROW_SPACING = int(0.0125 * W * RSCALE)   # separación de líneas de siembra


def ellipse_poly(cx, cy, rx, ry, ang, n=10):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return pts


def trifoliate(cx, cy, r, color, shade=True, spread=None):
    """Hoja trifoliada de alfalfa vista desde arriba (3 folíolos) + sombra."""
    base_ang = rng.uniform(0, 2 * math.pi)
    parts = []
    for k in range(3):
        a = base_ang + k * 2 * math.pi / 3 + rng.uniform(-0.25, 0.25)
        off = r * 0.75
        parts.append((cx + math.cos(a) * off, cy + math.sin(a) * off, a))
    if shade:
        sh = tuple(int(v) for v in lerp(color, SHADOW, 0.78))
        for (px, py, a) in parts:
            d.polygon(ellipse_poly(px + r * 0.55, py + r * 0.75, r * 0.78, r * 0.42, a), fill=sh)
    for (px, py, a) in parts:
        lc = jitter(color, 10)
        d.polygon(ellipse_poly(px, py, r * 0.78, r * 0.42, a), fill=lc)
        # nervio central, más claro
        ex, ey = math.cos(a) * r * 0.62, math.sin(a) * r * 0.62
        d.line([(px - ex, py - ey), (px + ex, py + ey)],
               fill=tuple(int(min(255, v + 22)) for v in lc), width=max(1, int(r * 0.07)))


def flower(cx, cy, r):
    col = rng.choice([(122, 84, 168), (146, 100, 188), (104, 70, 150), (165, 120, 205)])
    for k in range(5):
        a = rng.uniform(0, 2 * math.pi)
        d.ellipse([cx + math.cos(a) * r * .7 - r * .5, cy + math.sin(a) * r * .7 - r * .5,
                   cx + math.cos(a) * r * .7 + r * .5, cy + math.sin(a) * r * .7 + r * .5], fill=jitter(col, 12))


# ---------------------------------------------------------------- parcelas
# etapa: nombre, color hoja, radio hoja, densidad (hojas por línea y por unidad), flores
STAGES = [
    dict(name='corte',    leaf=(142, 164, 72), r=0.0034, dens=0.6, flowers=0.0, stubble=True),
    dict(name='rebrote',  leaf=(118, 168, 62), r=0.0040, dens=1.0,  flowers=0.0),
    dict(name='vegetat',  leaf=(72, 144, 50),  r=0.0066, dens=1.5,  flowers=0.0),
    dict(name='floracion', leaf=(58, 128, 50), r=0.0070, dens=1.6,  flowers=0.5),
    dict(name='reposo',   leaf=(150, 138, 84), r=0.0036, dens=0.9, flowers=0.0, dormant=True),
]

# variación por fila para que no sea idéntico: cada fila de parcelas adelanta/atrasa un poco
ROW_SHIFT = [0.0, 0.18, -0.12, 0.08, 0.1, -0.05]


def plot_rect(ci, ri):
    x0 = MARGIN + ci * (colw + PATH)
    y0 = MARGIN + ri * (rowh + PATH)
    return x0, y0, x0 + colw, y0 + rowh


# caminos de tierra (más claros) — se pintan donde no hay parcela, ya es suelo; añadimos huellas de tractor
for ci in range(NCOL - 1):
    x = MARGIN + (ci + 1) * colw + ci * PATH + PATH / 2
    for dx in (-PATH * .28, PATH * .28):
        d.line([(x + dx, 0), (x + dx, H)], fill=SOIL_DARK, width=max(2, int(PATH * .10)))
for ri in range(NROW - 1):
    y = MARGIN + (ri + 1) * rowh + ri * PATH + PATH / 2
    for dy in (-PATH * .28, PATH * .28):
        d.line([(0, y + dy), (W, y + dy)], fill=SOIL_DARK, width=max(2, int(PATH * .10)))

def clump(px, py, r, col, z, nleaf=3):
    """Mata de alfalfa: varios foliolos a distintas alturas."""
    for _ in range(nleaf):
        qx = px + rng.gauss(0, r * .9); qy = py + rng.gauss(0, r * .9)
        zz = z * rng.uniform(.6, 1.0)
        c = lerp(tuple(v * .72 for v in col), tuple(min(255, v * 1.12) for v in col), zz)
        trifoliate(qx, qy, r * rng.uniform(.8, 1.15), c)


for ri in range(NROW):
    for ci in range(NCOL):
        st = STAGES[ORDER[ci % len(ORDER)]]
        x0, y0, x1, y1 = plot_rect(ci, ri)
        shift = ROW_SHIFT[ri]
        r = W * st['r'] * (1 + shift * .4) * RSCALE

        # suelo de la parcela, con surcos entre líneas de siembra
        soil = (122, 98, 70) if not st.get('dormant') else (140, 116, 84)
        d.rectangle([x0, y0, x1, y1], fill=jitter(soil, 4))
        nlines = int((x1 - x0) / ROW_SPACING)
        for li in range(nlines + 1):
            lx = x0 + li * ROW_SPACING
            d.line([(lx, y0), (lx, y1)], fill=(104, 82, 58), width=max(1, int(ROW_SPACING * .12)))
        for _ in range(int((x1 - x0) * (y1 - y0) / 900)):     # terrones / piedras
            px = rng.uniform(x0, x1); py = rng.uniform(y0, y1); q = rng.uniform(1, 3.2)
            c = jitter((148, 122, 92) if rng.random() < .5 else (96, 76, 56), 10)
            d.ellipse([px - q, py - q * .8, px + q, py + q * .8], fill=c)

        sigx = ROW_SPACING * (0.10 if st['r'] < .006 else 0.30)
        leaves = []
        step = ROW_SPACING / (st['dens'] * 1.2)
        for li in range(nlines):
            lx = x0 + (li + 0.5) * ROW_SPACING
            n = int((y1 - y0) / step)
            for k in range(n):
                py = y0 + (k + rng.random()) * step
                px = lx + rng.gauss(0, sigx)
                if x0 + r < px < x1 - r and y0 + r < py < y1 - r:
                    leaves.append((py, px))
        leaves.sort()

        for (py, px) in leaves:
            t = ((px - x0) / (x1 - x0)) * .2 + ((py - y0) / (y1 - y0)) * .12
            col = lerp(st['leaf'], tuple(v * 0.85 for v in st['leaf']), t)
            if rng.random() < .12:       # manchas de otro tono
                col = lerp(col, (96, 150, 60), .35)
            z = rng.random()
            if st.get('dormant'):
                # corona seca: tallos radiales marrones + algún brote verde
                c0 = lerp((158, 134, 84), (110, 88, 56), rng.random())
                for _ in range(rng.randint(5, 9)):
                    a = rng.uniform(0, 2 * math.pi); L = r * rng.uniform(1.2, 3.0)
                    c = jitter(c0, 14)
                    d.line([(px + 1.5, py + 2), (px + 1.5 + math.cos(a) * L, py + 2 + math.sin(a) * L)],
                           fill=tuple(int(v * .55) for v in c), width=max(1, int(r * .26)))
                    d.line([(px, py), (px + math.cos(a) * L, py + math.sin(a) * L)],
                           fill=c, width=max(1, int(r * .22)))
                if rng.random() < .3:
                    trifoliate(px + rng.gauss(0, r), py + rng.gauss(0, r), r * .55, (112, 140, 66))
            elif st.get('stubble'):
                c = (214, 202, 126)
                for _ in range(rng.randint(3, 6)):
                    a = rng.uniform(0, 2 * math.pi); L = r * rng.uniform(.8, 1.8)
                    d.line([(px, py), (px + math.cos(a) * L, py + math.sin(a) * L)],
                           fill=jitter(c, 14), width=max(1, int(r * .28)))
                if rng.random() < .55:
                    trifoliate(px, py, r * .75, col)
            else:
                nl = 3 if st['dens'] < 1.2 else 2
                clump(px, py, r, col, z, nl)
                if st['flowers'] and rng.random() < st['flowers']:
                    for _ in range(rng.randint(1, 3)):
                        flower(px + rng.gauss(0, r * .8), py + rng.gauss(0, r * .8), r * .5)

        if st.get('stubble'):
            for k in range(3):
                yy_ = y0 + (k + .55) * rowh / 3 + rng.uniform(-10, 10)
                for x in range(int(x0), int(x1), 2):
                    wob = math.sin(x * .045 + k * 2) * 4
                    th = rng.uniform(3.5, 6.5)
                    d.ellipse([x - 5, yy_ + wob - th, x + 5, yy_ + wob + th],
                              fill=jitter((150, 146, 78), 16))
                    if rng.random() < .3:
                        d.line([(x - 6, yy_ + wob + rng.uniform(-th, th)), (x + 6, yy_ + wob + rng.uniform(-th, th))],
                               fill=jitter((190, 182, 106), 14), width=1)

img = img.filter(ImageFilter.GaussianBlur(0.9 * SS / 2))

# ---------------------------------------------------------------- tinte: bandas de pasada + luz
arr = np.asarray(img).astype(np.float32)
yy, xx = np.mgrid[0:H, 0:W]
# luz: más clara arriba-izquierda
light = 1.06 - 0.16 * (xx / W * .6 + yy / H * .4)
# bandas de segado suaves (alternan 3%)
bands = 1 + 0.035 * np.sign(np.sin(yy / (rowh / 7.5) * math.pi))
# manchas de variación a baja frecuencia
low = nrng.normal(0, 1, (H // 64 + 2, W // 64 + 2))
low = np.asarray(Image.fromarray(((low - low.min()) / (low.max() - low.min()) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255
mott = 0.93 + 0.14 * low
arr = arr * (light * bands * mott)[..., None]
# grano
arr += nrng.normal(0, 3.2, arr.shape)
img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
img = img.resize((SIZE, int(SIZE * ASPECT)), Image.LANCZOS)
img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
img.save(out, quality=90, optimize=True)
print('ok', out, img.size)
