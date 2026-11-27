#!/usr/bin/env python3
"""Abertura (4,8s) no estilo da referência Db3T23XzKEn — tudo em amarelo manteiga.

Uso: python abertura.py VIDEO.mp4 SAIDA.mp4 PASTA_RECURSOS [t1,t2 para prévia em PNG]
"""
import os, sys, math, random, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops

SRC, SAIDA, REC = sys.argv[1:4]
PREVIA = [float(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else None
W, H, FPS = 1080, 1920, 30
NFR = 144                      # 4,8s
DUR = NFR / FPS
random.seed(2); np.random.seed(2)

AMARELO = (250, 233, 163)
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
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x


# ---------- palavras (tempo da fala) ----------
PAL = [(0.00, "talvez"), (0.44, "esse"), (0.58, "filme"), (0.78, "tenha"), (0.98, "passado"),
       (1.32, "despercebido"), (2.08, "mas"), (2.14, "ele"), (2.38, "merece"), (2.84, "a"), (2.98, "sua"),
       (3.14, "atenção"), (3.56, "e"), (3.82, "também"), (3.98, "um"), (4.16, "cafezinho")]

# Blocos: (início, fim, zoom, cx, cy, p&b, linhas)
#   linha: (estilo, [índices de palavras], x, y)  — estilo: mono | big | script
BLOCOS = [
    (0.00, 2.06, (1.00, 1.04), 560, 960, False, [
        ("mono", [0, 1, 2], 540, 975),
        ("mono", [3, 4], 540, 1050),
        ("big", [5], 540, 1210)]),
    (2.06, 3.56, (1.22, 1.25), 640, 900, False, [
        ("mono", [6, 7, 8, 9, 10], 540, 1330),
        ("script", [11], 540, 1450)]),
    (3.56, DUR + 1, (1.00, 1.02), 560, 960, True, [
        ("mono", [12, 13, 14], 320, 1400),
        ("script", [15], 320, 1510)]),
]
EXTRA = {15: " :)"}           # complemento depois da palavra


def texto_linha(idx, est="mono"):
    t = " ".join(PAL[k][1] + EXTRA.get(k, "") for k in idx)
    return t.upper() if est == "big" else t


def tamanho(est, txt):
    if est == "big":
        f = font(F_BIG, 100)
        return int(min(300, 100 * 900 / (sum(f.getlength(c) for c in txt) - 3 * len(txt))))
    return {"mono": 56, "script": 160}[est]


def camada(txt, est, n):
    k = (txt, est, n)
    if k in _c: return _c[k]
    path = {"mono": F_MONO, "big": F_BIG, "script": F_SCRIPT}[est]
    size = tamanho(est, txt); f = font(path, size); track = -3 if est == "big" else 0
    asc, desc = f.getmetrics()
    w = int(sum(f.getlength(c) for c in txt) + track * len(txt)) + 2; pad = 30
    lay = Image.new("RGBA", (w + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay); x = pad
    for c in txt[:n]:
        d.text((x, pad), c, font=f, fill=AMARELO + (255,)); x += f.getlength(c) + track
    a = lay.getchannel("A").filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(min(255, v * 1.1)))
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.putalpha(a)
    out = Image.new("RGBA", lay.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 3)); out.alpha_composite(sh, (0, 3)); out.alpha_composite(lay)
    _c[k] = out
    return out


def cola(canvas, lay, cx, cy, escala=1.0, alpha=1.0):
    if escala != 1.0:
        lay = lay.resize((max(1, int(lay.width * escala)), max(1, int(lay.height * escala))), Image.BILINEAR)
    if alpha < 0.999:
        lay = lay.copy(); lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    tmp.paste(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)), lay)
    canvas.alpha_composite(tmp)


CLIQUES, SFX = [], []
_vis = {}


def desenha(canvas, t, bloco):
    for j, (est, idx, x, y) in enumerate(bloco[6]):
        txt = texto_linha(idx, est)
        if est == "mono":
            # cada palavra é digitada no momento em que é falada
            n, pos = 0, 0
            for k in idx:
                palavra = PAL[k][1] + EXTRA.get(k, "")
                if t >= PAL[k][0]:
                    dentro = min(len(palavra), int((t - PAL[k][0]) / 0.03) + 1)
                    n = pos + dentro
                pos += len(palavra) + 1
            if n == 0: continue
            key = (bloco[0], j)
            if n > _vis.get(key, 0):
                CLIQUES.extend([t] * (n - _vis.get(key, 0))); _vis[key] = n
            cola(canvas, camada(txt, est, n), x, y)
        else:
            t0 = PAL[idx[0]][0]
            if t < t0: continue
            if t0 <= t < t0 + 1 / FPS: SFX.append((t, "pop" if est == "big" else "pop2"))
            p = clamp((t - t0) / 0.12)
            cola(canvas, camada(txt, est, len(txt)), x, y, escala=lerp(1.15, 1.0, ease(p)), alpha=clamp(p * 2.5))


