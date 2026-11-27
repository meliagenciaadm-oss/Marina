#!/usr/bin/env python3
"""Reel "Um Contratempo" — versão dinâmica (perspectiva + scrapbook + cartelas).

Uso: python montar_v3.py FALA.mp4 FILME.mp4 TELA_MAGALU.mp4 SAIDA.mp4 PASTA_RECURSOS
  PASTA_RECURSOS precisa de: Anton.ttf, InstrumentSerif-Italic.ttf, modnet.onnx
"""
import os, sys, math, random, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

FALA, FILME, TELA, SAIDA, REC = sys.argv[1:6]
W, H, FPS = 1080, 1920, 30
NFR = 909
DUR = NFR / FPS
random.seed(3); np.random.seed(3)

# ---------------- identidade ----------------
AMARELO = (250, 233, 163)
CAFE = (88, 58, 40)
CAFE_GRADE = (104, 71, 50)
TERRACOTA = (210, 108, 92)
CREME = (255, 248, 232)
PRETO = (14, 12, 11)

F_ANTON = os.path.join(REC, "Anton.ttf")
F_SERIF = os.path.join(REC, "InstrumentSerif-Italic.ttf")
F_INTER = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
F_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
_fonts = {}


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


# ---------------- utilidades de animação ----------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x); return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x); return x * x * (3 - 2 * x)


def back_out(x):
    x = clamp(x); c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, x):
    return a + (b - a) * x


# ---------------- camadas de texto ----------------
_tcache = {}


def text_layer(txt, path, size, color=AMARELO, track=0, n=None, shadow=True, stroke=0):
    """Texto inteiro define o tamanho; só os n primeiros caracteres são desenhados (digitação)."""
    n = len(txt) if n is None else n
    key = (txt, path, size, color, track, n, shadow, stroke)
    if key in _tcache:
        return _tcache[key]
    f = font(path, size)
    asc, desc = f.getmetrics()
    wid = int(sum(f.getlength(c) for c in txt) + track * max(len(txt) - 1, 0)) + 2
    pad = 40
    lay = Image.new("RGBA", (wid + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = pad
    for c in txt[:n]:
        d.text((x, pad), c, font=f, fill=color + (255,), stroke_width=stroke,
               stroke_fill=(CAFE + (255,)) if stroke else None)
        x += f.getlength(c) + track
    if shadow:
        a = lay.getchannel("A").filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.5))
        sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.putalpha(a)
        out = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 5)); out.alpha_composite(lay); lay = out
    _tcache[key] = lay
    return lay


def emoji(ch, size):
    key = ("emoji", ch, size)
    if key not in _tcache:
        f = font(F_EMOJI, 109)
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox())
        s = size / max(im.size)
        _tcache[key] = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return _tcache[key]


def paste_center(canvas, lay, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if lay is None or alpha <= 0.01 or scale <= 0.01:
        return
    if rot:
        lay = lay.rotate(rot, resample=Image.BICUBIC, expand=True)
    if abs(scale - 1) > 1e-3:
        lay = lay.resize((max(1, int(lay.width * scale)), max(1, int(lay.height * scale))), Image.BILINEAR)
    if alpha < 0.999:
        a = lay.getchannel("A").point(lambda v: int(v * alpha)); lay = lay.copy(); lay.putalpha(a)
    canvas.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2))) \
        if 0 <= int(cx - lay.width / 2) and 0 <= int(cy - lay.height / 2) and \
        int(cx + lay.width / 2) <= canvas.width and int(cy + lay.height / 2) <= canvas.height \
        else _paste_clip(canvas, lay, int(cx - lay.width / 2), int(cy - lay.height / 2))


def _paste_clip(canvas, lay, x, y):
    tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    tmp.paste(lay, (x, y), lay)
    canvas.alpha_composite(tmp)


# ---------------- perspectiva 3D ----------------
def _coeffs(dst, src):
    A, B = [], []
    for (x, y), (X, Y) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y]); B.append(X)
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y]); B.append(Y)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def project(canvas, lay, cx, cy, ry=0.0, rx=0.0, rz=0.0, scale=1.0, alpha=1.0, focal=1400):
    """Gira a camada no espaço 3D e projeta no quadro (texto 'deitado' / celular girando)."""
    if lay is None or alpha <= 0.01:
        return
    w, h = lay.size
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    ry, rx, rz = map(math.radians, (ry, rx, rz))
    dst = []
    for x, y in pts:
        x, y = x * scale, y * scale
        x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
        z = 0.0
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        k = focal / (focal + z)
        dst.append((cx + x * k, cy + y * k))
    xs = [p[0] for p in dst]; ys = [p[1] for p in dst]
    x0, y0 = int(max(0, min(xs))) , int(max(0, min(ys)))
    x1, y1 = int(min(W, max(xs) + 1)), int(min(H, max(ys) + 1))
    if x1 <= x0 or y1 <= y0:
        return
    loc = [(px - x0, py - y0) for px, py in dst]
    c = _coeffs(loc, [(0, 0), (w, 0), (w, h), (0, h)])
    out = lay.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, c, Image.BICUBIC)
    if alpha < 0.999:
        out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(out, (x0, y0))


