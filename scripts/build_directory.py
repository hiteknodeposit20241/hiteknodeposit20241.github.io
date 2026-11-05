"""Generate the site directory from sites.json and the GitHub API.

Usage: python scripts/build_directory.py <output-dir>

Each repo listed in sites.json appears under its category. A repo with a live
Pages site links to that site; any other repo links to GitHub. Public Pages
repos missing from sites.json appear under "未分类" so new sites are never lost.

Reads GITHUB_TOKEN from the environment if set, which raises the API rate limit.
Any GitHub API failure aborts the build, so the last good deployment stays live.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

OWNER = "kzhou003"
USER_SITE = f"{OWNER}.github.io"
CONFIG = Path(__file__).resolve().parents[1] / "sites.json"
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)

PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{owner} 的站点</title>
<style>
  :root {{ --bg: #fbfaf7; --fg: #24221e; --muted: #77726a; --line: #e4e0d8; --link: #1f5fa8; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #191816; --fg: #ece9e2; --muted: #9a958c; --line: #33302b; --link: #7db3ea; }}
  }}
  body {{ margin: 0; background: var(--bg); color: var(--fg);
         font: 16px/1.6 -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans SC", sans-serif; }}
  main {{ max-width: 680px; margin: 0 auto; padding: 56px 16px; }}
  h1 {{ font-size: 28px; margin: 0 0 8px; }}
  h2 {{ font-size: 18px; margin: 40px 0 10px; }}
  h2 small {{ color: var(--muted); font-size: 13px; font-weight: 400; margin-left: 8px; }}
  ul {{ list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--line); }}
  li {{ padding: 14px 0; border-bottom: 1px solid var(--line); }}
  a {{ color: var(--link); text-decoration: none; font-weight: 600; overflow-wrap: anywhere; }}
  a:hover {{ text-decoration: underline; }}
  p {{ margin: 2px 0 0; }}
  .meta {{ color: var(--muted); font-size: 13px; }}
</style>
</head>
<body>
<main>
<h1>{owner} 的站点</h1>
{sections}
</main>
</body>
</html>
"""


def public_repos():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "site-directory"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    repos, page = [], 1
    while True:
        url = f"https://api.github.com/users/{OWNER}/repos?type=owner&per_page=100&page={page}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as resp:
            batch = json.load(resp)
        repos.extend(batch)
        if len(batch) < 100:
            return {repo["name"]: repo for repo in repos}
        page += 1


def page_title(url):
    """Return the live page's <title>, or None if the site is not serving."""
    request = urllib.request.Request(url, headers={"User-Agent": "site-directory"})
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            body = resp.read(200_000).decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError):
        return None
    match = TITLE_RE.search(body)
    return html.unescape(" ".join(match.group(1).split())) if match else ""


def render_item(repo, description):
    name = repo["name"]
    url = repo["html_url"]
    title = name
    kind = "GitHub 仓库"
    if repo["has_pages"]:
        site_url = f"https://{USER_SITE}/{name}/"
        site_title = page_title(site_url)
        if site_title is not None:
            url, title, kind = site_url, site_title or name, "网站"
    item = f'<li><a href="{html.escape(url, quote=True)}">{html.escape(title)}</a>'
    if description:
        item += f"\n<p>{html.escape(description)}</p>"
    meta = f"{html.escape(name)} · {kind} · 更新于 {repo['pushed_at'][:10]}"
    return f'{item}\n<p class="meta">{meta}</p></li>'


def render_section(title, subtitle, entries):
    entries = sorted(entries, key=lambda entry: entry[0]["pushed_at"], reverse=True)
    items = "\n".join(render_item(repo, description) for repo, description in entries)
    small = f"<small>{html.escape(subtitle)}</small>" if subtitle else ""
    return f"<h2>{html.escape(title)}{small}</h2>\n<ul>\n{items}\n</ul>"


def main():
    output = Path(sys.argv[1])
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    repos = public_repos()
    placed = {USER_SITE, *config["hidden"]}
    sections = []
    count = 0

    for category in config["categories"]:
        entries = []
        for entry in category["repos"]:
            name = entry["repo"]
            placed.add(name)
            if name not in repos:
                print(f"Skipping {name}: not a public repo of {OWNER}")
                continue
            entries.append((repos[name], entry.get("description") or repos[name]["description"]))
        if entries:
            sections.append(render_section(category["title"], category.get("subtitle"), entries))
            count += len(entries)

    unsorted_repos = [
        (repo, repo["description"]) for name, repo in repos.items()
        if repo["has_pages"] and name not in placed
    ]
    if unsorted_repos:
        sections.append(render_section("未分类", "", unsorted_repos))
        count += len(unsorted_repos)

    output.mkdir(parents=True, exist_ok=True)
    page = PAGE.format(owner=OWNER, sections="\n".join(sections))
    (output / "index.html").write_text(page, encoding="utf-8")
    (output / ".nojekyll").touch()
    print(f"Listed {count} sites in {len(sections)} sections")


if __name__ == "__main__":
    main()
