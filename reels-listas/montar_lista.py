#!/usr/bin/env python3
"""Uso: python3 montar_lista.py lista.txt video_fundo.mp4 saida.mp4
lista.txt: 2 primeiras linhas = título; demais = itens."""
import subprocess, sys, os, tempfile
lista, bg, out = sys.argv[1:4]
here = os.path.dirname(os.path.abspath(__file__))
FT, FL = f"{here}/fonts/Anek-Titulo.ttf", f"{here}/fonts/Anek-Lista.ttf"
COR = os.environ.get("COR", "0xF9E79F")  # amarelo manteiga
OP = os.environ.get("OPACIDADE", "0.55")  # opacidade do vídeo sobre fundo preto
lines = [l.strip() for l in open(lista, encoding="utf-8") if l.strip()]
titulo, itens = lines[:2], lines[2:]
tmp = tempfile.mkdtemp()
def tf(i, txt):
    p = f"{tmp}/{i}.txt"; open(p, "w", encoding="utf-8").write(txt); return p
n = len(itens)
fs = 29 if n > 25 else 36; lh = int(fs * 1.21)
ty, tfs = 300, 52
ly = ty + 2 * int(tfs * 1.12) + 90
f = [f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,colorbalance=rs=0.06:gs=0.02:bs=-0.06:rm=0.05:gm=0.01:bm=-0.04,colorchannelmixer=rr={OP}:gg={OP}:bb={OP}"]
for i, t in enumerate(titulo):
    f.append(f"drawtext=fontfile={FT}:textfile={tf('t'+str(i), t)}:fontsize={tfs}:fontcolor={COR}:x=(w-tw)/2:y={ty + i*int(tfs*1.12)}")
# lista alinhada à esquerda, bloco centralizado pelo item mais largo (aprox.)
maxlen = max(len(x) for x in itens); x0 = int(os.environ.get('LISTA_X', 285))
for i, t in enumerate(itens):
    f.append(f"drawtext=fontfile={FL}:textfile={tf('i'+str(i), '•  ' + t)}:fontsize={fs}:fontcolor={COR}:x={x0}:y={ly + i*lh}")
fc = ",".join(f) + ",format=yuv420p[v]"
subprocess.run(["ffmpeg","-loglevel","error","-y","-i",bg,"-filter_complex",fc,"-map","[v]","-map","0:a?","-c:v","libx264","-crf","20","-c:a","aac","-movflags","+faststart",out], check=True)
print("ok:", out)
