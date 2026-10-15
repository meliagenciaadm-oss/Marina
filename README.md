# Marina 🎬

Vídeos de meme verticais (1080x1920, para Reels e TikTok) com reações de fundo verde.
O formato é: texto da situação em cima e a reação embaixo, já sem o fundo verde.

## Como usar

1. Salve os clipes de fundo verde na pasta `clipes/`. Pode ser mp4, mov ou gif.
2. Para fazer uma cena só:
   ```bash
   python3 meme.py --texto "Eu quando o Derek aparece no elevador" \
       --reacao clipes/cachorro.mp4 --saida saida/derek.mp4
   ```
3. Para juntar várias cenas num vídeo, escreva um roteiro como `roteiros/exemplo.json` e rode:
   ```bash
   python3 meme.py --roteiro roteiros/exemplo.json --saida saida/greys.mp4
   ```

## Opções de cada cena

| Opção | O que faz | Padrão |
|---|---|---|
| `texto` | Situação escrita no topo. Use `\n` para quebrar a linha | — |
| `reacao` | Clipe de fundo verde | — |
| `inicio` / `fim` | Trecho do clipe, em segundos | o clipe inteiro |
| `fundo` | Cor (`white`, `black`, `#ffd1dc`) ou caminho de uma imagem ou vídeo | `white` |
| `cor_texto` | Cor do texto | preto em cores claras, branco com contorno no resto |
| `audio` | `false` tira o som da reação | `true` |
| `cor_chave` / `similaridade` | Ajuste fino do verde, se sobrar borda verde | detectado sozinho / `0.18` |

O que você coloca fora de `cenas` no roteiro vale para todas as cenas.
