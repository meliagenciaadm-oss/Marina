"""Monta a página da semana a partir de dados/<semana>-posts.json.

Uso: python3 montar.py s41 41 "5 a 11 de outubro" 08/10/2026 --destaque 13,15,7 --visual 2,4

Gera duas versões:
- semanas/2026-<semana>.html: prévia publicada no Claude (sem a caixinha de entrada)
- site/semana-<numero>/index.html: versão do site no Netlify, com a caixinha que registra os acessos.
  Também copia as imagens para site/assets/ e faz o endereço principal do site abrir a semana mais recente.
"""
import argparse, json, pathlib, shutil

aqui = pathlib.Path(__file__).parent
site = aqui.parent / "site"
p = argparse.ArgumentParser()
p.add_argument("semana"); p.add_argument("numero"); p.add_argument("periodo"); p.add_argument("atualizado")
p.add_argument("--destaque", default=""); p.add_argument("--visual", default="")
a = p.parse_args()

lista = lambda s: json.dumps([int(x) for x in s.split(",") if x])
dados = json.loads((aqui / f"dados/{a.semana}-posts.json").read_text())
modelo = (aqui / "_modelo.html").read_text()

def montar(posts, portaria):
    html = modelo
    for k, v in {"{{PORTARIA}}": portaria, "{{SEMANA}}": a.numero, "{{PERIODO}}": a.periodo,
                 "{{ATUALIZADO}}": a.atualizado,
                 "{{DATA}}": json.dumps(posts, ensure_ascii=False).replace("</", "<\\/"),
                 "{{DESTAQUE}}": lista(a.destaque), "{{VISUAL}}": lista(a.visual)}.items():
        html = html.replace(k, v)
    return html

# Prévia no Claude
(aqui / f"2026-{a.semana}.html").write_text(montar(dados, ""))

# Site no Netlify: imagens com caminho a partir da raiz do site
posts_site = [{**d, "img": "/" + d["img"]} for d in dados]
portaria = (aqui / "_portaria.html").read_text()
pagina = montar(posts_site, portaria).replace('src="assets/', 'src="/assets/')
cabeca = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
          '<meta name="robots" content="noindex"></head><body>')
destino = site / f"semana-{a.numero}"
destino.mkdir(parents=True, exist_ok=True)
(destino / "index.html").write_text(cabeca + pagina + "</body></html>")

(site / "assets/refs").mkdir(parents=True, exist_ok=True)
shutil.copy(aqui / "assets/foto-perfil.jpg", site / "assets/foto-perfil.jpg")
for d in dados:
    shutil.copy(aqui / d["img"], site / d["img"])
(site / "_redirects").write_text(f"/  /semana-{a.numero}/  302\n")

print(f"{len(dados)} posts · prévia 2026-{a.semana}.html · site/semana-{a.numero}/")