# ---------- seta desenhada apontando pra xícara ----------
def seta_pincel(prog):
    im = Image.new("RGBA", (420, 360), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = []
    for k in range(41):
        u = k / 40
        x = 30 + 330 * u; y = 320 - 270 * u + 70 * math.sin(math.pi * u)
        pts.append((x, y))
    m = max(2, int(len(pts) * clamp(prog)))
    d.line(pts[:m], fill=AMARELO + (255,), width=13, joint="curve")
    if prog >= 0.98:
        (x1, y1), (x0, y0) = pts[-1], pts[-4]
        ang = math.atan2(y1 - y0, x1 - x0)
        for s in (-1, 1):
            a = ang + math.pi + s * 0.55
            d.line([(x1, y1), (x1 + 60 * math.cos(a), y1 + 60 * math.sin(a))], fill=AMARELO + (255,), width=13)
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.5))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(a)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 3)); out.alpha_composite(im)
    return out


# posição da xícara (centro) ao longo do tempo, medida no vídeo
XICARA = [(4.00, 700, 1100), (4.30, 675, 1090), (4.60, 640, 1075), (4.80, 640, 1075)]


def xicara(t):
    for (a, xa, ya), (b, xb, yb) in zip(XICARA, XICARA[1:]):
        if a <= t <= b:
            u = (t - a) / (b - a); return lerp(xa, xb, u), lerp(ya, yb, u)
    return XICARA[-1][1:]


# ---------- imagem ----------
def lut():
    x = np.arange(256) / 255.0
    s = np.clip(0.5 + (x - 0.5) * 1.08 + 0.05 * np.sin(2 * np.pi * x) * 0, 0, 1)
    r = np.clip(s * 1.03 + 0.01, 0, 1); b = np.clip(s * 0.90 + 0.02, 0, 1)
    return [int(v * 255) for v in np.concatenate([r, s, b])]


LUT = lut()


def pb_brilho(img):
    g = ImageOps.grayscale(img).point(lambda v: int(max(0, min(255, (v - 128) * 1.25 + 105))))
    out = ImageChops.screen(g, g.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.35)))
    return Image.merge("RGB", (out, out, out))


def enquadra(img, z, cx, cy):
    bw, bh = W / z, H / z
    cx = clamp(cx, bw / 2, W - bw / 2); cy = clamp(cy, bh / 2, H - bh / 2)
    box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    return img.resize((W, H), Image.BICUBIC, box=box), box


def render(i, src):
    t = i / FPS
    b = [bl for bl in BLOCOS if bl[0] <= t < bl[1]][0]
    if b[0] <= t < b[0] + 1 / FPS and b[0] > 0: SFX.append((t, "whoosh"))
    z = lerp(b[2][0], b[2][1], (t - b[0]) / max(0.1, min(b[1], DUR) - b[0]))
    base, box = enquadra(src, z, b[3], b[4])
    base = pb_brilho(base) if b[5] else base.point(LUT)
    canvas = base.convert("RGBA")
    desenha(canvas, t, b)
    if t >= 4.16:                                       # seta pra xícara
        if 4.16 <= t < 4.16 + 1 / FPS: SFX.append((t, "risco"))
        xc, yc = xicara(t)
        # converte posição da xícara para o enquadramento atual
        xo = (xc - box[0]) * W / (box[2] - box[0]); yo = (yc - box[1]) * H / (box[3] - box[1])
        cola(canvas, seta_pincel((t - 4.16) / 0.22), xo - 230, yo + 175)
    if b[5] and t - b[0] < 0.12:                        # flash na virada pro P&B
        canvas = Image.blend(canvas, Image.new("RGBA", (W, H), (255, 252, 240, 255)), 0.85 * (1 - (t - b[0]) / 0.12))
    return canvas.convert("RGB")


