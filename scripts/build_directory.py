"""Generate the knowledge-graph directory from sites.json and the GitHub API.

Usage: python scripts/build_directory.py <output-dir>

sites.json holds the regions, nodes, and hand-verified knowledge links.
site/template.html holds the page. A repo with a live Pages site links to that
site, a repo marked "readmePage" links to its README rendered on this site, and
any other repo links to GitHub. Public Pages repos missing from sites.json go to
a "未分类" region so new sites are never lost.

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

from readme_pages import write_readme_page

OWNER = "kzhou003"
USER_SITE = f"{OWNER}.github.io"
ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "sites.json"
SITE = ROOT / "site"
TEMPLATE = SITE / "template.html"
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
OTHER_REGION = {"id": "other", "title": "未分类", "subtitle": "尚未归类的站点", "color": "#8b8f9a", "colorLight": "#5f6f76"}


def github_get(path, accept="application/vnd.github+json"):
    headers = {"Accept": accept, "User-Agent": "site-directory"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as resp:
        return resp.read().decode("utf-8")


def public_repos():
    repos, page = [], 1
    while True:
        batch = json.loads(github_get(f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}"))
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
    if entry.get("readmePage") and not repo["has_pages"]:
        url, kind = f"https://{USER_SITE}/{name}/", "网站"
    elif repo["has_pages"]:
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


def shared_values(graph, author):
    """Return the placeholders that both page templates use."""
    read = lambda name: (SITE / name).read_text(encoding="utf-8")
    return {
        "__NAME__": html.escape(author["name"]),
        "__GITHUB__": html.escape(author["github"], quote=True),
        "__THEME_CSS__": read("theme.css") + region_vars(graph["regions"]),
        "__THEME_BOOT__": read("theme-boot.html"),
        "__THEME_TOGGLE__": read("theme-toggle.js"),
    }


def fill(page, values):
    for key, value in values.items():
        page = page.replace(key, value)
    return page


def write_readme_pages(config, repos, graph, shared, output):
    template = (SITE / "readme.html").read_text(encoding="utf-8")
    nodes = {node["id"]: node for node in graph["nodes"]}
    regions = {region["id"]: region for region in graph["regions"]}
    count = 0
    for category in config["categories"]:
        for entry in category["repos"]:
            repo = repos.get(entry["repo"])
            if entry.get("readmePage") and repo and not repo["has_pages"]:
                node = nodes[repo["name"]]
                path = f"/repos/{OWNER}/{repo['name']}/readme"
                rendered = github_get(path, "application/vnd.github.html+json")
                markdown = github_get(path, "application/vnd.github.raw")
                page = fill(template, shared)
                write_readme_page(page, rendered, markdown, repo, node, regions[node["region"]], output)
                count += 1
    return count


def main():
    output = Path(sys.argv[1])
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    repos = public_repos()
    graph = build_graph(config, repos)
    author = config["author"]
    shared = shared_values(graph, author)
    data = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    page = fill(page, shared)
    for key, value in {
        "__BIO__": html.escape(author["bio"]),
        "__AVATAR__": html.escape(author["avatar"], quote=True),
        "__WEBSITE__": html.escape(author["website"], quote=True),
        "__WEBSITE_LABEL__": html.escape(author["website"].removeprefix("https://")),
        "__STATS__": f'{len(graph["nodes"])} 个节点 · {len(graph["links"])} 条关联',
        "__LIST__": render_list(graph),
        "__DATA__": data,
    }.items():
        page = page.replace(key, value)
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(page, encoding="utf-8")
    (output / ".nojekyll").touch()
    readme_count = write_readme_pages(config, repos, graph, shared, output)
    print(f"Built {len(graph['nodes'])} nodes, {len(graph['links'])} links, {readme_count} README pages")


if __name__ == "__main__":
    main()
