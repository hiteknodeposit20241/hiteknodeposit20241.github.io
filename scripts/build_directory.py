"""Generate a directory page of every public GitHub Pages site owned by OWNER.

Usage: python scripts/build_directory.py <output-dir>

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
EXCLUDE = set()  # repo names to hide from the directory
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
  h1 {{ font-size: 28px; margin: 0 0 32px; }}
  ul {{ list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--line); }}
  li {{ padding: 14px 0; border-bottom: 1px solid var(--line); }}
  a {{ color: var(--link); text-decoration: none; font-weight: 600; }}
  a:hover {{ text-decoration: underline; }}
  p {{ margin: 2px 0 0; }}
  .meta {{ color: var(--muted); font-size: 13px; }}
</style>
</head>
<body>
<main>
<h1>{owner} 的站点</h1>
<ul>
{items}
</ul>
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
            return repos
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


def main():
    output = Path(sys.argv[1])
    sites = [
        repo for repo in public_repos()
        if repo["has_pages"] and repo["name"] != USER_SITE and repo["name"] not in EXCLUDE
    ]
    sites.sort(key=lambda repo: repo["pushed_at"], reverse=True)

    items = []
    for repo in sites:
        url = f"https://{USER_SITE}/{repo['name']}/"
        title = page_title(url)
        if title is None:
            print(f"Skipping {repo['name']}: {url} is not reachable")
            continue
        description = repo["description"] or ""
        items.append(
            f'<li><a href="{html.escape(url, quote=True)}">{html.escape(title or repo["name"])}</a>'
            + (f"\n<p>{html.escape(description)}</p>" if description else "")
            + f'\n<p class="meta">{html.escape(repo["name"])} · 更新于 {repo["pushed_at"][:10]}</p></li>'
        )

    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(PAGE.format(owner=OWNER, items="\n".join(items)), encoding="utf-8")
    (output / ".nojekyll").touch()
    print(f"Listed {len(items)} sites")


if __name__ == "__main__":
    main()
