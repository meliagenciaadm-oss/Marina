#!/usr/bin/env python3
"""Reel "Um Contratempo" — versão cinematográfica (estilo palavra gigante + máquina de escrever).

Uso: python montar_v4.py FALA.mp4 FILME.mp4 TELA_MAGALU.mp4 SAIDA.mp4 PASTA_RECURSOS [t1,t2,... para prévia]
  PASTA_RECURSOS: Anton.ttf, CourierPrime.ttf, Caveat.ttf, modnet.onnx
"""
import os, sys, math, random, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops

FALA, FILME, TELA, SAIDA, REC = sys.argv[1:6]
PREVIA = [float(x) for x in sys.argv[6].split(",")] if len(sys.argv) > 6 else None
W, H, FPS, NFR = 1080, 1920, 30, 909
DUR = NFR / FPS
random.seed(5); np.random.seed(5)

AMARELO = (250, 233, 163)
VERMELHO = (222, 40, 40)
BRANCO = (255, 255, 255)
F_BIG = os.path.join(REC, "Anton.ttf")
F_MONO = os.path.join(REC, "CourierPrime.ttf")
F_SCRIPT = os.path.join(REC, "Caveat.ttf")
_f, _c = {}, {}


def font(p, s):
    if (p, s) not in _f:
        f = ImageFont.truetype(p, s)
        if p == F_SCRIPT:
            try: f.set_variation_by_axes([700])
            except Exception: pass
        _f[(p, s)] = f
    return _f[(p, s)]


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_io(x): x = clamp(x); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x


# ---------------- texto ----------------
def camada(txt, path, size, cor, track=0, n=None, sombra=0.45):
    n = len(txt) if n is None else n
    k = (txt, path, size, cor, track, n)
    if k in _c: return _c[k]
    f = font(path, size); asc, desc = f.getmetrics()
    w = int(sum(f.getlength(c) for c in txt) + track * max(len(txt) - 1, 0)) + 2
    pad = 30
    lay = Image.new("RGBA", (w + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay); x = pad
    for c in txt[:n]:
        d.text((x, pad), c, font=f, fill=cor + (255,)); x += f.getlength(c) + track
    if sombra:
        a = lay.getchannel("A").filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * sombra))
        sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.putalpha(a)
        out = Image.new("RGBA", lay.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 3)); out.alpha_composite(lay)
        lay = out
    _c[k] = lay
    return lay


def cola(canvas, lay, cx, cy, escala=1.0, alpha=1.0):
    if escala != 1.0:
        lay = lay.resize((max(1, int(lay.width * escala)), max(1, int(lay.height * escala))), Image.BILINEAR)
    if alpha < 0.999:
        lay = lay.copy(); lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    tmp.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)
    canvas.alpha_composite(tmp)