def frames(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    for _ in range(NFR):
        raw = p.stdout.read(W * H * 3)
        if len(raw) < W * H * 3: break
        yield Image.frombytes("RGB", (W, H), raw)
    p.stdout.close(); p.wait()


if PREVIA:
    alvo = {int(round(x * FPS)) for x in PREVIA}
    for i, fr in enumerate(frames(SRC)):
        img = render(i, fr)
        if i in alvo: img.save(f"{SAIDA}_{i / FPS:04.2f}.png")
    sys.exit(0)

VID = SAIDA + ".v.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-vf", "vignette=PI/5.5,noise=alls=5:allf=t",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", VID],
                       stdin=subprocess.PIPE)
for i, fr in enumerate(frames(SRC)):
    enc.stdin.write(render(i, fr).tobytes())
enc.stdin.close(); enc.wait()

# ---------- som ----------
SR = 48000
sfx = np.zeros(int((DUR + 1) * SR), np.float32)


def add(s, t, g):
    a = int(max(0, t) * SR); n = min(len(s), len(sfx) - a); sfx[a:a + n] += s[:n] * g


def ruido_filtrado(n, corte):
    nz = np.random.randn(n).astype(np.float32); y = np.empty_like(nz); acc = 0.0
    for k in range(n):
        acc += corte[k] * (nz[k] - acc); y[k] = acc
    return y


ult = -1
for t in CLIQUES:                                    # teclado
    if t == ult: t += random.uniform(0.008, 0.022)
    ult = t
    n = int(0.04 * SR); r = np.random.randn(n)
    s = (np.diff(r, prepend=0) * 0.6 + r * 0.4) * np.exp(-np.linspace(0, 1, n) * random.uniform(40, 60))
    s += np.sin(2 * np.pi * random.uniform(180, 260) * np.arange(n) / SR) * np.exp(-np.linspace(0, 1, n) * 25) * 0.4
    add(s.astype(np.float32), t, 0.28 * random.uniform(0.7, 1.0))
for t, tipo in SFX:
    if tipo in ("pop", "pop2"):                      # batida grave + estalo na palavra grande
        n = int(0.22 * SR); x = np.arange(n) / SR
        f = (110 if tipo == "pop" else 300) * np.exp(-x * 9) + (55 if tipo == "pop" else 180)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * (14 if tipo == "pop" else 30))
        add(s.astype(np.float32), t, 0.55 if tipo == "pop" else 0.35)
    elif tipo == "whoosh":
        n = int(0.4 * SR); x = np.linspace(0, 1, n)
        y = ruido_filtrado(n, 0.02 + 0.22 * np.sin(np.pi * x) ** 2) * np.sin(np.pi * x) ** 1.5
        add(y / (np.abs(y).max() + 1e-9), t - 0.16, 0.30)
    elif tipo == "risco":                            # som de caneta riscando (seta)
        n = int(0.22 * SR); x = np.linspace(0, 1, n)
        y = ruido_filtrado(n, np.full(n, 0.35)) * np.sin(np.pi * x) * (0.7 + 0.3 * np.sin(x * 90))
        y = np.diff(y, prepend=0)
        add(y / (np.abs(y).max() + 1e-9), t, 0.25)
sfx = np.tanh(sfx) * 0.85
WAV = SAIDA + ".sfx.wav"
with wave.open(WAV, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(sfx, -1, 1) * 32767).astype(np.int16).tobytes())

# voz: efeito de rádio antigo (sem graves, médios realçados) a partir do "e também um cafezinho"
VOZ_FX = ("highpass=f=450:poles=2,highpass=f=450:poles=2,equalizer=f=1500:t=o:w=1.3:g=9,"
          "lowpass=f=6000,acompressor=threshold=0.12:ratio=4:attack=5:release=80,volume=0.9")
fc = (f"[0:a]asplit=2[a][b];[a]atrim=0:3.54,asetpts=PTS-STARTPTS[p1];"
      f"[b]atrim=3.54,asetpts=PTS-STARTPTS,{VOZ_FX},afade=t=in:d=0.03[p2];"
      f"[p1][p2]concat=n=2:v=0:a=1,aresample=48000[voz];[2:a]volume=1.0[fx];"
      f"[voz][fx]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[aout]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-i", VID, "-i", WAV, "-filter_complex", fc,
                "-map", "1:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-t", f"{DUR:.3f}", "-movflags", "+faststart", SAIDA], check=True)
os.remove(VID); os.remove(WAV)
print("ok:", SAIDA)