# ---------------- fontes de imagem ----------------
def ffmpeg_frames(path, ss, n, vf, w, h, fps_in=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-i", path, "-vf", vf, "-frames:v", str(n),
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    fr = len(raw) // (w * h * 3)
    return [Image.fromarray(np.frombuffer(raw[i * w * h * 3:(i + 1) * w * h * 3], np.uint8).reshape(h, w, 3))
            for i in range(fr)]


def fala_frame(i):
    return ffmpeg_frames(FALA, i / FPS, 1, "null", W, H)[0]


FILM_VF = "crop=676:276:40:502,scale=1000:408:flags=lanczos,eq=contrast=1.05:saturation=1.05"


def film_clip(src, dur):
    return ffmpeg_frames(FILME, src, max(1, round(dur * FPS)), FILM_VF + f",fps={FPS}", 1000, 408)


def film_still(src, vf_extra=""):
    return ffmpeg_frames(FILME, src, 1, FILM_VF + vf_extra, 1000, 408)[0]


# ---------------- recorte da pessoa (MODNet) ----------------
import onnxruntime as ort
_sess = ort.InferenceSession(os.path.join(REC, "modnet.onnx"), providers=["CPUExecutionProvider"])


def mascara(img):
    x = np.asarray(img.resize((512, 896), Image.BILINEAR), np.float32) / 255.0
    x = ((x - 0.5) / 0.5).transpose(2, 0, 1)[None]
    m = _sess.run(None, {"input": x})[0][0, 0]
    return Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).resize(img.size, Image.BILINEAR)


def recorte_adesivo(img, borda=16):
    """Pessoa recortada com contorno branco de adesivo."""
    m = mascara(img).point(lambda v: 255 if v > 110 else 0)
    big = m.filter(ImageFilter.MaxFilter(borda * 2 + 1)).filter(ImageFilter.GaussianBlur(1.5))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    branco = Image.new("RGBA", img.size, CREME + (255,))
    out.paste(branco, mask=big)
    pessoa = img.convert("RGBA"); pessoa.putalpha(m.filter(ImageFilter.GaussianBlur(1)))
    out.alpha_composite(pessoa)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(big.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.45)))
    final = Image.new("RGBA", img.size, (0, 0, 0, 0))
    final.alpha_composite(sh, (10, 16)); final.alpha_composite(out)
    return final.crop(final.getbbox())


# ---------------- elementos gráficos ----------------
def fundo_cafe():
    im = Image.new("RGB", (W, H), CAFE)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 54):
        d.line([(x, 0), (x, H)], fill=CAFE_GRADE, width=2)
    for y in range(0, H, 54):
        d.line([(0, y), (W, y)], fill=CAFE_GRADE, width=2)
    vin = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vin).ellipse([-300, -200, W + 300, H + 200], fill=255)
    vin = vin.filter(ImageFilter.GaussianBlur(220))
    escuro = Image.new("RGB", (W, H), (50, 32, 22))
    return Image.composite(im, escuro, vin)


FUNDO_CAFE = None


def etiqueta(txt, size=42):
    key = ("tag", txt, size)
    if key not in _tcache:
        f = font(F_INTER, size)
        w = int(f.getlength(txt)) + 44; h = size + 30
        im = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([10, 10, 10 + w, 10 + h], radius=12, fill=TERRACOTA + (255,))
        d.text((10 + 22, 10 + 9), txt, font=f, fill=CREME + (255,))
        _tcache[key] = im
    return _tcache[key]


def estrela(size, cor=AMARELO, n_txt=None):
    key = ("star", size, cor, n_txt)
    if key not in _tcache:
        s = size * 2
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        pts = []
        for k in range(10):
            r = s / 2 * (0.95 if k % 2 == 0 else 0.42)
            a = -math.pi / 2 + k * math.pi / 5
            pts.append((s / 2 + r * math.cos(a), s / 2 + r * math.sin(a)))
        d.polygon(pts, fill=cor + (255,), outline=CAFE + (255,), width=4)
        if n_txt:
            f = font(F_ANTON, int(s * 0.38))
            d.text((s / 2, s / 2 + 4), n_txt, font=f, fill=CAFE + (255,), anchor="mm")
        _tcache[key] = im.resize((size, size), Image.LANCZOS)
    return _tcache[key]


