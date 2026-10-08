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
python3 semanas/montar.py s41 41 "5 a 11 de outubro" 08/10/2026 --destaque 13,15,7 --visual 2,4
```

Isso gera:
- `semanas/2026-<semana>.html`: prévia publicada no Claude.
- `site/semana-<numero>/`: página do site no Netlify, com a caixinha de nome e @ do Instagram.
  O endereço principal do site abre a semana mais recente.

O visual fica em `semanas/_modelo.html` e a caixinha de entrada em `semanas/_portaria.html`.

## Site e lista de acessos (Netlify)

O site é publicado a partir da pasta `site/` (veja `netlify.toml`).
Cada pessoa que entra deixa nome e @ do Instagram no formulário **acessos**, que aparece no painel do Netlify em **Forms**.
Quem já entrou num aparelho não precisa preencher de novo, e o acesso de cada semana nova é registrado sozinho.
