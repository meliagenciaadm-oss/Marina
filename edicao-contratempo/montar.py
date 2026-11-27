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
F_LEG = ImageFont.truetype(FONTS + "Inter-LightItalic.otf", 40)
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
        draw.text((x, y), txt, font=font, fill=(255, 255, 255, 255))
        return
    for ch in txt:
        draw.text((x, y), ch, font=font, fill=(255, 255, 255, 255))
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


def bloco_grande(linhas_vis, linhas_full, y0, font, track=-2, entrelinha=0.98):
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


def legenda(txt):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = (W - largura(txt, F_LEG)) / 2
    escreve(d, (x, LEG_Y), txt, F_LEG)
    return lay


cache = {}


def quadro(t):
    # abertura: título digitando
    if t < STRIP_IN:
        total = sum(len(l) for l in TITULO)
        n = min(total, int(max(0, t - 0.10) / 1.9 * total))
        vis, rest = [], n
        for l in TITULO:
            vis.append(l[:rest]); rest = max(0, rest - len(l))
        key = ("tit", n, t >= 2.3)
        if key not in cache:
            lay, yfim = bloco_grande(vis, TITULO, TIT_Y, F_TIT)
            if t >= 2.3:
                d = ImageDraw.Draw(lay)
                escreve(d, ((W - largura(TITULO_SUB, F_SUB)) / 2, yfim + 14), TITULO_SUB, F_SUB)
            cache[key] = com_sombra(lay, 10, 0.55)
        return cache[key]
    # final: chamada
    if t >= STRIP_OUT:
        n = sum(1 for (t0, _) in CTA if t >= t0)
        key = ("cta", n)
        if key not in cache:
            full = [c for _, c in CTA]
            vis = [c if i < n else "" for i, c in enumerate(full)]
            lay, _ = bloco_grande(vis, full, CTA_Y, ImageFont.truetype(FONTS + "InterDisplay-Bold.otf", 88))
            cache[key] = com_sombra(lay, 10, 0.55)
        return cache[key]
    # meio: legenda
    atual = [f for f in FRASES if f[0] <= t + 1e-6][-1]
    key = ("leg", atual[1])
    if key not in cache:
        cache[key] = com_sombra(legenda(atual[1]), 5, 0.45)
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

# ---------- 3. composição final ----------
sw, sh = round(W * ESCALA / 2) * 2, round(H * ESCALA / 2) * 2
fc = (
    f"[0:v]fps={FPS},scale={sw}:{sh}:flags=lanczos,crop={W}:{H}:{(sw - W) // 2}:0,setsar=1[bg];"
    f"[1:v]setpts=PTS-STARTPTS+{STRIP_IN}/TB[fx];"
    f"[bg][fx]overlay=0:{FAIXA_Y}:eof_action=pass:enable='between(t,{STRIP_IN},{STRIP_OUT - 0.001})'[v1];"
    f"[v1][2:v]overlay=0:0:format=auto[v2];[v2]format=yuv420p[v]"
)
run(["ffmpeg", "-v", "error", "-y", "-i", FALA, "-i", FAIXA,
     "-framerate", str(FPS), "-i", f"{TMP}/ov/%04d.png",
     "-filter_complex", fc, "-map", "[v]", "-map", "0:a",
     "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high",
     "-c:a", "aac", "-b:a", "192k", "-t", str(DUR), "-movflags", "+faststart", SAIDA])
shutil.rmtree(TMP)
print("ok:", SAIDA)