def brilho(size):
    """Estrelinha de 4 pontas (brilho)."""
    key = ("spark", size)
    if key not in _tcache:
        s = size * 2
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = s / 2
        d.polygon([(c, 0), (c + s * 0.1, c - s * 0.1), (s, c), (c + s * 0.1, c + s * 0.1), (c, s),
                   (c - s * 0.1, c + s * 0.1), (0, c), (c - s * 0.1, c - s * 0.1)], fill=AMARELO + (255,))
        _tcache[key] = im.resize((size, size), Image.LANCZOS)
    return _tcache[key]


def cartao_arredondado(img, raio=36, borda=6, cor_borda=(60, 52, 46)):
    w, h = img.size
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=raio, fill=255)
    out = Image.new("RGBA", (w + 2 * borda, h + 2 * borda), (0, 0, 0, 0))
    ImageDraw.Draw(out).rounded_rectangle([0, 0, w + 2 * borda - 1, h + 2 * borda - 1],
                                          radius=raio + borda, fill=cor_borda + (255,))
    rgba = img.convert("RGBA"); rgba.putalpha(m)
    out.alpha_composite(rgba, (borda, borda))
    return out


def polaroid(img, legenda):
    foto = ImageOps.fit(img, (300, 300), Image.LANCZOS)
    pol = Image.new("RGBA", (340, 410), CREME + (255,))
    pol.paste(foto, (20, 20))
    d = ImageDraw.Draw(pol)
    d.text((170, 368), legenda, font=font(F_SERIF, 44), fill=CAFE + (255,), anchor="mm")
    sh = Image.new("RGBA", (380, 450), (0, 0, 0, 0))
    m = Image.new("L", (380, 450), 0); ImageDraw.Draw(m).rectangle([20, 26, 360, 436], fill=110)
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(10)))
    sh.alpha_composite(pol, (20, 14))
    # prendedor
    ImageDraw.Draw(sh).rounded_rectangle([178, 0, 202, 54], radius=6, fill=(196, 150, 104, 255),
                                         outline=CAFE + (255,), width=2)
    return sh


def seta(comp=220):
    im = Image.new("RGBA", (comp + 60, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(10 + i, 60 + 26 * math.sin(i / comp * math.pi * 1.2)) for i in range(0, comp, 4)]
    d.line(pts, fill=AMARELO + (255,), width=12, joint="curve")
    x, y = pts[-1]
    d.polygon([(x + 40, y), (x - 6, y - 30), (x - 6, y + 30)], fill=AMARELO + (255,))
    return im


def celular(tela):
    """Moldura de celular com a tela (tela 480x1040)."""
    w, h = 520, 1080
    ph = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ph)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=70, fill=(24, 24, 28, 255))
    d.rounded_rectangle([4, 4, w - 5, h - 5], radius=66, outline=(90, 90, 98, 255), width=3)
    m = Image.new("L", tela.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, tela.width - 1, tela.height - 1], radius=50, fill=255)
    t = tela.convert("RGBA"); t.putalpha(m)
    ph.alpha_composite(t, (20, 20))
    d.rounded_rectangle([w / 2 - 70, 38, w / 2 + 70, 74], radius=18, fill=(10, 10, 12, 255))
    return ph


def texto_curvo(txt, raio, ang_centro, cor=AMARELO, size=78):
    f = font(F_SERIF, size)
    s = int(raio * 2 + size * 3)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    total = sum(f.getlength(c) for c in txt)
    ang_total = total / raio
    a = math.radians(ang_centro) - ang_total / 2
    for c in txt:
        cw = f.getlength(c)
        a_c = a + (cw / 2) / raio
        ch = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
        ImageDraw.Draw(ch).text((size, size), c, font=f, fill=cor + (255,), anchor="mm")
        ch = ch.rotate(-math.degrees(a_c) - 90, resample=Image.BICUBIC)
        px = s / 2 + raio * math.cos(a_c); py = s / 2 + raio * math.sin(a_c)
        im.alpha_composite(ch, (int(px - size), int(py - size)))
        a += cw / raio
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.5))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(a)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 4)); out.alpha_composite(im)
    return out


