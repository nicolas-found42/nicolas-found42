#!/usr/bin/env python3
import json
import os
import re
import urllib.request
from pathlib import Path

OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "nicolas-found42")
PROFILE_REPO = OWNER
README_PATH = Path(__file__).resolve().parent.parent / "README.md"

DESC_OVERRIDES = {
    "society": "deterministic living-village simulation in rust",
    "logo-maker": "judged 3d logo pipeline in python + blender cycles (no ai image gen)",
    "sl-remastered": "street legal racing: redline for apple silicon (c++ / sdl3)",
}


def fetch_public_repos(owner: str) -> list[dict]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-updater",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{owner}/repos?type=owner&per_page=100&sort=pushed&page={page}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            batch = json.loads(resp.read().decode("utf-8"))
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return [r for r in repos if not r.get("private") and r.get("name") != PROFILE_REPO]


def fmt_desc(repo: dict) -> str:
    name = repo["name"]
    raw = DESC_OVERRIDES.get(name) or (repo.get("description") or "").strip()
    if not raw:
        return ""
    return f" — {raw[0].lower() + raw[1:]}" if len(raw) > 1 else f" — {raw.lower()}"


def render_recent(repos: list[dict], limit: int = 5) -> str:
    top = sorted(repos, key=lambda r: r.get("pushed_at") or "", reverse=True)[:limit]
    return "\n".join(
        f"- [{r['name']}]({r['html_url']}){fmt_desc(r)}" for r in top
    )


def render_starred(repos: list[dict]) -> str:
    starred = sorted(
        [r for r in repos if (r.get("stargazers_count") or 0) > 0],
        key=lambda r: (-r["stargazers_count"], r["name"].lower()),
    )
    return "\n".join(
        f"- [{r['name']}]({r['html_url']}) ({r['stargazers_count']}★){fmt_desc(r)}"
        for r in starred
    )


def replace_block(text: str, marker: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- {marker}:START -->\n)(.*?)(\n<!-- {marker}:END -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise RuntimeError(f"Missing markers for {marker}")
    return pattern.sub(rf"\g<1>{body}\g<3>", text, count=1)


def main() -> None:
    repos = fetch_public_repos(OWNER)
    text = README_PATH.read_text(encoding="utf-8")
    text = replace_block(text, "RECENT", render_recent(repos))
    text = replace_block(text, "STARRED", render_starred(repos))
    README_PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
