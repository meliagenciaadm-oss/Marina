#!/usr/bin/env python3
"""Monta o Reel "Um Contratempo" no estilo de referência.

Layout (1080x1920):
  - fundo: vídeo da fala, ampliado 1.15x e ancorado no topo (cabeça fica abaixo da faixa)
  - faixa: cenas do filme (1080x440) em y=110, trocando a cada frase
  - legenda: Inter Light Italic, branca, logo abaixo da faixa
  - abertura: título grande digitando (sem faixa)
  - final: chamada grande (sem faixa)

Uso: python montar.py FALA.mp4 FILME.mp4 SAIDA.mp4
"""
import os, subprocess, sys, shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FALA, FILME, SAIDA = sys.argv[1:4]
W, H, FPS = 1080, 1920, 30
DUR = 30.30
NFR = 909
ESCALA = 1.15
FAIXA_Y, FAIXA_H = 110, 440
STRIP_IN, STRIP_OUT = 4.68, 28.70
LEG_Y = FAIXA_Y + FAIXA_H + 22          # topo da legenda

FONTS = "/usr/share/fonts/opentype/inter/"
F_LEG = ImageFont.truetype(FONTS + "Inter-LightItalic.otf", 41)
COR = (250, 233, 163, 255)      # amarelo manteiga
TRACK_TIT, TRACK_LEG = -4.5, -1.6
F_TIT = ImageFont.truetype(FONTS + "InterDisplay-Bold.otf", 76)
F_SUB = ImageFont.truetype(FONTS + "InterDisplay-SemiBold.otf", 32)

TMP = os.path.join(os.path.dirname(os.path.abspath(SAIDA)), "_tmp_montagem")
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP + "/ov")

# (início, texto da legenda, segundo do filme usado na faixa)
FRASES = [
    (4.68,  "o filme é “Um Contratempo”",          1.0),
    (6.04,  "um empresário que acorda",            6.5),
    (7.10,  "num quarto de hotel",                 13.5),
    (8.12,  "onde aconteceu um crime",             31.0),
    (9.30,  "e ele jura que é inocente",           36.0),
    (10.60, "então ele vai tentar convencer",      42.5),
    (11.74, "a advogada",                          39.0),
    (12.42, "e a gente também",                    52.1),
    (13.18, "prepara o café",                      21.0),
    (14.40, "porque você vai precisar",            54.0),
    (15.28, "ficar bem acordada",                  57.0),
    (16.58, "pra não perder nenhum detalhe",       60.0),
    (18.06, "e eu duvido você conseguir",          64.0),
    (19.68, "adivinhar o final desse filme",       71.0),
    (20.78, "e pra fazer o melhor café",           74.5),
    (22.62, "entra lá no aplicativo da Magalu",    79.0),
    (23.90, "e procura essa cafeteira",            82.5),
    (25.20, "igual a minha",                       89.0),
    (25.82, "porque hoje eu não vivo mais sem ela", 85.5),
    (27.76, "faz parte da minha rotina",           68.0),
]
TITULO = ["o filme que passou", "despercebido mas", "merece sua atenção"]
TITULO_SUB = "(e um cafezinho também)"
TIT_Y = 300
CTA = [(28.70, "bora dar play"), (29.62, "e bom café")]
CTA_Y = 300


def run(cmd):
    subprocess.run(cmd, check=True)


# ---------- 1. faixa com as cenas do filme ----------
lista = []
for i, (t0, _, src) in enumerate(FRASES):
    t1 = FRASES[i + 1][0] if i + 1 < len(FRASES) else STRIP_OUT
    seg = f"{TMP}/seg{i:02d}.mp4"
    nfr = round((t1 - t0) * FPS)
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(src), "-i", FILME,
         "-vf", f"crop=676:276:40:502,scale={W}:{FAIXA_H}:flags=lanczos,fps={FPS},"
                f"eq=contrast=1.04:saturation=1.05",
         "-frames:v", str(nfr), "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", seg])
    lista.append(f"file '{seg}'")
open(f"{TMP}/lista.txt", "w").write("\n".join(lista))
FAIXA = f"{TMP}/faixa.mp4"
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{TMP}/lista.txt",
     "-c", "copy", FAIXA])


# ---------- 2. camada de textos (PNG por quadro) ----------
def largura(txt, font, track=0):
    return font.getlength(txt) + track * max(len(txt) - 1, 0)


def escreve(draw, xy, txt, font, track=0):
    x, y = xy
    if track == 0:
        draw.text((x, y), txt, font=font, fill=COR)
        return
    for ch in txt:
        draw.text((x, y), ch, font=font, fill=COR)
        x += font.getlength(ch) + track


def com_sombra(layer, raio, opac):
    a = layer.getchannel("A").filter(ImageFilter.GaussianBlur(raio))
    a = a.point(lambda v: int(v * opac))
    sombra = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sombra.putalpha(a)
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(sombra, (0, 3))
    out.alpha_composite(layer)
    return out