# ---------------- roteiro ----------------
# blocos: (início, fim, cena, elementos)
#   cena: ("pessoa", zoom0, zoom1, cx, cy, pb) | ("filme", [(t0, seg_filme), ...]) | ("preto",) | ("celular",)
#   elemento: (t, estilo, texto, x, y, atrás_da_cabeça)
#     estilo: "big_y" (amarelo), "big_r" (vermelho), "mono", "script"
P = "pessoa"
BLOCOS = [
    (0.00, 2.20, (P, 1.00, 1.04, 540, 960, False), [
        (0.00, "mono", "talvez esse filme tenha passado", 540, 300, False),
        (1.48, "big_y", "DESPERCEBIDO", 540, 480, True)]),
    (2.20, 3.72, (P, 1.30, 1.33, 700, 860, False), [
        (2.22, "mono", "mas ele", 540, 1330, False),
        (2.58, "big_r", "MERECE", 540, 1500, False),
        (3.00, "mono", "a sua atenção", 540, 1680, False)]),
    (3.72, 4.68, (P, 1.00, 1.00, 540, 960, False), [
        (3.72, "mono", "e também um", 540, 1130, False),
        (4.32, "script", "cafezinho :)", 540, 1250, False)]),
    (4.68, 6.04, ("filme", [(4.68, 1.0)]), [
        (4.68, "mono", "o filme é um", 540, 640, False),
        (5.40, "big_y", "CONTRATEMPO", 540, 1290, False)]),
    (6.04, 8.12, (P, 1.15, 1.18, 620, 930, False), [
        (6.04, "mono", "um empresário", 330, 1100, False),
        (6.66, "mono", "que acorda", 800, 1100, False),
        (7.10, "mono", "num quarto de hotel", 540, 1170, False)]),
    (8.12, 10.60, ("filme", [(8.12, 31.0), (9.30, 36.0)]), [
        (8.12, "mono", "onde aconteceu um", 540, 640, False),
        (9.18, "big_r", "CRIME", 540, 1300, False),
        (9.46, "mono", "e ele jura que é inocente", 540, 1480, False)]),
    (10.60, 12.42, (P, 1.30, 1.33, 700, 860, False), [
        (10.60, "mono", "então ele vai tentar", 540, 300, False),
        (11.26, "big_y", "CONVENCER", 540, 470, True),
        (11.74, "mono", "a advogada", 540, 1500, False)]),
    (12.42, 13.18, ("preto",), [
        (12.42, "mono", "e a gente também :)", 540, 960, False)]),
    (13.18, 14.40, (P, 1.00, 1.03, 540, 960, False), [
        (13.18, "mono", "prepara o", 540, 1060, False),
        (14.20, "big_r", "CAFÉ", 540, 1240, False)]),
    (14.40, 16.58, (P, 1.22, 1.30, 640, 900, False), [
        (14.40, "mono", "porque você vai precisar ficar", 540, 1330, False),
        (15.50, "script", "bem acordada", 540, 1460, False)]),
    (16.58, 18.06, ("filme", [(16.58, 57.0), (17.07, 60.0), (17.56, 64.0)]), [
        (16.58, "mono", "pra não perder nenhum", 540, 640, False),
        (17.56, "big_y", "DETALHE", 540, 1300, False)]),
    (18.06, 20.78, (P, 1.15, 1.20, 640, 920, True), [
        (18.06, "mono_y", "e eu duvido", 540, 1100, False),
        (19.08, "mono_y", "você conseguir adivinhar", 540, 1165, False),
        (20.06, "mono_y", "o final desse filme :)", 540, 1230, False)]),
    (20.78, 22.62, (P, 1.00, 1.03, 540, 960, False), [
        (20.78, "mono", "e pra fazer o", 540, 1060, False),
        (21.38, "big_y", "MELHOR CAFÉ", 540, 1240, False)]),
    (22.62, 23.90, ("celular",), [
        (22.62, "mono", "entra lá no app da", 540, 250, False),
        (23.56, "big_y", "MAGALU", 540, 1660, False)]),
    (23.90, 25.82, ("cafeteira",), [
        (23.90, "mono", "e procura essa", 540, 300, False),
        (24.78, "big_r", "CAFETEIRA", 540, 470, False),
        (25.34, "mono", "igual a minha", 540, 640, False)]),
    (25.82, 28.70, (P, 1.20, 1.24, 640, 900, False), [
        (25.82, "mono", "porque hoje eu não vivo mais", 540, 1300, False),
        (27.48, "big_r", "SEM ELA", 540, 1470, False),
        (27.76, "mono", "faz parte da minha rotina", 540, 1650, False)]),
    (28.70, 30.40, (P, 1.00, 1.03, 540, 960, False), [
        (28.70, "mono", "bora dar", 540, 300, False),
        (29.06, "big_y", "PLAY", 540, 480, True),
        (29.62, "mono", "e bom café pra vocês :)", 540, 1250, False)]),
]
ESTILO = {"big_y": (F_BIG, AMARELO), "big_r": (F_BIG, AMARELO), "mono": (F_MONO, BRANCO), "mono_y": (F_MONO, AMARELO),
          "script": (F_SCRIPT, AMARELO)}
CLIQUES, SFX, _vis = [], [], {}


def tamanho(estilo, txt):
    if estilo.startswith("big"):
        f = font(F_BIG, 100)
        larg = sum(f.getlength(c) for c in txt) - 2 * (len(txt) - 1)
        return int(min(300, 100 * 880 / larg))
    return {"mono": 46, "mono_y": 46, "script": 128}[estilo]


