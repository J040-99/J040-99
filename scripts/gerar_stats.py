"""Gera stats.svg com estatísticas públicas do utilizador, usando só a API do GitHub."""
import json
import os
import re
import urllib.request
from datetime import date, datetime, timedelta
from html import escape

USER = "J040-99"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "stats-profile",
}


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def contar(path):
    """Total de itens de uma listagem, lido da última página com per_page=1."""
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(f"https://api.github.com{path}{sep}per_page=1", headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as r:
            ultima = re.search(r'[?&]page=(\d+)>; rel="last"', r.headers.get("Link", ""))
            return int(ultima.group(1)) if ultima else len(json.load(r))
    except Exception:
        return 0


def tentar(path, vazio):
    try:
        return api(path)
    except Exception:
        return vazio


user = api(f"/users/{USER}")
repos = api(f"/users/{USER}/repos?per_page=100&type=owner")
own = [r for r in repos if not r["fork"]]

# O GITHUB_TOKEN do Actions não vê o calendário de contribuições, por isso
# reconstruímos a atividade a partir dos commits dos repositórios públicos.
desde = (datetime.now() - timedelta(days=364)).strftime("%Y-%m-%dT00:00:00Z")
contagem = {}
for r in own:
    for pagina in range(1, 6):
        commits = tentar(
            f"/repos/{USER}/{r['name']}/commits?author={USER}&since={desde}&per_page=100&page={pagina}", []
        )
        for c in commits:
            dia = c["commit"]["author"]["date"][:10]
            contagem[dia] = contagem.get(dia, 0) + 1
        if len(commits) < 100:
            break

inicio = date.today() - timedelta(days=364)
inicio -= timedelta(days=(inicio.weekday() + 1) % 7)
dias = []
d0 = inicio
while d0 <= date.today():
    dias.append({"date": d0.isoformat(), "contributionCount": contagem.get(d0.isoformat(), 0)})
    d0 += timedelta(days=1)

commits_total = sum(contar(f"/repos/{USER}/{r['name']}/commits?author={USER}") for r in own)
prs = sum(contar(f"/repos/{USER}/{r['name']}/pulls?state=all") for r in own)
issues = sum(r["open_issues_count"] for r in own) - sum(
    contar(f"/repos/{USER}/{r['name']}/pulls?state=open") for r in own
)
commits_12m = sum(contagem.values())

hoje = date.today().isoformat()
dias_passados = dias

maior = atual = 0
for d in dias_passados:
    atual = atual + 1 if d["contributionCount"] else 0
    maior = max(maior, atual)
seq_atual = 0
for d in reversed(dias_passados):
    if d["contributionCount"]:
        seq_atual += 1
    elif d["date"] != hoje:
        break

melhor_dia = max(dias_passados, key=lambda d: d["contributionCount"])
dias_ativos = sum(1 for d in dias_passados if d["contributionCount"])

stars = sum(r["stargazers_count"] for r in own)
forks = sum(r["forks_count"] for r in own)
anos = (datetime.now() - datetime.fromisoformat(user["created_at"].rstrip("Z"))).days / 365.25
top_repo = max(own, key=lambda r: r["stargazers_count"], default=None)

langs = {}
for r in own:
    for lang, size in api(f"/repos/{USER}/{r['name']}/languages").items():
        langs[lang] = langs.get(lang, 0) + size
langs = {k: v for k, v in langs.items() if k not in {"HTML", "CSS"}}
total = sum(langs.values()) or 1
top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6]