# ---------------- roteiro de textos ----------------
# Cada item: (t_in, t_out, texto, fonte, tamanho, cx, cy, extras)
A, S = "anton", "serif"
ITENS = [
    # abertura (DESPERCEBIDO atrás da cabeça)
    (0.00, 2.20, "TALVEZ ESSE FILME", A, 112, 540, 250, {}),
    (1.48, 2.20, "despercebido", S, 190, 540, 430, {"atras": True}),
    # close
    (2.58, 3.72, "merece", S, 110, 360, 300, {"rz": -4}),
    (3.12, 3.72, "SUA ATENÇÃO", A, 160, 560, 450, {"ry": -24, "rx": 10, "shake": 3.30}),
    # congelado cafezinho
    (3.96, 4.68, "e também um", S, 96, 540, 300, {}),
    (4.32, 4.68, "CAFEZINHO", A, 190, 540, 450, {"rz": -3}),
    # cartela filme
    (5.18, 6.04, "UM", A, 200, 540, 780, {}),
    (5.40, 6.04, "CONTRATEMPO", A, 200, 540, 990, {}),
    # cenas no cartão
    (6.04, 7.10, "um", S, 100, 540, 360, {}),
    (6.16, 7.10, "EMPRESÁRIO", A, 160, 540, 500, {}),
    (7.10, 8.12, "num quarto de", S, 100, 540, 360, {}),
    (7.74, 8.12, "HOTEL", A, 180, 540, 510, {}),
    (8.94, 9.30, "UM CRIME", A, 230, 540, 1210, {"ry": 26, "rx": 12, "shake": 9.18}),
    (9.30, 10.60, "ele jura que é", S, 100, 540, 1180, {}),
    (10.12, 10.60, "INOCENTE", A, 190, 540, 1350, {}),
    # varal
    (10.60, 13.18, "ele vai tentar", S, 96, 540, 260, {}),
    (11.26, 13.18, "CONVENCER", A, 170, 540, 410, {}),
    # cartela café
    (13.18, 14.40, "PREPARA", A, 210, 540, 820, {}),
    (13.98, 14.40, "O CAFÉ", A, 210, 540, 1040, {}),
    # detalhe
    (17.26, 18.06, "NENHUM DETALHE", A, 140, 540, 300, {}),
    # eu duvido (atrás)
    (18.24, 20.78, "EU DUVIDO", A, 270, 540, 420, {"atras": True, "ry": -18, "rx": 14, "shake": 18.52}),
    (19.08, 20.78, "você adivinhar o", S, 100, 540, 1090, {}),
    (20.14, 20.78, "FINAL", A, 220, 540, 1260, {"rz": -3}),
    # cartela melhor café
    (21.28, 22.62, "O MELHOR", A, 200, 540, 820, {}),
    (21.60, 22.62, "CAFÉ", A, 260, 540, 1050, {}),
    # celular
    (22.88, 23.90, "app da", S, 104, 540, 160, {}),
    (23.56, 23.90, "MAGALU", A, 170, 560, 300, {"rz": -3}),
    # cafeteira
    (24.44, 25.82, "ESSA", A, 170, 790, 330, {}),
    (24.78, 25.82, "cafeteira", S, 130, 780, 480, {}),
    (25.34, 25.82, "igual a minha", S, 80, 780, 600, {}),
    # sem ela
    (26.68, 28.70, "não vivo mais", S, 104, 560, 270, {}),
    (27.48, 28.70, "SEM ELA", A, 230, 560, 450, {"ry": -20, "rx": 10}),
    # final
    (28.94, 30.40, "bora dar", S, 110, 540, 280, {}),
    (29.06, 30.40, "PLAY ▶", A, 220, 540, 450, {}),
    (29.62, 30.40, "e bom", S, 100, 380, 1290, {}),
    (29.84, 30.40, "CAFÉ", A, 230, 620, 1330, {"rz": -4}),
]
LEGENDAS = [
    (0.00, "talvez esse filme"), (1.14, "tenha passado despercebido"), (2.22, "mas ele merece"),
    (3.00, "a sua atenção"), (3.72, "e também um cafezinho"), (4.68, "o filme é Um Contratempo"),
    (6.04, "um empresário que acorda"), (7.10, "num quarto de hotel"), (8.12, "onde aconteceu um crime"),
    (9.30, "e ele jura que é inocente"), (10.60, "então ele vai tentar convencer"), (11.74, "a advogada"),
    (12.42, "e a gente também"), (13.18, "prepara o café"), (14.40, "porque você vai precisar"),
    (15.28, "ficar bem acordada"), (16.58, "pra não perder nenhum detalhe"),
    (18.06, "e eu duvido você conseguir"), (19.68, "adivinhar o final desse filme"),
    (20.78, "e pra fazer o melhor café"), (22.62, "entra lá no aplicativo da Magalu"),
    (23.90, "e procura essa cafeteira"), (25.20, "igual a minha"),
    (25.82, "porque hoje eu não vivo mais sem ela"), (27.76, "faz parte da minha rotina"),
    (28.70, "bora dar play lá no filme"), (29.62, "e bom café pra vocês"),
]
LEG_Y = 1560
SHAKES = sorted({it[7]["shake"] for it in ITENS if "shake" in it[7]})
CLIQUES = []        # (t, força)  -> som de teclado
SFX = []            # (t, tipo)
_vistos = {}


