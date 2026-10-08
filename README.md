# Radar de Formatos

Dashboard semanal com formatos e trends do Instagram que dá pra adaptar a qualquer nicho.

Cada semana tem seu próprio arquivo em `semanas/` e é publicada com um link diferente.

| Semana | Período | Arquivo | Link |
|---|---|---|---|
| 41 | 5 a 11 out 2026 | `semanas/2026-s41.html` | https://claude.ai/artifact/V3PurV7a7WnFwpM1M3PH1T |

## Como montar uma semana

1. Coloque os posts em `semanas/dados/<semana>-posts.json` e os prints em `semanas/assets/refs/`.
2. Rode, por exemplo:

```
python3 semanas/montar.py s41 41 "5 a 11 de outubro" 08/10/2026 --destaque 13,16,7 --visual 2,4,15
```

3. Publique o `semanas/2026-<semana>.html` gerado junto com a pasta `assets/`.

O visual fica em `semanas/_modelo.html`.
