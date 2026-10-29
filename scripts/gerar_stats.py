"""Gera stats.svg com estatísticas públicas do utilizador, usando só a API do GitHub."""
import json
import os
import urllib.request
from html import escape

USER = "J040-99"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "stats-profile",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


user = api(f"/users/{USER}")
repos = api(f"/users/{USER}/repos?per_page=100&type=owner")
own = [r for r in repos if not r["fork"]]

stars = sum(r["stargazers_count"] for r in own)
langs = {}
for r in own:
    for lang, size in api(f"/repos/{USER}/{r['name']}/languages").items():
        langs[lang] = langs.get(lang, 0) + size

ignorar = {"HTML", "CSS"}
langs = {k: v for k, v in langs.items() if k not in ignorar}
total = sum(langs.values()) or 1
top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6]

cores = ["#512BD4", "#3776AB", "#3178C6", "#F05032", "#3DDC84", "#8957E5"]

stats = [
    ("Repositórios públicos", user["public_repos"]),
    ("Estrelas recebidas", stars),
    ("Seguidores", user["followers"]),
]

h = 150 + 28 * len(top)
out = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="{h}" viewBox="0 0 495 {h}">',
    '<style>text{font-family:Segoe UI,Helvetica,Arial,sans-serif}'
    '.t{font-size:16px;font-weight:600;fill:#58a6ff}'
    '.l{font-size:13px;fill:#8b949e}.v{font-size:13px;font-weight:600;fill:#c9d1d9}</style>',
    f'<rect x="0.5" y="0.5" width="494" height="{h - 1}" rx="8" fill="#0d1117" stroke="#30363d"/>',
    '<text x="24" y="34" class="t">Estatísticas do GitHub</text>',
]
for i, (nome, valor) in enumerate(stats):
    y = 62 + i * 22
    out.append(f'<text x="24" y="{y}" class="l">{escape(nome)}</text>')
    out.append(f'<text x="471" y="{y}" class="v" text-anchor="end">{valor}</text>')

base = 62 + len(stats) * 22 + 20
out.append(f'<text x="24" y="{base}" class="t">Linguagens mais usadas</text>')
for i, (lang, size) in enumerate(top):
    y = base + 28 + i * 28
    pct = size / total * 100
    out.append(f'<text x="24" y="{y}" class="l">{escape(lang)}</text>')
    out.append(f'<rect x="140" y="{y - 10}" width="260" height="8" rx="4" fill="#21262d"/>')
    out.append(
        f'<rect x="140" y="{y - 10}" width="{260 * pct / 100:.1f}" height="8" rx="4" fill="{cores[i % len(cores)]}"/>'
    )
    out.append(f'<text x="471" y="{y}" class="v" text-anchor="end">{pct:.1f}%</text>')
out.append("</svg>")

with open("stats.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
