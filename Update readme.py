#!/usr/bin/env python3
"""Atualiza as seções dinâmicas do README.md com dados públicos da API do GitHub.

Seções controladas por marcadores HTML no README:
    <!-- RECENT:START --> ... <!-- RECENT:END -->   tabela dos repositórios mais recentes
    <!-- SUMMARY:START --> ... <!-- SUMMARY:END --> resumo (total de repositórios e última atividade)

Uso local:   python scripts/update_readme.py
Variáveis:   GH_USER (padrão: Br4yaan), GITHUB_TOKEN (opcional, evita limite de requisições),
             INCLUDE_FORKS=1 (inclui forks na lista)
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

USER = os.environ.get("GH_USER", "Br4yaan")
INCLUDE_FORKS = os.environ.get("INCLUDE_FORKS") == "1"
README = Path(__file__).resolve().parent.parent / "README.md"
API_URL = f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed&type=owner"
MAX_RECENT = 6


def fetch_repos() -> list[dict]:
    """Busca os repositórios públicos do usuário na API do GitHub."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-readme-updater",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(API_URL, headers=headers), timeout=30) as response:
        return json.load(response)


def select_repos(repos: list[dict]) -> list[dict]:
    """Remove o repositório de perfil (e forks, por padrão) e ordena pelo push mais recente."""
    chosen = [
        repo
        for repo in repos
        if repo["name"].lower() != USER.lower() and (INCLUDE_FORKS or not repo.get("fork"))
    ]
    return sorted(chosen, key=lambda repo: repo["pushed_at"], reverse=True)


def format_date(iso_date: str) -> str:
    """Converte '2026-10-26T18:49:06Z' em '26/10/2026'."""
    return datetime.fromisoformat(iso_date.replace("Z", "+00:00")).strftime("%d/%m/%Y")


def build_recent_table(repos: list[dict]) -> str:
    lines = ["| Repositório | Descrição | Última atividade |", "|:--|:--|:-:|"]
    for repo in repos[:MAX_RECENT]:
        description = (repo.get("description") or "—").replace("|", "\\|")
        lines.append(
            f"| [**{repo['name']}**]({repo['html_url']}) | {description} | {format_date(repo['pushed_at'])} |"
        )
    return "\n".join(lines)


def build_summary(repos: list[dict]) -> str:
    latest = format_date(repos[0]["pushed_at"]) if repos else "—"
    return f"📦 **{len(repos)}** repositórios próprios · ⏱️ última atividade em **{latest}**"


def replace_block(text: str, tag: str, content: str) -> str:
    """Troca o conteúdo entre <!-- TAG:START --> e <!-- TAG:END -->."""
    pattern = re.compile(rf"(<!-- {tag}:START -->)(.*?)(<!-- {tag}:END -->)", re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"Marcadores {tag}:START/END não encontrados no README.")
    return pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)


def render(text: str, repos: list[dict]) -> str:
    selected = select_repos(repos)
    text = replace_block(text, "RECENT", build_recent_table(selected))
    text = replace_block(text, "SUMMARY", build_summary(selected))
    return text


def main() -> None:
    original = README.read_text(encoding="utf-8")
    updated = render(original, fetch_repos())
    if updated == original:
        print("README já está atualizado.")
        return
    README.write_text(updated, encoding="utf-8")
    print("README atualizado.")


if __name__ == "__main__":
    main()
