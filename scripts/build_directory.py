"""Generate the knowledge-graph directory from sites.json and the GitHub API.

Usage: python scripts/build_directory.py <output-dir>

sites.json holds the regions, nodes, and hand-verified knowledge links.
site/template.html holds the page. A repo with a live Pages site links to that
site; any other repo links to GitHub. Public Pages repos missing from sites.json
go to a "未分类" region so new sites are never lost.

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
ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "sites.json"
TEMPLATE = ROOT / "site" / "template.html"
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
OTHER_REGION = {"id": "other", "title": "未分类", "subtitle": "尚未归类的站点", "color": "#8b8f9a", "colorLight": "#5f6f76"}


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


def license_of(repo, entry):
    if entry.get("license"):
        return entry["license"]
    spdx = (repo.get("license") or {}).get("spdx_id")
    return spdx if spdx and spdx != "NOASSERTION" else "未声明"


def hub_node(repo, entry, region_id):
    name = repo["name"]
    url, kind, title = repo["html_url"], "GitHub 仓库", name
    if repo["has_pages"]:
        site_url = f"https://{USER_SITE}/{name}/"
        site_title = page_title(site_url)
        if site_title is not None:
            url, kind, title = site_url, "网站", site_title or name
    return {
        "id": name,
        "title": entry.get("title") or title,
        "region": region_id,
        "hub": True,
        "url": url,
        "kind": kind,
        "description": entry.get("description") or repo["description"] or "",
        "license": license_of(repo, entry),
        "updated": repo["pushed_at"][:10],
    }


def build_graph(config, repos):
    regions, nodes = [], []
    placed = {USER_SITE, *config["hidden"]}
    for category in config["categories"]:
        count = len(nodes)
        for entry in category["repos"]:
            name = entry["repo"]
            placed.add(name)
            if name not in repos:
                print(f"Skipping {name}: not a public repo of {OWNER}")
                continue
            hub = hub_node(repos[name], entry, category["id"])
            nodes.append(hub)
            for child in entry.get("children", []):
                nodes.append({
                    **child,
                    "region": category["id"],
                    "hub": False,
                    "parent": name,
                    "kind": hub["kind"],
                    "license": hub["license"],
                    "updated": hub["updated"],
                })
        if len(nodes) > count:
            regions.append({key: category[key] for key in ("id", "title", "subtitle", "color", "colorLight")})

    unsorted_repos = [
        repo for name, repo in repos.items() if repo["has_pages"] and name not in placed
    ]
    if unsorted_repos:
        regions.append(OTHER_REGION)
        nodes.extend(hub_node(repo, {}, OTHER_REGION["id"]) for repo in unsorted_repos)

    ids = {node["id"] for node in nodes}
    links = []
    for link in config["links"]:
        if link["source"] in ids and link["target"] in ids:
            links.append(link)
        else:
            print(f"Skipping link {link['source']} -> {link['target']}: unknown node")
    return {"regions": regions, "nodes": nodes, "links": links}


def render_list(graph):
    """Render the full static index, which also serves readers without JavaScript."""
    sections = []
    for region in graph["regions"]:
        hubs = [node for node in graph["nodes"] if node["region"] == region["id"] and node["hub"]]
        hubs.sort(key=lambda node: node["updated"], reverse=True)
        items = []
        for hub in hubs:
            children = [node for node in graph["nodes"] if node.get("parent") == hub["id"]]
            child_links = "".join(
                f'<a href="{html.escape(child["url"], quote=True)}">{html.escape(child["title"])}</a>'
                for child in children
            )
            items.append(
                f'<li><a class="item-title" href="{html.escape(hub["url"], quote=True)}">{html.escape(hub["title"])}</a>'
                + (f'<p>{html.escape(hub["description"])}</p>' if hub["description"] else "")
                + (f'<div class="item-children">{child_links}</div>' if child_links else "")
                + f'<p class="item-meta">{html.escape(hub["kind"])} · {html.escape(hub["license"])}'
                + f' · 更新于 {hub["updated"]}</p></li>'
            )
        sections.append(
            f'<section><h3><span class="dot" style="--c:var(--r-{region["id"]})"></span>{html.escape(region["title"])}'
            f'<small>{html.escape(region["subtitle"])}</small></h3><ul>{"".join(items)}</ul></section>'
        )
    return "\n".join(sections)


def region_vars(regions):
    """Emit one CSS variable per region so both themes recolor the whole page."""
    dark = "".join(f'--r-{r["id"]}:{r["color"]};' for r in regions)
    light = "".join(f'--r-{r["id"]}:{r["colorLight"]};' for r in regions)
    return f':root{{{dark}}}\n  :root[data-theme="latte"]{{{light}}}'


def main():
    output = Path(sys.argv[1])
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    graph = build_graph(config, public_repos())
    author = config["author"]
    data = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    for key, value in {
        "__NAME__": html.escape(author["name"]),
        "__BIO__": html.escape(author["bio"]),
        "__AVATAR__": html.escape(author["avatar"], quote=True),
        "__GITHUB__": html.escape(author["github"], quote=True),
        "__WEBSITE__": html.escape(author["website"], quote=True),
        "__WEBSITE_LABEL__": html.escape(author["website"].removeprefix("https://")),
        "__STATS__": f'{len(graph["nodes"])} 个节点 · {len(graph["links"])} 条关联',
        "__REGION_VARS__": region_vars(graph["regions"]),
        "__LIST__": render_list(graph),
        "__DATA__": data,
    }.items():
        page = page.replace(key, value)
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(page, encoding="utf-8")
    (output / ".nojekyll").touch()
    print(f"Built {len(graph['nodes'])} nodes and {len(graph['links'])} links in {len(graph['regions'])} regions")


if __name__ == "__main__":
    main()
