#!/usr/bin/env python3
"""Uso: python3 montar_lista.py lista.txt video_fundo.mp4 saida.mp4
lista.txt: 2 primeiras linhas = título; demais = itens."""
import subprocess, sys, os, tempfile
lista, bg, out = sys.argv[1:4]
here = os.path.dirname(os.path.abspath(__file__))
FT, FL = f"{here}/fonts/Anek-Titulo.ttf", f"{here}/fonts/Anek-Lista.ttf"
COR = os.environ.get("COR", "0xF9E79F")  # amarelo manteiga
lines = [l.strip() for l in open(lista, encoding="utf-8") if l.strip()]
titulo, itens = lines[:2], lines[2:]
tmp = tempfile.mkdtemp()
def tf(i, txt):
    p = f"{tmp}/{i}.txt"; open(p, "w", encoding="utf-8").write(txt); return p
n = len(itens)
fs = 34 if n > 25 else 40; lh = int(fs * 1.25)
ty, tfs = 330, 62
ly = ty + 2 * int(tfs * 1.2) + 70
f = ["[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,drawbox=c=black@0.28:t=fill"]
for i, t in enumerate(titulo):
    f.append(f"drawtext=fontfile={FT}:textfile={tf('t'+str(i), t)}:fontsize={tfs}:fontcolor={COR}:shadowcolor=black@0.45:shadowx=2:shadowy=2:x=(w-tw)/2:y={ty + i*int(tfs*1.2)}")
# lista alinhada à esquerda, bloco centralizado pelo item mais largo (aprox.)
maxlen = max(len(x) for x in itens); x0 = max(60, int((1080 - maxlen * fs * 0.52) / 2))
for i, t in enumerate(itens):
    f.append(f"drawtext=fontfile={FL}:textfile={tf('i'+str(i), '•  ' + t)}:fontsize={fs}:fontcolor={COR}:shadowcolor=black@0.45:shadowx=2:shadowy=2:x={x0}:y={ly + i*lh}")
fc = ",".join(f) + ",format=yuv420p[v]"
subprocess.run(["ffmpeg","-loglevel","error","-y","-i",bg,"-filter_complex",fc,"-map","[v]","-map","0:a?","-c:v","libx264","-crf","20","-c:a","aac","-movflags","+faststart",out], check=True)
print("ok:", out)