def font_of(kind):
    return F_ANTON if kind == A else F_SERIF


def desenha_itens(canvas, t, atras):
    for idx, (t0, t1, txt, kind, size, cx, cy, ex) in enumerate(ITENS):
        if not (t0 <= t < t1) or bool(ex.get("atras")) != atras:
            continue
        dur = min(0.30, 0.045 * len(txt))
        n = min(len(txt), int((t - t0) / dur * len(txt)) + 1)
        if n > _vistos.get(idx, 0):
            for _ in range(n - _vistos.get(idx, 0)):
                CLIQUES.append((t, 1.0 if kind == A else 0.7))
            _vistos[idx] = n
        track = -2 if kind == A else -1
        lay = text_layer(txt, font_of(kind), size, track=track, n=n)
        sc = back_out((t - t0) / 0.20) * 0.25 + 0.75 if kind == A else 1.0
        if "ry" in ex or "rx" in ex:
            project(canvas, lay, cx, cy, ry=ex.get("ry", 0), rx=ex.get("rx", 0), rz=ex.get("rz", 0), scale=sc)
        else:
            paste_center(canvas, lay, cx, cy, scale=sc, rot=ex.get("rz", 0))


def legenda(canvas, t):
    atual = [l for l in LEGENDAS if l[0] <= t + 1e-6]
    if not atual:
        return
    txt = atual[-1][1]
    key = ("leg", txt)
    if key not in _tcache:
        f = font(F_INTER, 40)
        w = int(f.getlength(txt)) + 60
        im = Image.new("RGBA", (w, 110), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((w / 2, 55), txt, font=f, fill=(255, 255, 255, 255), anchor="mm")
        a = im.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.75))
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(a)
        out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 3)); out.alpha_composite(im)
        _tcache[key] = out
    paste_center(canvas, _tcache[key], W / 2, LEG_Y)


# ---------------- enquadramento da pessoa ----------------
def enquadra(img, zoom, cx, cy):
    bw, bh = W / zoom, H / zoom
    cx = clamp(cx, bw / 2, W - bw / 2); cy = clamp(cy, bh / 2, H - bh / 2)
    box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    return img.resize((W, H), Image.BILINEAR, box=box), box


def enquadra_mask(m, box):
    return m.resize((W, H), Image.BILINEAR, box=box)


def camera(t):
    """(zoom, cx, cy) da pessoa em cada momento."""
    if t < 2.20:
        return lerp(1.0, 1.07, t / 2.2), 540, 960
    if t < 3.72:
        return 1.45, 760, 820
    if t < 13.18:
        return 1.0, 540, 960
    if t < 16.58:
        x = ease_io((t - 14.40) / 2.0)
        return lerp(1.0, 1.18, x), 600, lerp(960, 1000, x)
    if t < 22.62:
        x = (t - 18.06) / 2.7
        return lerp(1.0, 1.06, clamp(x)), 540, 960
    if t < 25.82:
        x = ease_io((t - 23.90) / 0.9)
        return lerp(1.0, 1.38, x), lerp(540, 420, x), lerp(960, 1150, x)
    x = ease_io((t - 25.82) / 0.45)
    return lerp(1.38, 1.0, x), lerp(420, 540, x), lerp(1150, 960, x)


# ---------------- pré-carregamento ----------------
print("carregando recursos…", flush=True)
FUNDO_CAFE = fundo_cafe()
CONGELA_1 = recorte_adesivo(fala_frame(112))      # 3,72s
CONGELA_2 = recorte_adesivo(fala_frame(861))      # 28,70s
CENAS_CARTAO = [  # (t0, t1, segundo do filme, p&b)
    (6.04, 7.10, 42.5, False), (7.10, 8.12, 74.5, False), (8.12, 9.30, 31.0, True), (9.30, 10.60, 36.0, False)]
CLIPES = {c[0]: film_clip(c[2], c[1] - c[0]) for c in CENAS_CARTAO}
FLASHES = [(16.58, 17.07, 57.0), (17.07, 17.56, 60.0), (17.56, 18.06, 64.0)]
for f0, f1, src in FLASHES:
    CLIPES[f0] = film_clip(src, f1 - f0)
POL = [polaroid(film_still(42.6), "ele"), polaroid(film_still(39.2), "a advogada"),
       polaroid(fala_frame(375).crop((300, 380, 1080, 1160)), "a gente 👀".replace(" 👀", ""))]
TELA_FR = []
for a, b, n in [(0.95, 1.9, 14), (3.55, 4.1, 14), (4.05, 4.06, 10)]:
    fr = ffmpeg_frames(TELA, a, 1, f"scale=480:1040", 480, 1040) if n == 10 else None
    if fr:
        TELA_FR += fr * n
    else:
        step = (b - a) / n
        for k in range(n):
            TELA_FR += ffmpeg_frames(TELA, a + k * step, 1, "scale=480:1040", 480, 1040)