def bloco_grande(linhas_vis, linhas_full, y0, font, track=TRACK_TIT, entrelinha=0.98):
    """Desenha linhas centradas pela largura final (efeito máquina de escrever sem tremer)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lh = int(font.size * entrelinha)
    for k, (vis, full) in enumerate(zip(linhas_vis, linhas_full)):
        if not vis:
            continue
        x = (W - largura(full, font, track)) / 2
        escreve(d, (x, y0 + k * lh), vis, font, track)
    return lay, y0 + len(linhas_full) * lh


def legenda(txt, n):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = (W - largura(txt, F_LEG, TRACK_LEG)) / 2
    escreve(d, (x, LEG_Y), txt[:n], F_LEG, TRACK_LEG)
    return lay


def digitados(texto_total, t, t0, dur):
    """Quantos caracteres já apareceram (máquina de escrever)."""
    if t < t0:
        return 0
    return min(len(texto_total), int((t - t0) / dur * len(texto_total)) + 1)


def cortar(linhas, n):
    vis = []
    for l in linhas:
        vis.append(l[:n]); n = max(0, n - len(l))
    return vis


F_CTA = ImageFont.truetype(FONTS + "InterDisplay-Bold.otf", 88)
TIT_T0, TIT_DUR = 0.10, 1.9
SUB_T0, SUB_DUR = 2.25, 0.55
cache = {}
CLIQUES = []          # (tempo, intensidade) para o som de teclado
_vistos = {}


def registra(chave, n, t, forca):
    if n > _vistos.get(chave, 0):
        for _ in range(n - _vistos.get(chave, 0)):
            CLIQUES.append((t, forca))
        _vistos[chave] = n


def quadro(t):
    if t < STRIP_IN:
        n = digitados("".join(TITULO), t, TIT_T0, TIT_DUR)
        m = digitados(TITULO_SUB, t, SUB_T0, SUB_DUR)
        registra("tit", n, t, 1.0); registra("tsub", m, t, 0.7)
        key = ("tit", n, m)
        if key not in cache:
            lay, yfim = bloco_grande(cortar(TITULO, n), TITULO, TIT_Y, F_TIT)
            if m:
                d = ImageDraw.Draw(lay)
                x = (W - largura(TITULO_SUB, F_SUB, -1.2)) / 2
                escreve(d, (x, yfim + 14), TITULO_SUB[:m], F_SUB, -1.2)
            cache[key] = com_sombra(lay, 10, 0.55)
        return cache[key]
    if t >= STRIP_OUT:
        full = [c for _, c in CTA]
        ns = [digitados(c, t, t0, 0.45) for (t0, c) in CTA]
        for i, k in enumerate(ns):
            registra(("cta", i), k, t, 1.0)
        key = ("cta",) + tuple(ns)
        if key not in cache:
            vis = [c[:k] for c, k in zip(full, ns)]
            lay, _ = bloco_grande(vis, full, CTA_Y, F_CTA)
            cache[key] = com_sombra(lay, 10, 0.55)
        return cache[key]
    i = max(j for j, f in enumerate(FRASES) if f[0] <= t + 1e-6)
    t0, txt, _ = FRASES[i]
    t1 = FRASES[i + 1][0] if i + 1 < len(FRASES) else STRIP_OUT
    n = digitados(txt, t, t0, min(0.35, (t1 - t0) * 0.4))
    registra(("leg", i), n, t, 0.35)
    key = ("leg", i, n)
    if key not in cache:
        cache[key] = com_sombra(legenda(txt, n), 5, 0.45)
    return cache[key]


ultimo, ultimo_path = None, None
for f in range(NFR):
    img = quadro(f / FPS)
    p = f"{TMP}/ov/{f:04d}.png"
    if img is ultimo:
        os.link(ultimo_path, p)
    else:
        img.save(p, compress_level=1)
        ultimo, ultimo_path = img, p

# ---------- 2b. som de teclado ----------
import numpy as np, wave, random
random.seed(7); np.random.seed(7)
SR = 48000
som = np.zeros(int((DUR + 1) * SR), dtype=np.float32)
ultimo_t = -1
for t, forca in CLIQUES:
    if t == ultimo_t:                      # vários caracteres no mesmo quadro: espalha
        t += random.uniform(0.008, 0.028)
    ultimo_t = t
    t += random.uniform(-0.006, 0.006)
    n = int(0.045 * SR)
    env = np.exp(-np.linspace(0, 1, n) * random.uniform(38, 55))
    ruido = np.random.randn(n)
    clique = np.diff(ruido, prepend=0) * 0.6 + ruido * 0.4        # agudo do "tec"
    f = random.uniform(170, 260)                                    # corpo da tecla
    corpo = np.sin(2 * np.pi * f * np.arange(n) / SR) * np.exp(-np.linspace(0, 1, n) * 25)
    k = (clique * env * 0.55 + corpo * 0.45) * forca * random.uniform(0.75, 1.0)
    a = int(max(t, 0) * SR)
    som[a:a + n] += k[: len(som) - a]
som = som / (np.abs(som).max() + 1e-9) * 0.9
TECLADO = f"{TMP}/teclado.wav"
with wave.open(TECLADO, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((som * 32767).astype(np.int16).tobytes())

# ---------- 3. composição final ----------
sw, sh = round(W * ESCALA / 2) * 2, round(H * ESCALA / 2) * 2
fc = (
    f"[0:v]fps={FPS},scale={sw}:{sh}:flags=lanczos,crop={W}:{H}:{(sw - W) // 2}:0,setsar=1[bg];"
    f"[1:v]setpts=PTS-STARTPTS+{STRIP_IN}/TB[fx];"
    f"[bg][fx]overlay=0:{FAIXA_Y}:eof_action=pass:enable='between(t,{STRIP_IN},{STRIP_OUT - 0.001})'[v1];"
    f"[v1][2:v]overlay=0:0:format=auto[v2];[v2]format=yuv420p[v];"
    f"[3:a]volume=0.32,aresample=44100[tec];[0:a][tec]amix=inputs=2:duration=first:normalize=0[a]"
)
run(["ffmpeg", "-v", "error", "-y", "-i", FALA, "-i", FAIXA,
     "-framerate", str(FPS), "-i", f"{TMP}/ov/%04d.png", "-i", TECLADO,
     "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
     "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high",
     "-c:a", "aac", "-b:a", "192k", "-t", str(DUR), "-movflags", "+faststart", SAIDA])
shutil.rmtree(TMP)
print("ok:", SAIDA)
