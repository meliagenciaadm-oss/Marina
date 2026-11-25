#!/usr/bin/env bash
# Uso: ./montar.sh [video_de_fundo.mp4] [saida.mp4]
# Sem vídeo de fundo, gera uma prévia com fundo escuro.
set -e
cd "$(dirname "$0")"
BG="${1:-}"; OUT="${2:-ranking_jogos_vorazes.mp4}"
DUR=10            # duração total (s)
START=0.8         # quando aparece o 6º
STEP=1.1          # intervalo entre pôsteres
TITLE="meu ranking dos filmes de Jogos Vorazes:"
F=/usr/share/fonts/opentype/inter/Inter-Bold.otf
FN=/usr/share/fonts/opentype/inter/Inter-Black.otf
P=(posters/1_*.jpg posters/2_*.jpg posters/3_*.jpg posters/4_*.jpg posters/5_*.jpg posters/6_*.jpg)
# posições (x y w h) do 1º ao 6º
POS=("60 130 300 450" "390 130 300 450" "720 130 300 450" "60 700 300 370" "60 1090 300 370" "60 1480 300 370")
printf '%s' "$TITLE" > /tmp/_title.txt
if [ -n "$BG" ]; then
  IN=(-stream_loop -1 -i "$BG")
  BGF="[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,trim=duration=$DUR,setpts=PTS-STARTPTS[bg]"
else
  IN=(-f lavfi -i "color=c=0x2a2522:s=1080x1920:d=$DUR")
  BGF="[0:v]drawtext=fontfile=$F:text='seu vídeo aqui':fontsize=60:fontcolor=white@0.35:x=600:y=1100,setsar=1[bg]"
fi
FC="$BGF;"; last="bg"
for i in 0 1 2 3 4 5; do
  IN+=(-loop 1 -t $DUR -i "${P[$i]}")
  read x y w h <<<"${POS[$i]}"
  n=$((i+1)); idx=$((i+1))
  T=$(python3 -c "print(round($START+(6-$n)*$STEP,2))")
  FC+="[$idx:v]scale=$w:$h:force_original_aspect_ratio=increase,crop=$w:$h,
drawbox=x=16:y=16:w=62:h=72:color=0xDCD3F2@0.95:t=fill,
drawtext=fontfile=$FN:text='$n':fontsize=50:fontcolor=0x6A3D9A:x=16+(62-tw)/2:y=16+(72-th)/2,
format=rgba,fade=in:st=$T:d=0.25:alpha=1[p$n];
[$last][p$n]overlay=$x:$y:enable='gte(t,$T)'[o$n];"
  last="o$n"
done
FC+="[$last]drawtext=fontfile=$F:textfile=/tmp/_title.txt:fontsize=46:fontcolor=white:shadowcolor=black@0.6:shadowx=2:shadowy=2:x=(w-tw)/2:y=615,format=yuv420p[v]"
AUD=(); [ -n "$BG" ] && AUD=(-map "0:a?" -c:a aac)
ffmpeg -loglevel error -y "${IN[@]}" -filter_complex "$FC" -map "[v]" "${AUD[@]}" -t $DUR -r 30 -c:v libx264 -crf 20 -movflags +faststart "$OUT"
echo "ok: $OUT"