MASK_FRAMES = set(range(0, 67)) | set(range(541, 624))


# ---------------- renderização ----------------
def fundo_freeze(canvas, cut, t, t0, rot, sc):
    canvas.paste(FUNDO_CAFE)
    k = back_out((t - t0) / 0.28)
    paste_center(canvas, cut, W / 2, H / 2 + 120, scale=sc * (0.85 + 0.15 * k), rot=rot)
    for i, (bx, by, s) in enumerate([(170, 700, 70), (930, 820, 54), (880, 1350, 80), (150, 1250, 50)]):
        tw = 0.6 + 0.4 * math.sin((t - t0) * 9 + i * 1.7)
        paste_center(canvas, brilho(s), bx, by, scale=tw)


def render(i, src):
    t = i / FPS
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    pessoa_mask = None

    if 3.72 <= t < 4.68:                                   # congelado cafezinho
        if i == 112: SFX.append((t, "foto"))
        fundo_freeze(canvas, CONGELA_1, t, 3.72, -3, 0.92)
        e = emoji("☕", 150)
        paste_center(canvas, e, 860, 1180, scale=back_out((t - 4.32) / 0.25) if t >= 4.32 else 0, rot=12)
    elif 4.68 <= t < 6.04 or 13.18 <= t < 14.40 or 20.78 <= t < 22.62:   # cartelas
        canvas.paste(FUNDO_CAFE)
        t0, tag = (4.68, "o filme é") if t < 6.04 else ((13.18, "dica") if t < 14.40 else (20.78, "pra fazer"))
        if (t0 <= t < t0 + 1 / FPS): SFX.append((t, "whoosh"))
        paste_center(canvas, etiqueta(tag), 540, 600, scale=back_out((t - t0) / 0.2))
        if t0 == 13.18:
            paste_center(canvas, emoji("☕", 130), 860, 1230, scale=back_out((t - 14.2) / 0.25) if t >= 14.2 else 0, rot=-10)
    elif 6.04 <= t < 10.60:                                 # cenas no cartão
        canvas.paste(PRETO + (255,), (0, 0, W, H))
        for c0, c1, _, pb in CENAS_CARTAO:
            if c0 <= t < c1:
                fr = CLIPES[c0][min(len(CLIPES[c0]) - 1, int((t - c0) * FPS))]
                if pb:
                    fr = ImageOps.grayscale(fr).convert("RGB")
                if (c0 <= t < c0 + 1 / FPS): SFX.append((t, "whoosh"))
                sc = 1.0
                if c0 == 9.30:
                    sc = lerp(1.0, 1.08, ease_out((t - c0) / 1.2))
                card = cartao_arredondado(fr)
                paste_center(canvas, card, W / 2, 830, scale=sc)
    elif 10.60 <= t < 13.18:                                # varal de polaroids
        canvas.paste(FUNDO_CAFE)
        d = ImageDraw.Draw(canvas)
        pts = [(x, 640 + 60 * math.sin(x / W * math.pi)) for x in range(-20, W + 21, 20)]
        d.line(pts, fill=CREME + (255,), width=5)
        for k, (pt0, px) in enumerate([(10.60, 200), (11.74, 540), (12.42, 880)]):
            if t < pt0:
                continue
            if (pt0 <= t < pt0 + 1 / FPS): SFX.append((t, "pop"))
            ang = 7 * math.sin((t - pt0) * 4.2 + k) * math.exp(-(t - pt0) * 0.9) + (k - 1) * 3
            sc = back_out((t - pt0) / 0.3)
            if k == 2 and t >= 12.66:
                sc *= lerp(1.0, 1.22, ease_out((t - 12.66) / 0.25))
            y = 640 + 60 * math.sin(px / W * math.pi)
            paste_center(canvas, POL[k], px, y + 215 * sc, scale=0.92 * sc, rot=ang)
            if k == 2 and t >= 12.66:
                paste_center(canvas, emoji("👀", 110), px + 120, y + 60, scale=back_out((t - 12.66) / 0.2), rot=10)
    elif 16.58 <= t < 18.06:                                # flashes de cenas
        canvas.paste(PRETO + (255,), (0, 0, W, H))
        for f0, f1, _ in FLASHES:
            if f0 <= t < f1:
                if (f0 <= t < f0 + 1 / FPS): SFX.append((t, "whoosh"))
                fr = CLIPES[f0][min(len(CLIPES[f0]) - 1, int((t - f0) * FPS))]
                card = cartao_arredondado(fr.resize((860, 351), Image.BILINEAR), raio=30)
                rot = {16.58: -4, 17.07: 3, 17.56: -2}[f0]
                paste_center(canvas, card, W / 2, 860, scale=back_out((t - f0) / 0.18) * 0.2 + 0.8, rot=rot)
    elif 22.62 <= t < 23.90:                                # celular 3D com o app
        if (22.62 <= t < 22.62 + 1 / FPS): SFX.append((t, "whoosh"))
        z, cx, cy = camera(t)
        base, _ = enquadra(src, 1.0, 540, 960)
        base = base.filter(ImageFilter.GaussianBlur(18))
        base = Image.blend(base, Image.new("RGB", (W, H), (40, 26, 18)), 0.45)
        canvas.paste(base)
        k = int((t - 22.62) * FPS)
        ph = celular(TELA_FR[min(k, len(TELA_FR) - 1)])
        x_in = ease_out((t - 22.62) / 0.35)
        x_out = ease_io((t - 23.62) / 0.28)
        ry = lerp(70, 22, x_in) + lerp(0, -80, x_out) + 3 * math.sin(t * 3)
        cxp = lerp(1300, 650, x_in) + lerp(0, -900, x_out)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        project(sh, Image.new("RGBA", ph.size, (0, 0, 0, 150)), cxp + 30, 1000, ry=ry, rx=6, rz=-6, scale=1.02)
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(25)))
        project(canvas, ph, cxp, 960, ry=ry, rx=6, rz=-6, scale=1.0, focal=1600)
        paste_center(canvas, estrela(120, n_txt="1"), cxp - 250, 470, scale=back_out((t - 22.75) / 0.25))
    elif 28.70 <= t:                                        # congelado final
        if i == 861: SFX.append((t, "foto"))
        fundo_freeze(canvas, CONGELA_2, t, 28.70, 3, 0.86)
        paste_center(canvas, emoji("☕", 140), 880, 1320, scale=back_out((t - 29.92) / 0.25) if t >= 29.92 else 0, rot=-12)
    else:                                                   # pessoa
        z, cx, cy = camera(t)
        base, box = enquadra(src, z, cx, cy)
        if 8.12 <= t < 9.30:
            base = ImageOps.grayscale(base).convert("RGB")
        canvas.paste(base)
        if i in MASKS:
            pessoa_mask = enquadra_mask(MASKS[i], box)
            desenha_itens(canvas, t, atras=True)
            pessoa = base.convert("RGBA"); pessoa.putalpha(pessoa_mask)
            canvas.alpha_composite(pessoa)
        if 13.9 < t < 16.58 and t >= 15.28:                # texto curvo
            arco = _tcache.setdefault("arco", texto_curvo("fica bem acordada", 330, -90))
            paste_center(canvas, arco, 640, 760, alpha=ease_out((t - 15.28) / 0.3))
        if 23.90 <= t < 25.82:                              # cafeteira em destaque
            if (23.90 <= t < 23.90 + 1 / FPS): SFX.append((t, "whoosh"))
            paste_center(canvas, estrela(120, n_txt="2"), 820, 160, scale=back_out((t - 24.0) / 0.25))
            if t >= 24.78:
                sa = seta(230)
                paste_center(canvas, sa, 560, 760, scale=back_out((t - 24.78) / 0.25), rot=-140)
        if 25.82 <= t < 28.70 and t >= 27.58:
            if (27.58 <= t < 27.58 + 1 / FPS): SFX.append((t, "pop"))
            paste_center(canvas, emoji("❤️", 130), 250, 870, scale=back_out((t - 27.58) / 0.25) * (1 + 0.06 * math.sin(t * 12)), rot=-10)

    desenha_itens(canvas, t, atras=False)
    legenda(canvas, t)

    # tremida
    for s0 in SHAKES:
        if s0 <= t < s0 + 0.3:
            a = 18 * (1 - (t - s0) / 0.3)
            dx, dy = random.uniform(-a, a), random.uniform(-a, a)
            canvas = canvas.transform((W, H), Image.AFFINE, (1, 0, -dx, 0, 1, -dy), Image.BILINEAR,
                                      fillcolor=(0, 0, 0, 255))
            big = canvas.resize((int(W * 1.04), int(H * 1.04)), Image.BILINEAR)
            canvas = big.crop(((big.width - W) // 2, (big.height - H) // 2, (big.width - W) // 2 + W,
                               (big.height - H) // 2 + H))
    if t > DUR - 0.25:
        canvas = Image.blend(canvas, Image.new("RGBA", (W, H), CAFE + (255,)), (t - (DUR - 0.25)) / 0.25)
    return canvas.convert("RGB")


# máscaras (texto atrás da cabeça)
print("recortando pessoa…", flush=True)
MASKS = {}
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", FALA, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                        stdout=subprocess.PIPE)
prev = None
for i in range(NFR):
    raw = proc.stdout.read(W * H * 3)
    if i in MASK_FRAMES:
        m = np.asarray(mascara(Image.frombytes("RGB", (W, H), raw)), np.float32)
        if prev is not None and i - 1 in MASKS:
            m = 0.6 * m + 0.4 * prev
        prev = m
        MASKS[i] = Image.fromarray(m.astype(np.uint8))
    if i > max(MASK_FRAMES):
        break
proc.stdout.close(); proc.wait()

print("renderizando quadros…", flush=True)
VID = SAIDA + ".video.mp4"
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", FALA, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                        "-pix_fmt", "yuv420p", VID], stdin=subprocess.PIPE)
for i in range(NFR):
    raw = dec.stdout.read(W * H * 3)
    src = Image.frombytes("RGB", (W, H), raw)
    enc.stdin.write(render(i, src).tobytes())
    if i % 60 == 0:
        print(f"  {i}/{NFR}", flush=True)
enc.stdin.close(); enc.wait(); dec.stdout.close(); dec.wait()

# ---------------- som ----------------
print("montando o som…", flush=True)
SR = 48000
sfx = np.zeros(int((DUR + 1) * SR), np.float32)


def add(sig, t, g=1.0):
    a = int(max(0, t) * SR)
    n = min(len(sig), len(sfx) - a)
    sfx[a:a + n] += sig[:n] * g


def lowpass(x, alpha):
    y = np.empty_like(x); acc = 0.0
    for k in range(len(x)):
        acc += alpha[k] * (x[k] - acc) if hasattr(alpha, "__len__") else alpha * (x[k] - acc)
        y[k] = acc
    return y


ultimo = -1
for t, f in CLIQUES:
    if t == ultimo:
        t += random.uniform(0.01, 0.03)
    ultimo = t
    n = int(0.045 * SR)
    env = np.exp(-np.linspace(0, 1, n) * random.uniform(38, 55))
    r = np.random.randn(n)
    corpo = np.sin(2 * np.pi * random.uniform(170, 260) * np.arange(n) / SR) * np.exp(-np.linspace(0, 1, n) * 25)
    add(((np.diff(r, prepend=0) * 0.6 + r * 0.4) * env * 0.5 + corpo * 0.4) * f * random.uniform(0.7, 1.0), t, 0.55)

for t, tipo in SFX:
    if tipo == "whoosh":
        n = int(0.42 * SR); x = np.linspace(0, 1, n)
        cut = (0.02 + 0.25 * np.sin(np.pi * x) ** 2).astype(np.float32)
        s = lowpass(np.random.randn(n).astype(np.float32), cut)
        s *= np.sin(np.pi * x) ** 1.5
        add(s / (np.abs(s).max() + 1e-9), t - 0.12, 0.55)
    elif tipo == "pop":
        n = int(0.09 * SR); x = np.arange(n) / SR
        fr = 900 * np.exp(-x * 18) + 380
        s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-x * 40)
        add(s.astype(np.float32), t, 0.5)
    elif tipo == "foto":
        for dt, g in [(0, 1.0), (0.07, 0.7)]:
            n = int(0.03 * SR)
            s = np.random.randn(n) * np.exp(-np.linspace(0, 1, n) * 30)
            add(np.diff(s, prepend=0).astype(np.float32), t + dt, 0.6 * g)

sfx = np.tanh(sfx * 1.2) * 0.9
SFXWAV = SAIDA + ".sfx.wav"
with wave.open(SFXWAV, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(sfx, -1, 1) * 32767).astype(np.int16).tobytes())

RADIO = "highpass=f=700,lowpass=f=2600,aeval='tanh(5*val(0))/1.1',volume=1.4"
fc = (f"[0:a]asplit=3[a][b][c];[a]atrim=0:3.70,asetpts=PTS-STARTPTS[p1];"
      f"[b]atrim=3.70:4.66,asetpts=PTS-STARTPTS,{RADIO},afade=t=in:d=0.02,afade=t=out:st=0.92:d=0.04[p2];"
      f"[c]atrim=4.66,asetpts=PTS-STARTPTS[p3];[p1][p2][p3]concat=n=3:v=0:a=1,aresample=48000[voz];"
      f"[2:a]volume=0.45[fx];[voz][fx]amix=inputs=2:duration=first:normalize=0,"
      f"afade=t=out:st={DUR - 0.3:.2f}:d=0.3[aout]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", FALA, "-i", VID, "-i", SFXWAV, "-filter_complex", fc,
                "-map", "1:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-t", f"{DUR:.3f}", "-movflags", "+faststart", SAIDA], check=True)
os.remove(VID); os.remove(SFXWAV)
print("ok:", SAIDA)