cores = ["#512BD4", "#3776AB", "#3178C6", "#F05032", "#3DDC84", "#8957E5"]
W = 495
caixas = [
    ("Commits (total)", commits_total),
    ("Pull requests", prs),
    ("Issues", issues),
    ("Linguagens usadas", len(langs)),
    ("Repositórios públicos", user["public_repos"]),
    ("Estrelas", stars),
    ("Forks recebidos", forks),
    ("Seguidores", user["followers"]),
]
extras = [
    ("Commits (12 meses)", commits_12m),
    ("Sequência atual", f"{seq_atual} dias"),
    ("Maior sequência", f"{maior} dias"),
    ("Dias com atividade", dias_ativos),
    ("Melhor dia", f"{melhor_dia['contributionCount']} ({melhor_dia['date']})"),
    ("No GitHub há", f"{anos:.1f} anos"),
]
if top_repo and top_repo["stargazers_count"]:
    extras.append(("Repo mais estrelado", top_repo["name"]))

y_caixas = 56
linhas_caixas = (len(caixas) + 1) // 2
y_extras = y_caixas + linhas_caixas * 50 + 14
y_heat = y_extras + 22 + len(extras) * 22 + 14
y_lang = y_heat + 22 + 7 * 11 + 18
H = y_lang + 24 + len(top) * 28 + 10

o = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
    "<style>text{font-family:Segoe UI,Helvetica,Arial,sans-serif}"
    ".t{font-size:16px;font-weight:600;fill:#58a6ff}.l{font-size:13px;fill:#8b949e}"
    ".v{font-size:13px;font-weight:600;fill:#c9d1d9}.n{font-size:20px;font-weight:700;fill:#c9d1d9}"
    ".s{font-size:12px;fill:#8b949e}</style>",
    f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="8" fill="#0d1117" stroke="#30363d"/>',
    '<text x="24" y="34" class="t">Estatísticas do GitHub</text>',
]

for i, (nome, valor) in enumerate(caixas):
    x = 24 + (i % 2) * 227
    y = y_caixas + (i // 2) * 50
    o.append(f'<rect x="{x}" y="{y}" width="220" height="42" rx="6" fill="#161b22" stroke="#21262d"/>')
    o.append(f'<text x="{x + 12}" y="{y + 27}" class="n">{valor}</text>')
    o.append(f'<text x="{x + 208}" y="{y + 26}" class="s" text-anchor="end">{escape(nome)}</text>')

o.append(f'<text x="24" y="{y_extras}" class="t">Atividade</text>')
for i, (nome, valor) in enumerate(extras):
    y = y_extras + 24 + i * 22
    o.append(f'<text x="24" y="{y}" class="l">{escape(nome)}</text>')
    o.append(f'<text x="471" y="{y}" class="v" text-anchor="end">{escape(str(valor))}</text>')

o.append(f'<text x="24" y="{y_heat}" class="t">Calendário de contribuições</text>')
maximo = max((d["contributionCount"] for d in dias), default=1) or 1
paleta = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
semanas = [dias[i : i + 7] for i in range(0, len(dias), 7)]
passo = (W - 48) / max(len(semanas), 1)
for wi, w in enumerate(semanas):
    for d in w:
        c = d["contributionCount"]
        nivel = 0 if c == 0 else min(4, 1 + int(3 * (c - 1) / max(maximo - 1, 1)))
        dow = datetime.fromisoformat(d["date"]).weekday()
        dow = (dow + 1) % 7
        o.append(
            f'<rect x="{24 + wi * passo:.1f}" y="{y_heat + 10 + dow * 11}" width="{passo - 2:.1f}" height="9" rx="2" fill="{paleta[nivel]}"/>'
        )

o.append(f'<text x="24" y="{y_lang}" class="t">Linguagens mais usadas</text>')
for i, (lang, size) in enumerate(top):
    y = y_lang + 28 + i * 28
    pct = size / total * 100
    o.append(f'<text x="24" y="{y}" class="l">{escape(lang)}</text>')
    o.append(f'<rect x="140" y="{y - 10}" width="260" height="8" rx="4" fill="#21262d"/>')
    o.append(f'<rect x="140" y="{y - 10}" width="{260 * pct / 100:.1f}" height="8" rx="4" fill="{cores[i % len(cores)]}"/>')
    o.append(f'<text x="471" y="{y}" class="v" text-anchor="end">{pct:.1f}%</text>')
o.append("</svg>")

with open("stats.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(o))