def desenha_textos(canvas, t, bloco, atras):
    for j, (te, est, txt, x, y, behind) in enumerate(bloco[3]):
        if t < te or behind != atras:
            continue
        path, cor = ESTILO[est]
        size = tamanho(est, txt)
        if est.startswith("mono"):
            n = min(len(txt), int((t - te) / 0.028) + 1)
            k = (bloco[0], j)
            if not PREVIA and n > _vis.get(k, 0):
                for _ in range(n - _vis.get(k, 0)):
                    if txt[min(n, len(txt)) - 1] != " ": CLIQUES.append(t)
                _vis[k] = n
            cola(canvas, camada(txt, path, size, cor, 0, n, 0.7), x, y)
        else:
            p = clamp((t - te) / 0.12)
            track = -3 if est.startswith("big") else 0
            cola(canvas, camada(txt, path, size, cor, track), x, y, escala=lerp(1.12, 1.0, ease_io(p)),
                 alpha=clamp(p * 2.5))


# ---------------- imagem ----------------
def ffmpeg_frames(path, ss, n, vf, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(ss), "-i", path, "-vf", vf, "-frames:v", str(n),
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
    return [Image.frombytes("RGB", (w, h), raw[i * w * h * 3:(i + 1) * w * h * 3]) for i in range(len(raw) // (w * h * 3))]


def lut_cinema():
    x = np.arange(256) / 255.0
    s = x + 0.10 * np.sin(2 * np.pi * x) * -0.5 * 0 + 0.08 * (x - 0.5) * (1 - np.abs(2 * x - 1)) * 2
    s = np.clip(0.5 + (s - 0.5) * 1.08, 0, 1)
    r = np.clip(s * 1.03 + 0.01, 0, 1); g = s; b = np.clip(s * 0.90 + 0.02, 0, 1)
    return [int(v * 255) for v in np.concatenate([r, g, b])]


LUT = lut_cinema()


def grade(img):
    img = img.point(LUT)
    return ImageOps.autocontrast(img, cutoff=0) if False else img


def pb_brilho(img):
    g = ImageOps.grayscale(img)
    g = g.point(lambda v: int(min(255, v * 1.15 + 18)))
    glow = g.filter(ImageFilter.GaussianBlur(28))
    out = ImageChops.screen(g, glow.point(lambda v: int(v * 0.55)))
    return Image.merge("RGB", (out, out, out.point(lambda v: int(v * 0.97))))


def enquadra(img, zoom, cx, cy):
    bw, bh = W / zoom, H / zoom
    cx = clamp(cx, bw / 2, W - bw / 2); cy = clamp(cy, bh / 2, H - bh / 2)
    box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    return img.resize((W, H), Image.BICUBIC, box=box), box


FILM_VF = "crop=676:276:40:502,scale=1080:441:flags=lanczos,eq=contrast=1.06:saturation=0.95"
_clips = {}


def film_frame(src, dt):
    if src not in _clips:
        _clips[src] = ffmpeg_frames(FILME, src, 45, FILM_VF + f",fps={FPS}", 1080, 441)
    fr = _clips[src]
    return fr[min(len(fr) - 1, int(dt * FPS))]


# perspectiva (celular 3D)
def _coeffs(dst, src):
    A, B = [], []
    for (x, y), (X, Y) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y]); B.append(X)
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y]); B.append(Y)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def project(canvas, lay, cx, cy, ry=0.0, rx=0.0, rz=0.0, focal=1600):
    w, h = lay.size
    ry, rx, rz = map(math.radians, (ry, rx, rz))
    dst = []
    for x, y in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]:
        x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
        x, z = x * math.cos(ry), -x * math.sin(ry)
        y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        k = focal / (focal + z); dst.append((cx + x * k, cy + y * k))
    xs = [p[0] for p in dst]; ys = [p[1] for p in dst]
    x0, y0 = int(max(0, min(xs))), int(max(0, min(ys)))
    x1, y1 = int(min(W, max(xs) + 1)), int(min(H, max(ys) + 1))
    if x1 <= x0 or y1 <= y0: return
    c = _coeffs([(px - x0, py - y0) for px, py in dst], [(0, 0), (w, 0), (w, h), (0, h)])
    canvas.alpha_composite(lay.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, c, Image.BICUBIC), (x0, y0))


