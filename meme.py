#!/usr/bin/env python3
"""Gera vídeos de meme verticais (1080x1920) com reações de fundo verde.

Formato: texto da situação em cima + reação (fundo verde removido) embaixo.

Uso rápido (uma cena):
    python3 meme.py --texto "Eu quando a Cristina vai embora" \
        --reacao clipes/cachorro.mp4 --saida saida/cristina.mp4

Vários momentos num vídeo só (roteiro JSON):
    python3 meme.py --roteiro roteiros/exemplo.json --saida saida/greys.mp4
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import textwrap

from PIL import ImageFont

W, H, FPS = 1080, 1920, 30
FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EXT_IMAGEM = (".png", ".jpg", ".jpeg", ".webp")


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def duracao(arquivo):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", arquivo], capture_output=True, text=True)
    return float(out.stdout.strip())


def tem_audio(arquivo):
    out = run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
               "stream=index", "-of", "csv=p=0", arquivo], capture_output=True, text=True)
    return bool(out.stdout.strip())


def cor_do_fundo(arquivo, inicio):
    """Lê a cor do canto superior esquerdo do clipe (o verde a ser removido)."""
    out = run(["ffmpeg", "-v", "error", "-ss", str(inicio), "-i", arquivo,
               "-vf", "crop=24:24:4:4,scale=1:1", "-frames:v", "1",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    r, g, b = out.stdout[:3]
    return f"0x{r:02X}{g:02X}{b:02X}"


def quebrar_texto(texto, tamanho, largura_max):
    """Quebra o texto em linhas que cabem na largura (drawtext não quebra sozinho)."""
    fonte = ImageFont.truetype(FONTE, tamanho)
    linhas = []
    for paragrafo in texto.split("\n"):
        palavras, atual = paragrafo.split(), ""
        for p in palavras:
            teste = f"{atual} {p}".strip()
            if fonte.getlength(teste) <= largura_max:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = p
        linhas.append(atual)
    return linhas


def ajustar_texto(texto, altura_max, largura_max=W - 120):
    """Escolhe o maior tamanho de fonte em que o texto cabe na área do topo."""
    for tamanho in range(84, 31, -4):
        linhas = quebrar_texto(texto, tamanho, largura_max)
        if len(linhas) * tamanho * 1.25 <= altura_max:
            return tamanho, linhas
    return 32, quebrar_texto(texto, 32, largura_max)


def gerar_cena(cena, saida, tmp):
    reacao = cena["reacao"]
    inicio = float(cena.get("inicio", 0))
    fim = cena.get("fim")
    dur = (float(fim) if fim is not None else duracao(reacao)) - inicio
    if dur <= 0:
        sys.exit(f"Trecho inválido em {reacao}: fim deve ser maior que início.")

    fundo = cena.get("fundo", "white")
    # Texto preto em fundo de cor clara; branco com contorno sobre preto, imagem ou vídeo
    escuro = os.path.isfile(fundo) or fundo.lower() in ("black", "#000000", "0x000000")
    cor_texto = cena.get("cor_texto", "white" if escuro else "black")
    area_texto = int(cena.get("area_texto", 560))
    chave = cena.get("cor_chave") or cor_do_fundo(reacao, inicio)
    similaridade = cena.get("similaridade", 0.18)

    texto = cena.get("texto", "")
    sem_emoji = "".join(c for c in texto if ord(c) < 0x2190)
    if sem_emoji != texto:
        print("  Aviso: emojis removidos (a fonte do vídeo não suporta emoji).")
    tamanho, linhas = ajustar_texto(sem_emoji, area_texto - 120)
    arq_texto = os.path.join(tmp, f"{os.path.basename(saida)}.txt")
    with open(arq_texto, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    # Entrada 0: fundo (cor, imagem ou vídeo em loop)
    if os.path.isfile(fundo) and fundo.lower().endswith(EXT_IMAGEM):
        ent_fundo = ["-loop", "1", "-i", fundo]
    elif os.path.isfile(fundo):
        ent_fundo = ["-stream_loop", "-1", "-i", fundo]
    else:
        ent_fundo = ["-f", "lavfi", "-i", f"color=c={fundo}:s={W}x{H}:r={FPS}"]

    # Entrada 1: reação com fundo verde
    ent_reacao = ["-ss", str(inicio), "-t", str(dur)]
    if reacao.lower().endswith(".gif"):
        ent_reacao += ["-ignore_loop", "0"]
    ent_reacao += ["-i", reacao]

    # Entrada 2: áudio (o da reação ou silêncio)
    usa_audio = cena.get("audio", True) and tem_audio(reacao)
    ent_audio = [] if usa_audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]

    altura_reacao = H - area_texto
    borda = "borderw=4:bordercolor=black" if cor_texto == "white" else "borderw=0"
    filtro = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"fps={FPS},setsar=1[bg];"
        f"[1:v]fps={FPS},chromakey={chave}:{similaridade}:0.08,despill=type=green,"
        f"scale={W}:{altura_reacao}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:H-h:shortest=0[comp];"
        f"[comp]drawtext=fontfile={FONTE}:textfile='{arq_texto}':fontsize={tamanho}:"
        f"fontcolor={cor_texto}:{borda}:line_spacing={int(tamanho * 0.25)}:"
        f"text_align=center:x=(w-text_w)/2:y=({area_texto}-text_h)/2,"
        f"format=yuv420p[v]"
    )
    audio_map = "1:a:0" if usa_audio else "2:a:0"
    run(["ffmpeg", "-y", "-v", "error", *ent_fundo, *ent_reacao, *ent_audio,
         "-filter_complex", filtro, "-map", "[v]", "-map", audio_map,
         "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
         "-movflags", "+faststart", saida])


def main():
    ap = argparse.ArgumentParser(description="Vídeos de meme com reações de fundo verde.")
    ap.add_argument("--texto", help="Texto da situação (vai no topo)")
    ap.add_argument("--reacao", help="Clipe de reação com fundo verde (mp4, mov, gif...)")
    ap.add_argument("--inicio", type=float, default=0, help="Segundo inicial do clipe")
    ap.add_argument("--fim", type=float, help="Segundo final do clipe")
    ap.add_argument("--fundo", default="white", help="Cor (white, black, #ffd1dc) ou imagem/vídeo")
    ap.add_argument("--sem-audio", action="store_true", help="Remove o som da reação")
    ap.add_argument("--roteiro", help="JSON com várias cenas (ver roteiros/exemplo.json)")
    ap.add_argument("--saida", default="saida/meme.mp4")
    a = ap.parse_args()

    if a.roteiro:
        with open(a.roteiro, encoding="utf-8") as f:
            dados = json.load(f)
        padrao = {k: v for k, v in dados.items() if k != "cenas"}
        cenas = [{**padrao, **c} for c in dados["cenas"]]
    elif a.texto is not None and a.reacao:
        cenas = [{"texto": a.texto, "reacao": a.reacao, "inicio": a.inicio, "fim": a.fim,
                  "fundo": a.fundo, "audio": not a.sem_audio}]
    else:
        ap.error("use --texto e --reacao, ou --roteiro")

    os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        partes = []
        for i, cena in enumerate(cenas):
            parte = os.path.join(tmp, f"cena{i:02d}.mp4")
            print(f"Cena {i + 1}/{len(cenas)}: {textwrap.shorten(cena.get('texto', ''), 50)}")
            gerar_cena(cena, parte, tmp)
            partes.append(parte)
        lista = os.path.join(tmp, "lista.txt")
        with open(lista, "w") as f:
            f.writelines(f"file '{p}'\n" for p in partes)
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lista,
             "-c", "copy", "-movflags", "+faststart", a.saida])
    print(f"Pronto: {a.saida} ({duracao(a.saida):.1f}s)")


if __name__ == "__main__":
    main()
