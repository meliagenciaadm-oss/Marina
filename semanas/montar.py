"""Monta a página da semana a partir de dados/<semana>-posts.json.

Uso: python3 montar.py s41 41 "5 a 11 de outubro" 08/10/2026 --destaque 13,15,7 --visual 2,4
Gera 2026-<semana>.html ao lado deste arquivo.
"""
import argparse, json, pathlib

aqui = pathlib.Path(__file__).parent
p = argparse.ArgumentParser()
p.add_argument("semana"); p.add_argument("numero"); p.add_argument("periodo"); p.add_argument("atualizado")
p.add_argument("--destaque", default=""); p.add_argument("--visual", default="")
a = p.parse_args()

lista = lambda s: json.dumps([int(x) for x in s.split(",") if x])
dados = json.loads((aqui / f"dados/{a.semana}-posts.json").read_text())
html = (aqui / "_modelo.html").read_text()
for k, v in {"{{SEMANA}}": a.numero, "{{PERIODO}}": a.periodo, "{{ATUALIZADO}}": a.atualizado,
             "{{DATA}}": json.dumps(dados, ensure_ascii=False).replace("</", "<\\/"),
             "{{DESTAQUE}}": lista(a.destaque), "{{VISUAL}}": lista(a.visual)}.items():
    html = html.replace(k, v)
(aqui / f"2026-{a.semana}.html").write_text(html)
print(f"2026-{a.semana}.html: {len(dados)} posts")