def celular(tela):
    w, h = 520, 1080
    ph = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(ph)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=70, fill=(22, 22, 25, 255))
    d.rounded_rectangle([4, 4, w - 5, h - 5], radius=66, outline=(88, 88, 95, 255), width=3)
    m = Image.new("L", tela.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, tela.width - 1, tela.height - 1], radius=50, fill=255)
    t = tela.convert("RGBA"); t.putalpha(m); ph.alpha_composite(t, (20, 20))
    d.rounded_rectangle([w / 2 - 70, 38, w / 2 + 70, 74], radius=18, fill=(8, 8, 10, 255))
    return ph


TELA_FR = []
for a, b, n in [(1.25, 2.1, 14), (3.55, 4.1, 14)]:
    for k in range(n):
        TELA_FR += ffmpeg_frames(TELA, a + k * (b - a) / n, 1, "scale=480:1040", 480, 1040)
TELA_FR += TELA_FR[-1:] * 12

# ---------------- recorte (texto atrás da cabeça) ----------------
import onnxruntime as ort
_sess = ort.InferenceSession(os.path.join(REC, "modnet.onnx"), providers=["CPUExecutionProvider"])


def mascara(img):
    x = np.asarray(img.resize((512, 896), Image.BILINEAR), np.float32) / 255.0
    m = _sess.run(None, {"input": ((x - 0.5) / 0.5).transpose(2, 0, 1)[None]})[0][0, 0]
    return Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).resize(img.size, Image.BILINEAR)


def bloco_em(t):
    for b in BLOCOS:
        if b[0] <= t < b[1]: return b
    return BLOCOS[-1]


PRECISA_MASCARA = set()
for b in BLOCOS:
    if any(e[5] for e in b[3]):
        t0 = min(e[0] for e in b[3] if e[5])
        PRECISA_MASCARA |= set(range(int(t0 * FPS), int(b[1] * FPS) + 1))


# ---------------- quadro ----------------
def render(i, src, mask):
    t = i / FPS
    b = bloco_em(t)
    cena = b[2]
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    pessoa = None
    if cena[0] == P:
        _, z0, z1, cx, cy, pb = cena
        z = lerp(z0, z1, (t - b[0]) / (b[1] - b[0]))
        base, box = enquadra(src, z, cx, cy)
        base = pb_brilho(base) if pb else grade(base)
        canvas.paste(base)
        if mask is not None:
            pessoa = base.convert("RGBA"); pessoa.putalpha(mask.resize((W, H), Image.BILINEAR, box=box))
    elif cena[0] == "cafeteira":
        x = ease_io((t - 23.90) / 0.9)
        base, _ = enquadra(src, lerp(1.0, 1.38, x), lerp(540, 420, x), lerp(960, 1150, x))
        canvas.paste(grade(base))
    elif cena[0] == "filme":
        segs = cena[1]
        s0, src_t = [s for s in segs if s[0] <= t + 1e-6][-1]
        if s0 <= t < s0 + 1 / FPS: SFX.append((t, "whoosh"))
        canvas.paste(film_frame(src_t, t - s0), (0, int(H / 2 - 441 / 2)))
    elif cena[0] == "celular":
        if 22.62 <= t < 22.62 + 1 / FPS: SFX.append((t, "whoosh"))
        base, _ = enquadra(src, 1.0, 540, 960)
        base = Image.blend(grade(base).filter(ImageFilter.GaussianBlur(22)), Image.new("RGB", (W, H), (18, 12, 9)), 0.5)
        canvas.paste(base)
        k = int((t - 22.62) * FPS)
        ph = celular(TELA_FR[min(k, len(TELA_FR) - 1)])
        xi = ease_io((t - 22.62) / 0.35); xo = ease_io((t - 23.62) / 0.28)
        ry = lerp(65, 20, xi) + lerp(0, -75, xo) + 2.5 * math.sin(t * 3)
        cxp = lerp(1350, 560, xi) + lerp(0, -1000, xo)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        project(sh, Image.new("RGBA", ph.size, (0, 0, 0, 160)), cxp + 30, 990, ry=ry, rx=6, rz=-5)
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)))
        project(canvas, ph, cxp, 950, ry=ry, rx=6, rz=-5)

    desenha_textos(canvas, t, b, atras=True)
    if pessoa is not None:
        canvas.alpha_composite(pessoa)
    desenha_textos(canvas, t, b, atras=False)

    # flash branco na entrada das imagens do filme / celular
    if cena[0] in ("filme", "celular") and t - b[0] < 0.16:
        canvas = Image.blend(canvas, Image.new("RGBA", (W, H), (255, 250, 240, 255)), 1 - (t - b[0]) / 0.16)
    if t > DUR - 0.3:
        canvas = Image.blend(canvas, Image.new("RGBA", (W, H), (0, 0, 0, 255)), (t - (DUR - 0.3)) / 0.3)
    return canvas.convert("RGB")


# ---------------- execução ----------------
if PREVIA:
    for tp in PREVIA:
        i = int(round(tp * FPS))
        src = ffmpeg_frames(FALA, i / FPS, 1, "null", W, H)[0]
        m = mascara(src) if i in PRECISA_MASCARA else None
        render(i, src, m).save(f"{SAIDA}_{tp:05.2f}.png")
    sys.exit(0)

VID = SAIDA + ".video.mp4"
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", FALA, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-vf", "vignette=PI/5.5,noise=alls=5:allf=t", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "17", "-pix_fmt", "yuv420p", VID], stdin=subprocess.PIPE)
prev = None
for i in range(NFR):
    src = Image.frombytes("RGB", (W, H), dec.stdout.read(W * H * 3))
    m = None
    if i in PRECISA_MASCARA:
        arr = np.asarray(mascara(src), np.float32)
        if prev is not None: arr = 0.6 * arr + 0.4 * prev
        prev = arr; m = Image.fromarray(arr.astype(np.uint8))
    else:
        prev = None
    enc.stdin.write(render(i, src, m).tobytes())
    if i % 90 == 0: print(f"  {i}/{NFR}", flush=True)
enc.stdin.close(); enc.wait(); dec.stdout.close(); dec.wait()

# ---------------- som ----------------
SR = 48000
sfx = np.zeros(int((DUR + 1) * SR), np.float32)


def add(sig, t, g):
    a = int(max(0, t) * SR); n = min(len(sig), len(sfx) - a); sfx[a:a + n] += sig[:n] * g


for t in CLIQUES:
    n = int(0.04 * SR)
    r = np.random.randn(n)
    s = (np.diff(r, prepend=0) * 0.6 + r * 0.4) * np.exp(-np.linspace(0, 1, n) * random.uniform(40, 60))
    s += np.sin(2 * np.pi * random.uniform(180, 260) * np.arange(n) / SR) * np.exp(-np.linspace(0, 1, n) * 25) * 0.4
    add(s.astype(np.float32), t + random.uniform(0, 0.012), 0.22 * random.uniform(0.7, 1.0))
for t, _ in SFX:
    n = int(0.45 * SR); x = np.linspace(0, 1, n)
    nz = np.random.randn(n).astype(np.float32); y = np.empty_like(nz); acc = 0.0
    a = 0.02 + 0.22 * np.sin(np.pi * x) ** 2
    for k in range(n):
        acc += a[k] * (nz[k] - acc); y[k] = acc
    y *= np.sin(np.pi * x) ** 1.5
    add(y / (np.abs(y).max() + 1e-9), t - 0.15, 0.30)
sfx = np.tanh(sfx) * 0.8
WAV = SAIDA + ".sfx.wav"
with wave.open(WAV, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(sfx, -1, 1) * 32767).astype(np.int16).tobytes())
RADIO = "highpass=f=700,lowpass=f=2600,aeval='tanh(5*val(0))/1.1',volume=1.4"
fc = (f"[0:a]asplit=3[a][b][c];[a]atrim=0:3.70,asetpts=PTS-STARTPTS[p1];"
      f"[b]atrim=3.70:4.66,asetpts=PTS-STARTPTS,{RADIO},afade=t=in:d=0.02,afade=t=out:st=0.92:d=0.04[p2];"
      f"[c]atrim=4.66,asetpts=PTS-STARTPTS[p3];[p1][p2][p3]concat=n=3:v=0:a=1,aresample=48000,volume=0.92[voz];"
      f"[2:a]volume=1.0[fx];[voz][fx]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,"
      f"afade=t=out:st={DUR - 0.35:.2f}:d=0.35[aout]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", FALA, "-i", VID, "-i", WAV, "-filter_complex", fc, "-map", "1:v",
                "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{DUR:.3f}",
                "-movflags", "+faststart", SAIDA], check=True)
os.remove(VID); os.remove(WAV)
print("ok:", SAIDA)
